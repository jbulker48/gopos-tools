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
import time

# --- Tema ve UI Ayarları ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("GoPOS Ürün Aktarıcı (Temizle & Yükle)")
root.geometry("550x550")

# --- UI Elemanları ---
frame = ctk.CTkFrame(root)
frame.pack(padx=10, pady=10, fill="x")

# 1. Kaynak URL
ctk.CTkLabel(frame, text="Kaynak Admin URL:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
source_url_entry = ctk.CTkEntry(frame, width=350)
source_url_entry.grid(row=0, column=1, padx=5, pady=5)

# 2. v2 Kullanıcı Adı
ctk.CTkLabel(frame, text="v2 Kullanıcı Adı:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
v2_username_entry = ctk.CTkEntry(frame, width=350)
v2_username_entry.grid(row=1, column=1, padx=5, pady=5)

# 3. v2 Şifre
ctk.CTkLabel(frame, text="v2 Şifresi:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
v2_password_entry = ctk.CTkEntry(frame, width=350, show="*")
v2_password_entry.grid(row=2, column=1, padx=5, pady=5)

start_button = ctk.CTkButton(frame, text="Temizle ve Transferi Başlat", command=lambda: start_process(), fg_color="#E74C3C", text_color="white", hover_color="#C0392B")
start_button.grid(row=3, column=0, columnspan=2, pady=15)

# Konsol
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
        elif message.startswith("ERROR"):
            start_button.configure(state="normal")
            console.configure(state="normal")
            console.insert("end", message + "\n")
            console.see("end")
            console.configure(state="disabled")
        else:
            console.configure(state="normal")
            console.insert("end", message + "\n")
            console.see("end")
            console.configure(state="disabled")
    root.after(100, check_queue)

root.after(100, check_queue)

# --- Tarayıcı Ayarlarını Getiren Yardımcı Fonksiyon ---
def get_chrome_options():
    options = Options()
    # Headless Mod (Arka planda çalışır)
    options.add_argument("--headless=new") 
    options.add_argument("--window-size=1920,1080")
    
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

# --- İşlem Başlatıcı ---
def start_process():
    source_url = source_url_entry.get()
    v2_user = v2_username_entry.get()
    v2_pass = v2_password_entry.get()

    if not source_url or not v2_user or not v2_pass:
        msg_queue.put("ERROR: Lütfen tüm alanları doldurun.")
        return

    start_button.configure(state="disabled", text="İşlem Sürüyor...")
    thread = threading.Thread(target=run_transfer_flow, args=(source_url, v2_user, v2_pass))
    thread.start()

# --- YARDIMCI: SİLME ONAYI ---
def handle_delete_confirm(wait):
    """Silme butonuna bastıktan sonra çıkan olası 'Emin misiniz?' onayını geçer."""
    try:
        # Genellikle SweetAlert veya benzeri bir modal çıkar. "Evet", "Sil" veya "Onayla" butonunu arar.
        # XPath: Class'ında confirm geçen VEYA text'i Evet/Sil olan buton.
        confirm_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(@class, 'swal2-confirm') or contains(text(), 'Evet') or contains(text(), 'Sil') or contains(text(), 'Yes')]")
        ))
        confirm_btn.click()
    except:
        # Onay kutusu çıkmazsa veya yakalayamazsa devam et
        pass

# --- Ana Transfer Akışı ---
def run_transfer_flow(source_url, v2_user, v2_pass):
    try:
        # ----------------------------------------
        # AŞAMA 1: VERİYİ KAYNAKTAN ÇEKME (HEADLESS)
        # ----------------------------------------
        msg_queue.put("--- AŞAMA 1: Veriler Çekiliyor ---")
        
        driver_source = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=get_chrome_options())
        
        try:
            msg_queue.put("Kaynak Admin paneline bağlanılıyor...")
            driver_source.get("https://admin.gopos.com.tr/Login")
            
            driver_source.find_element(By.NAME, "Email").send_keys("Admin@gopos.com")
            pass_field = driver_source.find_element(By.NAME, "Sifre")
            pass_field.send_keys("!ResOtoPro@4107-?")
            pass_field.send_keys(Keys.RETURN)
            time.sleep(2)
            
            driver_source.get(source_url)
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
            msg_queue.put(f"SQL Bağlantısı: {db_name}")
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
            
            product_count = len(df)
            category_count = len(df['KategoriAdi'].unique())
            
            msg_queue.put(f"Veri Hazır: {category_count} Kategori, {product_count} Ürün.")
            conn.close()

        finally:
            driver_source.quit()

        if df.empty:
            msg_queue.put("ERROR: Çekilecek veri bulunamadı.")
            msg_queue.put("PROCESS_DONE")
            return

        # ----------------------------------------
        # AŞAMA 2: HEDEF SİSTEME GİRİŞ VE TEMİZLİK
        # ----------------------------------------
        msg_queue.put("\n--- AŞAMA 2: Hedef Sistem Temizliği ---")
        msg_queue.put("Hedef tarayıcı başlatılıyor (Headless)...")

        driver_dest = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=get_chrome_options())
        wait = WebDriverWait(driver_dest, 15)

        try:
            # --- LOGIN ---
            msg_queue.put("Giriş yapılıyor...")
            driver_dest.get("https://pos.gopos.com.tr/")
            wait.until(EC.presence_of_element_located((By.NAME, "loginModel.Username")))
            
            driver_dest.find_element(By.NAME, "loginModel.Username").send_keys(v2_user)
            driver_dest.find_element(By.NAME, "loginModel.Password").send_keys(v2_pass)
            driver_dest.find_element(By.NAME, "loginModel.Password").send_keys(Keys.RETURN)
            
            time.sleep(8) # Login bekleme
            
            # Sayfaya Git
            try:
                kategori_yonetimi_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div/div[1]/div[1]/div[2]/div/a[1]/span")))
                kategori_yonetimi_btn.click()
            except:
                driver_dest.get("https://pos.gopos.com.tr/Product/CategoryList")
            
            time.sleep(3)

            # --- SİLME DÖNGÜSÜ ---
            msg_queue.put("Mevcut veriler temizleniyor...")
            
            while True:
                # 1. Mevcut kategorileri bul (data-type="category")
                categories = driver_dest.find_elements(By.CSS_SELECTOR, "div[data-type='category']")
                
                if not categories:
                    msg_queue.put("Silinecek kategori kalmadı. Temizlik bitti.")
                    break
                
                # Listenin başındaki kategoriyi al
                current_category = categories[0]
                
                # Kategori ismini al (log için)
                try:
                    current_cat_name = current_category.find_element(By.CLASS_NAME, "item-name").text
                except:
                    current_cat_name = "Bilinmeyen Kategori"
                
                msg_queue.put(f"Temizleniyor: {current_cat_name}")

                # Önce kategorinin üzerine tıkla ki ürünleri yüklensin
                # Dikkat: Silme butonuna değil, karta tıklıyoruz.
                try:
                    driver_dest.execute_script("arguments[0].click();", current_category)
                except:
                    current_category.click()
                
                time.sleep(1.5) # Ürünlerin gelmesini bekle

                # 2. İçindeki Ürünleri Sil (data-type="product")
                while True:
                    products = driver_dest.find_elements(By.CSS_SELECTOR, "div[data-type='product']")
                    if not products:
                        break # Ürün kalmadı
                    
                    prod = products[0]
                    try:
                        # Ürünün içindeki silme butonu
                        # CSS: div[data-type='product'] .icon-button-danger[title='Sil']
                        del_btn = prod.find_element(By.CSS_SELECTOR, "button.icon-button-danger[title='Sil']")
                        
                        # Tıkla
                        driver_dest.execute_script("arguments[0].click();", del_btn)
                        
                        # Onay varsa geç
                        time.sleep(0.5)
                        handle_delete_confirm(wait)
                        
                        # DOM'un güncellenmesi için kısa bekleme
                        time.sleep(1)
                    except Exception as e:
                        msg_queue.put(f"Ürün silinemedi, atlanıyor: {str(e)}")
                        break

                # 3. Kategoriyi Sil (Artık içi boş)
                # Kategoriyi tekrar bulmak lazım çünkü DOM değişti
                cats_again = driver_dest.find_elements(By.CSS_SELECTOR, "div[data-type='category']")
                if cats_again:
                    cat_to_del = cats_again[0]
                    try:
                        # Kategorinin silme butonu
                        cat_del_btn = cat_to_del.find_element(By.CSS_SELECTOR, "button.icon-button-danger[title='Sil']")
                        
                        driver_dest.execute_script("arguments[0].click();", cat_del_btn)
                        
                        time.sleep(0.5)
                        handle_delete_confirm(wait)
                        
                        time.sleep(1.5) # Kategori silindikten sonra bekle
                    except Exception as e:
                        msg_queue.put(f"Kategori silinemedi: {str(e)}")
                        break
            
            # ----------------------------------------
            # AŞAMA 3: YENİ VERİ YÜKLEME
            # ----------------------------------------
            msg_queue.put("\n--- AŞAMA 3: Yeni Veriler Yükleniyor ---")
            
            # A. KATEGORİ EKLEME
            unique_categories = df['KategoriAdi'].unique()
            msg_queue.put(f"{len(unique_categories)} kategori oluşturuluyor...")
            
            for cat_name in unique_categories:
                try:
                    new_cat_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div/div[2]/div[1]/div[2]/div/button")))
                    new_cat_btn.click()
                    
                    cat_name_input = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[2]/div/div[1]/input")))
                    cat_name_input.clear()
                    cat_name_input.send_keys(cat_name)
                    
                    icons = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "icon-option")))
                    if icons:
                        icons[0].click() # Senin seçimin, değiştirilmedi.
                    
                    save_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[3]/button[2]")))
                    save_btn.click()
                    
                    time.sleep(1)
                except Exception as e:
                    msg_queue.put(f"HATA (Kategori Ekleme - {cat_name}): {str(e)}")

            msg_queue.put("Kategoriler tamamlandı. Ürünler yükleniyor...")
            time.sleep(2)

            # B. ÜRÜN EKLEME
            for index, row in df.iterrows():
                try:
                    p_name = row['UrunAdi']
                    p_cat = row['KategoriAdi']
                    p_price = str(row['Fiyat']).replace('.', ',')
                    if int(float(row['Fiyat'])) == float(row['Fiyat']):
                        p_price = str(int(row['Fiyat']))
                    
                    ignored_portions = ['normal', 'tek', 'porsiyon', 'standart', 'adet']
                    if row['PorsiyonAdi'] and row['PorsiyonAdi'].lower() not in ignored_portions:
                         final_name = f"{p_name} ({row['PorsiyonAdi']})"
                    else:
                         final_name = p_name

                    msg_queue.put(f"Eklendi ({index+1}/{product_count}): {final_name}")

                    new_prod_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div/div[2]/div[2]/div[1]/div[1]/div[2]/div[2]/button[1]")))
                    new_prod_btn.click()
                    
                    cat_dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[2]/form/div[1]/div[2]/div[2]/div[1]/div[2]/div/div[1]/select")))
                    select_cat = Select(cat_dropdown)
                    try:
                        select_cat.select_by_visible_text(p_cat)
                    except:
                        try:
                            driver_dest.find_element(By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[2]/form/div[2]/button[1]").click()
                        except: pass
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
                    
                    save_prod_btn = driver_dest.find_element(By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[2]/form/div[2]/button[2]")
                    save_prod_btn.click()
                    
                    time.sleep(1)

                except Exception as e:
                    msg_queue.put(f"HATA (Ürün Ekleme): {str(e)}")
                    try:
                        driver_dest.refresh()
                        time.sleep(3)
                    except: pass
            
            msg_queue.put("\nTamamlandı: Eskiler silindi, yeniler eklendi.")

        except Exception as e:
            msg_queue.put(f"GENEL HATA: {str(e)}")

    except Exception as e:
        msg_queue.put(f"KRİTİK HATA: {str(e)}")
    
    finally:
        if 'driver_dest' in locals():
            driver_dest.quit()
        msg_queue.put("PROCESS_DONE")

root.mainloop()
