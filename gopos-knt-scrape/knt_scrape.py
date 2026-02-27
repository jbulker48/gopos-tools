from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from openpyxl import load_workbook
from openpyxl.styles import NamedStyle
from openpyxl.utils import get_column_letter
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options

import time
import datetime
import pandas as pd

# Load Chrome Driver
# Chrome Driver otomatik kurulum
options = Options()
# options.add_argument(r"C:\Users\GoPos\AppData\Local\Google\Chrome\User Data")  # Gerekirse açın
driver = webdriver.Chrome(
    service=ChromeService(ChromeDriverManager().install()),
    options=options
)

# Load Page and login
driver.get("https://portal.mysoft.com.tr/#!/login")
time.sleep(2)
username_field = driver.find_element(By.NAME, "Login_UserName")
password_field = driver.find_element(By.NAME, "Login_Password")

username_field.send_keys("info@gopos.com.tr")
password_field.send_keys("X2loKHO4")
password_field.send_keys(Keys.RETURN)
time.sleep(2)

driver.get("https://portal.mysoft.com.tr/#!/app/TenantDocumentUsageSummary")
wait = WebDriverWait(driver, 10)
button = wait.until(
    EC.element_to_be_clickable((By.XPATH, '//*[@id="Index_Header"]/div[1]/div[3]/div/div/div/div/button'))
)
button.click()
time.sleep(10)
