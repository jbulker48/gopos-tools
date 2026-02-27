import pyodbc
import time
from datetime import datetime

# CONFIGURATION
server = 'izmir.gopos.com.tr'
username = 'gopos'
password = 'GoposPos21@48'
exclude_databases = ['master', 'tempdb', 'model', 'msdb']  # Hariç tutulacak DB'ler

def get_all_databases(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sys.databases WHERE state = 0")  # Sadece online DB'ler
    return [row[0] for row in cursor.fetchall() 
            if row[0] not in exclude_databases]

def fetch_last_transaction_dates():
    try:
        # Bağlantı dizesi
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};UID={username};PWD={password};MARS_Connection=Yes'
        conn = pyodbc.connect(conn_str, autocommit=True)
        
        databases = get_all_databases(conn)
        print(f"İşlenecek database sayısı: {len(databases)}")
        
        results = []
        db_times = {}
        total_start = time.perf_counter()

        for db in databases:
            try:
                db_start = time.perf_counter()
                conn.execute(f"USE [{db}]")
                
                # Son işlem tarihini al
                cursor = conn.execute("""
                    SELECT COALESCE(
                        (SELECT MAX(AcilisTarihi) FROM PosSatislari),
                        (SELECT MAX(KapanisTarihi) FROM BAK_PosSatislari)
                    ) AS LastTransactionDate
                """)
                
                row = cursor.fetchone()
                last_date = row.LastTransactionDate if row else None
                
                results.append((db, last_date))
                
                db_time = time.perf_counter() - db_start
                db_times[db] = db_time
                print(f"[{db}] Son işlem tarihi: {last_date} | {db_time:.3f}s")
                
            except Exception as e:
                print(f"[{db}] Hata: {str(e)}")
                results.append((db, None))  # Hata durumunda None olarak ekle
                continue

        # PERFORMANS SONUÇLARI
        total_time = time.perf_counter() - total_start
        
        # Sonuçları tarihe göre sırala (yeni -> eski)
        results.sort(key=lambda x: x[1] or datetime.min, reverse=True)
        
        print("\n" + "="*50)
        print(f"TOPLAM SÜRE: {total_time:.2f} saniye")
        print(f"Database başına ortalama süre: {total_time/len(databases):.4f}s")
        print("En yavaş 3 database:")
        for db, t in sorted(db_times.items(), key=lambda x: x[1], reverse=True)[:3]:
            print(f"- {db}: {t:.3f}s")
        
        return results
        
    except Exception as e:
        print(f"Genel hata: {str(e)}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

# Performans testini çalıştır
if __name__ == "__main__":
    last_transactions = fetch_last_transaction_dates()
    
    # Sonuçları tablo şeklinde göster
    print("\n{:<30} {:<20}".format('Database Adı', 'Son İşlem Tarihi'))
    print("-" * 50)
    for db, date in last_transactions:
        date_str = date.strftime("%Y-%m-%d %H:%M:%S") if date else "TARİH YOK"
        print("{:<30} {:<20}".format(db, date_str))
