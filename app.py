import csv
import datetime
import os
from flask import Flask, request, render_template_string, redirect, url_for, flash, session
from functools import wraps

app = Flask(__name__)
app.secret_key = 'hemmelig_nogler'

# CSV filer
BRUGERE_CSV = 'brugere.csv'
BOEGER_CSV = 'boeger.csv'
UDLAAN_CSV = 'udlaan.csv'

# Hjælpemetoder til CSV

def read_csv(filename):
    try:
        with open(filename, newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []

def write_csv(filename, data, fieldnames):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def append_csv(filename, row, fieldnames):
    file_exists = os.path.exists(filename)
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def find_in_csv(filename, key, value):
    rows = read_csv(filename)
    for row in rows:
        if row[key] == value:
            return row
    return None

def bog_udlaant(bog_kode):
    udlaan = read_csv(UDLAAN_CSV)
    for u in udlaan:
        if u['bog_kode'] == bog_kode and u['afleveret_dato'] == '':
            return True
    return False

# Ruter
@app.route('/')
def index():
    return render_template_string("""
        ...
    """)

@app.route('/udlaan', methods=['POST'])
def udlaan():
    bruger = request.form['bruger']
    bog = request.form['bog']

    if not find_in_csv(BRUGERE_CSV, 'kode', bruger):
        flash("Bruger ikke fundet")
        return redirect(url_for('index'))
    if not find_in_csv(BOEGER_CSV, 'kode', bog):
        flash("Bog ikke fundet")
        return redirect(url_for('index'))
    if bog_udlaant(bog):
        flash("Bog er allerede udlånt")
        return redirect(url_for('index'))

    append_csv(UDLAAN_CSV, {
        'bruger_kode': bruger,
        'bog_kode': bog,
        'udlaan_dato': datetime.datetime.now().isoformat(),
        'afleveret_dato': ''
    }, ['bruger_kode', 'bog_kode', 'udlaan_dato', 'afleveret_dato'])

    flash("Udlån registreret")
    return redirect(url_for('index'))

@app.route('/aflevering', methods=['POST'])
def aflevering():
    bog = request.form['bog']
    udlaan = read_csv(UDLAAN_CSV)
    for u in udlaan:
        if u['bog_kode'] == bog and u['afleveret_dato'] == '':
            u['afleveret_dato'] = datetime.datetime.now().isoformat()
            write_csv(UDLAAN_CSV, udlaan, ['bruger_kode', 'bog_kode', 'udlaan_dato', 'afleveret_dato'])
            flash("Aflevering registreret")
            return redirect(url_for('index'))
    flash("Bog er ikke udlånt")
    return redirect(url_for('index'))

# De resterende ruter (udlaan_oversigt, admin, opret_bruger/bog, osv.) skal på lignende vis omskrives til CSV.
# Jeg fortsætter med at opdatere disse ruter i næste trin.
