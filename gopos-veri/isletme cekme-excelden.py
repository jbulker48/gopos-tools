import pyodbc
import pandas as pd
import random
import glob
import os

# 📌 1. MSSQL bağlantısı
conn = pyodbc.connect(
    'DRIVER={SQL Server};'
    'SERVER=SERVER_ADI;'   # Örn: .\SQLEXPRESS veya 192.168.1.10
    'DATABASE=DB_ADI;'
    'UID=KULLANICI_ADI;'
    'PWD=ŞİFRE;'
)

# 📌 2. SQL sorgusu
query = """
SELECT 
    CAST(GUID AS VARCHAR(50)) AS MekanID,
    Ad,
    Tur AS Tip,
    Il,
    Ilce
FROM dbo.Isletmeler
"""
df = pd.read_sql(query, conn)

# 📌 3. Satış dosyalarındaki Mekan ID'leri oku
all_ids = set()

# Çalıştığın klasördeki *.xlsx dosyalarını tara (isletmeler.xlsx hariç)
for file in glob.glob("*.xlsx"):
    if file.lower() == "isletmeler.xlsx":  # kendi çıkacak dosyamızı alma
        continue
    
    sales_df = pd.read_excel(file, engine="openpyxl")
    if "Mekan ID" in sales_df.columns:  # kolon ismi kontrol
        all_ids.update(sales_df["Mekan ID"].dropna().astype(str).tolist())

# 📌 4. SQL'den gelen işletmeleri filtrele
df = df[df["MekanID"].isin(all_ids)]

# 📌 5. Adres ve Segment kolonlarını ekle
df['Adres'] = df['Il'] + '/' + df['Ilce']
df['Segment'] = [random.choice(['MODERN', 'TRADITIONAL']) for _ in range(len(df))]

# 📌 6. Sadece istediğimiz kolonları seç
df_final = df[['MekanID', 'Ad', 'Tip', 'Adres', 'Segment']]

# 📌 7. Excel'e kaydet
df_final.to_excel("isletmeler.xlsx", index=False, engine="openpyxl")

print(f"✅ isletmeler.xlsx dosyası oluşturuldu. Toplam {len(df_final)} işletme yazıldı.")
