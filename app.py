import sqlite3
import datetime
import os
import io
import csv
from flask import Flask, request, render_template_string, redirect, url_for, flash, g, session

app = Flask(__name__)
app.secret_key = 'hemmelig_nogler'

DATABASE = 'bibliotek.db'

# --- DATABASE HELPERE ---
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
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
        cursor.execute('''CREATE TABLE IF NOT EXISTS brugere (
            kode TEXT PRIMARY KEY,
            navn TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS boeger (
            kode TEXT PRIMARY KEY,
            titel TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS udlaan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bruger_kode TEXT,
            bog_kode TEXT,
            udlaan_dato TEXT,
            afleveret_dato TEXT
        )''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS admin (
            brugernavn TEXT PRIMARY KEY,
            kodeord TEXT
        )''')
        # Tilføj default admin (brugernavn: admin, kodeord: admin)
        try:
            cursor.execute("INSERT INTO admin (brugernavn, kodeord) VALUES (?, ?)", ("admin", "admin"))
        except sqlite3.IntegrityError:
            pass
        db.commit()

init_db()

# --- ADMIN LOGIN BESKYTTELSE ---
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Du skal være logget ind som admin")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# --- UTILS ---
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

# --- ROUTES ---

# Forside med udlån/aflevering
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
@admin_required
def udlaan_oversigt():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT u.id, u.bog_kode, u.bruger_kode, u.udlaan_dato, u.afleveret_dato, b.titel, br.navn
        FROM udlaan u
        LEFT JOIN boeger b ON u.bog_kode = b.kode
        LEFT JOIN brugere br ON u.bruger_kode = br.kode
        ORDER BY u.udlaan_dato DESC
    """)
    udlaante = cursor.fetchall()

    html = '''
    <html><head><title>Udlåns Historik</title><style>
    body { font-family: Segoe UI, sans-serif; background: #f8f9f4; color: #333; padding: 2em; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ccc; padding: 0.5em; text-align: left; }
    th { background: #2a5d3b; color: white; }
    tr:nth-child(even) { background: #e9f1e7; }
    a { color: white; background: #2a5d3b; padding: 0.5em 1em; text-decoration: none; border-radius: 4px; display: inline-block; margin-top: 1em; }
    </style></head><body>
    <h2>Udlåns Historik (inkl. afleverede)</h2>
    <table>
    <tr><th>ID</th><th>Bog</th><th>Bruger</th><th>Udlånsdato</th><th>Afleveringsdato</th></tr>
    '''
    for udlaan in udlaante:
        titel = udlaan['titel'] or udlaan['bog_kode']
        navn = udlaan['navn'] or udlaan['bruger_kode']
        afleveret = udlaan['afleveret_dato'][:10] if udlaan['afleveret_dato'] else '-'
        html += f"<tr><td>{udlaan['id']}</td><td>{titel}</td><td>{navn}</td><td>{udlaan['udlaan_dato'][:10]}</td><td>{afleveret}</td></tr>"
    html += "</table><a href='/admin'>Tilbage til admin</a></body></html>"
    return html

# --- ADMIN LOGIN/LOGOUT ---
LOGIN_TEMPLATE = '''
<html><head><title>Admin Login</title><style>
body { font-family: Segoe UI, sans-serif; background: #f0f4f8; padding: 2em; }
form { max-width: 300px; margin: auto; background: white; padding: 1em; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
input[type=text], input[type=password] { width: 100%; padding: 0.5em; margin-bottom: 1em; border-radius: 4px; border: 1px solid #ccc; }
input[type=submit] { background: #2a5d3b; color: white; border: none; padding: 0.5em 1em; border-radius: 4px; cursor: pointer; }
input[type=submit]:hover { background: #244e33; }
.message { color: red; margin-bottom: 1em; }
</style></head><body>
<h2>Admin Login</h2>
{% with messages = get_flashed_messages() %}
  {% if messages %}
    {% for message in messages %}
      <div class="message">{{ message }}</div>
    {% endfor %}
  {% endif %}
{% endwith %}
<form method="POST">
    <label>Brugernavn:</label>
    <input type="text" name="brugernavn" required>
    <label>Kodeord:</label>
    <input type="password" name="kodeord" required>
    <input type="submit" value="Log ind">
</form>
</body></html>
'''

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        brugernavn = request.form['brugernavn']
        kodeord = request.form['kodeord']
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM admin WHERE brugernavn = ? AND kodeord = ?", (brugernavn, kodeord))
        admin = cursor.fetchone()
        if admin:
            session['admin_logged_in'] = True
            session['admin_brugernavn'] = brugernavn
            flash("Logget ind som admin")
            return redirect(url_for('admin'))
        else:
            flash("Forkert brugernavn eller kodeord")
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/admin/logout')
@admin_required
def admin_logout():
    session.clear()
    flash("Du er logget ud")
    return redirect(url_for('admin_login'))

# --- ADMIN SIDE MED BRUGERE & BØGER ---
ADMIN_TEMPLATE = '''
<html><head><title>Adminside</title><style>
body { font-family: Segoe UI, sans-serif; padding: 2em; background: #f8f9f4; }
h2 { color: #2a5d3b; }
section { background: white; padding: 1em; margin-bottom: 2em; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1);}
table { border-collapse: collapse; width: 100%; margin-top: 1em;}
th, td { border: 1px solid #ccc; padding: 0.5em; text-align: left;}
th { background: #2a5d3b; color: white;}
tr:nth-child(even) { background: #e9f1e7;}
input[type=text] { width: 95%; padding: 0.3em; }
button, input[type=submit] { background: #2a5d3b; color: white; border: none; padding: 0.3em 0.7em; border-radius: 4px; cursor: pointer; margin: 0 0.2em;}
button:hover, input[type=submit]:hover { background: #244e33;}
form.inline { display: inline; }
.message { padding: 0.5em; background-color: #e3f7e0; border-left: 5px solid #2a5d3b; margin-bottom: 1em; }
.filter-input { width: 100%; padding: 0.5em; margin-bottom: 1em; border-radius: 4px; border: 1px solid #ccc; }
.delete-confirm { color: red; font-weight: bold; }
a { color: #2a5d3b; text-decoration: none; display: inline-block; margin-top: 1em; }
</style>
<script>
function filterTable(inputId, tableId) {
    let input = document.getElementById(inputId);
    let filter = input.value.toLowerCase();
    let table = document.getElementById(tableId);
    let trs = table.getElementsByTagName("tr");
    for (let i = 1; i < trs.length; i++) {
        let tds = trs[i].getElementsByTagName("td");
        let found = false;
        for(let j=0; j<tds.length; j++) {
            if(tds[j].textContent.toLowerCase().indexOf(filter) > -1) {
                found = true;
                break;
            }
        }
        trs[i].style.display = found ? "" : "none";
    }
}

function confirmDelete(type, kode) {
    return confirm('Er du sikker på du vil slette ' + type + ' med kode ' + kode + '?');
}
</script>
</head><body>
<h1>Adminside</h1>
<p>Logget ind som: {{admin_brugernavn}} | <a href="{{url_for('admin_logout')}}">Log ud</a></p>

<section>
    <h2>Brugere (aktive udlån vist i parentes)</h2>
    <input class="filter-input" type="text" id="filterBrugere" onkeyup="filterTable('filterBrugere', 'brugereTable')" placeholder="Søg brugere...">
    <table id="brugereTable">
    <tr><th>Kode</th><th>Navn</th><th>Aktive udlån</th><th>Rediger</th><th>Slet</th></tr>
    {% for b in brugere %}
    <tr>
        <form method="POST" action="{{url_for('admin_edit_bruger', kode=b['kode'])}}" class="inline">
            <td>{{b['kode']}}</td>
            <td><input name="navn" type="text" value="{{b['navn']}}" required></td>
            <td style="text-align:center;">{{b['aktive']}}</td>
            <td><input type="submit" value="Gem"></td>
        </form>
        <td><form method="POST" action="{{url_for('admin_delete_bruger', kode=b['kode'])}}" onsubmit="return confirmDelete('brugeren', '{{b['kode']}}');" class="inline">
            <input type="submit" value="Slet" {% if b['aktive'] > 0 %}disabled title="Kan ikke slettes pga aktive udlån"{% endif %}>
        </form></td>
    </tr>
    {% endfor %}
    </table>
</section>

<section>
    <h2>Bøger (aktive udlån vist i parentes)</h2>
    <input class="filter-input" type="text" id="filterBoeger" onkeyup="filterTable('filterBoeger', 'boegerTable')" placeholder="Søg bøger...">
    <table id="boegerTable">
    <tr><th>Kode</th><th>Titel</th><th>Aktive udlån</th><th>Rediger</th><th>Slet</th></tr>
    {% for b in boeger %}
    <tr>
        <form method="POST" action="{{url_for('admin_edit_bog', kode=b['kode'])}}" class="inline">
            <td>{{b['kode']}}</td>
            <td><input name="titel" type="text" value="{{b['titel']}}" required></td>
            <td style="text-align:center;">{{b['aktive']}}</td>
            <td><input type="submit" value="Gem"></td>
        </form>
        <td><form method="POST" action="{{url_for('admin_delete_bog', kode=b['kode'])}}" onsubmit="return confirmDelete('bogen', '{{b['kode']}}');" class="inline">
            <input type="submit" value="Slet" {% if b['aktive'] > 0 %}disabled title="Kan ikke slettes pga aktive udlån"{% endif %}>
        </form></td>
    </tr>
    {% endfor %}
    </table>
</section>

<section>
    <h2>Importer Brugere (CSV)</h2>
    <form method="POST" action="{{url_for('admin_upload_brugere')}}" enctype="multipart/form-data">
        <input type="file" name="csvfile" accept=".csv" required>
        <input type="submit" value="Upload">
    </form>
</section>

<section>
    <h2>Importer Bøger (CSV)</h2>
    <form method="POST" action="{{url_for('admin_upload_boeger')}}" enctype="multipart/form-data">
        <input type="file" name="csvfile" accept=".csv" required>
        <input type="submit" value="Upload">
    </form>
</section>

<section>
    <h2>Udlåns Historik</h2>
    <a href="{{url_for('udlaan_oversigt')}}">Se alle udlån (inkl. afleverede)</a>
</section>

</body></html>
'''

@app.route('/admin')
@admin_required
def admin():
    db = get_db()
    cursor = db.cursor()

    # Brugere med aktive udlån
    cursor.execute("""
    SELECT b.kode, b.navn,
      (SELECT COUNT(*) FROM udlaan u WHERE u.bruger_kode = b.kode AND u.afleveret_dato IS NULL) as aktive
    FROM brugere b ORDER BY b.kode
    """)
    brugere = cursor.fetchall()

    # Bøger med aktive udlån
    cursor.execute("""
    SELECT b.kode, b.titel,
      (SELECT COUNT(*) FROM udlaan u WHERE u.bog_kode = b.kode AND u.afleveret_dato IS NULL) as aktive
    FROM boeger b ORDER BY b.kode
    """)
    boeger = cursor.fetchall()

    return render_template_string(ADMIN_TEMPLATE, brugere=brugere, boeger=boeger, admin_brugernavn=session.get('admin_brugernavn'))

# --- ADMIN REDIGER OG SLET BRUGER ---
@app.route('/admin/brugere/<kode>', methods=['POST'])
@admin_required
def admin_edit_bruger(kode):
    navn = request.form['navn']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE brugere SET navn = ? WHERE kode = ?", (navn, kode))
    db.commit()
    flash(f"Bruger {kode} opdateret")
    return redirect(url_for('admin'))

@app.route('/admin/brugere/<kode>/delete', methods=['POST'])
@admin_required
def admin_delete_bruger(kode):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM udlaan WHERE bruger_kode = ? AND afleveret_dato IS NULL", (kode,))
    aktive = cursor.fetchone()[0]
    if aktive > 0:
        flash("Kan ikke slette bruger med aktive udlån")
        return redirect(url_for('admin'))

    cursor.execute("DELETE FROM brugere WHERE kode = ?", (kode,))
    db.commit()
    flash(f"Bruger {kode} slettet")
    return redirect(url_for('admin'))

# --- ADMIN REDIGER OG SLET BOG ---
@app.route('/admin/boeger/<kode>', methods=['POST'])
@admin_required
def admin_edit_bog(kode):
    titel = request.form['titel']
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE boeger SET titel = ? WHERE kode = ?", (titel, kode))
    db.commit()
    flash(f"Bog {kode} opdateret")
    return redirect(url_for('admin'))

@app.route('/admin/boeger/<kode>/delete', methods=['POST'])
@admin_required
def admin_delete_bog(kode):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM udlaan WHERE bog_kode = ? AND afleveret_dato IS NULL", (kode,))
    aktive = cursor.fetchone()[0]
    if aktive > 0:
        flash("Kan ikke slette bog med aktive udlån")
        return redirect(url_for('admin'))

    cursor.execute("DELETE FROM boeger WHERE kode = ?", (kode,))
    db.commit()
    flash(f"Bog {kode} slettet")
    return redirect(url_for('admin'))

# --- UPLOAD CSV FOR BRUGERE ---
@app.route('/admin/upload/brugere', methods=['POST'])
@admin_required
def admin_upload_brugere():
    if 'csvfile' not in request.files:
        flash("Ingen fil valgt")
        return redirect(url_for('admin'))
    file = request.files['csvfile']
    if file.filename == '':
        flash("Ingen fil valgt")
        return redirect(url_for('admin'))
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)
    db = get_db()
    cursor = db.cursor()
    count = 0
    for row in csv_input:
        if len(row) < 2:
            continue
        kode, navn = row[0].strip(), row[1].strip()
        try:
            cursor.execute("INSERT INTO brugere (kode, navn) VALUES (?, ?)", (kode, navn))
            count += 1
        except sqlite3.IntegrityError:
            cursor.execute("UPDATE brugere SET navn = ? WHERE kode = ?", (navn, kode))
    db.commit()
    flash(f"{count} brugere importeret/opdateret")
    return redirect(url_for('admin'))

# --- UPLOAD CSV FOR BØGER ---
@app.route('/admin/upload/boeger', methods=['POST'])
@admin_required
def admin_upload_boeger():
    if 'csvfile' not in request.files:
        flash("Ingen fil valgt")
        return redirect(url_for('admin'))
    file = request.files['csvfile']
    if file.filename == '':
        flash("Ingen fil valgt")
        return redirect(url_for('admin'))
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)
    db = get_db()
    cursor = db.cursor()
    count = 0
    for row in csv_input:
        if len(row) < 2:
            continue
        kode, titel = row[0].strip(), row[1].strip()
        try:
            cursor.execute("INSERT INTO boeger (kode, titel) VALUES (?, ?)", (kode, titel))
            count += 1
        except sqlite3.IntegrityError:
            cursor.execute("UPDATE boeger SET titel = ? WHERE kode = ?", (titel, kode))
    db.commit()
    flash(f"{count} bøger importeret/opdateret")
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
