import pyodbc
import mysql.connector
from mysql.connector import Error
import datetime
import traceback
import time

# MSSQL bağlantı bilgileri
MSSQL_SERVER = 'izmir.gopos.com.tr'
MSSQL_DB = 'GoAdmin'
MSSQL_USER = 'gopos'
MSSQL_PASSWORD = 'GoposPos21@48'

# MySQL bağlantı bilgileri
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'password123'
MYSQL_DB = MSSQL_DB  # Aynı ismi kullanıyoruz

def convert_data(value):
    if isinstance(value, datetime.datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(value, bytes):
        return value
    elif isinstance(value, str):
        return value.encode('utf-8', 'ignore').decode('utf-8')
    return value

try:
    # MySQL veritabanını tamamen sil ve yeniden oluştur
    print("MySQL veritabanı yeniden oluşturuluyor...")
    init_mysql_conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        auth_plugin='mysql_native_password'
    )
    init_cursor = init_mysql_conn.cursor()
    init_cursor.execute(f"DROP DATABASE IF EXISTS `{MYSQL_DB}`")  # ÖNEMLİ: Önce sil
    init_cursor.execute(f"CREATE DATABASE `{MYSQL_DB}`")
    print(f"MySQL'de veritabanı oluşturuldu: {MYSQL_DB}")
    init_cursor.close()
    init_mysql_conn.close()
    
    # MSSQL bağlantısı
    print("MSSQL sunucusuna bağlanılıyor...")
    mssql_conn = pyodbc.connect(
        f"DRIVER={{SQL Server Native Client 11.0}};"
        f"SERVER={MSSQL_SERVER};"
        f"DATABASE={MSSQL_DB};"
        f"UID={MSSQL_USER};"
        f"PWD={MSSQL_PASSWORD}"
    )
    mssql_cursor = mssql_conn.cursor()
    
    # MySQL bağlantısı (yeni oluşturulan veritabanına)
    mysql_conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        auth_plugin='mysql_native_password'
    )
    mysql_cursor = mysql_conn.cursor()
    
    # Kullanıcı tablolarını listele (sistem tablolarını ve filetable'ları hariç tut)
    print("Tablolar listeleniyor...")
    query = """
        SELECT t.TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES t
        LEFT JOIN sys.tables st ON t.TABLE_NAME = st.name
        WHERE t.TABLE_TYPE = 'BASE TABLE'
          AND t.TABLE_SCHEMA = 'dbo'  -- Sadece dbo şemasındaki tablolar
          AND (st.is_filetable = 0 OR st.is_filetable IS NULL)  -- FileTables hariç
          AND t.TABLE_NAME NOT IN (
            'sysdiagrams', 
            'spt_fallback_db',
            'spt_fallback_dev',
            'spt_fallback_usg',
            'spt_monitor',
            'MSreplication_options'
          )  -- Bilinen sistem tablolarını hariç tut
    """
    mssql_cursor.execute(query)
    tables = [row[0] for row in mssql_cursor.fetchall()]
    print(f"Aktarılacak tablo sayısı: {len(tables)}")
    
    # Her tablo için işlem
    for table in tables:
        table_start_time = time.time()
        try:
            print(f"\nİşleniyor: {table}")
            
            # Sütun bilgilerini al
            mssql_cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = '{table}'
                ORDER BY ORDINAL_POSITION
            """)
            columns_info = mssql_cursor.fetchall()
            
            # MySQL için tablo oluşturma sorgusu hazırla
            col_definitions = []
            for col in columns_info:
                col_name, col_type, is_nullable, max_length = col
                
                # MSSQL -> MySQL tip dönüşümü
                if col_type in ('int', 'bigint', 'smallint', 'tinyint'):
                    mysql_type = 'INT'
                elif col_type in ('varchar', 'nvarchar', 'char', 'nchar'):
                    if max_length == -1 or max_length > 65535:
                        mysql_type = 'LONGTEXT'
                    else:
                        mysql_type = f'VARCHAR({max_length})'
                elif col_type in ('text', 'ntext'):
                    mysql_type = 'LONGTEXT'
                elif col_type in ('datetime', 'smalldatetime'):
                    mysql_type = 'DATETIME'
                elif col_type == 'date':
                    mysql_type = 'DATE'
                elif col_type in ('decimal', 'numeric'):
                    mysql_type = 'DECIMAL(18,6)'
                elif col_type in ('float', 'real'):
                    mysql_type = 'FLOAT'
                elif col_type == 'bit':
                    mysql_type = 'BOOLEAN'
                elif col_type == 'uniqueidentifier':
                    mysql_type = 'CHAR(36)'
                elif col_type in ('varbinary', 'binary', 'image'):
                    mysql_type = 'LONGBLOB'
                else:
                    mysql_type = 'LONGTEXT'
                
                null_clause = "NULL" if is_nullable == 'YES' else "NOT NULL"
                col_definitions.append(f"`{col_name}` {mysql_type} {null_clause}")
            
            create_table_sql = f"CREATE TABLE IF NOT EXISTS `{table}` (\n"
            create_table_sql += ",\n".join(col_definitions)
            create_table_sql += "\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
            
            # Tabloyu oluştur
            mysql_cursor.execute(create_table_sql)
            print(f"  Tablo oluşturuldu: {table}")
            
            # Veri aktarımı için MSSQL'den veri çek
            mssql_cursor.execute(f"SELECT * FROM {table}")
            columns = [column[0] for column in mssql_cursor.description]
            placeholders = ', '.join(['%s'] * len(columns))
            insert_query = f"INSERT INTO `{table}` VALUES ({placeholders})"
            
            # Toplu işlem boyutu
            batch_size = 1000
            total_rows = 0
            batch_count = 0
            
            while True:
                rows = mssql_cursor.fetchmany(batch_size)
                if not rows:
                    break
                    
                converted_rows = []
                for row in rows:
                    converted_rows.append([convert_data(value) for value in row])
                
                try:
                    mysql_cursor.executemany(insert_query, converted_rows)
                    mysql_conn.commit()
                except Exception as e:
                    print(f"  HATA (batch): {str(e)}")
                    print(traceback.format_exc())
                    mysql_conn.rollback()
                    # Hata alınan batch'i atlayıp devam edebilir veya durdurabilirsiniz.
                    # Bu örnekte devam ediyoruz.
                    continue
                
                row_count = len(rows)
                total_rows += row_count
                batch_count += 1
                if batch_count % 10 == 0:  # Her 10 batch'te bir ilerleme raporu
                    elapsed = time.time() - table_start_time
                    print(f"  Aktarılan: {total_rows} satır (Toplam süre: {elapsed:.2f}s)")
            
            elapsed = time.time() - table_start_time
            print(f"  TABLO TAMAMLANDI: {total_rows} satır, {elapsed:.2f} saniye")
            
        except Exception as e:
            print(f"  HATA: {table} işlenirken sorun oluştu: {str(e)}")
            print(traceback.format_exc())
            mysql_conn.rollback()
            continue

except Error as e:
    print("MySQL hatası:", e)
    print(traceback.format_exc())
except pyodbc.Error as e:
    print("MSSQL hatası:", e)
    print(traceback.format_exc())
except Exception as e:
    print("Genel hata:", e)
    print(traceback.format_exc())
finally:
    if 'mssql_conn' in locals() and mssql_conn:
        mssql_conn.close()
    if 'mysql_conn' in locals() and mysql_conn:
        mysql_conn.close()
    if 'init_mysql_conn' in locals() and init_mysql_conn:
        init_mysql_conn.close()
    print("İşlem tamamlandı")
