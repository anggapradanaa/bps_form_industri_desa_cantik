import os
import io
import json
import base64
import pandas as pd
import streamlit as st
import gspread
from datetime import date
from google.oauth2.service_account import Credentials
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Paragraph

# Judul dan konfigurasi halaman
st.set_page_config(page_title="Formulir Pendataan Industri Pengolahan", layout="wide")

# Judul aplikasi
st.title("Pendataan Industri Pengolahan di Kelurahan Kejambon")
st.markdown("#### Kelurahan Cinta Statistik 2025")

# Fungsi untuk menghubungkan ke Google Sheets
@st.cache_resource
def connect_to_gsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        # Cek apakah ada secrets yang tersedia
        if "gcp_service_account" in st.secrets:
            # Gunakan secrets jika tersedia
            credentials = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=scope
            )
            st.success("Berhasil menggunakan kredensial dari secrets.")
        else:
            # Definisikan path kredensial yang mungkin
            cred_paths = [
                r"D:\Perkuliahan\PRIGEL\Form Pendataan Desa Cantik\brave-reason-460003-d0-af9a852a98c9.json",
                # Tambahkan path alternatif lain jika ada
                "credentials.json",  # Untuk path relatif di direktori yang sama
                os.path.join(os.path.expanduser("~"), "credentials.json")  # Di home directory
            ]

            credentials_found = False
            for cred_path in cred_paths:
                if os.path.exists(cred_path):
                    st.info(f"Menggunakan kredensial dari file: {cred_path}")
                    credentials = Credentials.from_service_account_file(
                        cred_path,
                        scopes=scope
                    )
                    credentials_found = True
                    break
            
            if not credentials_found:
                st.error("Tidak dapat menemukan file kredensial Google Cloud. Pastikan Anda telah menempatkan file credentials.json di direktori yang benar.")
                return None
        
        # Authorize dengan gspread
        client = gspread.authorize(credentials)
        
        # Buka spreadsheet dengan ID
        spreadsheet_id = '1bb8_rTHLUKANZyi30FGRZO5vl44siHheV2AaFomH-D4'  
        
        try:
            spreadsheet = client.open_by_key(spreadsheet_id)
        except gspread.exceptions.SpreadsheetNotFound:
            st.error(f"Spreadsheet dengan ID {spreadsheet_id} tidak ditemukan. Periksa ID dan pastikan kredensial memiliki akses.")
            return None
        except gspread.exceptions.APIError as e:
            if "quota" in str(e).lower():
                st.error("Kuota Google Sheets API terlampaui. Coba lagi nanti.")
            else:
                st.error(f"Error API Google Sheets: {e}")
            return None
        
        # Coba dapatkan worksheet, jika tidak ada, buat baru
        try:
            worksheet = spreadsheet.worksheet("Data Industri")
            
            # Periksa jumlah baris yang sudah ada
            try:
                all_values = worksheet.get_all_values()
                current_rows = len(all_values)
                if current_rows > 900:  # Warning jika mendekati batas
                    st.warning(f"Perhatian: Sheet sudah berisi {current_rows} baris data dari 1000 baris. Pertimbangkan untuk membuat sheet baru.")
            except:
                pass  # Jika gagal mendapatkan jumlah baris, lanjutkan saja
                
        except gspread.exceptions.WorksheetNotFound:
            # Worksheet tidak ditemukan, buat baru
            worksheet = spreadsheet.add_worksheet(title="Data Industri", rows=1000, cols=30)
            
            # Tambahkan header
            headers = [
                "Provinsi", "Kabupaten/Kota", "Kecamatan", "Desa/Kelurahan", "RT/RW", 
                "Nama Pendata", "Nama Pemeriksa", "Tanggal", "Timestamp",
                "Jumlah Industri Makanan", "Jumlah Industri Alat Rumah Tangga", 
                "Jumlah Industri Material Bahan Bangunan", "Jumlah Industri Alat Pertanian",
                "Jumlah Industri Kerajinan selain logam", "Jumlah Industri Logam", 
                "Jumlah Industri Lainnya", "Nama Usaha", "Nama Pemilik", "Jumlah Tenaga Kerja",
                "Ind.Makanan(3.1)", "Ind.Alat RT(3.2)", "Ind.Material(3.3)", 
                "Ind.Alat Pertanian(3.4)", "Ind.Kerajinan(3.5)", "Ind.Logam(3.6)", 
                "Ind.Lainnya(3.7)"
            ]
            worksheet.append_row(headers)
            st.success("Worksheet 'Data Industri' berhasil dibuat!")
            
        return worksheet
        
    except Exception as e:
        st.error(f"Terjadi kesalahan dalam koneksi ke Google Sheets: {str(e)}")
        import traceback
        st.error(traceback.format_exc())  # Untuk debugging
        return None

# Fungsi untuk membuat PDF
def create_pdf(form_data, usaha_data):
    # Perbaikan import statement - mengubah import ParagraphStyle
    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Konstanta untuk mengelola tata letak PDF
    page_margin = 50 # Margin dari tepi halaman
    max_text_width = width - (2 * page_margin) # Lebar maksimum untuk text
    header_height = 100 # Ruang untuk header halaman
    block_spacing = 30 # Spasi antar blok
    row_height = 25 # Tinggi baris standar
    
    # Fungsi utilitas untuk membuat text yang bisa wrap
    def get_wrapped_text(text, max_width, font_name, font_size):
        if not text:
            return [""]
        
        c.setFont(font_name, font_size)
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if c.stringWidth(test_line, font_name, font_size) <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Jika satu kata sudah terlalu panjang, potong saja kata tersebut
                    truncated_word = word
                    while c.stringWidth(truncated_word, font_name, font_size) > max_width:
                        truncated_word = truncated_word[:-1]
                    
                    lines.append(truncated_word)
                    current_line = []
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines
    
    # Fungsi untuk membuat header pada setiap halaman
    def create_header(canvas, page_number=1):
        canvas.setFont("Times-Bold", 14)
        
        # Judul dalam huruf kapital
        judul = "PENDATAAN INDUSTRI PENGOLAHAN DI KELURAHAN KEJAMBON"
        text_width = canvas.stringWidth(judul, "Times-Bold", 14)
        canvas.drawString((width - text_width) / 2, height - 50, judul)

        # Subjudul
        canvas.setFont("Times-Bold", 14)
        subjudul = "KELURAHAN CINTA STATISTIK 2025"
        text_width = canvas.stringWidth(subjudul, "Times-Bold", 14)
        canvas.drawString((width - text_width) / 2, height - 80, subjudul)
        
        # Nomor halaman
        if page_number > 1:
            canvas.setFont("Times-Roman", 10)
            page_text = f"Halaman {page_number}"
            canvas.drawString(width - 80, height - 30, page_text)

    # Halaman pertama - Header, BLOK I, BLOK II, dan BLOK III
    create_header(c)
    y_position = height - header_height
    
    # Sediakan ruang untuk setiap blok data
    block_heights = {
        "blok_i": 120,   # Estimasi tinggi BLOK I
        "blok_ii": 90,   # Estimasi tinggi BLOK II
        "blok_iii": 180  # Estimasi tinggi BLOK III
    }

    # BLOK I
    data = [
        ["BLOK I. KETERANGAN TEMPAT", "", ""],
        ["1.1", "Provinsi", form_data["provinsi"]],
        ["1.2", "Kabupaten/Kota", form_data["kabupaten"]],
        ["1.3", "Kecamatan", form_data["kecamatan"]],
        ["1.4", "Desa/Kelurahan", form_data["desa"]],
        ["1.5", "SLS (RT/RW)", f"RT {form_data['rt']} RW {form_data['rw']}"]
    ]
    
    table = Table(data, colWidths=[40, 150, 300])
    table.setStyle(TableStyle([
        ('GRID', (0, 1), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, 0), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),
        ('SPAN', (0, 0), (2, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    # Periksa apakah BLOK I muat di halaman ini
    if y_position - block_heights["blok_i"] < page_margin:
        c.showPage()
        create_header(c, 2)
        y_position = height - header_height
    
    table.wrapOn(c, width, height)
    table.drawOn(c, page_margin, y_position - block_heights["blok_i"])
    y_position -= (block_heights["blok_i"] + block_spacing)

    # BLOK II
    data = [
        ["BLOK II. KETERANGAN PENDATAAN", "", "", "", ""],
        ["", "Uraian", "Nama", "Tanggal", "Tanda Tangan"],
        ["2.1", "Pendata", form_data["nama_pendata"], form_data["tanggal"], ""],
        ["2.2", "Pemeriksa", form_data["nama_pemeriksa"], form_data["tanggal"], ""]
    ]
    
    table = Table(data, colWidths=[40, 100, 150, 100, 100])
    table.setStyle(TableStyle([
        ('GRID', (0, 1), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, 0), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
        ('ALIGN', (0, 2), (0, -1), 'CENTER'),
        ('SPAN', (0, 0), (4, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    # Periksa apakah BLOK II muat di halaman ini
    if y_position - block_heights["blok_ii"] < page_margin:
        c.showPage()
        create_header(c, 2)
        y_position = height - header_height
    
    table.wrapOn(c, width, height)
    table.drawOn(c, page_margin, y_position - block_heights["blok_ii"])
    y_position -= (block_heights["blok_ii"] + block_spacing)

    # BLOK III
    data = [
        ["BLOK III. REKAPITULASI", "", ""],
        ["", "Industri Mikro Kecil dan Menengah", "Jumlah (diisi oleh Pemeriksa)"],
        ["3.1", "Industri Makanan", form_data["jml_industri_makanan"]],
        ["3.2", "Industri Alat Rumah Tangga", form_data["jml_industri_alat_rt"]],
        ["3.3", "Industri Material Bahan Bangunan", form_data["jml_industri_material"]],
        ["3.4", "Industri Alat Pertanian", form_data["jml_industri_alat_pertanian"]],
        ["3.5", "Industri Kerajinan selain logam", form_data["jml_industri_kerajinan"]],
        ["3.6", "Industri Logam", form_data["jml_industri_logam"]],
        ["3.7", "Industri Lainnya", form_data["jml_industri_lainnya"]],
    ]
    
    table = Table(data, colWidths=[40, 250, 200])
    table.setStyle(TableStyle([
        ('GRID', (0, 1), (-1, -1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, 0), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
        ('ALIGN', (0, 2), (0, -1), 'CENTER'),
        ('SPAN', (0, 0), (2, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    
    # Periksa apakah BLOK III muat di halaman ini
    if y_position - block_heights["blok_iii"] < page_margin:
        c.showPage()
        create_header(c, 2)
        y_position = height - header_height
    
    table.wrapOn(c, width, height)
    table.drawOn(c, page_margin, y_position - block_heights["blok_iii"])

    # Halaman Baru untuk BLOK IV
    c.showPage()
    page_number = 2
    create_header(c, page_number)

    # Konstanta untuk tata letak BLOK IV
    block_iv_header_height = 80  # Tinggi header BLOK IV
    max_rows_per_page = (height - header_height - block_iv_header_height - page_margin) // row_height
    
    # Definisi lebar kolom
    col_widths = [30, 100, 100, 30, 30, 30, 30, 30, 30, 30, 60]
    
    # Hitung total industri dan tenaga kerja
    total_industri = [0] * 7
    total_tenaga_kerja = 0
    for usaha in usaha_data:
        for j in range(1, 8):
            if f"3.{j}" in usaha["kode_industri"]:
                total_industri[j-1] += 1
        total_tenaga_kerja += int(usaha["jumlah_tenaga_kerja"])
    
    # Fungsi untuk membuat dan menggambar header tabel BLOK IV
    def draw_block_iv_header(canvas, y_pos):
        headers = [
            ["BLOK IV. KETERANGAN USAHA", "", "", "", "", "", "", "", "", "", ""],
            ["No", "Nama Usaha", "Nama Pemilik", "Kode Jenis Industri Mikro Kecil dan Menengah", "", "", "", "", "", "", "Jumlah\nTenaga Kerja"],
            ["", "", "", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", ""]
        ]
        header_table = Table(headers, colWidths=col_widths)
        header_table.setStyle(TableStyle([
            ('GRID', (0, 1), (-1, -1), 0.5, colors.black),
            ('GRID', (0, 1), (-1, 2), 0.5, colors.black),
            ('BOX', (0, 0), (-1, 0), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('SPAN', (0, 0), (10, 0)),
            ('SPAN', (0, 1), (0, 2)),
            ('SPAN', (1, 1), (1, 2)),
            ('SPAN', (2, 1), (2, 2)),
            ('SPAN', (3, 1), (9, 1)),
            ('SPAN', (10, 1), (10, 2)),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('BACKGROUND', (0, 1), (-1, 2), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('PADDING', (0, 0), (-1, -1), 3),  # Kurangi padding agar tidak terlihat berspasi
        ]))
        header_table.wrapOn(canvas, width, height)
        header_table.drawOn(canvas, page_margin, y_pos - block_iv_header_height)
        return y_pos - block_iv_header_height

    # Fungsi untuk menghitung tinggi baris yang diperlukan untuk teks yang di-wrap
    def calculate_row_height(name_usaha, name_pemilik, max_width_usaha, max_width_pemilik, font_name, font_size):
        lines_usaha = len(get_wrapped_text(name_usaha, max_width_usaha, font_name, font_size))
        lines_pemilik = len(get_wrapped_text(name_pemilik, max_width_pemilik, font_name, font_size))
        max_lines = max(lines_usaha, lines_pemilik, 1)  # Minimal 1 baris
        return max_lines * (row_height - 6)  # Tinggi baris dasar dikurangi sedikit untuk padding

    # Fungsi untuk menggambar baris data dengan handling wrapping teks
    def draw_usaha_rows(canvas, start_index, end_index, y_pos):
        # Siapkan data untuk tabel dengan paragraf untuk teks panjang
        rows_data = []
        row_heights = []
        
        # Persiapkan style paragraf untuk text wrapping
        style = ParagraphStyle(
            name='Normal',
            fontName='Times-Roman',
            fontSize=10,
            leading=12,  # Jarak antar baris dalam paragraf
            alignment=0  # 0=kiri, 1=tengah, 2=kanan
        )
        
        for i in range(start_index, min(end_index, len(usaha_data))):
            usaha = usaha_data[i]
            
            # Gunakan Paragraph untuk teks yang panjang
            nama_usaha_para = Paragraph(usaha["nama_usaha"], style)
            nama_pemilik_para = Paragraph(usaha["nama_pemilik"], style)
            
            row = [str(i+1), nama_usaha_para, nama_pemilik_para]
            for j in range(1, 8):
                kode = f"3.{j}"
                row.append("✓" if kode in usaha["kode_industri"] else "")
            row.append(str(usaha["jumlah_tenaga_kerja"]))
            rows_data.append(row)
            
            # Minimal tinggi baris adalah 30 poin (bisa disesuaikan)
            # Kita tidak perlu menghitung tinggi secara manual lagi,
            # karena ReportLab akan menghitungnya berdasarkan Paragraph
            row_heights.append(30)
        
        if rows_data:
            # Buat tabel dengan baris data yang sudah berisi Paragraph
            data_table = Table(rows_data, colWidths=col_widths)
            
            data_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # Kolom No (0) tengah
                ('ALIGN', (3, 0), (9, -1), 'CENTER'),  # Kode industri tengah
                ('ALIGN', (10, 0), (10, -1), 'CENTER'), # Jumlah tenaga kerja tengah
                ('FONTNAME', (0, 0), (0, -1), 'Times-Roman'),
                ('FONTNAME', (3, 0), (-1, -1), 'Times-Roman'),
                ('PADDING', (0, 0), (-1, -1), 2),      # Kurangi padding lebih lagi
            ]))
            
            # Biarkan ReportLab menentukan tinggi yang tepat
            w, h = data_table.wrapOn(canvas, width - 2*page_margin, height)
            data_table.drawOn(canvas, page_margin, y_pos - h)
            return y_pos - h
        
        return y_pos

    # Fungsi untuk menggambar baris jumlah
    def draw_total_row(canvas, y_pos):
        jumlah_row = [["Jumlah", "", ""] + [str(j) for j in total_industri] + [str(total_tenaga_kerja)]]
        total_table = Table(jumlah_row, colWidths=col_widths)
        total_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('SPAN', (0, 0), (2, 0)), # Gabungkan 3 kolom pertama untuk "Jumlah"
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Times-Bold'),
            ('PADDING', (0, 0), (-1, -1), 2),  # Kurangi padding agar tidak terlihat berspasi
        ]))
        w, h = total_table.wrapOn(canvas, width - 2*page_margin, height)
        total_table.drawOn(canvas, page_margin, y_pos - h)
        return y_pos - h

    # Proses menghitung tinggi baris yang diperlukan untuk setiap data usaha
    row_heights = []
    for usaha in usaha_data:
        height_needed = calculate_row_height(
            usaha["nama_usaha"], 
            usaha["nama_pemilik"],
            col_widths[1] - 12,
            col_widths[2] - 12,
            "Times-Roman", 
            10
        )
        row_heights.append(height_needed)

    # Mulai menggambar BLOK IV
    y_position = height - header_height  # Posisi awal setelah header halaman
    
    # Gambar header BLOK IV
    y_position = draw_block_iv_header(c, y_position)
    
    # Inisialisasi style paragraph untuk digunakan nanti
    styles = getSampleStyleSheet()
    normal_style = styles['Normal']
    normal_style.fontSize = 10
    normal_style.fontName = 'Times-Roman'
    normal_style.leading = 12  # Jarak antar baris
    
    # Proses data usaha per halaman
    current_row = 0
    
    while current_row < len(usaha_data):
        # Tentukan perkiraan berapa baris yang bisa ditampilkan
        rows_left = len(usaha_data) - current_row
        estimated_rows = min(max_rows_per_page, rows_left)
        
        # Gambar baris-baris data
        new_y_position = draw_usaha_rows(c, current_row, current_row + estimated_rows, y_position)
        rows_drawn = min(estimated_rows, rows_left)
        current_row += rows_drawn
        y_position = new_y_position
        
        # Cek apakah ini adalah baris terakhir
        if current_row >= len(usaha_data):
            # Jika sudah mencapai baris terakhir, tambahkan baris total
            if (y_position - 30) >= page_margin:  # Perkiraan tinggi baris total
                draw_total_row(c, y_position)
            else:
                # Tidak cukup ruang, buat halaman baru untuk total
                c.showPage()
                page_number += 1
                create_header(c, page_number)
                y_position = height - header_height
                y_position = draw_block_iv_header(c, y_position)
                draw_total_row(c, y_position)
        elif (y_position - 30) < page_margin:
            # Tidak cukup ruang untuk baris berikutnya, buat halaman baru
            c.showPage()
            page_number += 1
            create_header(c, page_number)
            y_position = height - header_height
            y_position = draw_block_iv_header(c, y_position)
    
    # Selesai membuat PDF
    c.save()
    buffer.seek(0)
    return buffer

# Fungsi untuk menyimpan data ke Google Sheets
def save_to_gsheet(worksheet, form_data, usaha_data):
    if worksheet is None:
        st.error("Tidak dapat menyimpan data: koneksi worksheet tidak tersedia")
        return False

    try:
        # Siapkan timestamp untuk tracking
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Untuk efisiensi, siapkan semua baris sekaligus untuk append_rows
        all_rows = []
        
        for usaha in usaha_data:
            # Siapkan kolom industri sebagai biner (1 atau 0)
            industri_flags = {
                "3.1": 0,
                "3.2": 0,
                "3.3": 0,
                "3.4": 0,
                "3.5": 0,
                "3.6": 0,
                "3.7": 0
            }
            for kode in usaha["kode_industri"]:
                if kode in industri_flags:
                    industri_flags[kode] = 1

            # Susun baris data
            row_data = [
                form_data["provinsi"],
                form_data["kabupaten"],
                form_data["kecamatan"],
                form_data["desa"],
                f"RT {form_data['rt']} RW {form_data['rw']}",
                form_data["nama_pendata"],
                form_data["nama_pemeriksa"],
                form_data["tanggal"],
                timestamp,  # Tambahkan timestamp
                form_data["jml_industri_makanan"],
                form_data["jml_industri_alat_rt"],
                form_data["jml_industri_material"],
                form_data["jml_industri_alat_pertanian"],
                form_data["jml_industri_kerajinan"],
                form_data["jml_industri_logam"],
                form_data["jml_industri_lainnya"],
                usaha["nama_usaha"],
                usaha["nama_pemilik"],
                usaha["jumlah_tenaga_kerja"],
                industri_flags["3.1"],
                industri_flags["3.2"],
                industri_flags["3.3"],
                industri_flags["3.4"],
                industri_flags["3.5"],
                industri_flags["3.6"],
                industri_flags["3.7"]
            ]
            
            # Tambahkan ke daftar baris
            all_rows.append(row_data)

        # Jika ada data untuk disimpan
        if all_rows:
            # Cek ruang yang tersedia
            try:
                cell_values = worksheet.get_all_values()
                current_rows = len(cell_values)
                if current_rows + len(all_rows) > 1000:
                    st.warning(f"Perhatian: Setelah menambahkan data ini, sheet akan berisi {current_rows + len(all_rows)} baris dari 1000 baris maksimum.")
            except:
                pass  # Jika gagal memeriksa, lanjutkan saja
            
            # Simpan semua baris sekaligus untuk efisiensi
            try:
                # Gunakan batch append untuk efisiensi
                if len(all_rows) > 1:
                    worksheet.append_rows(all_rows)
                    st.success(f"Berhasil menyimpan {len(all_rows)} data usaha ke Google Sheets!")
                else:
                    worksheet.append_row(all_rows[0])
                    st.success("Berhasil menyimpan data usaha ke Google Sheets!")
                
                return True
            except gspread.exceptions.APIError as e:
                if "quota" in str(e).lower():
                    st.error("Kuota Google Sheets API terlampaui. Coba lagi nanti atau simpan data secara lokal terlebih dahulu.")
                else:
                    st.error(f"Error API Google Sheets: {e}")
                return False
        else:
            st.warning("Tidak ada data usaha untuk disimpan.")
            return False
            
    except Exception as e:
        st.error(f"Terjadi kesalahan saat menyimpan data: {e}")
        import traceback
        st.error(traceback.format_exc())  # Untuk debugging
        return False

# Inisialisasi state
if 'page' not in st.session_state:
    st.session_state.page = 'form'
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}
if 'usaha_data' not in st.session_state:
    st.session_state.usaha_data = []
if 'current_usaha' not in st.session_state:
    st.session_state.current_usaha = 0
if 'jumlah_usaha' not in st.session_state:
    st.session_state.jumlah_usaha = 0
if 'data_saved' not in st.session_state:
    st.session_state.data_saved = False    
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = None
if 'edit_form_data' not in st.session_state:
    st.session_state.edit_form_data = {}
if 'edit_usaha_index' not in st.session_state:
    st.session_state.edit_usaha_index = 0

# Fungsi untuk mengatur halaman
def set_page(page):
    st.session_state.page = page

# Fungsi untuk menyimpan data form
def save_form_data():
    # Hitung total usaha dari input BLOK III
    total_usaha = (
        int(st.session_state.jml_industri_makanan) +
        int(st.session_state.jml_industri_alat_rt) +
        int(st.session_state.jml_industri_material) +
        int(st.session_state.jml_industri_alat_pertanian) +
        int(st.session_state.jml_industri_kerajinan) +
        int(st.session_state.jml_industri_logam) +
        int(st.session_state.jml_industri_lainnya)
    )
    
    form_data = {
        "provinsi": st.session_state.provinsi,
        "kabupaten": st.session_state.kabupaten,
        "kecamatan": st.session_state.kecamatan,
        "desa": st.session_state.desa,
        "rt": st.session_state.rt,
        "rw": st.session_state.rw,
        "nama_pendata": st.session_state.nama_pendata,
        "nama_pemeriksa": st.session_state.nama_pemeriksa,
        "tanggal": st.session_state.tanggal.strftime('%Y-%m-%d'),
        "jml_industri_makanan": st.session_state.jml_industri_makanan,
        "jml_industri_alat_rt": st.session_state.jml_industri_alat_rt,
        "jml_industri_material": st.session_state.jml_industri_material,
        "jml_industri_alat_pertanian": st.session_state.jml_industri_alat_pertanian,
        "jml_industri_kerajinan": st.session_state.jml_industri_kerajinan,
        "jml_industri_logam": st.session_state.jml_industri_logam,
        "jml_industri_lainnya": st.session_state.jml_industri_lainnya,
    }
    
    st.session_state.form_data = form_data
    st.session_state.jumlah_usaha = total_usaha  # Gunakan total yang dihitung
    set_page('usaha')

# Fungsi untuk menyimpan data usaha
def save_usaha_data():
    # Kumpulkan kode industri dari checkbox
    kode_industri = []
    if st.session_state.industri_makanan:
        kode_industri.append("3.1")
    if st.session_state.industri_alat_rt:
        kode_industri.append("3.2")
    if st.session_state.industri_material:
        kode_industri.append("3.3")
    if st.session_state.industri_alat_pertanian:
        kode_industri.append("3.4")
    if st.session_state.industri_kerajinan:
        kode_industri.append("3.5")
    if st.session_state.industri_logam:
        kode_industri.append("3.6")
    if st.session_state.industri_lainnya:
        kode_industri.append("3.7")

    # Data usaha yang akan disimpan
    usaha_data = {
        "nama_usaha": st.session_state.nama_usaha,
        "nama_pemilik": st.session_state.nama_pemilik,
        "kode_industri": kode_industri,
        "jumlah_tenaga_kerja": st.session_state.jumlah_tenaga_kerja
    }

    # Simpan ke session_state.usaha_data
    if st.session_state.current_usaha < len(st.session_state.usaha_data):
        st.session_state.usaha_data[st.session_state.current_usaha] = usaha_data
    else:
        st.session_state.usaha_data.append(usaha_data)

    # Naikkan index usaha yang sedang diisi
    st.session_state.current_usaha += 1

    # Jika sudah selesai semua, lanjut ke halaman preview
    if st.session_state.current_usaha >= st.session_state.jumlah_usaha:
        set_page('preview')
    else:
        # Hapus key input agar tidak error saat render ulang
        for key in [
            "nama_usaha", "nama_pemilik", "industri_makanan", "industri_alat_rt",
            "industri_material", "industri_alat_pertanian", "industri_kerajinan",
            "industri_logam", "industri_lainnya", "jumlah_tenaga_kerja"
        ]:
            if key in st.session_state:
                del st.session_state[key]

        # Render ulang halaman agar field kosong kembali
        st.rerun()

# Fungsi untuk kembali ke halaman form dari halaman usaha
def back_to_form():
    # Reset data usaha agar tidak tercampur
    st.session_state.usaha_data = []
    st.session_state.current_usaha = 0
    set_page('form')

# Fungsi reset_form_state untuk mengatur ulang seluruh state aplikasi
def reset_form_state():
    # Reset halaman ke form
    st.session_state.page = 'form'
    
    # Reset data form
    st.session_state.form_data = {}
    
    # Reset data usaha
    st.session_state.usaha_data = []
    st.session_state.current_usaha = 0
    st.session_state.jumlah_usaha = 0
    
    # Reset status penyimpanan data
    st.session_state.data_saved = False
    
    # Reset state edit - BARU
    st.session_state.edit_mode = None
    st.session_state.edit_form_data = {}
    st.session_state.edit_usaha_index = 0
    
    # Hapus key input lainnya jika ada
    keys_to_remove = [
        "provinsi", "kabupaten", "kecamatan", "desa", "rt", "rw",
        "nama_pendata", "nama_pemeriksa", "tanggal", 
        "jml_industri_makanan", "jml_industri_alat_rt", "jml_industri_material",
        "jml_industri_alat_pertanian", "jml_industri_kerajinan", "jml_industri_logam",
        "jml_industri_lainnya", "jml_usaha", "nama_usaha", "nama_pemilik",
        "industri_makanan", "industri_alat_rt", "industri_material", 
        "industri_alat_pertanian", "industri_kerajinan", "industri_logam", 
        "industri_lainnya", "jumlah_tenaga_kerja",
        # Tambahan untuk edit keys - BARU
        "edit_nama_usaha", "edit_nama_pemilik", "edit_industri_makanan", 
        "edit_industri_alat_rt", "edit_industri_material", "edit_industri_alat_pertanian", 
        "edit_industri_kerajinan", "edit_industri_logam", "edit_industri_lainnya", 
        "edit_jumlah_tenaga_kerja"
    ]
    
    for key in keys_to_remove:
        if key in st.session_state:
            del st.session_state[key]


# FUNGSI BARU - Untuk mengatur mode edit
def set_edit_mode(mode):
    st.session_state.edit_mode = mode
    if mode == 'form':
        st.session_state.edit_form_data = st.session_state.form_data.copy()
    elif mode == 'usaha':
        st.session_state.edit_usaha_index = 0

# FUNGSI BARU - Untuk menyimpan hasil edit form
def save_edited_form():
    st.session_state.form_data = st.session_state.edit_form_data.copy()
    # Hitung ulang jumlah usaha berdasarkan edit
    total_usaha = (
        int(st.session_state.edit_form_data['jml_industri_makanan']) +
        int(st.session_state.edit_form_data['jml_industri_alat_rt']) +
        int(st.session_state.edit_form_data['jml_industri_material']) +
        int(st.session_state.edit_form_data['jml_industri_alat_pertanian']) +
        int(st.session_state.edit_form_data['jml_industri_kerajinan']) +
        int(st.session_state.edit_form_data['jml_industri_logam']) +
        int(st.session_state.edit_form_data['jml_industri_lainnya'])
    )
    
    # Jika jumlah usaha berubah, sesuaikan data usaha
    current_usaha_count = len(st.session_state.usaha_data)
    if total_usaha < current_usaha_count:
        # Kurangi data usaha
        st.session_state.usaha_data = st.session_state.usaha_data[:total_usaha]
        st.warning(f"Data usaha dikurangi dari {current_usaha_count} menjadi {total_usaha}")
    elif total_usaha > current_usaha_count:
        # Tambah slot usaha kosong
        for i in range(total_usaha - current_usaha_count):
            st.session_state.usaha_data.append({
                "nama_usaha": "",
                "nama_pemilik": "",
                "kode_industri": [],
                "jumlah_tenaga_kerja": 0
            })
        st.warning(f"Slot usaha ditambah dari {current_usaha_count} menjadi {total_usaha}. Silakan isi data usaha yang kosong.")
    
    st.session_state.jumlah_usaha = total_usaha
    st.session_state.edit_mode = None
    st.success("Data form berhasil diperbarui!")

# FUNGSI BARU - Untuk menyimpan hasil edit usaha
def save_edited_usaha():
    index = st.session_state.edit_usaha_index
    
    # Kumpulkan kode industri dari checkbox
    kode_industri = []
    if st.session_state.get('edit_industri_makanan', False):
        kode_industri.append("3.1")
    if st.session_state.get('edit_industri_alat_rt', False):
        kode_industri.append("3.2")
    if st.session_state.get('edit_industri_material', False):
        kode_industri.append("3.3")
    if st.session_state.get('edit_industri_alat_pertanian', False):
        kode_industri.append("3.4")
    if st.session_state.get('edit_industri_kerajinan', False):
        kode_industri.append("3.5")
    if st.session_state.get('edit_industri_logam', False):
        kode_industri.append("3.6")
    if st.session_state.get('edit_industri_lainnya', False):
        kode_industri.append("3.7")

    # Update data usaha
    st.session_state.usaha_data[index] = {
        "nama_usaha": st.session_state.edit_nama_usaha,
        "nama_pemilik": st.session_state.edit_nama_pemilik,
        "kode_industri": kode_industri,
        "jumlah_tenaga_kerja": st.session_state.edit_jumlah_tenaga_kerja
    }
    
    st.session_state.edit_mode = None
    st.success(f"Data usaha {index + 1} berhasil diperbarui!")

# Hubungkan ke Google Sheets
worksheet = connect_to_gsheet()
# Tambahkan setelah worksheet = connect_to_gsheet()
if worksheet is not None:
    st.success("Berhasil terhubung ke Google Sheets!")
else:
    st.error("Tidak dapat terhubung ke Google Sheets. Pastikan credentials sudah benar.")

# Halaman Form
if st.session_state.page == 'form':
    with st.form("blok_1_2"):
        st.subheader("BLOK I. KETERANGAN TEMPAT")
        col1, col2 = st.columns(2)
        
        with col1:
            provinsi = st.text_input("1.1 Provinsi", value="JAWA TENGAH", key="provinsi")
            kabupaten = st.text_input("1.2 Kabupaten/Kota", value="TEGAL", key="kabupaten")
            kecamatan = st.text_input("1.3 Kecamatan", value="TEGAL TIMUR", key="kecamatan")
        
        with col2:
            desa = st.text_input("1.4 Desa/Kelurahan", value="KEJAMBON", key="desa")
            rt_rw = st.columns(2)
            with rt_rw[0]:
                rt = st.text_input("RT", key="rt", max_chars=2)
            with rt_rw[1]:
                rw = st.text_input("RW", key="rw", max_chars=2)
        
        st.subheader("BLOK II. KETERANGAN PENDATAAN")
        col1, col2 = st.columns(2)
        
        with col1:
            nama_pendata = st.text_input("2.1 Nama Pendata", key="nama_pendata")
            nama_pemeriksa = st.text_input("2.2 Nama Pemeriksa", key="nama_pemeriksa")
        
        with col2:
            tanggal = st.date_input("Tanggal", value=date.today(), key="tanggal")
        
        st.subheader("BLOK III. REKAPITULASI")
        
        col1, col2 = st.columns(2)
        
        with col1:
            jml_industri_makanan = st.number_input("3.1 Jumlah Industri Makanan", min_value=0, key="jml_industri_makanan")
            jml_industri_alat_rt = st.number_input("3.2 Jumlah Industri Alat Rumah Tangga", min_value=0, key="jml_industri_alat_rt")
            jml_industri_material = st.number_input("3.3 Jumlah Industri Material Bahan Bangunan", min_value=0, key="jml_industri_material")
            jml_industri_alat_pertanian = st.number_input("3.4 Jumlah Industri Alat Pertanian", min_value=0, key="jml_industri_alat_pertanian")
        
        with col2:
            jml_industri_kerajinan = st.number_input("3.5 Jumlah Industri Kerajinan selain logam", min_value=0, key="jml_industri_kerajinan")
            jml_industri_logam = st.number_input("3.6 Jumlah Industri Logam", min_value=0, key="jml_industri_logam")
            jml_industri_lainnya = st.number_input("3.7 Jumlah Industri Lainnya", min_value=0, key="jml_industri_lainnya")
        
        st.subheader("BLOK IV. KETERANGAN USAHA")
        total_usaha = (
            int(st.session_state.jml_industri_makanan) +
            int(st.session_state.jml_industri_alat_rt) +
            int(st.session_state.jml_industri_material) +
            int(st.session_state.jml_industri_alat_pertanian) +
            int(st.session_state.jml_industri_kerajinan) +
            int(st.session_state.jml_industri_logam) +
            int(st.session_state.jml_industri_lainnya)
        )
        st.session_state.jml_usaha = total_usaha
        st.info(f"Jumlah Usaha yang akan didata: {total_usaha} (otomatis dihitung dari total BLOK III)")

        submitted = st.form_submit_button("Lanjut ke Data Usaha")
        
        if submitted:
            save_form_data()

# Halaman Usaha
elif st.session_state.page == 'usaha':
    # Progress bar dan informasi yang lebih jelas
    progress = (st.session_state.current_usaha) / st.session_state.jumlah_usaha
    st.progress(progress)
    
    # Header dengan informasi yang lebih jelas
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader(f"BLOK IV. KETERANGAN USAHA")
    with col2:
        st.metric("Progress", f"{st.session_state.current_usaha + 1}/{st.session_state.jumlah_usaha}")
    
    # Info box dengan warna
    if st.session_state.current_usaha == 0:
        st.info(f"📝 Sedang mengisi data untuk *USAHA PERTAMA* dari {st.session_state.jumlah_usaha} usaha total")
    elif st.session_state.current_usaha == st.session_state.jumlah_usaha - 1:
        st.warning(f"📝 Sedang mengisi data untuk *USAHA TERAKHIR* ({st.session_state.current_usaha + 1} dari {st.session_state.jumlah_usaha})")
    else:
        st.info(f"📝 Sedang mengisi data untuk *USAHA KE-{st.session_state.current_usaha + 1}* dari {st.session_state.jumlah_usaha} usaha total")
    
    # Tombol kembali
    if st.button("Kembali ke Form"):
        back_to_form()

    # Tampilkan rekapitulasi dari halaman pertama - LANGSUNG TERLIHAT
    st.markdown("---")
    st.subheader("📊 Rekapitulasi Industri dari BLOK III")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"• Industri Makanan: **{st.session_state.form_data['jml_industri_makanan']}**")
        st.write(f"• Industri Alat Rumah Tangga: **{st.session_state.form_data['jml_industri_alat_rt']}**")
        st.write(f"• Industri Material Bahan Bangunan: **{st.session_state.form_data['jml_industri_material']}**")
        st.write(f"• Industri Alat Pertanian: **{st.session_state.form_data['jml_industri_alat_pertanian']}**")
    with col2:
        st.write(f"• Industri Kerajinan selain logam: **{st.session_state.form_data['jml_industri_kerajinan']}**")
        st.write(f"• Industri Logam: **{st.session_state.form_data['jml_industri_logam']}**")
        st.write(f"• Industri Lainnya: **{st.session_state.form_data['jml_industri_lainnya']}**")
    
    total = sum([
        st.session_state.form_data['jml_industri_makanan'],
        st.session_state.form_data['jml_industri_alat_rt'],
        st.session_state.form_data['jml_industri_material'],
        st.session_state.form_data['jml_industri_alat_pertanian'],
        st.session_state.form_data['jml_industri_kerajinan'],
        st.session_state.form_data['jml_industri_logam'],
        st.session_state.form_data['jml_industri_lainnya']
    ])
    st.success(f"**Total Usaha yang harus didata: {total}**")
        
    # Tampilkan usaha yang sudah diisi (jika ada) - LANGSUNG TERLIHAT
    if st.session_state.current_usaha > 0:
        st.markdown("---")
        st.subheader(f"✅ Data Usaha yang Sudah Diisi ({st.session_state.current_usaha} usaha)")
    
        # Mapping kode industri ke nama industri
        industri_mapping = {
            '3.1': 'Industri Makanan',
            '3.2': 'Industri Alat Rumah Tangga', 
            '3.3': 'Industri Material Bahan Bangunan',
            '3.4': 'Industri Alat Pertanian',
            '3.5': 'Industri Kerajinan selain logam',
            '3.6': 'Industri Logam',
            '3.7': 'Industri Lainnya'
        }

    # Tampilkan dalam format tabel yang lebih compact
    for i, usaha in enumerate(st.session_state.usaha_data[:st.session_state.current_usaha]):
        col1, col2, col3 = st.columns([1, 3, 2])
        with col1:
            st.write(f"**{i+1}.**")
        with col2:
            st.write(f"**{usaha['nama_usaha']}** ({usaha['nama_pemilik']})")
        with col3:
            # Buat list nama industri dari kode yang tersimpan
            nama_industri_list = []
            for kode in usaha['kode_industri']:
                if kode in industri_mapping:
                    nama_industri_list.append(industri_mapping[kode])
            
            # Tampilkan nama industri dan jumlah pekerja
            industri_text = ", ".join(nama_industri_list) if nama_industri_list else "Tidak ada industri"
            st.write(f"🏭 {industri_text}")
            st.write(f"👥 {usaha['jumlah_tenaga_kerja']} pekerja")

    # Form input usaha
    st.markdown("---")
    
    with st.form(f"usaha_{st.session_state.current_usaha}"):
        st.markdown(f"### 📋 Input Data Usaha ke-{st.session_state.current_usaha + 1}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            nama_usaha = st.text_input("Nama Usaha", key="nama_usaha", help="Masukkan nama usaha/toko/industri")
            nama_pemilik = st.text_input("Nama Pemilik", key="nama_pemilik", help="Masukkan nama pemilik usaha")
        
        with col2:
            jumlah_tenaga_kerja = st.number_input("Jumlah Tenaga Kerja", min_value=1, key="jumlah_tenaga_kerja", 
                                                help="Termasuk pemilik usaha")
        
        st.subheader("Kode Jenis Industri Mikro Kecil dan Menengah")
        st.caption("Pilih semua jenis industri yang sesuai dengan usaha ini:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            industri_makanan = st.checkbox("3.1 Industri Makanan", key="industri_makanan")
            industri_alat_rt = st.checkbox("3.2 Industri Alat Rumah Tangga", key="industri_alat_rt")
            industri_material = st.checkbox("3.3 Industri Material Bahan Bangunan", key="industri_material")
            industri_alat_pertanian = st.checkbox("3.4 Industri Alat Pertanian", key="industri_alat_pertanian")
        
        with col2:
            industri_kerajinan = st.checkbox("3.5 Industri Kerajinan selain logam", key="industri_kerajinan")
            industri_logam = st.checkbox("3.6 Industri Logam", key="industri_logam")
            industri_lainnya = st.checkbox("3.7 Industri Lainnya", key="industri_lainnya")
        
        # Tombol submit dengan teks yang lebih deskriptif
        if st.session_state.current_usaha < st.session_state.jumlah_usaha - 1:
            submitted = st.form_submit_button(f"💾 Simpan & Lanjut ke Usaha ke-{st.session_state.current_usaha + 2}")
        else:
            submitted = st.form_submit_button("✅ Simpan Data Terakhir & Lanjut ke Preview")
        
        if submitted:
            # Validasi input
            if not nama_usaha.strip():
                st.error("Nama Usaha harus diisi!")
            elif not nama_pemilik.strip():
                st.error("Nama Pemilik harus diisi!")
            elif not (industri_makanan or industri_alat_rt or industri_material or 
                     industri_alat_pertanian or industri_kerajinan or industri_logam or industri_lainnya):
                st.error("Minimal pilih satu jenis industri!")
            else:
                save_usaha_data()

# Halaman Preview
elif st.session_state.page == 'preview':    
    st.subheader("Preview Data")
    
    # Mode Edit Usaha
    if st.session_state.edit_mode == 'usaha':
        index = st.session_state.edit_usaha_index
        usaha = st.session_state.usaha_data[index]
        
        st.subheader(f"Edit Data Usaha {index + 1}")
        st.info(f"Mengedit: {usaha.get('nama_usaha', 'Nama usaha tidak tersedia')}")
        
        with st.form(f"edit_usaha_{index}"):
            nama_usaha = st.text_input("Nama Usaha", value=usaha.get('nama_usaha', ''), key=f"edit_nama_usaha_{index}")
            nama_pemilik = st.text_input("Nama Pemilik", value=usaha.get('nama_pemilik', ''), key=f"edit_nama_pemilik_{index}")
            
            st.write("**Kode Jenis Industri:**")
            col1, col2 = st.columns(2)
            
            with col1:
                industri_makanan = st.checkbox("3.1 Industri Makanan",
                                              value="3.1" in usaha.get('kode_industri', []), key=f"edit_industri_makanan_{index}")
                industri_alat_rt = st.checkbox("3.2 Industri Alat Rumah Tangga",
                                              value="3.2" in usaha.get('kode_industri', []), key=f"edit_industri_alat_rt_{index}")
                industri_material = st.checkbox("3.3 Industri Material Bahan Bangunan",
                                               value="3.3" in usaha.get('kode_industri', []), key=f"edit_industri_material_{index}")
                industri_alat_pertanian = st.checkbox("3.4 Industri Alat Pertanian",
                                                     value="3.4" in usaha.get('kode_industri', []), key=f"edit_industri_alat_pertanian_{index}")
            
            with col2:
                industri_kerajinan = st.checkbox("3.5 Industri Kerajinan selain logam",
                                                value="3.5" in usaha.get('kode_industri', []), key=f"edit_industri_kerajinan_{index}")
                industri_logam = st.checkbox("3.6 Industri Logam",
                                            value="3.6" in usaha.get('kode_industri', []), key=f"edit_industri_logam_{index}")
                industri_lainnya = st.checkbox("3.7 Industri Lainnya",
                                              value="3.7" in usaha.get('kode_industri', []), key=f"edit_industri_lainnya_{index}")
            
            jumlah_tenaga_kerja = st.number_input("Jumlah Tenaga Kerja",
                                                 min_value=0, value=int(usaha.get('jumlah_tenaga_kerja', 0)), key=f"edit_jumlah_tenaga_kerja_{index}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("Simpan Perubahan"):
                    # Update data usaha dengan nilai baru
                    kode_industri = []
                    if industri_makanan:
                        kode_industri.append("3.1")
                    if industri_alat_rt:
                        kode_industri.append("3.2")
                    if industri_material:
                        kode_industri.append("3.3")
                    if industri_alat_pertanian:
                        kode_industri.append("3.4")
                    if industri_kerajinan:
                        kode_industri.append("3.5")
                    if industri_logam:
                        kode_industri.append("3.6")
                    if industri_lainnya:
                        kode_industri.append("3.7")
                    
                    # Update data pada indeks yang benar
                    st.session_state.usaha_data[index].update({
                        'nama_usaha': nama_usaha,
                        'nama_pemilik': nama_pemilik,
                        'jumlah_tenaga_kerja': jumlah_tenaga_kerja,
                        'kode_industri': kode_industri
                    })
                    
                    st.session_state.edit_mode = None
                    st.session_state.edit_usaha_index = None
                    st.success(f"Data Usaha {index + 1} berhasil diupdate!")
                    st.rerun()
            
            with col2:
                if st.form_submit_button("Batal"):
                    st.session_state.edit_mode = None
                    st.session_state.edit_usaha_index = None
                    st.rerun()
    
    # Mode Preview Normal
    else:
        st.write("### BLOK I. KETERANGAN TEMPAT")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**1.1 Provinsi:** {st.session_state.form_data['provinsi']}")
            st.write(f"**1.2 Kabupaten/Kota:** {st.session_state.form_data['kabupaten']}")
            st.write(f"**1.3 Kecamatan:** {st.session_state.form_data['kecamatan']}")
        
        with col2:
            st.write(f"**1.4 Desa/Kelurahan:** {st.session_state.form_data['desa']}")
            st.write(f"**1.5 SLS (RT/RW):** RT {st.session_state.form_data['rt']} RW {st.session_state.form_data['rw']}")
        
        st.write("### BLOK II. KETERANGAN PENDATAAN")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**2.1 Nama Pendata:** {st.session_state.form_data['nama_pendata']}")
            st.write(f"**2.2 Nama Pemeriksa:** {st.session_state.form_data['nama_pemeriksa']}")
        
        with col2:
            st.write(f"**Tanggal:** {st.session_state.form_data['tanggal']}")
        
        st.write("### BLOK III. REKAPITULASI")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**3.1 Jumlah Industri Makanan:** {st.session_state.form_data['jml_industri_makanan']}")
            st.write(f"**3.2 Jumlah Industri Alat Rumah Tangga:** {st.session_state.form_data['jml_industri_alat_rt']}")
            st.write(f"**3.3 Jumlah Industri Material Bahan Bangunan:** {st.session_state.form_data['jml_industri_material']}")
            st.write(f"**3.4 Jumlah Industri Alat Pertanian:** {st.session_state.form_data['jml_industri_alat_pertanian']}")
        
        with col2:
            st.write(f"**3.5 Jumlah Industri Kerajinan selain logam:** {st.session_state.form_data['jml_industri_kerajinan']}")
            st.write(f"**3.6 Jumlah Industri Logam:** {st.session_state.form_data['jml_industri_logam']}")
            st.write(f"**3.7 Jumlah Industri Lainnya:** {st.session_state.form_data['jml_industri_lainnya']}")
        
        st.write("### BLOK IV. KETERANGAN USAHA")
        
        for i, usaha in enumerate(st.session_state.usaha_data):
            # Container untuk setiap usaha
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"#### Usaha {i+1}")
                    
                    # Sub kolom untuk detail usaha
                    detail_col1, detail_col2 = st.columns(2)
                    
                    with detail_col1:
                        st.write(f"**Nama Usaha:** {usaha['nama_usaha']}")
                        st.write(f"**Nama Pemilik:** {usaha['nama_pemilik']}")
                    
                    with detail_col2:
                        st.write(f"**Jumlah Tenaga Kerja:** {usaha['jumlah_tenaga_kerja']}")
                        st.write(f"**Kode Jenis Industri:** {', '.join(usaha['kode_industri'])}")
                
                with col2:
                    # Tombol edit di samping kanan
                    st.write("")  # Spacer untuk alignment
                    if st.button("✏️ Edit", key=f"edit_usaha_{i}"):
                        st.session_state.edit_usaha_index = i
                        st.session_state.edit_mode = 'usaha'
                        st.rerun()
                
                # Divider antar usaha
                if i < len(st.session_state.usaha_data) - 1:
                    st.divider()
        
        # Tombol aksi di bagian bawah
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Simpan & Unduh PDF"):
                # Buat PDF
                pdf_buffer = create_pdf(st.session_state.form_data, st.session_state.usaha_data)
                
                # Simpan ke Google Sheets jika belum disimpan
                if not st.session_state.data_saved:
                    success = save_to_gsheet(worksheet, st.session_state.form_data, st.session_state.usaha_data)
                
                if success:
                    st.success("Data berhasil disimpan ke Google Sheets!")
                    st.session_state.data_saved = True
                else:
                    st.info("Data sudah disimpan sebelumnya.")
                
                # Unduh PDF
                pdf_bytes = pdf_buffer.getvalue()
                b64 = base64.b64encode(pdf_bytes).decode()
                
                tanggal_str = st.session_state.form_data["tanggal"].replace("-", "")
                filename = f"Pendataan_Industri_{st.session_state.form_data['desa']}_{tanggal_str}.pdf"
                
                href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}">Klik di sini untuk mengunduh PDF</a>'
                st.markdown(href, unsafe_allow_html=True)
        
        with col2:
            if st.button("Isi Form Baru"):
                reset_form_state()
                st.rerun()

# Tampilkan petunjuk penggunaan
with st.expander("Petunjuk Penggunaan"):
    st.markdown("""
    ### Petunjuk Penggunaan
    
    1. **BLOK I & II**: Isi informasi lokasi dan pendataan.
    2. **BLOK III**: Masukkan jumlah industri untuk setiap kategori.
    3. **BLOK IV**: Tentukan jumlah usaha yang akan didata.
    4. **Data Usaha**: Isi detail untuk setiap usaha satu per satu.
    5. **Preview**: Periksa semua data yang telah diisi.
    6. **Simpan & Unduh**: Simpan data ke Google Sheets dan unduh formulir sebagai PDF.
                
    ### Keterangan
    1.  Industri adalah kegiatan produksi yang mengubah barang dasar (bahan mentah menjadi barang jadi/setengah jadi dan atau dari barang yang kurang nilainya menjadi barang yang lebih tinggi nilainya. Termasuk ke dalam kategori ini adalah kegiatan jasa industri (maklun).              
    2.  Industri Mikro adalah perusahaan industri yang pekerjanya antara 1-4 orang termasuk pemilik usaha.
    3.  Industri Kecil adalah perusahaan industri yang pekerjanya antara 5-19 orang termasuk pemilik usaha. 
    4.  Usaha/perusahaan industri skala menengah (sedang) adalah perusahaan yang memenuhi salah satu kriteria jumlah tenaga 20 sampai 99 orang atau nilai akumulasi investasi/modal tetap sejak pendirian pabrik hingga 31 Desember 2024 lebih dari 5 miliar dan kurang dari Rp 10 miliar atau omset perusahaan tahun 2024 lebih dari 15 miliar dan kurang dari Rp 50 miliar.                        
    5.  Jumlah tenaga kerja termasuk pemilik usaha.
    6.  Contoh industri makanan : membuat tempe, tahu, keripik, peyek, kue, roti dll.
    7.  Contoh industri alat rumah tangga : membuat Panci, cetakan kue, centong dll.
    8.  Contoh industri material bahan bangunan : membuat batu bata, batako, kluwung dll.
    9.  Contoh industri alat pertanian: membuat cangkul, sabit, dll.
    10. Contoh industri kerajinan selain logam: membuat mebel, lemari, kusen, dll.
    11. Contoh industri logam: membuat mur, baut, mesin bubut, spare part mesin, teralis, perbaikan mesin (bukan bengkel motor/mobil), dll.
    12. Industri lainnya: membaki, menjahit sesuai pesanan, mencetak undangan, sablon, dll.""")
