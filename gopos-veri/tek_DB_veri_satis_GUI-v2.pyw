import customtkinter as ctk
from tkinter import messagebox
from tkcalendar import DateEntry
from datetime import datetime
import pyodbc
from openpyxl import Workbook

class FixedDateEntry(DateEntry):
    def _show(self):
        super()._show()
        # sadece en önde tut, grab kaldır
        self._top_cal.wm_attributes("-topmost", True)
        self._top_cal.focus_force()

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class ReportApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Satış Raporu Oluşturucu")
        self.geometry("500x350")
        self.resizable(False, False)

        # Bağlantı Bilgileri
        conn_frame = ctk.CTkFrame(self)
        conn_frame.pack(padx=20, pady=(20, 10), fill="x")

        # 1) Server Dropdown
        ctk.CTkLabel(conn_frame, text="Server:").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        self.server_entry = ctk.CTkComboBox(
            conn_frame,
            values=[
                "genel-server.gopos.com.tr",
                "izmir.gopos.com.tr",
                "istanbul.gopos.com.tr",
                "ankara.gopos.com.tr"
            ],
            width=200
        )
        self.server_entry.grid(row=0, column=1, pady=5, sticky="ew", padx=5)
        # Varsayılan seçim
        self.server_entry.set("genel-server.gopos.com.tr")

        # 2) Diğer bağlantı bilgileri
        for i, (label, attr, placeholder, show) in enumerate([
            ("Database:", "db_entry", "veritabanı adı", None),
            ("UID:",      "uid_entry","kullanıcı adı", None),
            ("PWD:",      "pwd_entry","şifre", "*"),
        ], start=1):
            ctk.CTkLabel(conn_frame, text=label).grid(row=i, column=0, sticky="w", pady=5, padx=5)
            entry = ctk.CTkEntry(conn_frame, placeholder_text=placeholder, show=show)
            entry.grid(row=i, column=1, pady=5, padx=5, sticky="ew")
            setattr(self, attr, entry)

        conn_frame.grid_columnconfigure(1, weight=1)

        # Tarih Aralığı
        date_frame = ctk.CTkFrame(self)
        date_frame.pack(padx=20, pady=(0, 10), fill="x")

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

        # Buton ve Durum
        self.generate_btn = ctk.CTkButton(self, text="Raporu Oluştur", command=self.generate_report)
        self.generate_btn.pack(pady=(10,5))
        self.status_label = ctk.CTkLabel(self, text="")
        self.status_label.pack(pady=(5,20))


    def generate_report(self):
        # Girdi alma
        server   = self.server_entry.get().strip()
        database = self.db_entry.get().strip()
        uid      = self.uid_entry.get().strip()
        pwd      = self.pwd_entry.get().strip()
        start_dt = self.start_cal.get_date()
        end_dt   = self.end_cal.get_date()

        if not all([server, database, uid, pwd]):
            messagebox.showwarning("Eksik Bilgi", "Lütfen tüm bağlantı bilgilerini doldurun.")
            return
        if start_dt > end_dt:
            messagebox.showerror("Tarih Hatası", "Başlangıç, bitişten önce olmalı.")
            return

        conn_str = (
            f"DRIVER={{SQL Server Native Client 11.0}};"
            f"SERVER={server};DATABASE={database};"
            f"UID={uid};PWD={pwd};"
        )

        try:
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()

            cursor.execute("SELECT TOP 1 GUID, Tur, Il, Ilce, Ad FROM Isletmeler")
            isletme = cursor.fetchone()
            if not isletme:
                raise Exception("İşletmeler tablosunda veri bulunamadı!")
            guid, tur, il, ilce, ad = isletme

            cursor.execute("SELECT ID, UrunAdi FROM Urunler")
            urun_dict = {r.ID: r.UrunAdi for r in cursor.fetchall()}

            cursor.execute("""
                SELECT AdisyonGrupID, UrunID, Adet, BolgeID, AcilisTarihi
                FROM BAK_PosSatislari
                WHERE AcilisTarihi BETWEEN ? AND ?
            """, start_dt, end_dt)
            satislar = cursor.fetchall()

            wb = Workbook()
            ws = wb.active
            ws.title = "Satış Raporu"
            headers = [
                'Mekan GUID','Adisyon ID','Ürün Adı','Adet',
                'Tip','Tarih','Saat','Tür','Il','Ilce'
            ]
            ws.append(headers)

            for s in satislar:
                urun_adi = urun_dict.get(s.UrunID)
                if not urun_adi: continue
                tarih = s.AcilisTarihi.date() if s.AcilisTarihi else ""
                saat  = s.AcilisTarihi.time() if s.AcilisTarihi else ""
                servis = "Paket" if s.BolgeID==0 else "Masa"
                ws.append([guid, s.AdisyonGrupID, urun_adi, s.Adet,
                           servis, tarih, saat, tur, il, ilce])

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
            ws.column_dimensions["F"].width = 12
            ws.column_dimensions["G"].width = 12

            now = datetime.now()
            fname = f"{ad} - Satış Raporu - {now:%Y-%m-%d} - {now:%H%M%S}.xlsx"
            wb.save(fname)
            self.status_label.configure(text=f"✅ Rapor kaydedildi: {fname}")
        except Exception as ex:
            messagebox.showerror("Hata Oluştu", str(ex))
            self.status_label.configure(text="❌ Rapor oluşturulamadı.")
        finally:
            try: conn.close()
            except: pass

if __name__ == "__main__":
    app = ReportApp()
    app.mainloop()
