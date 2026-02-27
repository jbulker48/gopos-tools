import pandas as pd
import os
import glob

# 1. Ayarlar
urun_kolonu = "Ürün Adı"  # Excel'deki ürün adı sütununun başlığı
cikti_dosyasi = "benzersiz_urunler_listesi.xlsx"

# 2. Mevcut dizindeki tüm Excel dosyalarını bul
dosya_yollari = glob.glob("*.xlsx")  # .xlsx uzantılılar
dosya_yollari += glob.glob("*.xls")  # .xls uzantılılar

if not dosya_yollari:
    print("⚠️ Uyarı: Mevcut dizinde Excel dosyası (.xlsx veya .xls) bulunamadı!")
    exit()

print(f"📂 İşlenecek dosyalar ({len(dosya_yollari)} adet):")
for i, dosya in enumerate(dosya_yollari, 1):
    print(f"{i}. {dosya}")

# 3. Tüm benzersiz ürünleri topla
tum_urunler = set()
okunan_dosya_sayisi = 0

for dosya_yolu in dosya_yollari:
    try:
        # Excel'i oku (NaN değerleri boş bırak)
        df = pd.read_excel(dosya_yolu, keep_default_na=False)
        okunan_dosya_sayisi += 1
        
        # Sütun kontrolü
        if urun_kolonu not in df.columns:
            print(f"\n⚠️ Uyarı: '{urun_kolonu}' sütunu {dosya_yolu} dosyasında bulunamadı! Atlanıyor...")
            continue
        
        # Boş olmayan değerleri sete ekle
        urunler = df[urun_kolonu].astype(str).str.strip()
        yeni_urunler = urunler[urunler != ""]
        
        onceki_adet = len(tum_urunler)
        tum_urunler.update(yeni_urunler)
        yeni_eklenen = len(tum_urunler) - onceki_adet
        
        print(f"✓ {dosya_yolu} işlendi ({yeni_eklenen} yeni ürün eklendi)")
        
    except Exception as e:
        print(f"\n❌ Hata: {dosya_yolu} dosyası işlenirken hata oluştu: {str(e)}")

# 4. Yeni Excel dosyasına yaz
if tum_urunler:
    # Seti sıralı listeye çevir
    sirali_urunler = sorted(tum_urunler)
    
    # DataFrame'e dönüştür
    sonuc_df = pd.DataFrame(sirali_urunler, columns=["Benzersiz Ürünler"])
    
    # Excel'e yaz
    sonuc_df.to_excel(cikti_dosyasi, index=False)
    print(f"\n{'='*50}")
    print(f"✨ İşlem tamamlandı!")
    print(f"   Toplam işlenen dosya: {okunan_dosya_sayisi}/{len(dosya_yollari)}")
    print(f"   Benzersiz ürün sayısı: {len(tum_urunler)}")
    print(f"   Çıktı dosyası: {cikti_dosyasi}")
    print(f"{'='*50}")
else:
    print("\n❌ Hiç ürün bulunamadı! Ayarları kontrol edin.")
