import pyodbc
import pandas as pd
import random

# MSSQL bağlantısı
conn = pyodbc.connect(
    'DRIVER={SQL Server Native Client 11.0};'
    'SERVER=izmir.gopos.com.tr;'   # örn: 192.168.1.10 veya .\SQLEXPRESS
    'DATABASE=GoAdmin;'
    'UID=gopos;'
    'PWD=GoposPos21@48;'
)

# SQL sorgusu - sadece ihtiyacımız olan kolonları alıyoruz
query = """
SELECT 
    CAST(GUID AS VARCHAR(50)) AS MekanID,
    Ad,
    Tur AS Tip,
    Il,
    Ilce
FROM dbo.Isletmeler
"""

# Veriyi pandas DataFrame olarak çekiyoruz
df = pd.read_sql(query, conn)

# Adres kolonunu Il/Ilce şeklinde oluştur
df['Adres'] = df['Il'] + '/' + df['Ilce']

# Segment kolonunu rastgele MODERN / TRADITIONAL olarak ata
df['Segment'] = [random.choice(['MODERN', 'TRADITIONAL']) for _ in range(len(df))]

# Sadece istediğimiz kolonları sıralı şekilde seç
df_final = df[['MekanID', 'Ad', 'Tip', 'Adres', 'Segment']]

# Excel'e yaz
df_final.to_excel("isletmeler.xlsx", index=False, engine="openpyxl")

print("✅ isletmeler.xlsx dosyası oluşturuldu.")
