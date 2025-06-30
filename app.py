from flask import Flask, render_template, render_template_string, request, redirect, url_for, flash, session
from functools import wraps
from flask import send_file
import os
import datetime
import data_access as db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'skift_denne_til_en_stærk_nøgle')

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Bibliotek System</title>
    <style>
        :root {
            --primær-bg: #f8f9f4;
            --accent: #2a5d3b;
            --text-color: #333;
        }
        body {
            background: var(--primær-bg);
            color: var(--text-color);
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 0;
        }
        header {
            background: var(--accent);
            color: white;
            padding: 1em;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        nav a {
            color: white;
            margin: 0 1em;
            text-decoration: none;
            font-weight: bold;
        }
        .hero {
            padding: 2em;
            background: #e8ede5;
            text-align: center;
        }
        .container {
            max-width: 800px;
            margin: auto;
            padding: 2em;
        }
        form {
            background: white;
            padding: 1em;
            margin-bottom: 1em;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.05);
        }
        input, button {
            padding: 0.5em;
            margin: 0.5em 0;
            width: 100%;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        button {
            background: var(--accent);
            color: white;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover {
            background: #244a31;
        }
        ul {
            list-style: none;
            padding: 0;
        }
        li {
            background: #fff;
            margin-bottom: 0.5em;
            padding: 0.5em;
            border-left: 4px solid var(--accent);
        }
        .message {
            background: #fff3cd;
            padding: 1em;
            margin-bottom: 1em;
            border-left: 4px solid #ffeeba;
        }
    </style>
</head>
<body>
    <header>
        <h1>📚 Bibliotek</h1>
        <nav>
            <a href="/udlaan-oversigt">📚 Se aktuelle udlån</a><br>
            <a href="/admin">🔐 Gå til Adminside</a>
        </nav>
    </header>
    <section class="hero">
        <h2>Velkommen til Bibliotekssystemet</h2>
        <p>Scan, lån og aflever – nemt og hurtigt.</p>
    </section>
    <div class="container">
        <form method="POST" action="/udlaan">
            <h3>📤 Udlån</h3>
            Scan bruger: <input name="bruger" required><br>
            Scan bog: <input name="bog" required><br>
            <button type="submit">Udlån</button>
        </form>

        <form method="POST" action="/aflevering">
            <h3>📥 Aflevering</h3>
            Scan bog: <input name="bog" required><br>
            <button type="submit">Aflever</button>
        </form>

        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="message">
              {% for message in messages %}
                <p>{{ message }}</p>
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
    </div>
</body>
</html>
'''
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Du skal være logget ind som admin")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/udlaan', methods=['POST'])
def udlaan():
    bruger, bog = request.form['bruger'], request.form['bog']
    if not db.find_bruger(bruger):
        flash("Bruger ikke fundet"); return redirect(url_for('index'))
    if not db.find_bog(bog):
        flash("Bog ikke fundet"); return redirect(url_for('index'))
    if db.bog_udlaant(bog):
        flash("Bog er allerede udlånt"); return redirect(url_for('index'))
    db.registrer_udlaan(bruger, bog)
    flash("Udlån registreret"); return redirect(url_for('index'))

@app.route('/aflevering', methods=['POST'])
def aflevering():
    bog = request.form['bog']
    if db.registrer_aflevering(bog):
        flash("Aflevering registreret")
    else:
        flash("Bog er ikke udlånt")
    return redirect(url_for('index'))

@app.route('/udlaan-oversigt', methods=['GET', 'POST'])
def udlaan_oversigt():
    bruger = None
    udlaante = []
    fejl = None

    if request.method == 'POST':
        bruger = request.form['bruger'].strip()
        if not db.find_bruger(bruger):
            fejl = "Brugeren findes ikke."
        else:
            udlaante_rå = db.hent_udlaan_for_bruger(bruger)
            boeger = {b['kode']: b['titel'] for b in db.hent_alle_boeger()}
            udlaante = [{
                'bog': u['bog'],
                'titel': boeger.get(u['bog'], 'Ukendt titel'),
                'dato': u['dato']
            } for u in udlaante_rå]

    return render_template_string(HTML_TEMPLATE_OVERSIGT, bruger=bruger, udlaante=udlaante, fejl=fejl)
HTML_TEMPLATE_OVERSIGT = '''
<!DOCTYPE html>
<html>
<head>
    <title>Bibliotek Udlån Oversigt</title>
    <style>
        /* Samme CSS som din forside ... */
        {{ styles }}
    </style>
</head>
<body>
    <header>
        <h1>📚 Bibliotek</h1>
        <nav>
            <a href="/">🏠 Forside</a><br>
            <a href="/admin">🔐 Admin</a>
        </nav>
    </header>
    <section class="hero">
        <h2>Se aktuelle udlån</h2>
        <p>Indtast brugerkode for at se aktive udlån</p>
    </section>
    <div class="container">
        <form method="POST">
            Brugerkode: <input name="bruger" required><br>
            <button type="submit">Søg</button>
        </form>

        {% if bruger %}
            {% if fejl %}
                <div class="message">{{ fejl }}</div>
            {% elif udlaante %}
                <h3>Aktive udlån for: {{ bruger }}</h3>
                <ul>
                {% for u in udlaante %}
                    <li>{{ u.titel }} ({{ u.bog }}) – Udlånt: {{ u.dato[:10] }}</li>
                {% endfor %}
                </ul>
            {% else %}
                <div class="message">Ingen aktive udlån for {{ bruger }}.</div>
            {% endif %}
        {% endif %}
    </div>
</body>
</html>
'''.replace("{{ styles }}", HTML_TEMPLATE.split("<style>")[1].split("</style>")[0])

@app.route('/admin')
@admin_required
def admin():
    return render_template_string('''
        <!DOCTYPE html>
        <html lang="da">
        <head>
            <meta charset="UTF-8">
            <title>Adminpanel</title>
            <style>
                body { font-family: sans-serif; background-color: #f0f4f8; padding: 40px; }
                .container { max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                h2 { color: #2a5d3b; }
                a.button {
                    display: block;
                    background-color: #2a5d3b;
                    color: white;
                    padding: 12px;
                    margin: 10px 0;
                    text-align: center;
                    text-decoration: none;
                    border-radius: 6px;
                }
                a.button:hover {
                    background-color: #244e33;
                }
                .message {
                    padding: 10px;
                    background-color: #e3f7e0;
                    border-left: 5px solid #2a5d3b;
                    margin-bottom: 20px;
                    border-radius: 4px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🔐 Adminpanel</h2>

                {% with messages = get_flashed_messages() %}
                  {% if messages %}
                    {% for message in messages %}
                      <div class="message">{{ message }}</div>
                    {% endfor %}
                  {% endif %}
                {% endwith %}

                <a href="/admin/opret-bruger" class="button">➕ Opret ny bruger</a>
                <a href="/admin/opret-bog" class="button">📚 Opret ny bog</a>
                <a href="/admin/oversigt" class="button">📊 Se oversigt over brugere og bøger</a>
                <a href="/admin/download-brugere" class="button">⬇️ Download brugere</a>
                <a href="/admin/download-boeger" class="button">⬇️ Download bøger</a>
                <a href="/admin/download-udlaan" class="button">⬇️ Download udlån</a>
                <a href="/admin/logout" class="button">🚪 Log ud</a>
            </div>
        </body>
        </html>
    ''')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['admin_logged_in'] = True
            flash("Du er nu logget ind som admin")
            return redirect(url_for('admin'))
        else:
            flash("Forkert brugernavn eller kodeord")
            return redirect(url_for('admin_login'))

    return render_template_string('''
        <!DOCTYPE html>
        <html lang="da">
        <head>
            <meta charset="UTF-8">
            <title>Admin Login</title>
            <style>
                body { font-family: sans-serif; background-color: #f0f4f8; padding: 40px; }
                form { background-color: white; padding: 20px; max-width: 400px; margin: auto; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                h2 { color: #2a5d3b; }
                label, input { display: block; width: 100%; margin-bottom: 10px; }
                input[type="submit"] { background-color: #2a5d3b; color: white; border: none; padding: 10px; border-radius: 4px; cursor: pointer; }
                input[type="submit"]:hover { background-color: #244e33; }
                .message { padding: 10px; background-color: #e3f7e0; border-left: 5px solid #2a5d3b; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                {% for message in messages %}
                  <div class="message">{{ message }}</div>
                {% endfor %}
              {% endif %}
            {% endwith %}

            <form method="POST">
                <h2>Admin Login</h2>
                <label for="username">Brugernavn:</label>
                <input type="text" name="username" id="username" required>
                <label for="password">Kodeord:</label>
                <input type="password" name="password" id="password" required>
                <input type="submit" value="Login">
            </form>
        </body>
        </html>
    ''')


@app.route('/admin/opret-bruger', methods=['GET','POST'])
@admin_required
def opret_bruger():
    if request.method == 'POST':
        if db.opret_bruger(request.form['kode'], request.form['navn']):
            flash("Bruger oprettet")
        else:
            flash("Bruger med den kode findes allerede")
        return redirect(url_for('admin'))

    return render_template_string('''
        <html lang="da">
        <head>
            <meta charset="UTF-8">
            <title>Opret Bruger</title>
            <style>
                body { font-family: sans-serif; background-color: #f0f4f8; padding: 40px; }
                form { background: white; padding: 20px; max-width: 400px; margin: auto; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                label, input { display: block; width: 100%; margin-bottom: 10px; }
                input[type="submit"] { background-color: #2a5d3b; color: white; padding: 10px; border: none; border-radius: 4px; cursor: pointer; }
                input[type="submit"]:hover { background-color: #244e33; }
            </style>
        </head>
        <body>
            <form method="POST">
                <h2>➕ Opret ny bruger</h2>
                <label for="kode">Brugerens stregkode:</label>
                <input type="text" name="kode" id="kode" required>
                <label for="navn">Navn:</label>
                <input type="text" name="navn" id="navn" required>
                <input type="submit" value="Opret">
            </form>
        </body>
        </html>
    ''')

@app.route('/admin/opret-bog', methods=['GET','POST'])
@admin_required
def opret_bog():
    if request.method == 'POST':
        if db.opret_bog(request.form['kode'], request.form['titel']):
            flash("Bog oprettet")
        else:
            flash("Bog med den kode findes allerede")
        return redirect(url_for('admin'))

    return render_template_string('''
        <html lang="da">
        <head>
            <meta charset="UTF-8">
            <title>Opret Bog</title>
            <style>
                body { font-family: sans-serif; background-color: #f0f4f8; padding: 40px; }
                form { background: white; padding: 20px; max-width: 400px; margin: auto; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
                label, input { display: block; width: 100%; margin-bottom: 10px; }
                input[type="submit"] { background-color: #2a5d3b; color: white; padding: 10px; border: none; border-radius: 4px; cursor: pointer; }
                input[type="submit"]:hover { background-color: #244e33; }
            </style>
        </head>
        <body>
            <form method="POST">
                <h2>📚 Opret ny bog</h2>
                <label for="kode">Bog stregkode:</label>
                <input type="text" name="kode" id="kode" required>
                <label for="titel">Titel:</label>
                <input type="text" name="titel" id="titel" required>
                <input type="submit" value="Opret">
            </form>
        </body>
        </html>
    ''')

@app.route('/admin/oversigt')
@admin_required
def admin_oversigt():
    brugere = db.hent_alle_brugere()
    boeger = {bog['kode'].strip(): bog['titel'] for bog in db.hent_alle_boeger()}
    udlaan = db.hent_alle_udlaan()  # Antager den returnerer liste med dicts
    
    # Berig udlån med bogtitel
    for u in udlaan:
        u['titel'] = boeger.get(u['bog'].strip(), 'Ukendt titel')

    return render_template_string('''
<!DOCTYPE html>
<html lang="da">
<head>
    <meta charset="UTF-8">
    <title>Adminoversigt</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background-color: #f9f9f9; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 40px; cursor: default; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #2a5d3b; color: white; cursor: pointer; }
        h2 { color: #2a5d3b; }
        a { display: inline-block; margin-bottom: 20px; color: #2a5d3b; text-decoration: none; }
        input[type="text"] { width: 100%; padding: 8px; margin-bottom: 10px; border: 1px solid #ccc; border-radius: 4px; }
        label { display: block; margin-bottom: 10px; }
    </style>
    <script>
        function filterTable(inputId, tableId, showOnlyActive = false) {
            const input = document.getElementById(inputId).value.toLowerCase();
            const rows = document.querySelectorAll(`#${tableId} tbody tr`);
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                const isActive = row.dataset.afleveret === "nej";
                const match = text.includes(input);
                row.style.display = (match && (!showOnlyActive || isActive)) ? '' : 'none';
            });
        }

        function toggleActiveOnly() {
            filterTable('udlaanSearch', 'udlaantabel', document.getElementById('activeOnly').checked);
        }

        function sortTable(tableId, colIndex) {
            const table = document.getElementById(tableId);
            const tbody = table.tBodies[0];
            const rows = Array.from(tbody.rows);
            const ascending = table.dataset.sortAsc === "true" ? false : true;
            rows.sort((a, b) => {
                const valA = a.cells[colIndex].innerText.toLowerCase();
                const valB = b.cells[colIndex].innerText.toLowerCase();
                return ascending ? valA.localeCompare(valB) : valB.localeCompare(valA);
            });
            rows.forEach(row => tbody.appendChild(row));
            table.dataset.sortAsc = ascending;
        }
    </script>
</head>
<body>
    <h1>📊 Adminoversigt</h1>
    <a href="/admin">⬅️ Tilbage til adminside</a>

    <h2>Brugere</h2>
    <input type="text" id="brugerSearch" placeholder="🔍 Søg brugere..." onkeyup="filterTable('brugerSearch', 'brugertabel')">
    <table id="brugertabel" data-sort-asc="true">
        <thead>
            <tr>
                <th onclick="sortTable('brugertabel', 0)">Stregkode</th>
                <th onclick="sortTable('brugertabel', 1)">Navn</th>
            </tr>
        </thead>
        <tbody>
        {% for b in brugere %}
            <tr><td>{{ b['kode'] }}</td><td>{{ b['navn'] }}</td></tr>
        {% endfor %}
        </tbody>
    </table>

    <h2>Bøger</h2>
    <input type="text" id="bogSearch" placeholder="🔍 Søg bøger..." onkeyup="filterTable('bogSearch', 'bogtabel')">
    <table id="bogtabel" data-sort-asc="true">
        <thead>
            <tr>
                <th onclick="sortTable('bogtabel', 0)">Stregkode</th>
                <th onclick="sortTable('bogtabel', 1)">Titel</th>
            </tr>
        </thead>
        <tbody>
        {% for k, v in boeger.items() %}
            <tr><td>{{ k }}</td><td>{{ v }}</td></tr>
        {% endfor %}
        </tbody>
    </table>

    <h2>Udlån</h2>
    <input type="text" id="udlaanSearch" placeholder="🔍 Søg udlån (bruger/bog/titel)..." onkeyup="toggleActiveOnly()">
    <label><input type="checkbox" id="activeOnly" onchange="toggleActiveOnly()"> Vis kun aktive udlån</label>
    <table id="udlaantabel" data-sort-asc="true">

        <thead>
            <tr>
                <th onclick="sortTable('udlaantabel', 0)">Bruger</th>
                <th onclick="sortTable('udlaantabel', 1)">Bog</th>
                <th onclick="sortTable('udlaantabel', 2)">Titel</th>
                <th onclick="sortTable('udlaantabel', 3)">Udlånsdato</th>
                <th onclick="sortTable('udlaantabel', 4)">Afleveret</th>
            </tr>
        </thead>
        <tbody>
        {% for u in udlaan %}
            <tr data-afleveret="{{ 'nej' if not u['afleveret'] else 'ja' }}">
                <td>{{ u['bruger'] }}</td>
                <td>{{ u['bog'] }}</td>
                <td>{{ u['titel'] }}</td>
                <td>{{ u['dato'] }}</td>
                <td>{{ u['afleveret'] if u['afleveret'] else 'Nej' }}</td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
</body>
</html>
''', brugere=brugere, boeger=boeger, udlaan=udlaan)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash("Du er nu logget ud")
    return redirect(url_for('index'))

@app.route('/admin/download-udlaan')
@admin_required
def download_udlaan():
    return send_file('data/udlaan.csv', as_attachment=True)

@app.route('/admin/slet-bruger/<kode>', methods=['POST'])
@admin_required
def slet_bruger(kode):
    db.slet_bruger(kode)
    flash(f"Bruger '{kode}' er slettet.")
    return redirect(url_for('admin_oversigt'))

@app.route('/admin/slet-bog/<kode>', methods=['POST'])
@admin_required
def slet_bog(kode):
    if db.slet_bog(kode):
        flash(f"Bog '{kode}' er slettet.")
    else:
        flash(f"Kan ikke slette bog '{kode}': Bogen er stadig udlånt.", 'error')
    return redirect(url_for('admin_oversigt'))

@app.route('/admin/download-brugere')
@admin_required
def download_brugere():
    return send_file('data/brugere.csv', as_attachment=True)

@app.route('/admin/download-boeger')
@admin_required
def download_boeger():
    return send_file('data/boeger.csv', as_attachment=True)


if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
