import streamlit as st
import time
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Sayısal Tahmin Yarışması", layout="centered")

# --- 1. GLOBAL HAFIZA ---
@st.cache_resource
def global_veri_getir():
    return {
        "sorular": [],
        "oyuncular": {},       
        "durum": "hazirlik",   
        "aktif_soru_index": 0,
        "soru_baslama_zamani": 0.0,
        "gecis_kilitli_mi": False # Birden fazla kişinin aynı anda süreyi bitirmesini engeller
    }

db = global_veri_getir()

if "benim_adim" not in st.session_state:
    st.session_state.benim_adim = None

# --- 2. OTOMATİK YENİLEME ---
# Sadece yarışma esnasında saniyede 1 kez sayfa yenilenir ki sayaç geriye aksın
if db["durum"] == "basladi":
    st_autorefresh(interval=1000, key="sayac_yenileyici")


# --- 3. EKRANLAR ---

# A) YÖNETİCİ / SORU EKLEME EKRANI
if db["durum"] == "hazirlik":
    st.title("⚙️ Yönetici Paneli")
    st.info("Soruları ve süreleri ekleyin. Rakam bazlı tahmin yarışması başlıyor!")
    
    with st.form("soru_ekle"):
        soru = st.text_input("Soru Metni")
        cevap = st.number_input("Doğru Cevap (Sayısal)", value=0.0, step=1.0)
        sure = st.number_input("Bu Soru İçin Süre (Saniye)", min_value=5, max_value=120, value=20)
        
        ekle = st.form_submit_button("Soruyu Ekle")
        if ekle and soru:
            db["sorular"].append({"soru": soru, "cevap": float(cevap), "sure": int(sure)})
            st.success(f"Soru eklendi! Toplam: {len(db['sorular'])}")
            
    if len(db["sorular"]) > 0:
        if st.button("🚀 Yarışmayı Herkes İçin Başlat", type="primary"):
            db["durum"] = "basladi"
            db["aktif_soru_index"] = 0
            db["soru_baslama_zamani"] = time.time() # İlk sorunun süresini başlat
            db["gecis_kilitli_mi"] = False
            st.rerun()


# B) YARIŞMA EKRANI
elif db["durum"] == "basladi":
    
    # Adım 1: Kullanıcı Girişi
    if not st.session_state.benim_adim:
        st.title("Yarışmaya Katıl!")
        isim = st.text_input("Görünecek Adınız:")
        if st.button("Oyuna Gir"):
            if isim:
                st.session_state.benim_adim = isim
                if isim not in db["oyuncular"]:
                    db["oyuncular"][isim] = {"skor": 0.0, "son_cevap": None}
                st.rerun()
                
    # Adım 2: Canlı Soru ve Sayaç Ekranı
    else:
        idx = db["aktif_soru_index"]
        
        # Eğer sorular bittiyse oyun sonu ekranına geç
        if idx >= len(db["sorular"]):
            db["durum"] = "bitti"
            st.rerun()
            
        aktif_soru = db["sorular"][idx]
        benim_bilgim = db["oyuncular"][st.session_state.benim_adim]
        
        # Süre hesaplama mantığı
        gecen_zaman = time.time() - db["soru_baslama_zamani"]
        kalan_sure = max(0, int(aktif_soru["sure"] - gecen_zaman))
        
        # EĞER SÜRE BİTTİYSE (Otomatik Geçiş ve Puanlama)
        if kalan_sure == 0:
            st.warning("⏰ Süre Doldu! Puanlar hesaplanıyor...")
            
            # Bu bloğun sadece 1 kez çalışması için kilit mekanizması
            if not db["gecis_kilitli_mi"]:
                db["gecis_kilitli_mi"] = True
                
                dogru_cevap = aktif_soru["cevap"]
                
                # Herkesin puanını hesapla
                for oyuncu_adi, veri in db["oyuncular"].items():
                    tahmin = veri["son_cevap"]
                    if tahmin is not None:
                        if dogru_cevap != 0:
                            # Hata payını yüzdelik olarak hesapla
                            hata_orani = abs(tahmin - dogru_cevap) / abs(dogru_cevap)
                            kazanilan_puan = max(0.0, 100.0 - (hata_orani * 100.0))
                        else:
                            # Eğer cevap tam olarak 0 ise (örn: pH değeri 0 olan bir şey sorulursa)
                            kazanilan_puan = 100.0 if tahmin == 0 else 0.0
                            
                        db["oyuncular"][oyuncu_adi]["skor"] += kazanilan_puan
                        
                    # Bir sonraki soru için cevabı sıfırla
                    db["oyuncular"][oyuncu_adi]["son_cevap"] = None
                
                # Sonraki Soruya Geçiş Değerlerini Güncelle
                db["aktif_soru_index"] += 1
                db["soru_baslama_zamani"] = time.time()
                db["gecis_kilitli_mi"] = False
                st.rerun()
                
        # EĞER SÜRE DEVAM EDİYORSA
        else:
            st.header(f"Soru {idx + 1}")
            st.subheader(aktif_soru["soru"])
            
            # Canlı İlerleme Çubuğu ve Sayaç
            st.metric("⏳ Kalan Süre", f"{kalan_sure} saniye")
            st.progress(kalan_sure / aktif_soru["sure"])
            
            # Cevap girme alanı
            if benim_bilgim["son_cevap"] is None:
                with st.form(f"cevap_formu_{idx}"):
                    st.info("Lütfen sadece rakam kullanarak tahmininizi girin.")
                    tahmin = st.number_input("Tahmininiz:", value=0.0, step=1.0)
                    gonder = st.form_submit_button("Cevabı Gönder")
                    
                    if gonder:
                        db["oyuncular"][st.session_state.benim_adim]["son_cevap"] = float(tahmin)
                        st.rerun()
            else:
                st.success(f"Tahmininiz ({benim_bilgim['son_cevap']}) başarıyla alındı! Herkesin süresinin dolması bekleniyor...")


# C) BİTİŞ VE SKOR TABLOSU
elif db["durum"] == "bitti":
    st.balloons()
    st.title("🏆 Yarışma Sona Erdi!")
    
    # Skoru yüksekten düşüğe doğru listeleme
    skor_listesi = [{"Oyuncu": k, "Toplam Puan": round(v["skor"], 2)} for k, v in db["oyuncular"].items()]
    if skor_listesi:
        skor_listesi.sort(key=lambda x: x["Toplam Puan"], reverse=True)
        st.table(skor_listesi)
