import customtkinter as ctk
import threading
import queue
import pyodbc
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

# Tema ayarları
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Ana pencere
root = ctk.CTk()
root.title("GoPOS Ürün Kopyalama")
root.geometry("510x350")

# Giriş alanları için frame
frame = ctk.CTkFrame(root)
frame.pack(padx=10, pady=10, fill="x")

ctk.CTkLabel(frame, text="Kaynak Admin URL:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
source_url_entry = ctk.CTkEntry(frame, width=350)
source_url_entry.grid(row=0, column=1, padx=5, pady=5)

ctk.CTkLabel(frame, text="Hedef Admin URL:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
target_url_entry = ctk.CTkEntry(frame, width=350)
target_url_entry.grid(row=1, column=1, padx=5, pady=5)

# Başlat tuşu
start_button = ctk.CTkButton(frame, text="Başlat", command=lambda: start_process(), fg_color="#44546E", text_color="white", hover_color="#3333FF")
start_button.grid(row=2, column=0, columnspan=2, pady=10)

# Konsol alanı
console_frame = ctk.CTkFrame(root)
console_frame.pack(padx=10, pady=10, fill="both", expand=True)

# Konsol
console = ctk.CTkTextbox(console_frame, height=200, font=("Arial", 10), text_color="lightgray", state="disabled", wrap="word")
console.pack(side="left", fill="both", expand=True)


# Mesaj kuyruğu ve kontrol fonksiyonu
msg_queue = queue.Queue()

def check_queue():
    while not msg_queue.empty():
        message = msg_queue.get()
        if message == "PROCESS_DONE":
            start_button.configure(state="normal")
        else:
            console.configure(state="normal")
            console.insert("end", message + "\n")
            console.see("end")
            console.configure(state="disabled")
    root.after(100, check_queue)

root.after(100, check_queue)

# İşlemi başlatma fonksiyonu
def start_process():
    source_url = source_url_entry.get()
    target_url = target_url_entry.get()
    if not source_url or not target_url:
        msg_queue.put("Lütfen her iki URL'yi de girin.")
        return
    start_button.configure(state="disabled")
    thread = threading.Thread(target=run_process, args=(source_url, target_url))
    thread.start()

# Ana işlem fonksiyonu
def run_process(source_url, target_url):
    try:
        msg_queue.put("WebDriver başlatılıyor...")
        options = Options()
        options.add_argument("--headless=new")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        msg_queue.put("Giriş yapılıyor...")
        driver.get("https://admin.gopos.com.tr/Login")
        username_field = driver.find_element(By.NAME, "Email")
        password_field = driver.find_element(By.NAME, "Sifre")
        username_field.send_keys("Admin@gopos.com")
        password_field.send_keys("!AdminPos2025--@")
        password_field.send_keys(Keys.RETURN)
        time.sleep(2)
        msg_queue.put("Giriş başarılı.")
        
        # Kaynak bilgileri
        msg_queue.put("Kaynak veritabanı bilgileri çıkarılıyor...")
        kaynak_dict = {}
        driver.get(source_url)
        kaynak_html = driver.page_source
        kaynak_soup = BeautifulSoup(kaynak_html, 'html.parser')
        kaynak_cols = kaynak_soup.find_all("div", class_="col-lg-3")
        
        kaynak_DB_name = kaynak_cols[8].find('input', {"class": "form-control", "name": "temelKullanici.DbName"})["value"]
        kaynak_dict["DB Name"] = kaynak_DB_name
        
        kaynak_DB_pass = kaynak_cols[10].find('input', {"class": "form-control", "name": "temelKullanici.DbPass"})["value"]
        kaynak_dict["DB Pass"] = kaynak_DB_pass
        
        kaynak_server = str(kaynak_cols[7].find("option", selected=True).get_text()).strip()
        if kaynak_server == "Bursa":
            kaynak_server = "genel-server.gopos.com.tr"
        elif kaynak_server == "İzmir":
            kaynak_server = "izmir.gopos.com.tr"
        elif kaynak_server == "istanbul":
            kaynak_server = "istanbul.gopos.com.tr"
        kaynak_dict["Server"] = kaynak_server
        msg_queue.put(f"Kaynak Veritabanı Bilgileri Çekildi:\n{kaynak_dict}")
        
        # Hedef bilgileri
        msg_queue.put("Hedef veritabanı bilgileri çıkarılıyor...")
        hedef_dict = {}
        driver.get(target_url)
        hedef_html = driver.page_source
        hedef_soup = BeautifulSoup(hedef_html, 'html.parser')
        hedef_cols = hedef_soup.find_all("div", class_="col-lg-3")
        
        hedef_DB_name = hedef_cols[8].find('input', {"class": "form-control", "name": "temelKullanici.DbName"})["value"]
        hedef_dict["DB Name"] = hedef_DB_name
        
        hedef_DB_pass = hedef_cols[10].find('input', {"class": "form-control", "name": "temelKullanici.DbPass"})["value"]
        hedef_dict["DB Pass"] = hedef_DB_pass
        
        hedef_server = str(hedef_cols[7].find("option", selected=True).get_text()).strip()
        if hedef_server == "Bursa":
            hedef_server = "genel-server.gopos.com.tr"
        elif hedef_server == "İzmir":
            hedef_server = "izmir.gopos.com.tr"
        elif hedef_server == "istanbul":
            hedef_server = "istanbul.gopos.com.tr"
        hedef_dict["Server"] = hedef_server
        msg_queue.put(f"Hedef Veritabanı Bilgileri Çekildi:\n{hedef_dict}")
        
        # Bağlantı string'leri
        source_conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={kaynak_dict['Server']};DATABASE={kaynak_dict['DB Name']};UID={kaynak_dict['DB Name']};PWD={kaynak_dict['DB Pass']}"
        target_conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={hedef_dict['Server']};DATABASE={hedef_dict['DB Name']};UID={hedef_dict['DB Name']};PWD={hedef_dict['DB Pass']}"
        
        msg_queue.put("Veritabanlarına bağlanılıyor...")
        source_conn = pyodbc.connect(source_conn_str)
        target_conn = pyodbc.connect(target_conn_str)
        target_cursor = target_conn.cursor()
        target_cursor.fast_executemany = True
        msg_queue.put("Veritabanlarına bağlanıldı.")
        
        tables = [
            "Menu", "Menuler", "MenuKategoriTanim", "UrunKategorileri", "UrunPorsiyon",
            "UrunOzellikTanim", "UrunOzellikGrupTanim", "Stoklar", "UrunServisTuru",
            "MenuKategoriUrun", "KdvSablon", "KategoriDetay", "UrunlerCeviri",
            "IsletmeUrunleri", "TblUrunIndirimi", "Urunler"
        ]
        
        target_conn.autocommit = False
        
        for table in reversed(tables):
            target_cursor.execute(f"IF OBJECT_ID('{table}', 'U') IS NOT NULL DROP TABLE {table}")
            msg_queue.put(f"{table} tablosu silindi (varsa).")
        
        for table in tables:
            msg_queue.put(f"{table} tablosu kopyalanıyor...")
            source_cursor = source_conn.cursor()
            source_cursor.execute(f"""
                SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
            """, table)
            columns_info = source_cursor.fetchall()
            
            source_cursor.execute(f"""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1
                AND TABLE_NAME = ?
            """, table)
            pk_columns = [row[0] for row in source_cursor.fetchall()]
            
            column_defs = []
            for col in columns_info:
                name, dtype, length, precision, scale, nullable = col
                nullable = 'NULL' if nullable == 'YES' else 'NOT NULL'
                if dtype in ('varchar', 'char', 'nvarchar', 'nchar'):
                    col_def = f"{name} {dtype}({length if length != -1 else 'MAX'}) {nullable}"
                elif dtype in ('decimal', 'numeric'):
                    col_def = f"{name} {dtype}({precision}, {scale}) {nullable}"
                else:
                    col_def = f"{name} {dtype} {nullable}"
                column_defs.append(col_def)
            
            if pk_columns:
                column_defs.append(f"PRIMARY KEY ({', '.join(pk_columns)})")
            
            create_sql = f"CREATE TABLE {table} (\n    " + ",\n    ".join(column_defs) + "\n)"
            target_cursor.execute(create_sql)
            
            source_cursor.execute(f"SELECT * FROM {table}")
            rows = source_cursor.fetchall()
            if rows:
                columns = [col[0] for col in source_cursor.description]
                placeholders = ", ".join(["?"] * len(columns))
                insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                target_cursor.executemany(insert_sql, rows)
            
            source_cursor.close()
            msg_queue.put(f"{table} tablosu kopyalandı.")
        
        target_conn.commit()
        msg_queue.put("Tüm tablolar başarıyla kopyalandı!")
    
    except Exception as e:
        msg_queue.put(f"Hata oluştu: {e}")
        if 'target_conn' in locals():
            target_conn.rollback()
    
    finally:
        if 'source_conn' in locals():
            source_conn.close()
        if 'target_conn' in locals():
            target_conn.close()
        if 'driver' in locals():
            driver.quit()
        msg_queue.put("PROCESS_DONE")

# Tkinter ana döngüsü
root.mainloop()
