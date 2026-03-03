import streamlit as st
import time
from streamlit_autorefresh import st_autorefresh
import pandas as pd

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Sayısal Tahmin Yarışması", layout="centered")

# --- SABİT LOGO YERLEŞİMİ (SAĞ ÜST KÖŞE) ---
# Ekranı 2 sütuna bölüyoruz. Sol taraf çok geniş (4 birim), sağ taraf dar (1 birim)
# Böylece logo otomatik olarak sağ üst köşeye itilmiş olacak.
col_bosluk, col_logo = st.columns([4, 1])
with col_logo:
    try:
        # Görselin adını kendi dosya adınıza göre değiştirin (örn: logo.jpg)
        st.image("image_4843bd.jpg", use_column_width=True)
    except FileNotFoundError:
        pass # Dosya yoksa hata mesajı verip çirkin görünmemesi için sessizce geç
st.markdown("---")


# --- 1. GLOBAL HAFIZA (Tüm cihazlar için ortak) ---
@st.cache_resource
def global_veri_getir():
    return {
        "sorular": [],
        "oyuncular": {},       
        "durum": "hazirlik",   
        "aktif_soru_index": 0,
        "soru_baslama_zamani": 0.0,
        "gecis_kilitli_mi": False 
    }

db = global_veri_getir()

if "benim_adim" not in st.session_state:
    st.session_state.benim_adim = None


# --- 2. OTOMATİK YENİLEME MANTIĞI ---
if db["durum"] == "basladi":
    st_autorefresh(interval=1000, key="sayac_yenileyici")


# --- 3. EKRANLAR VE YÖNLENDİRMELER ---

# A) YÖNETİCİ / SORU EKLEME EKRANI
if db["durum"] == "hazirlik":
    st.title("⚙️ Yönetici Paneli")
    st.info("Soruları, doğru cevapları (sayısal) ve süreleri ekleyin. Rakam bazlı tahmin yarışması başlıyor!")
    
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
        if st.button("🚀 Yarışmayı Herkes İçin Başlat", type="primary"):
            db["durum"] = "basladi"
            db["aktif_soru_index"] = 0
            db["soru_baslama_zamani"] = time.time()
            db["gecis_kilitli_mi"] = False
            st.rerun()


# B) YARIŞMA EKRANI
elif db["durum"] == "basladi":
    
    # 1. Adım: Kullanıcı Girişi
    if not st.session_state.benim_adim:
        st.title("Yarışmaya Katıl!")
        st.write("Cevaplarınız sayısal tahmin şeklinde olmalı.")
        isim = st.text_input("Görünecek Adınız:")
        if st.button("Oyuna Gir"):
            if isim:
                st.session_state.benim_adim = isim
                if isim not in db["oyuncular"]:
                    db["oyuncular"][isim] = {"skor": 0.0, "son_cevap": None}
                st.rerun()
            else:
                st.warning("Lütfen bir isim girin.")
                
    # 2. Adım: Soru Ekranı
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
                st.write("Herkesin süresinin dolması bekleniyor...")


# C) BİTİŞ VE SKOR TABLOSU
elif db["durum"] == "bitti":
    st.balloons()
    st.title("🏆 Yarışma Sona Erdi!")
    
    skor_listesi = [{"Oyuncu": k, "Toplam Puan": v["skor"]} for k, v in db["oyuncular"].items()]
    
    if skor_listesi:
        st.write("Tüm soruları tamamladınız. İşte final puanları:")
        
        # Tabloyu oluştur ve en yüksek puanlıyı üste al
        df_skor = pd.DataFrame(skor_listesi)
        df_skor = df_skor.sort_values(by='Toplam Puan', ascending=False).reset_index(drop=True)
        
        # Puanları tablodaki görünümleri için tam 2 virgüllü string formata dönüştür (örn: 75.00)
        df_skor['Toplam Puan'] = df_skor['Toplam Puan'].map('{:.2f}'.format)
        
        st.table(df_skor)
    else:
        st.write("Kimse puan alamadı :(")
