import sqlite3
import datetime
import os
from flask import Flask, request, render_template_string, redirect, url_for, flash, g

app = Flask(__name__)
app.secret_key = 'hemmelig_nogler'

DATABASE = 'bibliotek.db'

# HTML Template med designinspiration fra Vejlefjordskolen
HTML_TEMPLATE = '''...'''  # (forkortet for læsbarhed)


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS brugere (kode TEXT PRIMARY KEY, navn TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS boeger (kode TEXT PRIMARY KEY, titel TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS udlaan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bruger_kode TEXT,
            bog_kode TEXT,
            udlaan_dato TEXT,
            afleveret_dato TEXT
        )''')
        db.commit()

init_db()


def find_i_db(tabel, kode):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM {tabel} WHERE kode = ?", (kode,))
    return cursor.fetchone()

def bog_udlaant(kode):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM udlaan WHERE bog_kode = ? AND afleveret_dato IS NULL", (kode,))
    return cursor.fetchone() is not None

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/udlaan', methods=['POST'])
def udlaan():
    bruger = request.form['bruger']
    bog = request.form['bog']

    if not find_i_db('brugere', bruger):
        flash("Bruger ikke fundet")
        return redirect(url_for('index'))
    if not find_i_db('boeger', bog):
        flash("Bog ikke fundet")
        return redirect(url_for('index'))
    if bog_udlaant(bog):
        flash("Bog er allerede udlånt")
        return redirect(url_for('index'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO udlaan (bruger_kode, bog_kode, udlaan_dato, afleveret_dato) VALUES (?, ?, ?, NULL)",
                   (bruger, bog, datetime.datetime.now().isoformat()))
    db.commit()
    flash("Udlån registreret")
    return redirect(url_for('index'))

@app.route('/aflevering', methods=['POST'])
def aflevering():
    bog = request.form['bog']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE udlaan SET afleveret_dato = ? WHERE bog_kode = ? AND afleveret_dato IS NULL",
                   (datetime.datetime.now().isoformat(), bog))
    if cursor.rowcount > 0:
        db.commit()
        flash("Aflevering registreret")
    else:
        flash("Bog er ikke udlånt")
    return redirect(url_for('index'))

@app.route('/udlaan-oversigt')
def udlaan_oversigt():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT u.bog_kode, u.bruger_kode, u.udlaan_dato, b.titel, br.navn
        FROM udlaan u
        LEFT JOIN boeger b ON u.bog_kode = b.kode
        LEFT JOIN brugere br ON u.bruger_kode = br.kode
        WHERE u.afleveret_dato IS NULL
    """)
    udlaante = cursor.fetchall()

    html = '''<html><head><title>Udlånsliste</title><style>
        body { font-family: Segoe UI, sans-serif; background: #f8f9f4; color: #333; padding: 2em; }
        ul { list-style: none; padding: 0; }
        li { background: #fff; margin-bottom: 0.5em; padding: 0.5em; border-left: 4px solid #2a5d3b; }
        a { display: inline-block; margin-top: 1em; color: white; background: #2a5d3b; padding: 0.5em 1em; text-decoration: none; border-radius: 4px; }
    </style></head><body><h2>Aktuelle udlån</h2><ul>'''
    for bog_kode, bruger_kode, dato, titel, navn in udlaante:
        vis_bog = titel or bog_kode
        vis_bruger = navn or bruger_kode
        html += f"<li><b>{vis_bog}</b> lånt af <i>{vis_bruger}</i> den {dato[:10]}</li>"
    html += '</ul><a href="/">Tilbage</a></body></html>'
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
