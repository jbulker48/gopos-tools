from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import random

import time
import datetime

# Load Chrome Driver
while True:
    try:
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
        driver.get("https://pos.gopos.com.tr/")
        driver.maximize_window()
        element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "loginModel.Username"))
            )
        username_field = driver.find_element(By.NAME, "loginModel.Username")
        password_field = driver.find_element(By.NAME, "loginModel.Password")

        username_field.send_keys("tester2@gopos.com")
        password_field.send_keys("123456")

        password_field.send_keys(Keys.RETURN)

        # Open a Table
        time.sleep(3)
        PosEkrani = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'POS')]"))
        )
        PosEkrani.click()
        time.sleep(35)

        while True:
            masalar = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'masa-orta-icerik')]"))
            )
            rastgele_masa = random.choice(masalar)
            rastgele_masa.click()

            # 10 tane ürün gir
            for s in range(10):
                time.sleep(0.2)
                kategoriler = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@class, 'category-filter-btn')]"))
                )
                rastgele_kategori = random.choice(kategoriler)
                rastgele_kategori.click()
                kategori_adi = rastgele_kategori.find_element(By.TAG_NAME, "span").text
                # Kategori adını yazdır
                print(f"Seçilen kategori: {kategori_adi}")
                time.sleep(0.2)

                urunler = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'product-item')]"))
                )
                rastgele_urun = random.choice(urunler)
                rastgele_urun.click()
                urun_adi = rastgele_urun.find_element(By.CLASS_NAME, "product-name").text
                # Ürün adını yazdır
                print(f"Seçilen ürün: {urun_adi}")
                time.sleep(0.2)

            # Ödeme Al:
            odeme_tipleri = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@class, 'payment-method-btn')]"))
            )
            rastgele_odeme_tipi = random.choice(odeme_tipleri)
            rastgele_odeme_tipi.click()

            evet_tusu = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/div[3]/button[2]"))
            )
            evet_tusu.click()
    
            print("Ödeme alındı.")
            time.sleep(0.2)
    except:
        driver.close()
        continue
