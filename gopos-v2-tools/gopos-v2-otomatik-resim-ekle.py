from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.ui import Select
import random
import pyautogui

import time
import datetime
import string

while True:
    try:
        # Load Chrome Driver
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
        element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "loginModel.Username"))
            )
        username_field = driver.find_element(By.NAME, "loginModel.Username")
        password_field = driver.find_element(By.NAME, "loginModel.Password")

        username_field.send_keys("menutest@gmail.com")
        password_field.send_keys("123456")

        password_field.send_keys(Keys.RETURN)
        time.sleep(10)

        # Kategori Ürün Yönetimi
        KategoriUrunYonetimi = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div/div[1]/div[2]/div/a[1]/span"))
        )
        KategoriUrunYonetimi.click()

        # Tüm Ürünler
        tum_urunler = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div[2]/div[1]/div[1]/div[2]/button[2]"))
        )
        tum_urunler.click()
        
        urunler = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'product-card-grid')]"))
            )
        
        for urun in urunler:
            duzenle_buton = urun.find_element(
                By.XPATH, 
                ".//button[1]"  # veya daha kesin: ".//div[4]/div[2]/button[1]"
            )

            duzenle_buton.click()
            time.sleep(2)
            resim_yukle_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Görsel Seç ve Düzenle')]"))
            )
    
            driver.execute_script("arguments[0].click();", resim_yukle_button)
            time.sleep(2)
            # Dosya adını yaz
            pyautogui.write("Variety-fruits-vegetables.jpg")

            # Enter'a bas
            pyautogui.press("enter")
            kirp_ve_yukle = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Kırp ve Yükle')]"))
            )
            kirp_ve_yukle.click()

            kaydet = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Kaydet')]"))
            )
            kaydet.click()

    except:
        driver.close()
