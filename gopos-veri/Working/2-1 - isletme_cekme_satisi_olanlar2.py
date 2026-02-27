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
    "yedek.gopos.com.tr",
    "bursa-3.gopos.com.tr",
    "ist.gopos.com.tr"
]

username = "gopos"
password = "GoposPos21@48"

# Excel için sonuç listesi
records = []

for server in servers:
    print(f"🔍 Sunucu taranıyor: {server}")
    try:
        # Master'a bağlan → database listesi çek
        master_conn_str = (
            f"DRIVER={{SQL Server Native Client 11.0}};"
            f"SERVER={server};DATABASE=master;"
            f"UID={username};PWD={password};"
        )
        master_conn = pyodbc.connect(master_conn_str)
        cursor = master_conn.cursor()
        cursor.execute("""
            SELECT name FROM sys.databases
            WHERE name NOT IN ('master','tempdb','model','msdb')
            AND state = 0
        """)
        databases = [row.name for row in cursor.fetchall()]
        master_conn.close()

        for db in databases:
            try:
                print(f"   📂 Database: {db}")
                db_conn_str = (
                    f"DRIVER={{SQL Server Native Client 11.0}};"
                    f"SERVER={server};DATABASE={db};"
                    f"UID={username};PWD={password};"
                )
                conn = pyodbc.connect(db_conn_str)
                cur = conn.cursor()

                # Satış kontrolü
                cur.execute("SELECT TOP 1 1 FROM BAK_PosSatislari")
                if not cur.fetchone():
                    conn.close()
                    continue  # hiç satış yok → atla

                # İşletme bilgisi al
                cur.execute("SELECT TOP 1 GUID, Ad, Tur, Il, Ilce FROM Isletmeler")
                isletme = cur.fetchone()
                if not isletme:
                    conn.close()
                    continue

                guid, ad, tur, il, ilce = isletme
                adres = f"{il}/{ilce}"
                segment = random.choice(["MODERN", "TRADITIONAL"])

                records.append([str(guid), ad, tur, adres, segment])

                conn.close()

            except Exception as e:
                print(f"   ⚠️ {db} hatası: {e}")

    except Exception as e:
        print(f"❌ Sunucu hatası {server}: {e}")


# Pandas DataFrame oluştur
df = pd.DataFrame(records, columns=["MekanID", "Ad", "Tip", "Adres", "Segment"])

# Excel'e kaydet
timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
filename = f"isletmeler_{timestamp}.xlsx"
df.to_excel(filename, index=False, engine="openpyxl")

print(f"✅ {filename} oluşturuldu. Toplam {len(df)} işletme yazıldı.")
