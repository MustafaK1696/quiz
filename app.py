import streamlit as st
import time
from streamlit_autorefresh import st_autorefresh
import pandas as pd

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Sayısal Tahmin Yarışması", layout="centered")

# --- SABİT LOGO YERLEŞİMİ (SAĞ ÜST KÖŞE) ---
col_bosluk, col_logo = st.columns([4, 1])
with col_logo:
    try:
        # Fotoğrafınızın tam adını buraya yazın
        st.image("image_4843bd.jpg", use_column_width=True)
    except FileNotFoundError:
        pass 
st.markdown("---")


# --- 1. GLOBAL HAFIZA (Tüm cihazlar için ortak) ---
@st.cache_resource
def global_veri_getir():
    return {
        "sorular": [],
        "oyuncular": {},       
        "durum": "hazirlik",   # YENİ AKIŞ: hazirlik -> lobi -> basladi -> bitti
        "aktif_soru_index": 0,
        "soru_baslama_zamani": 0.0,
        "gecis_kilitli_mi": False 
    }

db = global_veri_getir()

if "benim_adim" not in st.session_state:
    st.session_state.benim_adim = None


# --- 2. OTOMATİK YENİLEME MANTIĞI ---
# Sayfa hem lobide beklerken hem de yarışma sırasında saniyede bir güncellenir
if db["durum"] in ["lobi", "basladi"]:
    st_autorefresh(interval=1000, key="sayac_yenileyici")


# --- 3. EKRANLAR VE YÖNLENDİRMELER ---

# A) YÖNETİCİ / SORU EKLEME EKRANI
if db["durum"] == "hazirlik":
    st.title("⚙️ Yönetici Paneli")
    st.info("Soruları ekleyin. Hazır olduğunuzda lobi ekranına geçeceğiz.")
    
    with st.form("soru_ekle"):
        soru_metni = st.text_input("Soru Metni")
        dogru_cevap = st.number_input("Doğru Cevap (Sayısal Değer)", value=0.0, step=1.0)
        sure_siniri = st.number_input("Bu Soru İçin Süre (Saniye)", min_value=5, max_value=120, value=20)
        
        ekle = st.form_submit_button("Soruyu Ekle")
        if ekle and soru_metni:
            db["sorular"].append({
                "soru": soru_metni, 
                "cevap": float(dogru_cevap), 
                "sure": int(sure_siniri)
            })
            st.success(f"Soru başarıyla eklendi! Toplam soru: {len(db['sorular'])}")
            
    if len(db["sorular"]) > 0:
        if st.button("👥 Katılımcı Alımını Başlat (Lobi)", type="primary"):
            db["durum"] = "lobi" # Süreyi başlatmıyoruz, sadece lobiye geçiyoruz
            st.rerun()


# B) LOBİ (BEKLEME ODASI) EKRANI
elif db["durum"] == "lobi":
    st.title("⏳ Yarışma Başlamak Üzere!")
    
    # 1. Aşama: Kullanıcı İsim Girer (Süre Kaygısı Yok)
    if not st.session_state.benim_adim:
        st.write("Lütfen yarışmada görünecek adınızı girin.")
        isim = st.text_input("Adınız:")
        if st.button("Oyuna Bağlan"):
            if isim:
                st.session_state.benim_adim = isim
                if isim not in db["oyuncular"]:
                    db["oyuncular"][isim] = {"skor": 0.0, "son_cevap": None}
                st.rerun()
            else:
                st.warning("Lütfen bir isim girin.")
    else:
        st.success(f"Bağlandınız, {st.session_state.benim_adim}! Sunucunun yarışmayı başlatması bekleniyor...")
    
    st.markdown("---")
    
    # Sunucu oyunu buradan fiilen başlatır (Süre buradan itibaren işler)
    with st.expander("👑 Sunucu Kontrolleri (Sadece Yönetici)"):
        st.write(f"**Bağlanan Oyuncular ({len(db['oyuncular'])} kişi):**")
        st.write(", ".join(list(db["oyuncular"].keys())))
        
        if st.button("🚀 İlk Soruyu Başlat ve Süreyi Başlat", type="primary"):
            db["durum"] = "basladi"
            db["aktif_soru_index"] = 0
            db["soru_baslama_zamani"] = time.time() # SÜRE TAM OLARAK BURADA BAŞLAR!
            db["gecis_kilitli_mi"] = False
            st.rerun()


# C) YARIŞMA EKRANI
elif db["durum"] == "basladi":
    
    # Eğer lobiyi kaçırıp sonradan giren olursa diye hızlı isim alma
    if not st.session_state.benim_adim:
        st.warning("Yarışma başladı! Hızlıca isminizi girip katılın.")
        isim = st.text_input("Adınız:")
        if st.button("Oyuna Dal"):
            if isim:
                st.session_state.benim_adim = isim
                if isim not in db["oyuncular"]:
                    db["oyuncular"][isim] = {"skor": 0.0, "son_cevap": None}
                st.rerun()
    
    # Normal Soru Akışı
    else:
        idx = db["aktif_soru_index"]
        
        if idx >= len(db["sorular"]):
            db["durum"] = "bitti"
            st.rerun()
            
        aktif_soru = db["sorular"][idx]
        benim_bilgim = db["oyuncular"][st.session_state.benim_adim]
        
        gecen_zaman = time.time() - db["soru_baslama_zamani"]
        kalan_sure = max(0, int(aktif_soru["sure"] - gecen_zaman))
        
        # SÜRE BİTTİĞİNDE
        if kalan_sure == 0:
            st.warning("⏰ Süre Doldu! Puanlar hesaplanıyor...")
            
            if not db["gecis_kilitli_mi"]:
                db["gecis_kilitli_mi"] = True
                
                dogru_cevap = aktif_soru["cevap"]
                
                for oyuncu_adi, veri in db["oyuncular"].items():
                    tahmin = veri["son_cevap"]
                    if tahmin is not None:
                        if dogru_cevap != 0:
                            hata_orani = abs(tahmin - dogru_cevap) / abs(dogru_cevap)
                            raw_puan = max(0.0, 100.0 - (hata_orani * 100.0))
                            kazanilan_puan = round(raw_puan, 2)
                        else:
                            kazanilan_puan = 100.0 if tahmin == 0 else 0.0
                            
                        db["oyuncular"][oyuncu_adi]["skor"] += kazanilan_puan
                        
                    db["oyuncular"][oyuncu_adi]["son_cevap"] = None
                
                db["aktif_soru_index"] += 1
                db["soru_baslama_zamani"] = time.time()
                db["gecis_kilitli_mi"] = False
                st.rerun()
                
        # SÜRE DEVAM EDERKEN
        else:
            st.header(f"Soru {idx + 1}")
            st.subheader(aktif_soru["soru"])
            
            col1, col2 = st.columns([1, 4])
            with col1:
                st.metric("⏳ Kalan Süre", f"{kalan_sure} sn")
            with col2:
                st.progress(kalan_sure / aktif_soru["sure"])
            
            st.markdown("---")
            
            if benim_bilgim["son_cevap"] is None:
                with st.form(f"cevap_formu_{idx}"):
                    st.info("Lütfen sadece rakam kullanarak tahmininizi girin.")
                    tahmin = st.number_input("Tahmininiz:", value=0.0, step=1.0)
                    gonder = st.form_submit_button("Cevabı Gönder")
                    
                    if gonder:
                        db["oyuncular"][st.session_state.benim_adim]["son_cevap"] = float(tahmin)
                        st.rerun()
            else:
                st.success(f"Tahmininiz ({benim_bilgim['son_cevap']}) başarıyla alındı!")
                st.write("Diğer yarışmacıların süresinin dolması bekleniyor...")


# D) BİTİŞ VE SKOR TABLOSU
elif db["durum"] == "bitti":
    st.balloons()
    st.title("🏆 Yarışma Sona Erdi!")
    
    skor_listesi = [{"Oyuncu": k, "Toplam Puan": v["skor"]} for k, v in db["oyuncular"].items()]
    
    if skor_listesi:
        st.write("Tüm soruları tamamladınız. İşte final puanları:")
        
        df_skor = pd.DataFrame(skor_listesi)
        df_skor = df_skor.sort_values(by='Toplam Puan', ascending=False).reset_index(drop=True)
        df_skor['Toplam Puan'] = df_skor['Toplam Puan'].map('{:.2f}'.format)
        
        # hide_index=True parametresi sol taraftaki rahatsız edici "0, 1, 2" rakamlarını tamamen kaldırır!
        st.dataframe(df_skor, hide_index=True, use_container_width=True)
    else:
        st.write("Kimse puan alamadı :(")
