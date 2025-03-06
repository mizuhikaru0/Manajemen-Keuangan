import os
import sqlite3
from flask import Flask, request, redirect, url_for, render_template_string, flash
from dotenv import load_dotenv

# Load Environment Variables dari .env
load_dotenv()

# Ambil SECRET_KEY dari environment
SECRET_KEY = os.getenv("SECRET_KEY", "defaultsecret")
DATABASE_URL = os.getenv("DATABASE_URL", "keuangan.db")

app = Flask(__name__)
app.secret_key = SECRET_KEY  # Gunakan secret key dari environment

# Database Configuration
DATABASE = DATABASE_URL

def create_connection():
    """Membuat koneksi ke database SQLite."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE)
    except sqlite3.Error as e:
        print(f"Error: {e}")
    return conn

def init_db():
    """Inisialisasi database dan buat tabel jika belum ada."""
    conn = create_connection()
    with conn:
        try:
            sql_create_table = """
            CREATE TABLE IF NOT EXISTS transaksi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keterangan TEXT NOT NULL,
                jumlah REAL NOT NULL,
                jenis TEXT NOT NULL CHECK(jenis IN ('pemasukan', 'pengeluaran')),
                tanggal TEXT NOT NULL
            );
            """
            conn.execute(sql_create_table)
        except sqlite3.Error as e:
            print(f"Error saat membuat tabel: {e}")

# Inisialisasi database saat aplikasi pertama kali dijalankan
init_db()

# Template HTML untuk halaman utama
home_template = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Aplikasi Pengelola Keuangan</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/milligram/1.4.1/milligram.min.css">
    <style>
        body { margin: 2em; }
        .flash { color: green; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Aplikasi Pengelola Keuangan</h1>
    <h2>Tambah Transaksi</h2>
    <form method="post" action="{{ url_for('tambah') }}">
        <label for="keterangan">Keterangan:</label>
        <input type="text" name="keterangan" required>
        <label for="jumlah">Jumlah:</label>
        <input type="number" step="0.01" name="jumlah" required>
        <label for="jenis">Jenis:</label>
        <select name="jenis">
            <option value="pemasukan">Pemasukan</option>
            <option value="pengeluaran">Pengeluaran</option>
        </select>
        <label for="tanggal">Tanggal:</label>
        <input type="date" name="tanggal" required>
        <input type="submit" value="Tambah Transaksi">
    </form>
    
    {% with messages = get_flashed_messages() %}
    {% if messages %}
        <div class="flash">
            {% for message in messages %}
                <p>{{ message }}</p>
            {% endfor %}
        </div>
    {% endif %}
    {% endwith %}
    
    <h2>Daftar Transaksi</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Keterangan</th>
            <th>Jumlah</th>
            <th>Jenis</th>
            <th>Tanggal</th>
        </tr>
        {% for transaksi in transaksis %}
        <tr>
            <td>{{ transaksi[0] }}</td>
            <td>{{ transaksi[1] }}</td>
            <td>{{ transaksi[2] }}</td>
            <td>{{ transaksi[3] }}</td>
            <td>{{ transaksi[4] }}</td>
        </tr>
        {% endfor %}
    </table>
</body>
</html>
'''

@app.route('/')
def index():
    """Menampilkan halaman utama dengan daftar transaksi."""
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM transaksi ORDER BY tanggal DESC")
    transaksis = cur.fetchall()
    return render_template_string(home_template, transaksis=transaksis)

@app.route('/tambah', methods=['POST'])
def tambah():
    """Menangani penambahan transaksi baru."""
    keterangan = request.form['keterangan']
    jumlah = float(request.form['jumlah'])
    jenis = request.form['jenis']
    tanggal = request.form['tanggal']

    conn = create_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO transaksi (keterangan, jumlah, jenis, tanggal) VALUES (?, ?, ?, ?)", 
                (keterangan, jumlah, jenis, tanggal))
    conn.commit()
    flash("Transaksi berhasil ditambahkan!")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
