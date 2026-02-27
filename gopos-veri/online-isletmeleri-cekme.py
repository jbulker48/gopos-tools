import pyodbc
import pandas as pd
import random

# 📌 1. MSSQL bağlantısı
conn = pyodbc.connect(
    'DRIVER={SQL Server Native Client 11.0};'
    'SERVER=izmir.gopos.com.tr;'   # örn: 192.168.1.10 veya .\SQLEXPRESS
    'DATABASE=GoAdmin;'
    'UID=gopos;'
    'PWD=GoposPos21@48;'
)

# 📌 2. SQL sorgusu (LisansTipi=1 ve aynı AnaKullaniciID için sadece 1 kayıt)
query = """
WITH cte AS (
    SELECT 
        i.AnaKullaniciID,
        CAST(i.GUID AS VARCHAR(50)) AS MekanID,
        i.Ad,
        i.Tur AS Tip,
        i.Il,
        i.Ilce,
        ROW_NUMBER() OVER (PARTITION BY i.AnaKullaniciID ORDER BY i.GUID) AS rn
    FROM dbo.Isletmeler i
    INNER JOIN dbo.AnaKullanici a ON i.AnaKullaniciID = a.ID
    WHERE a.LisansTipi = 1
)
SELECT MekanID, Ad, Tip, Il, Ilce
FROM cte
WHERE rn = 1
"""
df = pd.read_sql(query, conn)

# 📌 3. Adres ve Segment kolonlarını ekle
df['Adres'] = df['Il'] + '/' + df['Ilce']
df['Segment'] = [random.choice(['MODERN', 'TRADITIONAL']) for _ in range(len(df))]

# 📌 4. Sadece istediğimiz kolonları seç
df_final = df[['MekanID', 'Ad', 'Tip', 'Adres', 'Segment']]

# 📌 5. Excel'e kaydet
df_final.to_excel("isletmeler.xlsx", index=False, engine="openpyxl")

print(f"✅ isletmeler.xlsx dosyası oluşturuldu. Toplam {len(df_final)} işletme yazıldı.")
