import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Canlı Quiz", layout="centered")

# --- 1. GLOBAL HAFIZA (GEÇİCİ VERİTABANI) ---
@st.cache_resource
def global_veri_getir():
    return {
        "sorular": [],
        "oyuncular": {},       
        "durum": "hazirlik",   
        "aktif_soru_index": 0
    }

db = global_veri_getir()

if "benim_adim" not in st.session_state:
    st.session_state.benim_adim = None

# --- 2. OTOMATİK YENİLEME MANTIĞI (HİLE KISMI) ---
# Eğer kullanıcı giriş yapmışsa ve mevcut soruyu cevapladıysa 
# VEYA yarışma henüz başlamadıysa arka planda her 2 saniyede bir sayfayı yenile!
otomatik_yenile = False

if db["durum"] == "hazirlik":
    otomatik_yenile = True
elif db["durum"] == "basladi" and st.session_state.benim_adim:
    benim_bilgim = db["oyuncular"].get(st.session_state.benim_adim, {})
    if benim_bilgim.get("cevapladi_mi", False) == True:
        otomatik_yenile = True

if otomatik_yenile:
    # 2000 milisaniye (2 saniye) aralıklarla sessizce sayfayı yeniler
    st_autorefresh(interval=2000, key="bekleme_yenileyici")


# --- 3. EKRAN YÖNLENDİRMELERİ ---

# A) HAZIRLIK EKRANI (Sunucu Görür)
if db["durum"] == "hazirlik":
    st.title("⚙️ Yarışma Kurulumu")
    st.info("Bu ekranı katılımcılar görmüyor. Soruları ekledikten sonra yarışmayı başlatın.")
    
    with st.form("soru_ekle"):
        soru = st.text_input("Soru Metni")
        cevap = st.selectbox("Doğru Seçenek", ["A", "B", "C", "D"])
        ekle = st.form_submit_button("Soruyu Ekle")
        if ekle and soru:
            db["sorular"].append({"soru": soru, "cevap": cevap})
            st.success(f"Soru eklendi! Toplam soru: {len(db['sorular'])}")
            
    if len(db["sorular"]) > 0:
        if st.button("🚀 Yarışmayı Herkes İçin Başlat", type="primary"):
            db["durum"] = "basladi"
            st.rerun()

# B) YARIŞMA EKRANI
elif db["durum"] == "basladi":
    
    # Adım 1: İsim Alma
    if not st.session_state.benim_adim:
        st.title("Yarışmaya Katıl!")
        isim = st.text_input("Görünecek Adınız:")
        if st.button("Oyuna Gir"):
            if isim:
                st.session_state.benim_adim = isim
                if isim not in db["oyuncular"]:
                    db["oyuncular"][isim] = {"skor": 0, "cevapladi_mi": False}
                st.rerun()
                
    # Adım 2: Soru Ekranı
    else:
        idx = db["aktif_soru_index"]
        
        if idx >= len(db["sorular"]):
            db["durum"] = "bitti"
            st.rerun()
            
        aktif_soru = db["sorular"][idx]
        benim_bilgim = db["oyuncular"][st.session_state.benim_adim]
        
        st.header(f"Soru {idx + 1}")
        st.write(aktif_soru["soru"])
        
        if not benim_bilgim["cevapladi_mi"]:
            st.write("Cevabınızı seçin:")
            col1, col2, col3, col4 = st.columns(4)
            
            def cevap_kontrol(secim):
                db["oyuncular"][st.session_state.benim_adim]["cevapladi_mi"] = True
                if secim == aktif_soru["cevap"]:
                    db["oyuncular"][st.session_state.benim_adim]["skor"] += 10
            
            with col1:
                if st.button("A", use_container_width=True): cevap_kontrol("A"); st.rerun()
            with col2:
                if st.button("B", use_container_width=True): cevap_kontrol("B"); st.rerun()
            with col3:
                if st.button("C", use_container_width=True): cevap_kontrol("C"); st.rerun()
            with col4:
                if st.button("D", use_container_width=True): cevap_kontrol("D"); st.rerun()
        else:
            st.success("Cevabınız alındı!")
            with st.spinner("Sunucunun diğer soruya geçmesi bekleniyor..."):
                pass # st_autorefresh burada devreye girip sayfayı 2 saniyede bir güncelliyor.
        
        st.markdown("---")
        # SUNUCU KONTROLLERİ (Sadece Yönetici)
        with st.expander("👑 Sunucu Kontrolleri (Sadece Yönetici)"):
            if st.button("Sonraki Soruya Geç Herkes İçin"):
                db["aktif_soru_index"] += 1
                for oyuncu in db["oyuncular"]:
                    db["oyuncular"][oyuncu]["cevapladi_mi"] = False
                st.rerun()

# C) BİTİŞ EKRANI
elif db["durum"] == "bitti":
    st.balloons()
    st.title("🏆 Yarışma Bitti!")
    
    skor_listesi = [{"Oyuncu": k, "Puan": v["skor"]} for k, v in db["oyuncular"].items()]
    if skor_listesi:
        skor_listesi.sort(key=lambda x: x["Puan"], reverse=True)
        st.table(skor_listesi)