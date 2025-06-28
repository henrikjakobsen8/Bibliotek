import sqlite3
import datetime
import os
from flask import Flask, request, render_template_string, redirect, url_for, flash, g, session, send_file
import csv
import io

app = Flask(__name__)
app.secret_key = 'hemmelig_nogler'  # Skift til noget sikkert i produktion

DATABASE = 'bibliotek.db'

# --- Admin login data (simpelt setup) ---
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "bibliotek123"

# HTML-template med responsivt design + alle funktioner
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="da">
<head>
    <meta charset="UTF-8" />
    <title>Bibliotek Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #f0f4f8; margin:0; padding:0; }
        header { background-color: #2a5d3b; padding: 1rem; color: white; text-align: center; }
        main { padding: 1rem; max-width: 900px; margin: auto; }
        h1, h2 { color: #2a5d3b; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 1rem; }
        th, td { border: 1px solid #ccc; padding: 0.5rem; text-align: left; }
        th { background-color: #d8e4d8; }
        input[type="text"], input[type="password"], select {
            padding: 0.4rem; margin-bottom: 0.5rem; width: 100%; max-width: 300px;
            border-radius: 4px; border: 1px solid #ccc;
        }
        button, input[type="submit"] {
            background-color: #2a5d3b; color: white; border: none; padding: 0.5rem 1rem;
            border-radius: 4px; cursor: pointer; margin-top: 0.5rem;
        }
        button:hover, input[type="submit"]:hover { background-color: #244e33; }
        .flex-row { display: flex; flex-wrap: wrap; gap: 1rem; }
        .flex-col { flex: 1 1 300px; }
        .message { padding: 0.5rem; background-color: #e3f7e0; border-left: 5px solid #2a5d3b; margin-bottom: 1rem; }
        nav a { color: white; text-decoration: none; margin-left: 1rem; }
        nav { text-align: right; margin-bottom: 1rem; }
        .search-input { max-width: 250px; margin-bottom: 1rem; }
        @media (max-width: 600px) {
            .flex-row { flex-direction: column; }
        }
        /* Modal styles for confirmation */
        .modal {
            display:none; position: fixed; z-index: 1000; left:0; top:0; width:100%; height:100%;
            overflow:auto; background-color: rgba(0,0,0,0.4);
        }
        .modal-content {
            background-color: #fefefe; margin: 15% auto; padding: 1rem; border: 1px solid #888;
            width: 90%; max-width: 400px; border-radius: 8px;
        }
        .modal-buttons { text-align: right; margin-top: 1rem; }
    </style>
    <script>
        // Simpel bekræftelse før sletning
        function confirmDelete(type, kode) {
            const modal = document.getElementById('modal');
            const modalText = document.getElementById('modal-text');
            modal.style.display = 'block';
            modalText.textContent = `Er du sikker på, at du vil slette ${type} med kode "${kode}"?`;
            document.getElementById('confirm-delete-btn').onclick = function() {
                window.location.href = `/admin/delete_${type}?kode=${kode}`;
            }
        }
        function closeModal() {
            document.getElementById('modal').style.display = 'none';
        }

        // Inline redigering - enable save button
        function enableSave(btn) {
            btn.disabled = false;
        }

        // Søgefunktion for tabeller
        function searchTable(inputId, tableId) {
            let input = document.getElementById(inputId);
            let filter = input.value.toLowerCase();
            let table = document.getElementById(tableId);
            let trs = table.getElementsByTagName("tr");
            for (let i=1; i<trs.length; i++) {
                let tds = trs[i].getElementsByTagName("td");
                let found = false;
                for (let j=0; j<tds.length; j++) {
                    if (tds[j].textContent.toLowerCase().indexOf(filter) > -1) {
                        found = true;
                        break;
                    }
                }
                trs[i].style.display = found ? "" : "none";
            }
        }
    </script>
</head>
<body>
<header>
    <h1>Bibliotek Admin</h1>
    <nav>
        <a href="/">Til Udlån</a>
        <a href="/admin/logout" style="color:#ff9999;">Log ud</a>
    </nav>
</header>
<main>

{% with messages = get_flashed_messages() %}
  {% if messages %}
    {% for message in messages %}
      <div class="message">{{ message }}</div>
    {% endfor %}
  {% endif %}
{% endwith %}

<h2>Brugere <input id="userSearch" class="search-input" type="text" placeholder="Søg brugere..." onkeyup="searchTable('userSearch', 'userTable')" /></h2>
<table id="userTable" aria-label="Brugerliste">
<thead>
    <tr><th>Kode</th><th>Navn</th><th>Aktuelle Udlån</th><th>Rediger</th><th>Slet</th></tr>
</thead>
<tbody>
    {% for kode, navn, udlaan_antal in brugere %}
    <tr>
        <form method="POST" action="/admin/edit_bruger">
        <td>{{ kode }}<input type="hidden" name="kode" value="{{ kode }}"></td>
        <td><input type="text" name="navn" value="{{ navn }}" oninput="enableSave(this.form.querySelector('button'))" required></td>
        <td>{{ udlaan_antal }}</td>
        <td><button type="submit" disabled>Gem</button></td>
        <td><button type="button" onclick="confirmDelete('bruger', '{{ kode }}')">Slet</button></td>
        </form>
    </tr>
    {% endfor %}
</tbody>
</table>

<h3>Tilføj ny bruger</h3>
<form method="POST" action="/admin/add_bruger" enctype="multipart/form-data">
    <input type="text" name="kode" placeholder="Bruger stregkode" required maxlength="50" />
    <input type="text" name="navn" placeholder="Brugernavn" required maxlength="100" />
    <button type="submit">Tilføj bruger</button>
</form>
<form method="POST" action="/admin/upload_brugere" enctype="multipart/form-data" style="margin-top: 1rem;">
    <label>Upload CSV (kode, navn):</label><br />
    <input type="file" name="file" accept=".csv" required />
    <button type="submit">Upload brugere</button>
</form>

<hr />

<h2>Bøger <input id="bookSearch" class="search-input" type="text" placeholder="Søg bøger..." onkeyup="searchTable('bookSearch', 'bookTable')" /></h2>
<table id="bookTable" aria-label="Bogliste">
<thead>
    <tr><th>Kode</th><th>Titel</th><th>Aktuelle Udlån</th><th>Rediger</th><th>Slet</th></tr>
</thead>
<tbody>
    {% for kode, titel, udlaan_antal in boeger %}
    <tr>
        <form method="POST" action="/admin/edit_bog">
        <td>{{ kode }}<input type="hidden" name="kode" value="{{ kode }}"></td>
        <td><input type="text" name="titel" value="{{ titel }}" oninput="enableSave(this.form.querySelector('button'))" required></td>
        <td>{{ udlaan_antal }}</td>
        <td><button type="submit" disabled>Gem</button></td>
        <td><button type="button" onclick="confirmDelete('bog', '{{ kode }}')">Slet</button></td>
        </form>
    </tr>
    {% endfor %}
</tbody>
</table>

<h3>Tilføj ny bog</h3>
<form method="POST" action="/admin/add_bog" enctype="multipart/form-data">
    <input type="text" name="kode" placeholder="Bog stregkode" required maxlength="50" />
    <input type="text" name="titel" placeholder="Bogtitel" required maxlength="200" />
    <button type="submit">Tilføj bog</button>
</form>
<form method="POST" action="/admin/upload_boeger" enctype="multipart/form-data" style="margin-top: 1rem;">
    <label>Upload CSV (kode, titel):</label><br />
    <input type="file" name="file" accept=".csv" required />
    <button type="submit">Upload bøger</button>
</form>

<hr />

<h2>Udlåns-historik</h2>
<form method="GET" action="/admin" style="margin-bottom: 1rem;">
    <input type="text" name="filter" placeholder="Søg efter bruger, bog eller dato" style="width: 300px;" value="{{ request.args.get('filter', '') }}" />
    <button type="submit">Søg</button>
</form>
<table aria-label="Udlåns Historik">
<thead>
    <tr>
        <th>Bruger</th><th>Bog</th><th>Udlån Dato</th><th>Afleveret Dato</th>
    </tr>
</thead>
<tbody>
    {% for bruger, bog, udlaan_dato, afleveret_dato in historik %}
    <tr>
        <td>{{ bruger }}</td>
        <td>{{ bog }}</td>
        <td>{{ udlaan_dato[:10] }}</td>
        <td>{% if afleveret_dato %}{{ afleveret_dato[:10] }}{% else %}Ikke afleveret{% endif %}</td>
    </tr>
    {% endfor %}
</tbody>
</table>

<!-- Modal for slet -->
<div id="modal" class="modal">
  <div class="modal-content">
    <p id="modal-text"></p>
    <div class="modal-buttons">
      <button onclick="closeModal()">Annuller</button>
      <button id="confirm-delete-btn">Slet</button>
    </div>
  </div>
</div>

</main>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="da">
<head>
    <meta charset="UTF-8" />
    <title>Admin Login</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f4f8; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;}
        form { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); width: 300px;}
        input { width: 100%; padding: 0.5rem; margin: 0.5rem 0; border-radius: 4px; border: 1px solid #ccc; }
        button { background-color: #2a5d3b; color: white; border: none; padding: 0.5rem; width: 100%; border-radius: 4px; cursor: pointer;}
        button:hover { background-color: #244e33;}
        .error { color: red; }
    </style>
</head>
<body>
<form method="POST">
    <h2>Admin Login</h2>
    {% if error %}
    <p class="error">{{ error }}</p>
    {% endif %}
    <input type="text" name="username" placeholder="Brugernavn" required autofocus />
    <input type="password" name="password" placeholder="Adgangskode" required />
    <button type="submit">Log ind</button>
</form>
</body>
</html>
'''

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

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        if (request.form['username'] == ADMIN_USERNAME and
            request.form['password'] == ADMIN_PASSWORD):
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            error = "Forkert brugernavn eller adgangskode"
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash("Du er nu logget ud.")
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin():
    db = get_db()
    cursor = db.cursor()

    # Hent brugere + antal aktive udlån pr bruger
    cursor.execute('''
        SELECT b.kode, b.navn, 
        COALESCE((SELECT COUNT(*) FROM udlaan u WHERE u.bruger_kode=b.kode AND u.afleveret_dato IS NULL), 0) AS udlaan_antal
        FROM brugere b ORDER BY b.navn
    ''')
    brugere = cursor.fetchall()

    # Hent bøger + antal aktive udlån pr bog
    cursor.execute('''
        SELECT b.kode, b.titel,
        COALESCE((SELECT COUNT(*) FROM udlaan u WHERE u.bog_kode=b.kode AND u.afleveret_dato IS NULL), 0) AS udlaan_antal
        FROM boeger b ORDER BY b.titel
    ''')
    boeger = cursor.fetchall()

    # Udlåns-historik med filter (søg efter bruger, bog eller dato)
    filter_val = request.args.get('filter', '').strip()
    query = '''
        SELECT br.navn AS bruger, bo.titel AS bog, u.udlaan_dato, u.afleveret_dato
        FROM udlaan u
        LEFT JOIN brugere br ON u.bruger_kode = br.kode
        LEFT JOIN boeger bo ON u.bog_kode = bo.kode
    '''
    params = ()
    if filter_val:
        query += '''
            WHERE br.navn LIKE ? OR bo.titel LIKE ? OR u.udlaan_dato LIKE ? OR u.afleveret_dato LIKE ?
        '''
        like_val = f'%{filter_val}%'
        params = (like_val, like_val, like_val, like_val)
    query += ' ORDER BY u.udlaan_dato DESC LIMIT 100'
    cursor.execute(query, params)
    historik = cursor.fetchall()

    return render_template_string(HTML_TEMPLATE, brugere=brugere, boeger=boeger, historik=historik, request=request)

# --- Bruger funktioner ---

@app.route('/admin/add_bruger', methods=['POST'])
@admin_required
def add_bruger():
    kode = request.form['kode'].strip()
    navn = request.form['navn'].strip()
    if not kode or not navn:
        flash("Kode og navn er påkrævet")
        return redirect(url_for('admin'))
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO brugere (kode, navn) VALUES (?, ?)", (kode, navn))
        db.commit()
        flash(f"Bruger '{navn}' tilføjet")
    except sqlite3.IntegrityError:
        flash(f"Bruger med kode '{kode}' findes allerede")
    return redirect(url_for('admin'))

@app.route('/admin/edit_bruger', methods=['POST'])
@admin_required
def edit_bruger():
    kode = request.form['kode'].strip()
    navn = request.form['navn'].strip()
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE brugere SET navn=? WHERE kode=?", (navn, kode))
    db.commit()
    flash(f"Bruger '{kode}' opdateret")
    return redirect(url_for('admin'))

@app.route('/admin/delete_bruger')
@admin_required
def delete_bruger():
    kode = request.args.get('kode')
    if not kode:
        flash("Manglende bruger kode")
        return redirect(url_for('admin'))
    db = get_db()
    cursor = db.cursor()
    # Før slet tjek om brugeren har aktive udlån
    cursor.execute("SELECT COUNT(*) FROM udlaan WHERE bruger_kode=? AND afleveret_dato IS NULL", (kode,))
    active = cursor.fetchone()[0]
    if active > 0:
        flash("Kan ikke slette bruger med aktive udlån")
        return redirect(url_for('admin'))
    cursor.execute("DELETE FROM brugere WHERE kode=?", (kode,))
    db.commit()
    flash(f"Bruger '{kode}' slettet")
    return redirect(url_for('admin'))

@app.route('/admin/upload_brugere', methods=['POST'])
@admin_required
def upload_brugere():
    if 'file' not in request.files:
        flash("Ingen fil valgt")
        return redirect(url_for('admin'))
    file = request.files['file']
    if file.filename == '':
        flash("Ingen fil valgt")
        return redirect(url_for('admin'))
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    reader = csv.reader(stream)
    db = get_db()
    cursor = db.cursor()
    count = 0
    for row in reader:
        if len(row) >= 2:
            kode, navn = row[0].strip(), row[1].strip()
            if kode and navn:
                try:
                    cursor.execute("INSERT INTO brugere (kode, navn) VALUES (?, ?)", (kode, navn))
                    count += 1
                except sqlite3.IntegrityError:
                    pass
    db.commit()
    flash(f"{count} brugere importeret")
    return redirect(url_for('admin'))

# --- Bog funktioner ---

@app.route('/admin/add_bog', methods=['POST'])
@admin_required
def add_bog():
    kode = request.form['kode'].strip()
    titel = request.form['titel'].strip()
    if not kode or not titel:
        flash("Kode og titel er påkrævet")
        return redirect(url_for('admin'))
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO boeger (kode, titel) VALUES (?, ?)", (kode, titel))
        db.commit()
        flash(f"Bog '{titel}' tilføjet")
    except sqlite3.IntegrityError:
        flash(f"Bog med kode '{kode}' findes allerede")
    return redirect(url_for('admin'))

@app.route('/admin/edit_bog', methods=['POST'])
@admin_required
def edit_bog():
    kode = request.form['kode'].strip()
    titel = request.form['titel'].strip()
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE boeger SET titel=? WHERE kode=?", (titel, kode))
    db.commit()
    flash(f"Bog '{kode}' opdateret")
    return redirect(url_for('admin'))

@app.route('/admin/delete_bog')
@admin_required
def delete_bog():
    kode = request.args.get('kode')
    if not kode:
        flash("Manglende bog kode")
        return redirect(url_for('admin'))
    db = get_db()
    cursor = db.cursor()
    # Tjek om bogen er udlånt
    cursor.execute("SELECT COUNT(*) FROM udlaan WHERE bog_kode=? AND afleveret_dato IS NULL", (kode,))
    active = cursor.fetchone()[0]
    if active > 0:
        flash("Kan ikke slette bog med aktive udlån")
        return redirect(url_for('admin'))
    cursor.execute("DELETE FROM boeger WHERE kode=?", (kode,))
    db.commit()
    flash(f"Bog '{kode}' slettet")
    return redirect(url_for('admin'))

@app.route('/admin/upload_boeger', methods=['POST'])
@admin_required
def upload_boeger():
    if 'file' not in request.files:
        flash("Ingen fil valgt")
        return redirect(url_for('admin'))
    file = request.files['file']
    if file.filename == '':
        flash("Ingen fil valgt")
        return redirect(url_for('admin'))
    stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
    reader = csv.reader(stream)
    db = get_db()
    cursor = db.cursor()
    count = 0
    for row in reader:
        if len(row) >= 2:
            kode, titel = row[0].strip(), row[1].strip()
            if kode and titel:
                try:
                    cursor.execute("INSERT INTO boeger (kode, titel) VALUES (?, ?)", (kode, titel))
                    count += 1
                except sqlite3.IntegrityError:
                    pass
    db.commit()
    flash(f"{count} bøger importeret")
    return redirect(url_for('admin'))

# --- Main app starter her ---

if __name__ == "__main__":
    app.run(debug=True, port=5000)
