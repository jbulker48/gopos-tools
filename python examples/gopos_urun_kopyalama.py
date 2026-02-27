import pyodbc

# Kullanıcıdan veritabanı bilgilerini alma
print("1. Veritabanı bilgilerini girin:")
server1 = input("SERVER: ")
database1 = input("DATABASE: ")
uid1 = input("UID: ")
pwd1 = input("PWD: ")

print("\n2. Veritabanı bilgilerini girin:")
server2 = input("SERVER: ")
database2 = input("DATABASE: ")
uid2 = input("UID: ")
pwd2 = input("PWD: ")

# Bağlantı string'lerini oluşturma
def create_conn_str(server, database, uid, pwd):
    return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={uid};PWD={pwd}"

source_conn_str = create_conn_str(server1, database1, uid1, pwd1)
target_conn_str = create_conn_str(server2, database2, uid2, pwd2)

# Bağlantıları kurma
try:
    source_conn = pyodbc.connect(source_conn_str)
    target_conn = pyodbc.connect(target_conn_str)
    target_cursor = target_conn.cursor()
    target_cursor.fast_executemany = True
except pyodbc.Error as e:
    print("Bağlantı hatası:", e)
    exit()

# İşlenecek tablo listesi
tables = [
    "Menu",
    "Menuler",
    "UrunKategorileri",
    "UrunPorsiyon",
    "UrunOzellikTanim",
    "UrunOzellikGrupTanim",
    "Stoklar",
    "UrunServisTuru",
    "MenuKategoriUrun",
    "KdvSablon",
    "UrunlerCeviri",
    "IsletmeUrunleri",
    "TblUrunIndirimi",
    "Urunler"
]

try:
    target_cursor = target_conn.cursor()
    target_conn.autocommit = False

    # Tabloları ters sırada silme
    for table in reversed(tables):
        target_cursor.execute(f"IF OBJECT_ID('{table}', 'U') IS NOT NULL DROP TABLE {table}")
    
    # Tabloları oluşturma ve verileri kopyalama
    for table in tables:
        # Sütun bilgilerini alma
        source_cursor = source_conn.cursor()
        source_cursor.execute(f"""
            SELECT 
                COLUMN_NAME, 
                DATA_TYPE, 
                CHARACTER_MAXIMUM_LENGTH,
                NUMERIC_PRECISION,
                NUMERIC_SCALE,
                IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            ORDER BY ORDINAL_POSITION
        """, table)
        
        columns_info = source_cursor.fetchall()
        
        # Primary key bilgisi
        source_cursor.execute(f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1
            AND TABLE_NAME = ?
        """, table)
        pk_columns = [row[0] for row in source_cursor.fetchall()]
        
        # CREATE TABLE komutu oluşturma
        column_defs = []
        for col in columns_info:
            name = col.COLUMN_NAME
            dtype = col.DATA_TYPE
            length = col.CHARACTER_MAXIMUM_LENGTH
            precision = col.NUMERIC_PRECISION
            scale = col.NUMERIC_SCALE
            nullable = 'NULL' if col.IS_NULLABLE == 'YES' else 'NOT NULL'

            if dtype in ('varchar', 'char', 'nvarchar', 'nchar'):
                if length == -1:
                    col_def = f"{name} {dtype}(MAX) {nullable}"
                else:
                    col_def = f"{name} {dtype}({length}) {nullable}"
            elif dtype in ('decimal', 'numeric'):
                col_def = f"{name} {dtype}({precision}, {scale}) {nullable}"
            else:
                col_def = f"{name} {dtype} {nullable}"
            
            column_defs.append(col_def)

        # Primary key ekleme
        if pk_columns:
            column_defs.append(f"PRIMARY KEY ({', '.join(pk_columns)})")
        
        create_sql = f"CREATE TABLE {table} (\n    " + ",\n    ".join(column_defs) + "\n);"
        
        # Tabloyu hedefte oluşturma
        target_cursor.execute(create_sql)
        
        # Verileri kopyalama
        source_cursor.execute(f"SELECT * FROM {table}")
        rows = source_cursor.fetchall()
        
        if rows:
            # Sütun isimlerini alma
            columns = [col[0] for col in source_cursor.description]
            placeholders = ", ".join(["?"] * len(columns))
            insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            
            # Verileri ekleme
            target_cursor.executemany(insert_sql, rows)
        
        source_cursor.close()
        print(f"{table} tablosu kopyalandı")

    target_conn.commit()
    print("\nTüm tablolar başarıyla kopyalandı!")

except Exception as e:
    print("Hata oluştu:", e)
    target_conn.rollback()
finally:
    source_conn.close()
    target_conn.close()
