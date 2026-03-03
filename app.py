import streamlit as st
import time
from streamlit_autorefresh import st_autorefresh
import pandas as pd

# --- Sayfa Ayarları ---
st.set_page_config(page_title="Sayısal Tahmin Yarışması", layout="centered")

# --- LOGO EKLEME ---
# Logoyu yan menünün (sidebar) en üstüne, ortalama bir boyutta ekle
try:
    # 'image_0.png' dosyasının uygulama ile aynı klasörde olduğunu varsayıyorum
    # Genişliği 150 piksel olarak ayarladım, 'ortalama' bir boyuttur.
    st.sidebar.image("image_0.png", width=150, use_column_width=False)
except FileNotFoundError:
    # Dosya yoksa bir uyarı göster (veya hiçbir şey yapma)
    st.sidebar.warning("Logo dosyası (image_0.png) bulunamadı. Lütfen dosyanın doğru yerde olduğundan emin olun.")
st.sidebar.markdown("---")


# --- 1. GLOBAL HAFIZA (Tüm cihazlar için ortak) ---
@st.cache_resource
def global_veri_getir():
    return {
        "sorular": [],
        "oyuncular": {},       # Format: {"Ali": {"skor": 0.0, "son_cevap": None}}
        "durum": "hazirlik",   # hazirlik, basladi, bitti
        "aktif_soru_index": 0,
        "soru_baslama_zamani": 0.0,
        "gecis_kilitli_mi": False # Birden fazla kişinin aynı anda süreyi bitirmesini engeller
    }

db = global_veri_getir()

# Kendi cihazımdaki (lokal) adımım
if "benim_adim" not in st.session_state:
    st.session_state.benim_adim = None


# --- 2. OTOMATİK YENİLEME MANTIĞI ---
# Saniye bazlı sayaç ve otomatik geçiş için sayfa her saniye yenilenir
if db["durum"] == "basladi":
    st_autorefresh(interval=1000, key="sayac_yenileyici")


# --- 3. EKRANLAR VE YÖNLENDİRMELER ---

# A) YÖNETİCİ / SORU EKLEME EKRANI (Sunucu Görür)
if db["durum"] == "hazirlik":
    st.title("⚙️ Yönetici Paneli")
    st.info("Soruları, doğru cevapları (sayısal) ve süreleri ekleyin. Rakam bazlı tahmin yarışması başlıyor!")
    
    with st.form("soru_ekle"):
        soru_metni = st.text_input("Soru Metni")
        # Doğru cevap artık çoktan seçmeli değil, sayısal
        dogru_cevap = st.number_input("Doğru Cevap (Sayısal Değer)", value=0.0, step=1.0)
        # Her soru için ayrı bir süre sınırı
        sure_siniri = st.number_input("Bu Soru İçin Süre (Saniye)", min_value=5, max_value=120, value=20)
        
        ekle = st.form_submit_button("Soruyu Ekle")
        if ekle and soru_metni:
            # Soruyu, cevabını ve süresini kaydet
            db["sorular"].append({
                "soru": soru_metni, 
                "cevap": float(dogru_cevap), # Puan hesaplamak için float'a çeviriyoruz
                "sure": int(sure_siniri)
            })
            st.success(f"Soru başarıyla eklendi! Toplam soru: {len(db['sorular'])}")
            
    if len(db["sorular"]) > 0:
        if st.button("🚀 Yarışmayı Herkes İçin Başlat", type="primary"):
            db["durum"] = "basladi"
            db["aktif_soru_index"] = 0
            db["soru_baslama_zamani"] = time.time() # İlk sorunun süresini başlat
            db["gecis_kilitli_mi"] = False
            st.rerun()


# B) YARIŞMA EKRANI (Katılımcılar ve Sunucu Görür)
elif db["durum"] == "basladi":
    
    # 1. Adım: Kullanıcı Girişi (Anonim İsim)
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
                
    # 2. Adım: Soru Ekranı ve Canlı Sayaç
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
        
        # --- EĞER SÜRE BİTTİYSE (Otomatik Geçiş) ---
        if kalan_sure == 0:
            st.warning("⏰ Süre Doldu! Puanlar hesaplanıyor...")
            
            # Bu bloğun sadece 1 kez çalışması için kilit mekanizması
            # Birden fazla katılımcı aynı anda süre biterken puan hesaplamasını bozmasın
            if not db["gecis_kilitli_mi"]:
                db["gecis_kilitli_mi"] = True
                
                dogru_cevap = aktif_soru["cevap"]
                
                # Herkesin puanını hesapla (Yakınlığa göre yüzdelik puanlama)
                for oyuncu_adi, veri in db["oyuncular"].items():
                    tahmin = veri["son_cevap"]
                    if tahmin is not None:
                        # Puan formülü: 100 - (Hata Payı Yüzdesi)
                        if dogru_cevap != 0:
                            # Hata payını yüzdelik olarak hesapla (örn: %25 hata -> 0.25)
                            hata_orani = abs(tahmin - dogru_cevap) / abs(dogru_cevap)
                            
                            # Değişiklik: Her sorudan alınan puanı hesapla ve hemen 2 basamağa yuvarla
                            raw_puan = max(0.0, 100.0 - (hata_orani * 100.0))
                            kazanilan_puan = round(raw_puan, 2)
                        else:
                            # Eğer cevap tam olarak 0 ise (örn: pH değeri 0 olan bir şey sorulursa)
                            kazanilan_puan = 100.0 if tahmin == 0 else 0.0
                            # Burası da yuvarlanabilir ama 100.0 veya 0.0 zaten tam
                            # kazanilan_puan = round(kazanilan_puan, 2)
                            
                        # Skoru güncelle
                        db["oyuncular"][oyuncu_adi]["skor"] += kazanilan_puan
                        
                    # Bir sonraki soru için cevabı sıfırla
                    db["oyuncular"][oyuncu_adi]["son_cevap"] = None
                
                # Sonraki Soruya Geçiş Değerlerini Güncelle
                db["aktif_soru_index"] += 1
                db["soru_baslama_zamani"] = time.time() # Yeni sorunun süresini başlat
                db["gecis_kilitli_mi"] = False
                st.rerun()
                
        # --- EĞER SÜRE DEVAM EDİYORSA ---
        else:
            st.header(f"Soru {idx + 1}")
            st.subheader(aktif_soru["soru"])
            
            # Canlı İlerleme Çubuğu ve Sayaç
            # st.metric("⏳ Kalan Süre", f"{kalan_sure} saniye")
            col1, col2 = st.columns([1, 4])
            with col1:
                st.metric("⏳ Kalan Süre", f"{kalan_sure} sn")
            with col2:
                # İlerleme çubuğunu kalan süreye göre görselleştir
                st.progress(kalan_sure / aktif_soru["sure"])
            
            st.markdown("---")
            
            # Cevap girme alanı
            if benim_bilgim["son_cevap"] is None:
                with st.form(f"cevap_formu_{idx}"):
                    st.info("Lütfen sadece rakam kullanarak tahmininizi girin.")
                    # Çoktan seçmeli yerine sayısal input
                    tahmin = st.number_input("Tahmininiz (Örn: 15.5):", value=0.0, step=1.0)
                    gonder = st.form_submit_button("Cevabı Gönder")
                    
                    if gonder:
                        db["oyuncular"][st.session_state.benim_adim]["son_cevap"] = float(tahmin)
                        st.rerun() # Hemen yenile ki 'Cevabınız alındı' mesajı çıksın
            else:
                st.success(f"Tahmininiz ({benim_bilgim['son_cevap']}) başarıyla alındı!")
                st.write("Herkesin süresinin dolması bekleniyor...")


# C) BİTİŞ VE SKOR TABLOSU
elif db["durum"] == "bitti":
    st.balloons()
    st.title("🏆 Yarışma Sona Erdi!")
    
    # Skorları yüksekten düşüğe doğru listeleme
    # Puanlar zaten hesaplama anında yuvarlanmıştı, 
    # ama toplam skor yine de küsuratlı olabilir (örn: 75.50 + 80.25 = 155.75)
    # Skor tablosunda temiz durması için tekrar round(v["skor"], 2) yapıyorum
    skor_listesi = [{"Oyuncu": k, "Toplam Puan": round(v["skor"], 2)} for k, v in db["oyuncular"].items()]
    
    if skor_listesi:
        st.write("Tüm soruları tamamladınız. İşte final puanları:")
        # DataFrame oluştur ve puanı en yüksek olanı en üste al
        df_skor = pd.DataFrame(skor_listesi)
        df_skor = df_skor.sort_values(by='Toplam Puan', ascending=False).reset_index(drop=True)
        # Tabloyu göster
        st.table(df_skor)
    else:
        st.write("Kimse puan alamadı :(")

    st.write("Uygulamayı kapatmak için terminaldeki Streamlit sürecini sonlandırabilirsiniz.")
