import os
import pandas as pd

# Kullanıcıdan klasör yolunu al
folder_path = input("Excel dosyalarının bulunduğu klasör yolunu girin: ").strip()

# Key-Value dosyasını oku
kv_file = os.path.join(folder_path, "Key Value.xlsx")
kv_df = pd.read_excel(kv_file)

# Key-Value dictionary oluştur (sadece Value'su dolu olanlar)
kv_dict = kv_df.dropna(subset=["Value"]).set_index("Key")["Value"].to_dict()

# Klasördeki tüm excel dosyalarını işle
for file in os.listdir(folder_path):
    if file.endswith(".xlsx") and file != "Key Value.xlsx":
        file_path = os.path.join(folder_path, file)

        # Dosyayı oku
        df = pd.read_excel(file_path)

        # E sütunu kontrolü (5. sütun index=4)
        col_index = 4
        if df.shape[1] > col_index:  # En az 5 sütun varsa
            df.iloc[:, col_index] = df.iloc[:, col_index].apply(
                lambda x: kv_dict.get(x, x)  # Key-Value eşleşmesi
            )

            # Yeni dosya adı
            output_path = os.path.join(folder_path, f"{os.path.splitext(file)[0]}_updated.xlsx")
            df.to_excel(output_path, index=False)

print("✅ İşlem tamamlandı! Tüm dosyalar güncellendi.")
