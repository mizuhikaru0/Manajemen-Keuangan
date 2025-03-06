from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import os, io, csv, json
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret-key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Model untuk pemasukan, anggaran, dan transaksi
class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    allocated = db.Column(db.Float, nullable=False)
    spent = db.Column(db.Float, default=0)
    start = db.Column(db.Date, nullable=False)
    end = db.Column(db.Date, nullable=False)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    note = db.Column(db.String(255))

with app.app_context():
    db.create_all()

# Fungsi helper untuk analisis keuangan
def get_budget_recommendations():
    recommendations = []
    budgets = Budget.query.all()
    for budget in budgets:
        if budget.allocated > 0:
            percentage_used = (budget.spent / budget.allocated) * 100
        else:
            percentage_used = 0
        if percentage_used > 90:
            recommendations.append(
                f"Anda telah menggunakan {percentage_used:.0f}% dari anggaran untuk {budget.category}. Pertimbangkan mengurangi pengeluaran di kategori ini."
            )
        elif percentage_used < 50:
            recommendations.append(
                f"Penggunaan anggaran untuk {budget.category} masih rendah ({percentage_used:.0f}%). Evaluasi apakah anggaran sudah sesuai dengan kebutuhan."
            )
    return recommendations

def get_overall_recommendation():
    income_record = Income.query.order_by(Income.date.desc()).first()
    total_income = income_record.amount if income_record else 0
    total_spending = db.session.query(func.sum(Transaction.amount)).scalar() or 0
    remaining = total_income - total_spending
    if total_income == 0:
        return "Belum ada data pemasukan, silakan input pemasukan terlebih dahulu."
    elif remaining < total_income * 0.1:
        return "Pengeluaran Anda sudah hampir mencapai batas pemasukan. Pertimbangkan mengurangi pengeluaran atau meningkatkan pemasukan."
    elif remaining > total_income * 0.3:
        return "Keuangan Anda dalam kondisi baik. Anda memiliki sisa yang cukup untuk ditabung atau diinvestasikan."
    else:
        return "Keuangan Anda stabil, namun tetap perhatikan pengeluaran agar tidak melebihi anggaran."

def get_smart_budget_advice():
    advice = []
    income_record = Income.query.order_by(Income.date.desc()).first()
    if not income_record or income_record.amount <= 0:
        advice.append("Silakan masukkan data pemasukan terlebih dahulu untuk mendapatkan saran pengelolaan anggaran yang tepat.")
        return advice
    total_income = income_record.amount
    total_spent = db.session.query(func.sum(Transaction.amount)).scalar() or 0
    savings = total_income - total_spent
    savings_rate = (savings / total_income) * 100
    if savings_rate < 20:
        advice.append("Anda menyisakan kurang dari 20% dari pemasukan sebagai tabungan. Pertimbangkan untuk mengurangi pengeluaran atau meningkatkan pemasukan.")
    elif savings_rate < 30:
        advice.append("Tabungan Anda cukup, namun masih bisa ditingkatkan untuk mencapai kestabilan keuangan yang lebih baik.")
    else:
        advice.append("Tabungan Anda sudah memadai.")
    budgets = Budget.query.all()
    for budget in budgets:
        if budget.allocated > 0:
            percentage_used = (budget.spent / budget.allocated) * 100
        else:
            percentage_used = 0
        if percentage_used > 90:
            advice.append(f"Penggunaan anggaran untuk kategori {budget.category} sudah sangat tinggi ({percentage_used:.0f}%). Pertimbangkan pengurangan pengeluaran atau penyesuaian anggaran.")
        elif 50 <= percentage_used <= 90:
            advice.append(f"Kategori {budget.category} sudah mencapai penggunaan anggaran sebesar {percentage_used:.0f}%. Jaga agar pengeluaran tidak terus meningkat.")
        elif 0 < percentage_used < 50:
            advice.append(f"Kategori {budget.category} masih rendah dalam penggunaan anggaran ({percentage_used:.0f}%). Evaluasi kembali apakah alokasi anggaran sudah sesuai dengan kebutuhan.")
    transaction_count = Transaction.query.count()
    if transaction_count > 0:
        average_expense = total_spent / transaction_count
        advice.append(f"Rata-rata pengeluaran per transaksi: Rp {average_expense:,.0f}. Pertimbangkan untuk mencatat dan mengelompokkan transaksi agar pengelolaan anggaran lebih efisien.")
    return advice

@app.template_filter('number_format')
def number_format(value):
    try:
        return "{:,.0f}".format(value)
    except (ValueError, TypeError):
        return value

# Rute utama untuk menampilkan halaman index
@app.route('/')
def index():
    income_record = Income.query.order_by(Income.date.desc()).first()
    budgets = Budget.query.all()
    transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    overall_income = income_record.amount if income_record else 0
    total_expense = db.session.query(func.sum(Transaction.amount)).scalar() or 0
    overall_balance = overall_income - total_expense
    recommendations = get_budget_recommendations()
    overall_recommendation = get_overall_recommendation()
    smart_advice = get_smart_budget_advice()
    return render_template("index.html", income=income_record, budgets=budgets, transactions=transactions,
                           overall_income=overall_income, total_expense=total_expense, overall_balance=overall_balance,
                           recommendations=recommendations, overall_recommendation=overall_recommendation, smart_advice=smart_advice)

# Rute untuk menambahkan pemasukan
@app.route('/add_income', methods=['POST'])
def add_income():
    amount = request.form.get('income_input')
    date_str = request.form.get('income_date')
    try:
        amount = float(amount)
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        flash("Data pemasukan tidak valid.")
        return redirect(url_for('index'))
    # Hapus data pemasukan sebelumnya (hanya menyimpan 1 data pemasukan)
    previous = Income.query.first()
    if previous:
        db.session.delete(previous)
    income_record = Income(amount=amount, date=date_obj)
    db.session.add(income_record)
    db.session.commit()
    return redirect(url_for('index'))

# Rute untuk menambahkan anggaran
@app.route('/add_budget', methods=['POST'])
def add_budget():
    category = request.form.get('budget_category')
    allocated = request.form.get('budget_amount')
    start_str = request.form.get('budget_start')
    end_str = request.form.get('budget_end')
    try:
        allocated = float(allocated)
        start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
    except:
        flash("Data anggaran tidak valid.")
        return redirect(url_for('index'))
    new_budget = Budget(category=category, allocated=allocated, spent=0, start=start_date, end=end_date)
    db.session.add(new_budget)
    db.session.commit()
    return redirect(url_for('index'))

# Rute untuk menambahkan pengeluaran
@app.route('/add_expense', methods=['POST'])
def add_expense():
    category = request.form.get('expense_category')
    amount = request.form.get('expense_amount')
    date_str = request.form.get('expense_date')
    note = request.form.get('expense_note')
    try:
        amount = float(amount)
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        flash("Data pengeluaran tidak valid.")
        return redirect(url_for('index'))
    # Perbarui nilai pengeluaran pada anggaran yang sesuai
    budget = Budget.query.filter_by(category=category).first()
    if budget:
        budget.spent += amount
    new_transaction = Transaction(category=category, amount=amount, date=date_obj, note=note)
    db.session.add(new_transaction)
    db.session.commit()
    return redirect(url_for('index'))

# Rute ekspor ke PDF menggunakan ReportLab
@app.route('/export_pdf')
def export_pdf():
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50
    p.drawString(50, y, "Data Keuangan")
    y -= 30
    income_record = Income.query.first()
    if income_record:
        p.drawString(50, y, f"Pemasukan: Rp {income_record.amount:,.0f} (Tanggal: {income_record.date})")
        y -= 20
    budgets = Budget.query.all()
    p.drawString(50, y, "Anggaran:")
    y -= 20
    for b in budgets:
        line = f"{b.category} - Anggaran: Rp {b.allocated:,.0f}, Terpakai: Rp {b.spent:,.0f}, Periode: {b.start} s/d {b.end}"
        p.drawString(50, y, line)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50
    transactions = Transaction.query.all()
    p.drawString(50, y, "Transaksi:")
    y -= 20
    for tx in transactions:
        line = f"{tx.date} - {tx.category} - Rp {tx.amount:,.0f} {f'({tx.note})' if tx.note else ''}"
        p.drawString(50, y, line)
        y -= 20
        if y < 50:
            p.showPage()
            y = height - 50
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="data-keuangan.pdf", mimetype='application/pdf')

# Rute ekspor ke Excel (CSV)
@app.route('/export_excel')
def export_excel():
    output = io.StringIO()
    writer = csv.writer(output)
    # Data pemasukan
    writer.writerow(["Pemasukan"])
    income_record = Income.query.first()
    if income_record:
        writer.writerow(["Amount", "Tanggal"])
        writer.writerow([income_record.amount, income_record.date])
    else:
        writer.writerow(["Tidak ada data"])
    writer.writerow([])
    # Data anggaran
    writer.writerow(["Anggaran"])
    writer.writerow(["Kategori", "Anggaran", "Terpakai", "Sisa", "Periode"])
    budgets = Budget.query.all()
    for b in budgets:
        remaining = b.allocated - b.spent
        writer.writerow([b.category, b.allocated, b.spent, remaining, f"{b.start} s/d {b.end}"])
    writer.writerow([])
    # Data transaksi
    writer.writerow(["Transaksi"])
    writer.writerow(["Tanggal", "Kategori", "Amount", "Note"])
    transactions = Transaction.query.all()
    for tx in transactions:
        writer.writerow([tx.date, tx.category, tx.amount, tx.note or ""])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode('utf-8')), as_attachment=True,
                     download_name="data-keuangan.csv", mimetype="text/csv")

# Ekspor data ke format JSON
@app.route('/export_json')
def export_json():
    data = {
        "income": None,
        "budgets": [],
        "transactions": []
    }
    income_record = Income.query.first()
    if income_record:
        data["income"] = {"amount": income_record.amount, "date": income_record.date.isoformat()}
    budgets = Budget.query.all()
    for b in budgets:
        data["budgets"].append({
            "category": b.category,
            "allocated": b.allocated,
            "spent": b.spent,
            "start": b.start.isoformat(),
            "end": b.end.isoformat()
        })
    transactions = Transaction.query.all()
    for tx in transactions:
        data["transactions"].append({
            "date": tx.date.isoformat(),
            "category": tx.category,
            "amount": tx.amount,
            "note": tx.note
        })
    return jsonify(data)

# Impor data dari file JSON
@app.route('/import_json', methods=['POST'])
def import_json():
    file = request.files.get('import_file')
    if not file:
        flash("Tidak ada file yang diunggah.")
        return redirect(url_for('index'))
    try:
        data = json.load(file)
    except:
        flash("Gagal membaca file JSON.")
        return redirect(url_for('index'))
    # Hapus data lama
    Income.query.delete()
    Budget.query.delete()
    Transaction.query.delete()
    db.session.commit()
    # Impor data pemasukan
    if data.get("income"):
        inc = data["income"]
        income_record = Income(amount=inc["amount"], date=datetime.fromisoformat(inc["date"]).date())
        db.session.add(income_record)
    # Impor data anggaran
    for b in data.get("budgets", []):
        budget = Budget(
            category=b["category"],
            allocated=b["allocated"],
            spent=b["spent"],
            start=datetime.fromisoformat(b["start"]).date(),
            end=datetime.fromisoformat(b["end"]).date()
        )
        db.session.add(budget)
    # Impor data transaksi
    for tx in data.get("transactions", []):
        transaction = Transaction(
            date=datetime.fromisoformat(tx["date"]).date(),
            category=tx["category"],
            amount=tx["amount"],
            note=tx.get("note")
        )
        db.session.add(transaction)
    db.session.commit()
    flash("Data berhasil diimpor!")
    return redirect(url_for('index'))

# Reset semua data
@app.route('/reset')
def reset_data():
    Income.query.delete()
    Budget.query.delete()
    Transaction.query.delete()
    db.session.commit()
    flash("Semua data telah direset.")
    return redirect(url_for('index'))

# Rute backup dan restore (implementasi dummy)
@app.route('/backup')
def backup():
    flash("Backup ke cloud berhasil (dummy).")
    return redirect(url_for('index'))

@app.route('/restore')
def restore():
    flash("Restore dari cloud berhasil (dummy).")
    return redirect(url_for('index'))

@app.route('/edit_income')
def edit_income():
    income_record = Income.query.first()
    if income_record:
        db.session.delete(income_record)
        db.session.commit()
    return redirect(url_for('index'))

@app.before_request
def remove_expired_budgets():
    today = datetime.today().date()
    expired_budgets = Budget.query.filter(Budget.end < today).all()
    if expired_budgets:
        for budget in expired_budgets:
            db.session.delete(budget)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
