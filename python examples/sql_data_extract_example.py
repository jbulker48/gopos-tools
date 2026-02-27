import pyodbc

# Bağlantı string'i oluştur
connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"  # Driver adı (versiyon kontrol edin)
    "SERVER=istanbul.gopos.com.tr;"                       # Sunucu adı veya IP
    "DATABASE=oguzhandeneme;"                  
    "UID=oguzhandeneme;"                       
    "PWD=oguzhandeneme94280;"                               
)

try:
    # Veritabanına bağlan
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    # SQL sorgusunu çalıştır
    cursor.execute("select * from PosSatislari")

    # Tüm verileri çek
    rows = cursor.fetchall()
    
    # Verileri işle
    for row in rows:
        print(row)

except Exception as e:
    print(f"Hata oluştu: {str(e)}")

finally:
    # Bağlantıyı kapat
    if 'conn' in locals():
        conn.close()


print("------------------------------------BREAK HERE-----------------------------------------")

# Bağlantı string'i oluştur
connection_string = (
    "DRIVER={ODBC Driver 17 for SQL Server};"  # Driver adı (versiyon kontrol edin)
    "SERVER=izmir.gopos.com.tr;"                       # Sunucu adı veya IP
    "DATABASE=batuhanyigit;"                  
    "UID=batuhanyigit;"                       
    "PWD=batuhanyigit13225;"                               
)

try:
    # Veritabanına bağlan
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    # SQL sorgusunu çalıştır
    cursor.execute("select * from PosSatislari")

    # Tüm verileri çek
    rows = cursor.fetchall()
    
    # Verileri işle
    for row in rows:
        print(row)

except Exception as e:
    print(f"Hata oluştu: {str(e)}")

finally:
    # Bağlantıyı kapat
    if 'conn' in locals():
        conn.close()