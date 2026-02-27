import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# Base URL and total number of pages
base_url = "https://www.netdata.com/netsite/d9d458c0/tablo"
total_pages = 1293
delay = 1  # Delay in seconds between requests

# List to store all table data
all_data = []

# Loop through each page
for page in range(1, total_pages + 1):
    # Construct URL
    if page == 1:
        url = base_url
    else:
        url = f"{base_url}?p={page}"
    
    try:
        # Fetch the page content
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad responses
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find the table
        table = soup.find('table')
        if not table:
            print(f"Sayfa {page}: Tablo bulunamadı")
            continue
        
        # Extract rows (skip header)
        rows = table.find_all('tr')[1:]
        for row in rows:
            cells = row.find_all('td')
            if len(cells) == 3:  # Ensure row has 3 columns
                id_ = cells[0].text.strip()
                barcode_id = cells[1].text.strip()
                product_name = cells[2].text.strip()
                all_data.append([id_, barcode_id, product_name])
        
        print(f"Sayfa {page} scrape edildi")
        time.sleep(delay)  # Delay to avoid overloading the server
    
    except requests.RequestException as e:
        print(f"Sayfa {page} alınırken hata oluştu: {e}")
        continue

# Create a DataFrame
df = pd.DataFrame(all_data, columns=["ID", "BarcodeId", "ProductName"])

# Save to Excel
df.to_excel("urun_verileri.xlsx", index=False)
print("Veriler 'urun_verileri.xlsx' dosyasına kaydedildi")
