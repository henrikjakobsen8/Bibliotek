import sqlite3
import datetime
import os
from flask import Flask, request, render_template_string, redirect, url_for, flash, g, session
from functools import wraps

app = Flask(__name__)
app.secret_key = 'hemmelig_nogler'  # Skift til en stærk nøgle i produktion

DATABASE = 'bibliotek.db'

# HTML Template med designinspiration fra Vejlefjordskolen
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="da">
<head>
    <meta charset="UTF-8">
    <title>Bibliotek - Udlånssystem</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #f0f4f8; margin: 0; padding: 0; }
        header { background-color: #2a5d3b; padding: 20px; color: white; text-align: center; }
        main { padding: 20px; max-width: 600px; margin: auto; }
        form { background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        input[type="text"], select { width: 100%; padding: 10px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
        input[type="submit"] { background-color: #2a5d3b; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; }
        input[type="submit"]:hover { background-color: #244e33; }
        .message { padding: 10px; background-color: #e3f7e0; border-left: 5px solid #2a5d3b; margin-bottom: 20px; }
        a { color: #2a5d3b; text-decoration: none; display: inline-block; margin-top: 10px; }
    </style>
</head>
<body>
    <header>
        <h1>Bibliotekets Udlånssystem</h1>
    </header>
    <main>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <div class="message">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <form method="POST" action="/udlaan">
            <h2>Udlån af bog</h2>
            <label>Bruger stregkode:</label>
            <input type="text" name="bruger" required>
            <label>Bog stregkode:</label>
            <input type="text" name="bog" required>
            <input type="submit" value="Udlån">
        </form>

        <form method="POST" action="/aflevering">
            <h2>Aflever bog</h2>
            <label>Bog stregkode:</label>
            <input type="text" name="bog" required>
            <input type="submit" value="Aflever">
        </form>

        <a href="/udlaan-oversigt">Se aktuelle udlån</a><br>
        <a href="/admin">Adminside</a>
    </main>
</body>
</html>
'''

# Decorator til at beskytte admin sider
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Du skal være logget ind som admin")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Database-forbindelse
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

# Rute: Forside
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# Rute: Udlån
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

# Rute: Aflevering
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

# Rute: Aktuelle udlån
@app.route('/udlaan-oversigt', methods=['GET', 'POST'])
def udlaan_oversigt():
    if request.method == 'POST':
        bruger_kode = request.form['bruger']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            SELECT u.bog_kode, u.udlaan_dato, b.titel
            FROM udlaan u
            LEFT JOIN boeger b ON u.bog_kode = b.kode
            WHERE u.afleveret_dato IS NULL AND u.bruger_kode = ?
        """, (bruger_kode,))
        udlaante = cursor.fetchall()

        html = '''<html><head><title>Dine udlån</title><style>
            body { font-family: Segoe UI, sans-serif; background: #f8f9f4; color: #333; padding: 2em; }
            ul { list-style: none; padding: 0; }
            li { background: #fff; margin-bottom: 0.5em; padding: 0.5em; border-left: 4px solid #2a5d3b; }
            .expired { border-color: red; }
            a { display: inline-block; margin-top: 1em; color: white; background: #2a5d3b; padding: 0.5em 1em; text-decoration: none; border-radius: 4px; }
        </style></head><body>
        <h2>Dine aktuelle udlån</h2><ul>'''

        for bog_kode, dato, titel in udlaante:
            dato_obj = datetime.datetime.fromisoformat(dato)
            overskredet = (datetime.datetime.now() - dato_obj).days > 30
            css_class = "expired" if overskredet else ""
            udlån_dato = dato_obj.strftime('%Y-%m-%d')
            html += f'<li class="{css_class}"><b>{titel or bog_kode}</b> udlånt den {udlån_dato}'
            if overskredet:
                html += ' <span style="color:red;">(for sent afleveret)</span>'
            html += '</li>'

        html += '</ul><a href="/">Tilbage</a></body></html>'
        return html

    return render_template_string('''
        <h2>Se dine udlån</h2>
        <form method="post">
            <label>Indtast din stregkode:</label><br>
            <input type="text" name="bruger" required><br><br>
            <input type="submit" value="Vis udlån">
        </form>
        <a href="/">Tilbage til forsiden</a>
    ''')

    
@app.route('/admin')
@admin_required
def admin():
    ...
    return render_template_string('''
        <h2>Velkommen til Adminsiden</h2>
        <ul>
            <li><a href="/admin/opret-bruger">Opret bruger</a></li>
            <li><a href="/admin/opret-bog">Opret bog</a></li>
            <li><a href="/">Tilbage til forsiden</a></li>
            <li><a href="/admin/logout">Log ud</a></li>
        </ul>
    ''')
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        brugernavn = request.form.get('username')
        kodeord = request.form.get('password')
        if brugernavn == 'admin' and kodeord == 'admin':
            session['admin_logged_in'] = True
            flash('Du er nu logget ind som admin')
            return redirect(url_for('admin'))
        else:
            flash('Forkert brugernavn eller kodeord')
            return redirect(url_for('admin_login'))
    return render_template_string('''
        <h2>Admin Login</h2>
        <form method="post">
            <label>Brugernavn:</label><br>
            <input type="text" name="username" required><br>
            <label>Kodeord:</label><br>
            <input type="password" name="password" required><br><br>
            <input type="submit" value="Log ind">
        </form>
        <a href="/">Tilbage til forsiden</a>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <p style="color:red;">{{ message }}</p>
            {% endfor %}
          {% endif %}
        {% endwith %}
    ''')
    
@app.route('/admin/opret-bruger', methods=['GET', 'POST'])
@admin_required
def opret_bruger():
    if request.method == 'POST':
        kode = request.form['kode']
        navn = request.form['navn']
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO brugere (kode, navn) VALUES (?, ?)", (kode, navn))
            db.commit()
            flash("Bruger oprettet")
        except sqlite3.IntegrityError:
            flash("Bruger med den kode findes allerede")
        return redirect(url_for('admin'))
    
    return render_template_string('''
        <h2>Opret ny bruger</h2>
        <form method="post">
            <label>Stregkode:</label><br>
            <input type="text" name="kode" required><br>
            <label>Navn:</label><br>
            <input type="text" name="navn" required><br><br>
            <input type="submit" value="Opret">
        </form>
        <a href="/admin">Tilbage til adminside</a>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <p style="color:green;">{{ message }}</p>
            {% endfor %}
          {% endif %}
        {% endwith %}
    ''')

@app.route('/admin/opret-bog', methods=['GET', 'POST'])
@admin_required
def opret_bog():
    if request.method == 'POST':
        kode = request.form['kode']
        titel = request.form['titel']
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO boeger (kode, titel) VALUES (?, ?)", (kode, titel))
            db.commit()
            flash("Bog oprettet")
        except sqlite3.IntegrityError:
            flash("Bog med den kode findes allerede")
        return redirect(url_for('admin'))

    return render_template_string('''
        <h2>Opret ny bog</h2>
        <form method="post">
            <label>Stregkode:</label><br>
            <input type="text" name="kode" required><br>
            <label>Titel:</label><br>
            <input type="text" name="titel" required><br><br>
            <input type="submit" value="Opret">
        </form>
        <a href="/admin">Tilbage til adminside</a>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <p style="color:green;">{{ message }}</p>
            {% endfor %}
          {% endif %}
        {% endwith %}
    ''')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash("Du er nu logget ud")
    return redirect(url_for('index'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
