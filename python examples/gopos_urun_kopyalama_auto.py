import pyodbc
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService


kaynak_admin_url = input("Kaynak işletmenin admin URL'si: ")
hedef_admin_url = input("Hedef işletmenin admin URL'si: ")

options = Options()
options.add_experimental_option("prefs", {
    "credentials_enable_service": False,
    "profile.password_manager_enabled": False,
    "autofill.passwords_enabled": False,
    "profile.password_manager_leak_detection": False,
})
driver = webdriver.Chrome(
    service=ChromeService(ChromeDriverManager().install()),
    options=options
)

# Load Page and login
driver.get("https://dev-wep.prokurye.com/")
driver.maximize_window()

# Load Page and login
driver.get("https://admin.gopos.com.tr/Login")
username_field = driver.find_element(By.NAME, "Email")
password_field = driver.find_element(By.NAME, "Sifre")

username_field.send_keys("Admin@gopos.com")
password_field.send_keys("!ResOtoPro@4107-?")
password_field.send_keys(Keys.RETURN)
time.sleep(2)

# Kaynak
kaynak_dict = {}
driver.get(kaynak_admin_url)
kaynak_html = driver.page_source
kaynak_soup = BeautifulSoup(kaynak_html, 'html.parser')
kaynak_cols = kaynak_soup.find_all("div", class_="col-lg-3")

# Kaynak DB Name & Pass
kaynak_DB_name = kaynak_cols[8]
kaynak_DB_name = kaynak_DB_name.find('input', {"class": "form-control", "name": "temelKullanici.DbName"})
kaynak_DB_name = kaynak_DB_name["value"]
kaynak_dict["DB Name"] = kaynak_DB_name

kaynak_DB_pass = kaynak_cols[10]
kaynak_DB_pass = kaynak_DB_pass.find('input', {"class": "form-control", "name": "temelKullanici.DbPass"})
kaynak_DB_pass = kaynak_DB_pass["value"]
kaynak_dict["DB Pass"] = kaynak_DB_pass

# Kaynak Server
kaynak_server = kaynak_cols[7]
kaynak_server = str(kaynak_server.find("option", selected=True).get_text()).strip()
if kaynak_server == "Bursa":
    kaynak_server = "genel-server.gopos.com.tr"
elif kaynak_server == "İzmir":
    kaynak_server = "izmir.gopos.com.tr"
elif kaynak_server == "istanbul":
    kaynak_server = "istanbul.gopos.com.tr"
elif kaynak_server == "Ankara":
    kaynak_server = "ankara.gopos.com.tr"
kaynak_dict["Server"] = kaynak_server

print(kaynak_dict)

# Hedef
hedef_dict = {}
driver.get(hedef_admin_url)
hedef_html = driver.page_source
hedef_soup = BeautifulSoup(hedef_html, 'html.parser')
hedef_cols = hedef_soup.find_all("div", class_="col-lg-3")

# hedef DB Name & Pass
hedef_DB_name = hedef_cols[8]
hedef_DB_name = hedef_DB_name.find('input', {"class": "form-control", "name": "temelKullanici.DbName"})
hedef_DB_name = hedef_DB_name["value"]
hedef_dict["DB Name"] = hedef_DB_name

hedef_DB_pass = hedef_cols[10]
hedef_DB_pass = hedef_DB_pass.find('input', {"class": "form-control", "name": "temelKullanici.DbPass"})
hedef_DB_pass = hedef_DB_pass["value"]
hedef_dict["DB Pass"] = hedef_DB_pass

# hedef Server
hedef_server = hedef_cols[7]
hedef_server = str(hedef_server.find("option", selected=True).get_text()).strip()
if hedef_server == "Bursa":
    hedef_server = "genel-server.gopos.com.tr"
elif hedef_server == "İzmir":
    hedef_server = "izmir.gopos.com.tr"
elif hedef_server == "istanbul":
    hedef_server = "istanbul.gopos.com.tr"
elif hedef_server == "Ankara":
    hedef_server = "ankara.gopos.com.tr"
hedef_dict["Server"] = hedef_server

print(hedef_dict)

server1 = kaynak_dict["Server"]
database1 = kaynak_dict["DB Name"]
uid1 = kaynak_dict["DB Name"]
pwd1 = kaynak_dict["DB Pass"]

server2 = hedef_dict["Server"]
database2 = hedef_dict["DB Name"]
uid2 = hedef_dict["DB Name"]
pwd2 = hedef_dict["DB Pass"]

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
    "MenuKategoriTanim",
    "UrunKategorileri",
    "UrunPorsiyon",
    "UrunOzellikTanim",
    "UrunOzellikGrupTanim",
    "Stoklar",
    "UrunServisTuru",
    "MenuKategoriUrun",
    "KdvSablon",
    "KategoriDetay",
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
