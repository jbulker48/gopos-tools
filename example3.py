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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from tkinter import filedialog
import time
import os

# --- Tema ve UI Ayarları ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("GoPOS Transfer (SQL & Excel)")
root.geometry("600x680")

# --- UI Elemanları ---
tabview = ctk.CTkTabview(root, width=550, height=180)
tabview.pack(padx=10, pady=10)

tab_sql = tabview.add("Admin URL (SQL)")
tab_local_sql = tabview.add("Yerel SQL")
tab_excel = tabview.add("Excel Dosyası")

# --- TAB 1: UZAK SQL GİRİŞLERİ ---
ctk.CTkLabel(tab_sql, text="Kaynak Admin URL:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
source_url_entry = ctk.CTkEntry(tab_sql, width=300)
source_url_entry.grid(row=0, column=1, padx=10, pady=10)

# --- TAB 2: YEREL SQL GİRİŞLERİ ---
ctk.CTkLabel(tab_local_sql, text="Sunucu Adı (Örn: .\\SQLEXPRESS):").grid(row=0, column=0, sticky="w", padx=10, pady=5)
local_server_entry = ctk.CTkEntry(tab_local_sql, width=250)
local_server_entry.insert(0, ".") 
local_server_entry.grid(row=0, column=1, padx=10, pady=5)

ctk.CTkLabel(tab_local_sql, text="Veritabanı Adı:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
local_db_entry = ctk.CTkEntry(tab_local_sql, width=250)
local_db_entry.grid(row=1, column=1, padx=10, pady=5)

# --- TAB 3: EXCEL GİRİŞLERİ ---
ctk.CTkLabel(tab_excel, text="Excel Dosyası Seç:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
excel_path_entry = ctk.CTkEntry(tab_excel, width=220)
excel_path_entry.grid(row=0, column=1, padx=5, pady=10)

def select_excel_file():
    file_path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx *.xls *.csv")])
    if file_path:
        excel_path_entry.delete(0, "end")
        excel_path_entry.insert(0, file_path)

browse_btn = ctk.CTkButton(tab_excel, text="Seç", width=60, command=select_excel_file)
browse_btn.grid(row=0, column=2, padx=5, pady=10)

ctk.CTkLabel(tab_excel, text="Format: KategoriAdi | UrunAdi | PorsiyonAdi | Fiyat", text_color="gray", font=("Arial", 10)).grid(row=1, column=0, columnspan=3)

# --- ORTAK ALAN (HEDEF SİSTEM) ---
frame_dest = ctk.CTkFrame(root)
frame_dest.pack(padx=10, pady=5, fill="x")

ctk.CTkLabel(frame_dest, text="v2 Kullanıcı Adı:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
v2_username_entry = ctk.CTkEntry(frame_dest, width=300)
v2_username_entry.grid(row=0, column=1, padx=10, pady=5)

ctk.CTkLabel(frame_dest, text="v2 Şifresi:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
v2_password_entry = ctk.CTkEntry(frame_dest, width=300, show="*")
v2_password_entry.grid(row=1, column=1, padx=10, pady=5)

start_button = ctk.CTkButton(root, text="Başlat (Temizle & Yükle)", command=lambda: start_process(), fg_color="#E74C3C", text_color="white", hover_color="#C0392B", height=40)
start_button.pack(padx=10, pady=15, fill="x")

# --- Konsol ---
console_frame = ctk.CTkFrame(root)
console_frame.pack(padx=10, pady=10, fill="both", expand=True)

console = ctk.CTkTextbox(console_frame, height=150, font=("Arial", 10), text_color="lightgray", state="disabled", wrap="word")
console.pack(side="left", fill="both", expand=True)

msg_queue = queue.Queue()

# --- Kuyruk Kontrol Mekanizması ---
def check_queue():
    while not msg_queue.empty():
        message = msg_queue.get()
        if message == "PROCESS_DONE":
            start_button.configure(state="normal")
            start_button.configure(text="İşlem Tamamlandı")
        elif message.startswith("ERROR") or message.startswith("HATA") or message.startswith("KRİTİK"):
            start_button.configure(state="normal")
            console.configure(state="normal", text_color="#FF5555")
            console.insert("end", message + "\n")
            console.see("end")
            console.configure(state="disabled", text_color="lightgray")
        else:
            console.configure(state="normal", text_color="lightgray")
            console.insert("end", message + "\n")
            console.see("end")
            console.configure(state="disabled")
    root.after(100, check_queue)

root.after(100, check_queue)

# --- Tarayıcı Ayarları ---
def get_chrome_options():
    options = Options()
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")
    options.add_argument("--force-device-scale-factor=1")
    
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "autofill.passwords_enabled": False,
        "profile.password_manager_leak_detection": False,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return options

# --- YARDIMCI FONKSİYONLAR ---
def safe_click(driver, element):
    try:
        element.click()
    except:
        driver.execute_script("arguments[0].click();", element)

def handle_delete_confirm(wait, driver):
    try:
        confirm_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.notification-btn.notification-btn-primary")
        ))
        safe_click(driver, confirm_btn)
        time.sleep(1) 
    except Exception:
        pass

# --- İşlem Başlatıcı ---
def start_process():
    active_tab = tabview.get()
    
    v2_user = v2_username_entry.get()
    v2_pass = v2_password_entry.get()
    
    source_data = {}
    
    if active_tab == "Admin URL (SQL)":
        url = source_url_entry.get()
        if not url:
            msg_queue.put("ERROR: Lütfen Kaynak URL girin.")
            return
        source_data = {"type": "SQL", "url": url}
        
    elif active_tab == "Yerel SQL": 
        server = local_server_entry.get()
        db = local_db_entry.get()
        if not server or not db:
            msg_queue.put("ERROR: Lütfen sunucu ve veritabanı adını doldurun.")
            return
        source_data = {"type": "LOCAL_SQL", "server": server, "db": db}
        
    else: 
        path = excel_path_entry.get()
        if not path:
            msg_queue.put("ERROR: Lütfen Excel dosyası seçin.")
            return
        source_data = {"type": "EXCEL", "path": path}

    if not v2_user or not v2_pass:
        msg_queue.put("ERROR: Lütfen v2 kullanıcı adı ve şifresini doldurun.")
        return

    start_button.configure(state="disabled", text="İşlem Sürüyor...")
    thread = threading.Thread(target=run_transfer_flow, args=(source_data, v2_user, v2_pass))
    thread.start()

def run_transfer_flow(source_data, v2_user, v2_pass):
    df = pd.DataFrame()
    driver_dest = None
    
    try:
        msg_queue.put(f"--- AŞAMA 1: Veri Kaynağı Okunuyor ({source_data['type']}) ---")
        
        if source_data['type'] == "EXCEL":
            try:
                file_path = source_data['path']
                if file_path.endswith(".csv"):
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                
                required_cols = ['KategoriAdi', 'UrunAdi', 'PorsiyonAdi', 'Fiyat']
                if not all(col in df.columns for col in required_cols):
                    msg_queue.put(f"ERROR: Excel formatı hatalı! Gerekli sütunlar: {required_cols}")
                    msg_queue.put("PROCESS_DONE")
                    return
                
                for col in required_cols:
                    df[col] = df[col].astype(str).str.strip()
                    df[col] = df[col].replace('nan', '')

                msg_queue.put(f"Excel'den {len(df)} adet satır okundu.")
                
            except Exception as e:
                msg_queue.put(f"ERROR: Excel okuma hatası: {str(e)}")
                msg_queue.put("PROCESS_DONE")
                return

        elif source_data['type'] == "LOCAL_SQL":
            try:
                msg_queue.put(f"Yerel sunucuya ({source_data['server']}) bağlanılıyor...")
                
                # Sistemdeki SQL Server sürücülerini bul
                available_drivers = [x for x in pyodbc.drivers() if 'SQL Server' in x]
                driver_to_use = 'SQL Server' # En temel varsayılan
                
                # En güncelden eskiye doğru sürücü tercih sırası
                for d in ['ODBC Driver 18 for SQL Server', 'ODBC Driver 17 for SQL Server', 'ODBC Driver 13 for SQL Server']:
                    if d in available_drivers:
                        driver_to_use = d
                        break
                        
                msg_queue.put(f"Sürücü Seçildi: {driver_to_use}")
                
                # TrustServerCertificate=yes parametresi SQL 2022 için kritik
                conn_str = f"DRIVER={{{driver_to_use}}};SERVER={source_data['server']};DATABASE={source_data['db']};Trusted_Connection=yes;TrustServerCertificate=yes;"
                conn = pyodbc.connect(conn_str)
                
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
                
                df = pd.read_sql(sql_query, conn)
                df['KategoriAdi'] = df['KategoriAdi'].str.strip()
                df['UrunAdi'] = df['UrunAdi'].str.strip()
                
                conn.close()
                msg_queue.put(f"Yerel veritabanından başarıyla {len(df)} adet satır okundu.")

            except Exception as e:
                msg_queue.put(f"ERROR: Yerel SQL Hatası: {str(e)}")
                msg_queue.put("PROCESS_DONE")
                return

        elif source_data['type'] == "SQL":
            driver_source = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=get_chrome_options())
            try:
                msg_queue.put("SQL bilgileri Admin panelinden alınıyor...")
                driver_source.get("https://admin.gopos.com.tr/Login")
                
                driver_source.find_element(By.NAME, "Email").send_keys("Admin@gopos.com")
                pass_field = driver_source.find_element(By.NAME, "Sifre")
                pass_field.send_keys("!ResOtoPro@4107-?")
                pass_field.send_keys(Keys.RETURN)
                time.sleep(2)
                
                driver_source.get(source_data['url'])
                soup = BeautifulSoup(driver_source.page_source, 'html.parser')
                cols = soup.find_all("div", class_="col-lg-3")
                
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
                msg_queue.put(f"Bağlantı: {db_name}")
                conn = pyodbc.connect(conn_str)
                
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
                
                df = pd.read_sql(sql_query, conn)
                df['KategoriAdi'] = df['KategoriAdi'].str.strip()
                df['UrunAdi'] = df['UrunAdi'].str.strip()
                
                conn.close()

            except Exception as e:
                msg_queue.put(f"ERROR: SQL Hatası: {str(e)}")
                msg_queue.put("PROCESS_DONE")
                return
            finally:
                driver_source.quit()

        if df.empty:
            msg_queue.put("ERROR: Yüklenecek veri bulunamadı.")
            msg_queue.put("PROCESS_DONE")
            return
        
        product_count = len(df)
        category_count = len(df['KategoriAdi'].unique())
        msg_queue.put(f"Hazır: {category_count} Kategori, {product_count} Ürün işlenecek.")


        # ----------------------------------------
        # AŞAMA 2: HEDEF İŞLEMLERİ (SİL VE YÜKLE)
        # ----------------------------------------
        msg_queue.put("\n--- AŞAMA 2: Hedef Sistem (Silme & Yükleme) ---")
        
        driver_dest = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=get_chrome_options())
        wait = WebDriverWait(driver_dest, 20)

        try:
            msg_queue.put("Giriş yapılıyor...")
            driver_dest.get("https://pos.gopos.com.tr/")
            
            wait.until(EC.presence_of_element_located((By.NAME, "loginModel.Username")))
            driver_dest.find_element(By.NAME, "loginModel.Username").send_keys(v2_user)
            driver_dest.find_element(By.NAME, "loginModel.Password").send_keys(v2_pass)
            driver_dest.find_element(By.NAME, "loginModel.Password").send_keys(Keys.RETURN)
            
            time.sleep(8) 
            
            msg_queue.put("Menü yönetimine gidiliyor...")
            try:
                kategori_yonetimi_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div/div[1]/div[1]/div[2]/div/a[1]/span")))
                safe_click(driver_dest, kategori_yonetimi_btn)
            except:
                driver_dest.get("https://pos.gopos.com.tr/Product/CategoryList")
            
            time.sleep(5)

            # --- SİLME DÖNGÜSÜ ---
            msg_queue.put("Mevcut kategoriler taranıyor...")
            initial_cats = driver_dest.find_elements(By.CSS_SELECTOR, "div[data-type='category']")
            total_delete_count = len(initial_cats)
            
            if total_delete_count == 0:
                msg_queue.put("Silinecek kategori bulunamadı.")
            else:
                msg_queue.put(f"Toplam {total_delete_count} adet kategori silinecek.")
                
            deleted_count = 0

            while True:
                categories = driver_dest.find_elements(By.CSS_SELECTOR, "div[data-type='category']")
                if not categories:
                    break
                
                deleted_count += 1
                current_category = categories[0]
                
                try:
                    cat_log_name = current_category.text.split('\n')[0]
                    if not cat_log_name: cat_log_name = "Kategori"
                except:
                    cat_log_name = "Bilinmeyen Kategori"

                msg_queue.put(f"Siliniyor ({deleted_count}/{total_delete_count}): {cat_log_name}")

                safe_click(driver_dest, current_category)
                time.sleep(2) 

                while True:
                    products = driver_dest.find_elements(By.CSS_SELECTOR, "div[data-type='product']")
                    if not products:
                        break
                    
                    try:
                        del_btn = products[0].find_element(By.CSS_SELECTOR, "button.icon-button-danger[title='Sil']")
                        safe_click(driver_dest, del_btn)
                        time.sleep(0.5)
                        handle_delete_confirm(wait, driver_dest)
                        time.sleep(1) 
                    except Exception as e:
                        msg_queue.put(f"Ürün silme hatası (atlanıyor): {str(e)[:50]}")
                        break

                cats_again = driver_dest.find_elements(By.CSS_SELECTOR, "div[data-type='category']")
                if cats_again:
                    try:
                        cat_del_btn = cats_again[0].find_element(By.CSS_SELECTOR, "button.icon-button-danger[title='Sil']")
                        safe_click(driver_dest, cat_del_btn)
                        time.sleep(0.5)
                        handle_delete_confirm(wait, driver_dest)
                        time.sleep(2)
                    except Exception as e:
                        msg_queue.put(f"Kategori silme hatası: {str(e)[:50]}")
                        break
            
            msg_queue.put("\n--- Temizlik bitti. Veri yükleniyor... ---")

            # --- EKLEME İŞLEMİ ---
            
            # A. KATEGORİLER
            unique_categories = df['KategoriAdi'].unique()
            for cat_name in unique_categories:
                try:
                    new_cat_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div/div[2]/div[1]/div[2]/div/button")))
                    safe_click(driver_dest, new_cat_btn)
                    
                    cat_name_input = wait.until(EC.visibility_of_element_located((By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[2]/div/div[1]/input")))
                    cat_name_input.clear()
                    cat_name_input.send_keys(cat_name)
                    
                    icons = driver_dest.find_elements(By.CLASS_NAME, "icon-option")
                    if icons and len(icons) > 19:
                        safe_click(driver_dest, icons[19])
                    elif icons:
                        safe_click(driver_dest, icons[0])
                    
                    save_btn = driver_dest.find_element(By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[3]/button[2]")
                    safe_click(driver_dest, save_btn)
                    
                    msg_queue.put(f"Kategori Eklendi: {cat_name}")
                    time.sleep(1.5)
                    
                except Exception as e:
                    msg_queue.put(f"HATA (Kategori Ekleme): {cat_name} - {str(e)}")
                    try: driver_dest.refresh(); time.sleep(3); 
                    except: pass

            time.sleep(2)

            # B. ÜRÜNLER
            for index, row in df.iterrows():
                try:
                    p_name = row['UrunAdi']
                    p_cat = row['KategoriAdi']
                    
                    raw_price = str(row['Fiyat']).replace(',', '.') 
                    try:
                        f_price = float(raw_price)
                        if f_price.is_integer():
                            p_price = str(int(f_price))
                        else:
                            p_price = str(f_price).replace('.', ',')
                    except:
                        p_price = str(row['Fiyat']) 

                    ignored_portions = ['normal', 'tek', 'porsiyon', 'standart', 'adet']
                    p_porsiyon = str(row['PorsiyonAdi'])
                    
                    if p_porsiyon and p_porsiyon.lower() not in ignored_portions and p_porsiyon.lower() != 'nan':
                         final_name = f"{p_name} ({p_porsiyon})"
                    else:
                         final_name = p_name

                    new_prod_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div/div[2]/div[2]/div[1]/div[1]/div[2]/div[2]/button[1]")))
                    safe_click(driver_dest, new_prod_btn)
                    
                    cat_dropdown = wait.until(EC.visibility_of_element_located((By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[2]/form/div[1]/div[2]/div[2]/div[1]/div[2]/div/div[1]/select")))
                    select_cat = Select(cat_dropdown)
                    try:
                        select_cat.select_by_visible_text(p_cat)
                    except:
                        msg_queue.put(f"Kategori bulunamadı, atlanıyor: {p_cat}")
                        cancel_btn = driver_dest.find_element(By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[2]/form/div[2]/button[1]")
                        safe_click(driver_dest, cancel_btn)
                        continue

                    kdv_dropdown = driver_dest.find_element(By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[2]/form/div[1]/div[2]/div[2]/div[1]/div[2]/div/div[3]/select")
                    select_kdv = Select(kdv_dropdown)
                    if len(select_kdv.options) > 1:
                        select_kdv.select_by_index(1)
                    
                    name_input = driver_dest.find_element(By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[2]/form/div[1]/div[2]/div[2]/div[1]/div[2]/div/div[2]/input")
                    name_input.clear()
                    name_input.send_keys(final_name)
                    
                    price_input = driver_dest.find_element(By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[2]/form/div[1]/div[2]/div[2]/div[2]/div[2]/div[2]/div[3]/input")
                    price_input.clear()
                    price_input.send_keys(p_price)
                    time.sleep(0.5)
                    
                    save_prod_btn = driver_dest.find_element(By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[2]/form/div[2]/button[2]")
                    safe_click(driver_dest, save_prod_btn)
                    
                    msg_queue.put(f"Eklendi ({index+1}/{product_count}): {final_name}")
                    time.sleep(1.2)

                except Exception as e:
                    msg_queue.put(f"HATA (Ürün Ekleme): {str(e)[:50]}")
                    try: driver_dest.refresh(); time.sleep(3); 
                    except: pass
            
            msg_queue.put("\nTÜM İŞLEMLER BAŞARILI.")

        except Exception as e:
            msg_queue.put(f"GENEL SİSTEM HATASI: {str(e)}")
            if driver_dest:
                driver_dest.save_screenshot("critical_error.png")

    except Exception as e:
        msg_queue.put(f"KRİTİK HATA: {str(e)}")
    
    finally:
        if driver_dest:
            driver_dest.quit()
        msg_queue.put("PROCESS_DONE")

root.mainloop()
