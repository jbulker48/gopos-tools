from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import time
import datetime


cService = webdriver.ChromeService(executable_path=r'C:\Users\GoPos\Desktop\oo-python2\chromedriver.exe')
options = Options()
options.add_argument(r"C:\Users\GoPos\AppData\Local\Google\Chrome\User Data")
driver = webdriver.Chrome(service=cService, options=options)

driver.get("https://admin.gopos.com.tr/Login")
username_field = driver.find_element(By.NAME, "Email")
password_field = driver.find_element(By.NAME, "Sifre")

username_field.send_keys("Admin@gopos.com")
password_field.send_keys("!AdminPos2024--")
password_field.send_keys(Keys.RETURN)

driver.get("https://admin.gopos.com.tr/IsletmeModul/Index?")
time.sleep(2)

search_field = driver.find_element(By.ID, "txt-customerSearch-New")
search_field.send_keys("a")
time.sleep(5)
search_field.send_keys(Keys.BACK_SPACE)
time.sleep(5)

page_html = driver.page_source

now = datetime.datetime.now()
timestamp = now.strftime('%Y%m%d%H%M%S%f')[:17]
fileToWrite = open(f"page_source.html", "w", encoding="utf-8")
fileToWrite.write(page_html)
fileToWrite.close()
