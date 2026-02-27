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
        driver.get("https://pos.gopos.com.tr/")
        driver.maximize_window()
        element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "loginModel.Username"))
            )
        username_field = driver.find_element(By.NAME, "loginModel.Username")
        password_field = driver.find_element(By.NAME, "loginModel.Password")

        username_field.send_keys("tester@gopos.com")
        password_field.send_keys("123456")

        password_field.send_keys(Keys.RETURN)

        time.sleep(10)

        # Kategori Ürün Yönetimi
        time.sleep(3)
        KategoriUrunYonetimi = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div/div[1]/div[1]/div[2]/div/a[1]/span"))
        )
        KategoriUrunYonetimi.click()

        for i in range(50):
            # YeniKategori
            YeniKategori = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div/div[2]/div[1]/div[2]/div/button"))
            )
            YeniKategori.click()

            # Kategori Adı Girme
            kategori_adi_alani = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[2]/div/div[1]/input"))
            )
            rastgele_isim = ''.join(random.choices(string.ascii_letters, k=25))
            kategori_adi_alani.clear()
            kategori_adi_alani.send_keys(rastgele_isim)

            ikonlar = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "icon-option"))
            )

            random.choice(ikonlar).click()

            kaydet_tusu = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/main/div/div[2]/div/div[3]/button[2]"))
            )
            kaydet_tusu.click()
      
        time.sleep(10)

    except:
        driver.close()
