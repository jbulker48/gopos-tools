import customtkinter as ctk
import threading
import queue
import pyodbc
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

# Tema ayarları
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("GoPOS Ürün Listesi Aktarıcı (Unique)")
root.geometry("510x300")

frame = ctk.CTkFrame(root)
frame.pack(padx=10, pady=10, fill="x")

ctk.CTkLabel(frame, text="Kaynak Admin URL:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
source_url_entry = ctk.CTkEntry(frame, width=350)
source_url_entry.grid(row=0, column=1, padx=5, pady=5)

start_button = ctk.CTkButton(frame, text="Ürün Listesini Al (Temiz Liste)", command=lambda: start_process(), fg_color="#2ECC71", text_color="white", hover_color="#27AE60")
start_button.grid(row=1, column=0, columnspan=2, pady=10)

console_frame = ctk.CTkFrame(root)
console_frame.pack(padx=10, pady=10, fill="both", expand=True)

console = ctk.CTkTextbox(console_frame, height=150, font=("Arial", 10), text_color="lightgray", state="disabled", wrap="word")
console.pack(side="left", fill="both", expand=True)

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

def start_process():
    source_url = source_url_entry.get()
    if not source_url:
        msg_queue.put("Hata: URL girin.")
        return
    start_button.configure(state="disabled")
    thread = threading.Thread(target=run_export, args=(source_url,))
    thread.start()

def run_export(source_url):
    try:
        msg_queue.put("Tarayıcı hazırlanıyor...")
        options = Options()
        options.add_argument("--headless=new")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        msg_queue.put("Giriş yapılıyor...")
        driver.get("https://admin.gopos.com.tr/Login")
        driver.find_element(By.NAME, "Email").send_keys("Admin@gopos.com")
        pass_field = driver.find_element(By.NAME, "Sifre")
        pass_field.send_keys("!ResOtoPro@4107-?")
        pass_field.send_keys(Keys.RETURN)
        time.sleep(2)
        
        msg_queue.put("Veritabanı bilgileri alınıyor...")
        driver.get(source_url)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        cols = soup.find_all("div", class_="col-lg-3")
        
        # db_name buradan çekiliyor, dosya isminde bunu kullanacağız
        db_name = cols[8].find('input', {"name": "temelKullanici.DbName"})["value"]
        db_pass = cols[10].find('input', {"name": "temelKullanici.DbPass"})["value"]
        server_raw = cols[7].find("option", selected=True).get_text().strip()
        
        server_map = {
            "Bursa": "bursa.gopos.com.tr",
            "server-2": "server.gopos.com.tr",
            "cemil bey bonjur": "menu.bonjurkey.com,1976",
            "Ankara": "ankara.gopos.com.tr",
            "İzmir": "izmir.gopos.com.tr",
            "genel-server": "bursa.gopos.com.tr",
            "Germany ( Almanya )": "germany.gopos.com.tr",
            "istanbul": "istanbul.gopos.com.tr",
            "Bursa-2": "yedek.gopos.com.tr",
            "ist": "ist.gopos.com.tr",
            "bursa-3": "bursa-3.gopos.com.tr",
            "ist-Radore": "ist.gopos.com.tr"
        }
        
        server = server_map.get(server_raw, server_raw)
        
        conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={db_name};UID={db_name};PWD={db_pass}"
        msg_queue.put(f"Bağlantı kuruluyor: {db_name}")
        conn = pyodbc.connect(conn_str)
        
        # --- SQL SORGUSU ---
        sql_query = """
        SELECT DISTINCT
            uk.KategoriAdi, 
            u.UrunAdi, 
            up.PorsiyonAdi,
            up.Fiyat
        FROM Urunler u
        LEFT JOIN UrunKategorileri uk ON u.UrunKategoriID = uk.ID
        JOIN UrunPorsiyon up ON u.ID = up.UrunID
        WHERE uk.KategoriAdi NOT IN ('Migrosyemek', 'Getir', 'Trendyol', 'Yemeksepeti')
          AND up.PorsiyonAdi IS NOT NULL
        ORDER BY uk.KategoriAdi, u.UrunAdi;
        """
        
        msg_queue.put("Veriler temizlenerek çekiliyor...")
        df = pd.read_sql(sql_query, conn)
        
        # --- GÜNCELLENEN KISIM: DOSYA İSMİ ---
        # Format: database_adı_tarih_saat.xlsx
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{db_name}_menu_{timestamp}.xlsx"
        
        df.to_excel(filename, index=False, sheet_name="UrunListesi")

        msg_queue.put(f"\nBaşarılı! Mükerrer kayıtlar temizlendi.\nDosya: {filename}")
        
    except Exception as e:
        msg_queue.put(f"Hata: {str(e)}")
    
    finally:
        if 'conn' in locals(): conn.close()
        if 'driver' in locals(): driver.quit()
        msg_queue.put("PROCESS_DONE")

root.mainloop()
