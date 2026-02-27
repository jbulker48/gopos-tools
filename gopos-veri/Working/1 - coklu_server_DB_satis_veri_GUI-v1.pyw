import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import DateEntry
from datetime import datetime
import pyodbc
from openpyxl import Workbook
import threading

class FixedDateEntry(DateEntry):
    def _show(self):
        super()._show()
        self._top_cal.wm_attributes("-topmost", True)
        self._top_cal.focus_force()

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class MultiServerReportApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Çoklu Sunucu Satış Raporu")
        self.geometry("500x550")
        self.resizable(False, False)
        
        # Sunucu kısaltma eşleştirmesi
        self.server_short_names = {
            "istanbul.gopos.com.tr": "istanbul",
            "ankara.gopos.com.tr": "ankara",
            "izmir.gopos.com.tr": "izmir",
            "bursa.gopos.com.tr": "bursa",
            "yedek.gopos.com.tr": "yedek",
            "bursa-3.gopos.com.tr": "bursa3",
            "ist.gopos.com.tr": "istanbul-radore"
        }
        
        # Sabit Kullanıcı Bilgileri
        self.username = "gopos"
        self.password = "GoposPos21@48"
        
        # Sunucu Seçim Çerçevesi
        server_frame = ctk.CTkFrame(self)
        server_frame.pack(padx=20, pady=(20, 10), fill="x")
        
        ctk.CTkLabel(server_frame, text="Sunucular:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        self.server_vars = {}
        servers = list(self.server_short_names.keys())
        
        for server in servers:
            var = ctk.BooleanVar(value=True)
            cb = ctk.CTkCheckBox(
                server_frame, 
                text=f"{server} ({self.server_short_names[server]})",
                variable=var
            )
            cb.pack(anchor="w", padx=5, pady=2)
            self.server_vars[server] = var

        # Tarih Aralığı
        date_frame = ctk.CTkFrame(self)
        date_frame.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(date_frame, text="Başlangıç Tarihi:").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.start_cal = FixedDateEntry(
            date_frame, date_pattern="yyyy-MM-dd",
            mindate=datetime(2000,1,1), maxdate=datetime(2100,12,31),
            width=20
        )
        self.start_cal.grid(row=0, column=1, pady=5, sticky="w", padx=5)

        ctk.CTkLabel(date_frame, text="Bitiş Tarihi:").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        self.end_cal = FixedDateEntry(
            date_frame, date_pattern="yyyy-MM-dd",
            mindate=datetime(2000,1,1), maxdate=datetime(2100,12,31),
            width=20
        )
        self.end_cal.grid(row=1, column=1, pady=5, sticky="w", padx=5)
        date_frame.grid_columnconfigure(1, weight=1)

        # İlerleme çubuğu ve durum bilgisi
        progress_frame = ctk.CTkFrame(self)
        progress_frame.pack(padx=20, pady=(10, 5), fill="x")
        
        self.status_label = ctk.CTkLabel(progress_frame, text="Hazır", text_color="gray")
        self.status_label.pack(anchor="w", pady=(5, 0))
        
        self.db_count_label = ctk.CTkLabel(progress_frame, text="0/0 veritabanı işlendi", text_color="gray")
        self.db_count_label.pack(anchor="w", pady=(0, 5))
        
        self.progress = ctk.CTkProgressBar(progress_frame, mode="determinate")
        self.progress.pack(fill="x", pady=5)
        self.progress.set(0)
        
        # Buton
        self.generate_btn = ctk.CTkButton(
            self, 
            text="Raporu Oluştur", 
            command=self.start_report_thread
        )
        self.generate_btn.pack(pady=15)
        
        # Sonuç bilgisi
        self.result_label = ctk.CTkLabel(self, text="", text_color="green")
        self.result_label.pack(pady=(0, 10))
        
        # Değişkenler
        self.total_databases = 0
        self.processed_databases = 0
        self.total_records = 0

    def start_report_thread(self):
        """Rapor oluşturma işlemini ayrı bir thread'de başlat"""
        if not any(var.get() for var in self.server_vars.values()):
            messagebox.showwarning("Uyarı", "En az bir sunucu seçmelisiniz!")
            return
            
        start_dt = self.start_cal.get_date()
        end_dt = self.end_cal.get_date()
        
        if start_dt > end_dt:
            messagebox.showerror("Hata", "Başlangıç tarihi bitiş tarihinden sonra olamaz!")
            return
        
        # UI elemanlarını güncelle
        self.generate_btn.configure(state="disabled")
        self.status_label.configure(text="Veritabanları taranıyor...", text_color="black")
        self.db_count_label.configure(text="0/0 veritabanı işlendi")
        self.result_label.configure(text="")
        self.progress.set(0)
        self.total_databases = 0
        self.processed_databases = 0
        self.total_records = 0
        
        # Seçili sunucuları al
        selected_servers = [
            server for server, var in self.server_vars.items() 
            if var.get()
        ]
        
        # Rapor thread'ini başlat
        thread = threading.Thread(
            target=self.generate_report,
            args=(selected_servers, start_dt, end_dt),
            daemon=True
        )
        thread.start()

    def generate_report(self, servers, start_dt, end_dt):
        """Rapor oluşturma işlemini gerçekleştir"""
        try:
            # 1. ADIM: Toplam veritabanı sayısını hesapla
            self.update_status("Veritabanları taranıyor...")
            total_dbs = self.calculate_total_databases(servers)
            self.update_progress(0, total_dbs)
            
            if total_dbs == 0:
                self.update_status("İşlenecek veritabanı bulunamadı")
                self.complete_report("", 0)
                return
                
            # 2. ADIM: Excel dosyasını hazırla
            wb = Workbook()
            ws = wb.active
            ws.title = "Tüm Satışlar"
            headers = [
                'Sunucu', 'Veritabanı', 'Mekan ID', 'Adisyon ID', 'Ürün Adı', 'Adet',
                'Tür', 'Tarih', 'Saat', 'Tip', 'Il', 'Ilce', 'Mekan Adı'
            ]
            ws.append(headers)
            
            # 3. ADIM: Veritabanlarını işle
            self.update_status("Veritabanları işleniyor...")
            total_records = 0
            processed_dbs = 0
            
            for server in servers:
                self.update_status(f"{server} işleniyor...")
                
                try:
                    # Master veritabanına bağlan
                    master_conn_str = (
                        f"DRIVER={{SQL Server Native Client 11.0}};"
                        f"SERVER={server};DATABASE=master;"
                        f"UID={self.username};PWD={self.password};"
                    )
                    master_conn = pyodbc.connect(master_conn_str)
                    master_cursor = master_conn.cursor()
                    
                    # Kullanıcı veritabanlarını al
                    master_cursor.execute("""
                        SELECT name FROM sys.databases
                        WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')
                        AND state = 0
                    """)
                    databases = [row.name for row in master_cursor.fetchall()]
                    master_conn.close()
                    
                    for db in databases:
                        try:
                            self.update_status(f"   {db}")
                            # Veritabanına bağlan
                            db_conn_str = (
                                f"DRIVER={{SQL Server Native Client 11.0}};"
                                f"SERVER={server};DATABASE={db};"
                                f"UID={self.username};PWD={self.password};"
                            )
                            conn = pyodbc.connect(db_conn_str)
                            cursor = conn.cursor()
                            
                            # İşletme bilgilerini al
                            cursor.execute("SELECT TOP 1 GUID, Tur, Il, Ilce, Ad FROM Isletmeler")
                            isletme_data = cursor.fetchone()
                            if not isletme_data:
                                processed_dbs += 1
                                self.update_progress(processed_dbs, self.total_databases)
                                continue
                            
                            guid, tur, il, ilce, ad = isletme_data
                            
                            # Ürün sözlüğü oluştur
                            cursor.execute("SELECT ID, UrunAdi FROM Urunler")
                            urun_dict = {row.ID: row.UrunAdi for row in cursor.fetchall()}
                            
                            # Satış verilerini al
                            cursor.execute("""
                                SELECT 
                                    AdisyonGrupID,
                                    UrunID,
                                    Adet,
                                    BolgeID,
                                    AcilisTarihi
                                FROM BAK_PosSatislari
                                WHERE AcilisTarihi >= ? AND AcilisTarihi <= ?
                            """, start_dt, end_dt)
                            
                            db_records = 0
                            for row in cursor.fetchall():
                                urun_adi = urun_dict.get(row.UrunID)
                                if not urun_adi:
                                    continue
                                
                                tarih = row.AcilisTarihi.date() if row.AcilisTarihi else ""
                                saat = row.AcilisTarihi.time() if row.AcilisTarihi else ""
                                servis = "Paket" if row.BolgeID == 0 else "Masa"
                                
                                ws.append([
                                    server, db, guid, row.AdisyonGrupID, urun_adi,
                                    row.Adet, servis, tarih, saat, tur, il, ilce, ad
                                ])
                                db_records += 1
                            
                            total_records += db_records
                            conn.close()
                            
                        except Exception as e:
                            self.update_status(f"  Hata: {str(e)}")
                        
                        # İlerlemeyi güncelle
                        processed_dbs += 1
                        self.update_progress(processed_dbs, self.total_databases)
                
                except Exception as e:
                    self.update_status(f"Sunucu hatası: {str(e)}")
            
            # 4. ADIM: Raporu kaydet
            if total_records > 0:
                timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
                server_prefix = self.get_server_prefix(servers)
                filename = f"{server_prefix}Satis_Raporu_{timestamp}.xlsx"

                # Yeniden boyutlandır
                for col in ws.columns:
                    max_length = 0
                    column = col[0].column_letter
                    for cell in col:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(cell.value)
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    ws.column_dimensions[column].width = adjusted_width
                # Tarih ve saat için özel boyut
                ws.column_dimensions["H"].width = 12
                ws.column_dimensions["I"].width = 12

                wb.save(filename)
                self.complete_report(filename, total_records)
            else:
                self.complete_report("", 0, no_records=True)
            
        except Exception as e:
            self.report_error(str(e))

    def calculate_total_databases(self, servers):
        """Toplam işlenecek veritabanı sayısını hesapla"""
        total_dbs = 0
        
        for server in servers:
            try:
                # Master veritabanına bağlan
                master_conn_str = (
                    f"DRIVER={{SQL Server Native Client 11.0}};"
                    f"SERVER={server};DATABASE=master;"
                    f"UID={self.username};PWD={self.password};"
                )
                master_conn = pyodbc.connect(master_conn_str)
                master_cursor = master_conn.cursor()
                
                # Kullanıcı veritabanlarını say
                master_cursor.execute("""
                    SELECT COUNT(name) 
                    FROM sys.databases
                    WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')
                    AND state = 0
                """)
                count = master_cursor.fetchone()[0]
                total_dbs += count
                master_conn.close()
                
                self.update_status(f"{server}: {count} veritabanı bulundu")
                
            except Exception as e:
                self.update_status(f"{server} tarama hatası: {str(e)}")
        
        self.total_databases = total_dbs
        return total_dbs

    def get_server_prefix(self, servers):
        """Seçilen sunuculara göre dosya adı öneki oluştur"""
        # Sunucuların kısa isimlerini al
        short_names = [self.server_short_names[server] for server in servers]
        
        # Alfabetik olarak sırala
        short_names.sort()
        
        # Önek oluştur (örnek: "ankara_bursa_")
        prefix = "_".join(short_names) + "_"
        return prefix

    def update_status(self, message):
        """Durum etiketini thread-safe güncelleme"""
        self.after(0, lambda: self.status_label.configure(text=message))

    def update_progress(self, processed, total):
        """İlerleme çubuğunu ve sayacı güncelle"""
        self.after(0, lambda: self.db_count_label.configure(
            text=f"{processed}/{total} veritabanı işlendi"
        ))
        
        if total > 0:
            progress_value = processed / total
            self.after(0, lambda: self.progress.set(progress_value))

    def complete_report(self, filename, count, no_records=False):
        """Rapor tamamlandığında UI güncelleme"""
        if no_records:
            self.after(0, lambda: self.result_label.configure(
                text="❌ Hiç kayıt bulunamadı",
                text_color="orange"
            ))
        elif filename:
            self.after(0, lambda: self.result_label.configure(
                text=f"✅ Rapor oluşturuldu: {filename}\nToplam {count} kayıt",
                text_color="green"
            ))
        
        self.after(0, lambda: self.generate_btn.configure(state="normal"))
        self.after(0, lambda: self.status_label.configure(text="Hazır", text_color="gray"))

    def report_error(self, error):
        """Hata durumunda UI güncelleme"""
        self.after(0, lambda: self.result_label.configure(
            text=f"❌ Hata: {error}",
            text_color="red"
        ))
        self.after(0, lambda: self.generate_btn.configure(state="normal"))
        self.after(0, lambda: self.status_label.configure(text="Hazır", text_color="gray"))

if __name__ == "__main__":
    app = MultiServerReportApp()
    app.mainloop()
