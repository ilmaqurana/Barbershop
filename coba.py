import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import os
import matplotlib.dates as mdates
from prophet import Prophet

# === Konfigurasi Halaman ===
st.set_page_config(page_title="💈 Jack Barber Analytics + AI", layout="wide")

# === Konstanta File ===
LOCAL_TX_FILE = "data_transaksi.csv"

# === Link CSV Google Form ===
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRhhXuynHqruriAnIHXxLXCebHC2IXNM8C6XqRIrf0_4GyURnD7kGsvo8mnQBcNJU4YFyewZDi9BIVR/pub?output=csv"

# === Pastikan file transaksi ada ===
if not os.path.exists(LOCAL_TX_FILE):
    pd.DataFrame(columns=["id_transaksi", "tanggal", "nama_pelanggan", "layanan", "harga"]).to_csv(LOCAL_TX_FILE, index=False)

# === Fungsi Generate PDF Pendapatan ===
def generate_pendapatan_pdf(df):
    buffer = BytesIO()
    df = df.copy()
    df["tanggal"] = pd.to_datetime(df["tanggal"], errors='coerce').dt.strftime("%Y-%m-%d")
    df.insert(0, "No", range(1, len(df) + 1))
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph("💈 Laporan Pendapatan Harian - Jack Barber", styles["Title"]))
    elements.append(Spacer(1, 12))
    data_table = [df.columns.to_list()] + df.values.tolist()
    t = Table(data_table, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# === Fungsi Load Data Transaksi Lokal ===
def load_data_local():
    try:
        df = pd.read_csv(LOCAL_TX_FILE, parse_dates=["tanggal"])
        df.columns = [str(c).lower().strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Gagal memuat data lokal: {e}")
        return pd.DataFrame(columns=["id_transaksi", "tanggal", "nama_pelanggan", "layanan", "harga"])

# === Fungsi Load Data dari Google Form ===
def load_data_from_google():
    try:
        df_form = pd.read_csv(GOOGLE_SHEET_URL)
        df_form.columns = [str(c).strip().lower() for c in df_form.columns]

        df_form.rename(columns={
            "timestamp": "timestamp",
            "nama pelanggan": "nama_pelanggan",
            "tanggal": "tanggal",
        }, inplace=True)

        # Gabungkan kolom penilaian pelayanan (rating)
        rating_cols = [col for col in df_form.columns if "penilaian pelayanan" in col]
        if rating_cols:
            df_form["rating"] = df_form[rating_cols].mean(axis=1)
        else:
            df_form["rating"] = 0

        # Pastikan tanggal ada
        df_form["tanggal"] = pd.to_datetime(df_form["tanggal"], errors='coerce')
        df_form["id_transaksi"] = [f"R{i+1:03d}" for i in range(len(df_form))]

        df_form = df_form[["id_transaksi", "tanggal", "nama_pelanggan", "rating"]]
        return df_form

    except Exception as e:
        st.error(f"Gagal memuat data dari Google Form: {e}")
        return pd.DataFrame()

# === Fungsi plotting grafik kepuasan ===
def plot_kepuasan(df_form):
    if not df_form.empty:
        df_form['tanggal'] = pd.to_datetime(df_form['tanggal'], errors='coerce')
        kepuasan_harian = df_form.groupby('tanggal')['rating'].mean().reset_index()
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(kepuasan_harian['tanggal'], kepuasan_harian['rating'], marker="s", color="green")
        ax.set_title("Rata-rata Kepuasan Pelanggan (1-5)")
        ax.set_xlabel("Tanggal Pengisian Form")
        ax.set_ylabel("Rating")
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
        plt.xticks(rotation=45)
        plt.grid(True, linestyle="--", alpha=0.5)
        st.pyplot(fig)
    else:
        st.info("ℹ️ Data kepuasan pelanggan belum tersedia dari Google Form.")

# === Load Data Awal ===
data_tx = load_data_local()
data_form = load_data_from_google()

# === Sidebar Menu ===
st.sidebar.title("📊 Navigasi")
menu = st.sidebar.selectbox(
    "Pilih Menu",
    ["Pendapatan & Kepuasan Harian", "Input Transaksi Kasir"]
)

# === 1. Analisis Pendapatan & Kepuasan ===
if menu == "Pendapatan & Kepuasan Harian":
    st.title("💈 Analisis Pendapatan & Kepuasan Pelanggan")

    if st.button("🔄 Refresh Data dari Google Form"):
        data_form = load_data_from_google()
        st.success("✅ Data kepuasan berhasil diperbarui dari Google Form.")

    # --- Grafik Pendapatan ---
    if not data_tx.empty:
        data_tx["harga"] = pd.to_numeric(data_tx["harga"], errors="coerce").fillna(0)
        pendapatan_harian = data_tx.groupby("tanggal")["harga"].sum().reset_index()
        st.write("### 💰 Tabel Pendapatan Harian")
        st.dataframe(pendapatan_harian)
        pdf_buffer = generate_pendapatan_pdf(pendapatan_harian)
        st.download_button("📄 Download PDF Laporan Pendapatan", data=pdf_buffer,
                           file_name="Laporan_Pendapatan_JackBarber.pdf", mime="application/pdf")
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(pendapatan_harian["tanggal"], pendapatan_harian["harga"], marker="o", color="blue")
        ax.set_title("Pendapatan Harian (Rp)")
        ax.set_xlabel("Tanggal")
        ax.set_ylabel("Total Pendapatan")
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
        plt.xticks(rotation=45)
        plt.grid(True, linestyle="--", alpha=0.5)
        st.pyplot(fig)

    # --- Grafik Kepuasan otomatis ---
    st.write("### 😊 Grafik Kepuasan Pelanggan")
    plot_kepuasan(data_form)

    # --- Prediksi Pendapatan AI ---
    if len(data_tx) > 2:
        df_pred = data_tx.groupby("tanggal")["harga"].sum().reset_index()
        df_pred.rename(columns={"tanggal": "ds", "harga": "y"}, inplace=True)
        model = Prophet(daily_seasonality=True)
        model.fit(df_pred)
        future = model.make_future_dataframe(periods=7)
        forecast = model.predict(future)
        fig3, ax3 = plt.subplots(figsize=(10, 5))
        ax3.plot(df_pred['ds'], df_pred['y'], label='Pendapatan Aktual', marker='o')
        ax3.plot(forecast['ds'], forecast['yhat'], label='Prediksi AI', linestyle='--', color='red')
        ax3.set_title("Prediksi Pendapatan Harian")
        ax3.legend()
        st.pyplot(fig3)
    else:
        st.info("⚠️ Data terlalu sedikit untuk prediksi AI.")

# === 2. Input Transaksi Kasir (tanpa rating) ===
elif menu == "Input Transaksi Kasir":
    st.title("💵 Input Transaksi Kasir")
    with st.form("form_transaksi"):
        nama = st.text_input("Nama Pelanggan")
        tanggal = st.date_input("Tanggal Transaksi")
        layanan = st.multiselect(
            "Pilih Layanan",
            ["Potong Rambut", "Cukur Jenggot", "Hair Spa", "Cat Rambut", "Creambath", "Paket Lengkap"]
        )
        harga_total = sum({
            "Potong Rambut": 20000,
            "Cukur Jenggot": 15000,
            "Hair Spa": 30000,
            "Cat Rambut": 40000,
            "Creambath": 25000,
            "Paket Lengkap": 80000
        }[l] for l in layanan)
        st.write(f"💰 Total Harga: Rp {harga_total:,.0f}")
        submitted = st.form_submit_button("💾 Simpan Transaksi")

    if submitted:
        transaksi = load_data_local()
        new_id = f"T{len(transaksi) + 1:03d}"
        new_data = pd.DataFrame([{
            "id_transaksi": new_id,
            "tanggal": pd.to_datetime(tanggal),
            "nama_pelanggan": nama,
            "layanan": ", ".join(layanan),
            "harga": harga_total
        }])
        transaksi = pd.concat([transaksi, new_data], ignore_index=True)
        transaksi.to_csv(LOCAL_TX_FILE, index=False)
        st.success("✅ Transaksi berhasil disimpan.")

        # --- Update otomatis grafik kepuasan ---
        data_form = load_data_from_google()
        st.write("### 😊 Grafik Kepuasan Pelanggan Terbaru")
        plot_kepuasan(data_form)

