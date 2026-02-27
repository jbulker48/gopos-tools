import pandas as pd

# Büyük dosyanın yüklenmesi (veri.xlsx)
# Sadece gerekli sütunu alırsan belleği daha verimli kullanırsın
veri_df = pd.read_excel("izmir_Satis_Raporu_2025-08-01_093820_CORRECTED.xlsx")  # veya usecols=['GüncellenecekSütun'] eklersen bellek kullanımını azaltır

# Key-Value eşleştirmesi olan dosya (eslestirme.xlsx)
eslestirme_df = pd.read_excel("benzersiz_urunler_listesi - Kopya.xlsx", usecols=["Ürün Adı", "Value"])

# Key-Value sözlüğü oluştur (daha hızlı işlem için)
mapping_dict = dict(zip(eslestirme_df["Ürün Adı"], eslestirme_df["Value"]))

# Güncellenecek sütun adı (örneğin 'Ürün Adı') — bunu kendi dosyana göre değiştir
sütun_adi = "Ürün Adı"

# Değerleri eşleştirerek güncelle
veri_df[sütun_adi] = veri_df[sütun_adi].map(mapping_dict).fillna(veri_df[sütun_adi])

# Sonuçları yeni dosyaya kaydet
veri_df.to_excel("izmir.xlsx", index=False)

print("bitti")
