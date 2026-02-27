import pyodbc
import pandas as pd
import random
from datetime import datetime

# Sunucu bilgileri
servers = [
    "istanbul.gopos.com.tr",
    "ankara.gopos.com.tr",
    "izmir.gopos.com.tr",
    "bursa.gopos.com.tr",
    "yedek.gopos.com.tr"
]

username = "gopos"
password = "GoposPos21@48"

all_records = []

for server in servers:
    try:
        # Master veritabanına bağlan
        master_conn_str = (
            f"DRIVER={{SQL Server Native Client 11.0}};"
            f"SERVER={server};DATABASE=master;"
            f"UID={username};PWD={password};"
        )
        master_conn = pyodbc.connect(master_conn_str)
        master_cursor = master_conn.cursor()
        
        # Kullanıcı veritabanlarını al
        master_cursor.execute("""
            SELECT name FROM sys.databases
            WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')
            AND state = 0
        """)
        databases = [row.name for row in master_cursor.fetchall()]
        master_conn.close()
        
        # Her database için işletme kontrolü
        for db in databases:
            try:
                db_conn_str = (
                    f"DRIVER={{SQL Server Native Client 11.0}};"
                    f"SERVER={server};DATABASE={db};"
                    f"UID={username};PWD={password};"
                )
                conn = pyodbc.connect(db_conn_str)
                cursor = conn.cursor()
                
                # İşletme bilgisi al (ilk satır)
                cursor.execute("SELECT TOP 1 GUID, Ad, Tur, Il, Ilce FROM Isletmeler")
                isletme = cursor.fetchone()
                if not isletme:
                    conn.close()
                    continue
                
                mekan_id, ad, tip, il, ilce = isletme
                
                # Satış var mı kontrol et
                cursor.execute("SELECT TOP 1 1 FROM BAK_PosSatislari")
                satis = cursor.fetchone()
                if satis:
                    adres = f"{il}/{ilce}"
                    segment = random.choice(["MODERN", "TRADITIONAL"])
                    
                    all_records.append([
                        str(mekan_id), ad, tip, adres, segment, server, db
                    ])
                
                conn.close()
            except Exception as e:
                print(f"{server} - {db} hatası: {e}")
    
    except Exception as e:
        print(f"{server} bağlantı hatası: {e}")

# DataFrame oluştur
df = pd.DataFrame(all_records, columns=["MekanID", "Ad", "Tip", "Adres", "Segment", "Sunucu", "Database"])

# Excel’e kaydet
if not df.empty:
    filename = f"isletmeler_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.xlsx"
    df.to_excel(filename, index=False, engine="openpyxl")
    print(f"✅ {filename} oluşturuldu. Toplam {len(df)} işletme eklendi.")
else:
    print("❌ Satış verisi olan hiçbir işletme bulunamadı.")
