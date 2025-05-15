import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
import base64
import io
import os
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

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
        else:
            # Sebagai alternatif, coba cari file kredensial di direktori tertentu
            credentials_path = r"D:\Perkuliahan\PRIGEL\Form Pendataan Desa Cantik\pendataan-industri-kejambon-a89a18e029b6.json"

            # Periksa apakah file kredensial ada
            if os.path.exists(credentials_path):
                st.info(f"Menggunakan kredensial dari file: {credentials_path}")
                credentials = Credentials.from_service_account_file(
                    credentials_path,
                    scopes=scope
                )
            else:
                st.error("Tidak dapat menemukan file kredensial Google Cloud. Pastikan Anda telah menempatkan file credentials.json di direktori yang benar.")
                return None
        
        # Authorize dengan gspread
        client = gspread.authorize(credentials)
        
        # Buka spreadsheet dengan ID
        spreadsheet_id = '1S7wBO23LVV1dK6MsgxuQO2It7P2Lh45LUiaFZoIshcU'  
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Coba dapatkan worksheet, jika tidak ada, buat baru
        try:
            worksheet = spreadsheet.worksheet("Data Industri")
        except gspread.exceptions.WorksheetNotFound:
            # Worksheet tidak ditemukan, buat baru
            worksheet = spreadsheet.add_worksheet(title="Data Industri", rows=1000, cols=20)
            
            # Tambahkan header
            headers = [
                "Provinsi", "Kabupaten/Kota", "Kecamatan", "Desa/Kelurahan", "RT/RW", 
                "Nama Pendata", "Nama Pemeriksa", "Tanggal", 
                "Jumlah Industri Makanan", "Jumlah Industri Alat Rumah Tangga", 
                "Jumlah Industri Material Bahan Bangunan", "Jumlah Industri Alat Pertanian",
                "Jumlah Industri Kerajinan selain logam", "Jumlah Industri Logam", 
                "Jumlah Industri Lainnya", "Detail Usaha"
            ]
            worksheet.append_row(headers)
            st.success("Worksheet 'Data Industri' berhasil dibuat!")
            
        return worksheet
        
    except Exception as e:
        st.error(f"Terjadi kesalahan dalam koneksi ke Google Sheets: {str(e)}")
        return None
        
# Fungsi untuk membuat PDF yang sudah diperbaiki
def create_pdf(form_data, usaha_data):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

   # Judul Halaman
    c.setFont("Times-Bold", 14)
    judul = "PENDATAAN INDUSTRI PENGOLAHAN DI KELURAHAN KEJAMBON"
    text_width = c.stringWidth(judul, "Times-Bold", 14)
    c.drawString((width - text_width) / 2, height - 50, judul)

    c.setFont("Times-Bold", 14)
    subjudul = "KELURAHAN CINTA STATISTIK 2025"
    text_width = c.stringWidth(subjudul, "Times-Bold", 14)
    c.drawString((width - text_width) / 2, height - 80, subjudul)

    y_position = height - 120

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
    table.wrapOn(c, width, height)
    table.drawOn(c, 50, y_position - 120)
    y_position -= 160

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
        ('ALIGN', (0, 2), (0, -1), 'CENTER'),  # Perataan tengah nomor 2.1 dan 2.2
        ('SPAN', (0, 0), (4, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    table.wrapOn(c, width, height)
    table.drawOn(c, 50, y_position - 90)
    y_position -= 130

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
        ('ALIGN', (0, 2), (0, -1), 'CENTER'),  # Perataan tengah nomor 3.1 - 3.7
        ('SPAN', (0, 0), (2, 0)),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    table.wrapOn(c, width, height)
    table.drawOn(c, 50, y_position - 180)

    # Halaman Baru - BLOK IV
    c.showPage()

    # BLOK IV Header
    headers = [
        ["BLOK IV. KETERANGAN USAHA", "", "", "", "", "", "", "", "", "", ""],
        ["No", "Nama Usaha", "Nama Pemilik", "Kode Jenis Industri Mikro Kecil dan Menengah", "", "", "", "", "", "", "Jumlah\nTenaga Kerja"],
        ["", "", "", "3.1", "3.2", "3.3", "3.4", "3.5", "3.6", "3.7", ""]
    ]
    usaha_rows = []
    total_industri = [0] * 7
    total_tenaga_kerja = 0

    for i, usaha in enumerate(usaha_data):
        row = [str(i+1), usaha["nama_usaha"], usaha["nama_pemilik"]]
        for j in range(1, 8):
            kode = f"3.{j}"
            row.append("✓" if kode in usaha["kode_industri"] else "")
        row.append(str(usaha["jumlah_tenaga_kerja"]))
        usaha_rows.append(row)
        for j in range(1, 8):
            if f"3.{j}" in usaha["kode_industri"]:
                total_industri[j-1] += 1
        total_tenaga_kerja += int(usaha["jumlah_tenaga_kerja"])

    jumlah_row = ["Jumlah", "", ""] + [str(j) for j in total_industri] + [str(total_tenaga_kerja)]
    data = headers + usaha_rows + [jumlah_row]
    col_widths = [30, 100, 100, 30, 30, 30, 30, 30, 30, 30, 60]

    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ('GRID', (0, 2), (-1, -1), 0.5, colors.black),
        ('GRID', (0, 1), (-1, 1), 0.5, colors.black),
        ('BOX', (0, 0), (-1, 0), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # default center
        ('SPAN', (0, 0), (10, 0)),
        ('SPAN', (0, 1), (0, 2)),
        ('SPAN', (1, 1), (1, 2)),
        ('SPAN', (2, 1), (2, 2)),
        ('SPAN', (3, 1), (9, 1)),
        ('SPAN', (10, 1), (10, 2)),
        ('SPAN', (0, -1), (2, -1)),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 1), (-1, 2), colors.lightgrey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
        ('FONTNAME', (0, -1), (-1, -1), 'Times-Bold'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (1, 3), (2, -2), 'LEFT'),
    ]))

    table.wrapOn(c, width, height)
    table.drawOn(c, 50, height - 250)

    c.save()
    buffer.seek(0)
    return buffer

# Fungsi untuk menyimpan data ke Google Sheets
def save_to_gsheet(worksheet, form_data, usaha_data):
    if worksheet is None:
        return False

    try:
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

            # Simpan ke sheet
            worksheet.append_row(row_data)

        return True
    except Exception as e:
        st.error(f"Terjadi kesalahan saat menyimpan data: {e}")
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

# Fungsi untuk mengatur halaman
def set_page(page):
    st.session_state.page = page

# Fungsi untuk menyimpan data form
def save_form_data():
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
    st.session_state.jumlah_usaha = st.session_state.jml_usaha
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
                rt = st.text_input("RT", key="rt")
            with rt_rw[1]:
                rw = st.text_input("RW", key="rw")
        
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
        jml_usaha = st.number_input("Jumlah Usaha yang akan didata", min_value=0, key="jml_usaha")
        
        submitted = st.form_submit_button("Lanjut ke Data Usaha")
        
        if submitted:
            save_form_data()

# Halaman Usaha
elif st.session_state.page == 'usaha':
    st.subheader(f"BLOK IV. KETERANGAN USAHA - Usaha {st.session_state.current_usaha + 1} dari {st.session_state.jumlah_usaha}")
    
    with st.form(f"usaha_{st.session_state.current_usaha}"):
        col1, col2 = st.columns(2)
        
        with col1:
            nama_usaha = st.text_input("Nama Usaha", key="nama_usaha")
            nama_pemilik = st.text_input("Nama Pemilik", key="nama_pemilik")
        
        with col2:
            jumlah_tenaga_kerja = st.number_input("Jumlah Tenaga Kerja", min_value=0, key="jumlah_tenaga_kerja")
        
        st.subheader("Kode Jenis Industri Mikro Kecil dan Menengah")
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
        
        submitted = st.form_submit_button("Simpan Data Usaha")
        
        if submitted:
            save_usaha_data()

# Halaman Preview
elif st.session_state.page == 'preview':
    st.subheader("Preview Data")
    
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
        st.write(f"#### Usaha {i+1}")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Nama Usaha:** {usaha['nama_usaha']}")
            st.write(f"**Nama Pemilik:** {usaha['nama_pemilik']}")
        
        with col2:
            st.write(f"**Jumlah Tenaga Kerja:** {usaha['jumlah_tenaga_kerja']}")
            st.write(f"**Kode Jenis Industri:** {', '.join(usaha['kode_industri'])}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Kembali ke Form"):
            set_page('form')
    
    with col2:
        if st.button("Simpan & Unduh PDF"):
            # Buat PDF
            pdf_buffer = create_pdf(st.session_state.form_data, st.session_state.usaha_data)
            
            # Simpan ke Google Sheets
            success = save_to_gsheet(worksheet, st.session_state.form_data, st.session_state.usaha_data)
            
            if success:
                st.success("Data berhasil disimpan ke Google Sheets!")
            
            # Unduh PDF
            pdf_bytes = pdf_buffer.getvalue()
            b64 = base64.b64encode(pdf_bytes).decode()
            
            tanggal_str = st.session_state.form_data["tanggal"].replace("-", "")
            filename = f"Pendataan_Industri_{st.session_state.form_data['desa']}_{tanggal_str}.pdf"
            
            href = f'<a href="data:application/pdf;base64,{b64}" download="{filename}">Klik di sini untuk mengunduh PDF</a>'
            st.markdown(href, unsafe_allow_html=True)

# Tampilkan petunjuk penggunaan
with st.expander("Petunjuk Penggunaan"):
    st.markdown("""
    ### Petunjuk Penggunaan
    
    1. **BLOK I & II**: Isi informasi lokasi dan pendataan.
    2. **BLOK III**: Masukkan jumlah industri untuk setiap kategori.
    3. **BLOK IV**: Tentukan jumlah usaha yang akan didata.
    4. **Data Usaha**: Isi detail untuk setiap usaha satu per satu.
    5. **Preview**: Periksa semua data yang telah diisi.
    6. **Simpan & Unduh**: Simpan data ke Google Sheets dan unduh formulir sebagai PDF)""")
