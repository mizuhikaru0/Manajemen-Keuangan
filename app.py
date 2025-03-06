from flask import Flask, request, redirect, url_for, render_template_string, flash
import sqlite3
from sqlite3 import Error

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Kunci rahasia untuk flash message

DATABASE = 'keuangan.db'

def create_connection(db_file):
    """Membuat koneksi ke database SQLite."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(f"Error: {e}")
    return conn

def init_db():
    """Inisialisasi database dan buat tabel transaksi jika belum ada."""
    conn = create_connection(DATABASE)
    with conn:
        try:
            sql_create_table = """
            CREATE TABLE IF NOT EXISTS transaksi (
                id integer PRIMARY KEY,
                keterangan text NOT NULL,
                jumlah real NOT NULL,
                jenis text NOT NULL,
                tanggal text NOT NULL
            );
            """
            conn.execute(sql_create_table)
        except Error as e:
            print(f"Error saat membuat tabel: {e}")

# Inisialisasi database
init_db()

# Template HTML dasar menggunakan render_template_string
home_template = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Aplikasi Pengelola Keuangan</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 2em; }
        table { border-collapse: collapse; width: 100%; }
        table, th, td { border: 1px solid #ddd; }
        th, td { padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .flash { color: green; }
    </style>
</head>
<body>
    <h1>Aplikasi Pengelola Keuangan</h1>
    <h2>Tambah Transaksi</h2>
    <form method="post" action="{{ url_for('tambah') }}">
        <label for="keterangan">Keterangan:</label>
        <input type="text" name="keterangan" required><br><br>
        <label for="jumlah">Jumlah:</label>
        <input type="number" step="0.01" name="jumlah" required><br><br>
        <label for="jenis">Jenis (Pemasukan/Pengeluaran):</label>
        <select name="jenis">
            <option value="pemasukan">Pemasukan</option>
            <option value="pengeluaran">Pengeluaran</option>
        </select><br><br>
        <label for="tanggal">Tanggal (YYYY-MM-DD):</label>
        <input type="date" name="tanggal" required><br><br>
        <input type="submit" value="Tambah Transaksi">
    </form>
    <br>
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

@app.route('/', methods=['GET'])
def index():
    """Menampilkan halaman utama dengan daftar transaksi."""
    conn = create_connection(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT * FROM transaksi ORDER BY tanggal DESC")
    transaksis = cur.fetchall()
    return render_template_string(home_template, transaksis=transaksis)

@app.route('/tambah', methods=['POST'])
def tambah():
    """Menangani penambahan transaksi baru."""
    keterangan = request.form['keterangan']
    jumlah = request.form['jumlah']
    jenis = request.form['jenis']
    tanggal = request.form['tanggal']
    
    conn = create_connection(DATABASE)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO transaksi (keterangan, jumlah, jenis, tanggal) VALUES (?, ?, ?, ?)",
        (keterangan, jumlah, jenis, tanggal)
    )
    conn.commit()
    flash("Transaksi berhasil ditambahkan! Keuangan Anda semakin gemilang!")
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
