import pyodbc
import time
from datetime import datetime

# CONFIGURATION
servers = [
    'genel-server.gopos.com.tr',
    'istanbul.gopos.com.tr',
    'ankara.gopos.com.tr',
    'izmir.gopos.com.tr',
    'germany.gopos.com.tr'
]
username = 'gopos'
password = 'GoposPos21@48'
exclude_databases = ['master', 'tempdb', 'model', 'msdb']

def get_all_databases(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sys.databases WHERE state = 0")
    return [row[0] for row in cursor.fetchall() 
            if row[0] not in exclude_databases]

def fetch_last_transaction_dates(server):
    try:
        print(f"\n{'='*50}")
        print(f"Sunucu başlatılıyor: {server}")
        print(f"{'='*50}")
        
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
                results.append((db, None))
                continue

        total_time = time.perf_counter() - total_start
        
        print("\n" + "="*50)
        print(f"TOPLAM SÜRE ({server}): {total_time:.2f} saniye")
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

def main():
    all_results = {}
    server_stats = {}
    grand_start = time.perf_counter()

    for server in servers:
        start_time = time.perf_counter()
        server_results = fetch_last_transaction_dates(server)
        server_time = time.perf_counter() - start_time
        server_stats[server] = {
            'time': server_time,
            'db_count': len(server_results)
        }
        
        # Tüm sonuçları topla (server, db) anahtarıyla
        for db, date in server_results:
            key = (server, db)
            
            # En güncel tarihi sakla
            if key not in all_results:
                all_results[key] = date
            elif date and (all_results[key] is None or date > all_results[key]):
                all_results[key] = date

    # Performans özeti
    grand_time = time.perf_counter() - grand_start
    print("\n\n" + "="*100)
    print("TÜM SUNUCULAR ÖZETİ")
    print("="*100)
    print(f"Toplam sunucu sayısı: {len(servers)}")
    print(f"Toplam çalışma süresi: {grand_time:.2f} saniye")
    
    print("\nSunucu Performansları:")
    for server, stats in server_stats.items():
        print(f"- {server}: {stats['db_count']} DB, {stats['time']:.2f}s")

    # Sonuçları sırala (tarihe göre yeniden eskiye)
    sorted_results = sorted(
        [(server, db, date) for (server, db), date in all_results.items()],
        key=lambda x: x[2] or datetime.min,
        reverse=True
    )

    # Raporu yazdır
    print("\n\n" + "="*100)
    print("SON İŞLEM TARİHLERİ (Tüm Sunucular)")
    print("="*100)
    print("{:<25} {:<30} {:<20}".format('Sunucu', 'Database Adı', 'Son İşlem Tarihi'))
    print("-" * 85)
    
    for server, db, date in sorted_results:
        date_str = date.strftime("%Y-%m-%d %H:%M:%S") if date else "TARİH YOK"
        print("{:<25} {:<30} {:<20}".format(server, db, date_str))

if __name__ == "__main__":
    main()