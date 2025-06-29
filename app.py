import csv
import datetime
import os
from flask import Flask, request, render_template_string, redirect, url_for, flash, g, session
from functools import wraps

app = Flask(__name__)
app.secret_key = 'hemmelig_nogler'

BRUGERE_CSV = 'brugere.csv'
BOEGER_CSV = 'boeger.csv'
UDLAAN_CSV = 'udlaan.csv'

os.makedirs('data', exist_ok=True)

# Hjælpefunktioner til CSV

def read_csv(filename):
    try:
        with open(filename, newline='', encoding='utf-8') as f:
            return list(csv.DictReader(f))
    except FileNotFoundError:
        return []

def write_csv(filename, fieldnames, rows):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def append_csv(filename, fieldnames, row):
    exists = os.path.exists(filename)
    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow(row)

def find_in_csv(filename, field, value):
    return next((row for row in read_csv(filename) if row[field] == value), None)

def bog_udlaant(bog_kode):
    for row in read_csv(UDLAAN_CSV):
        if row['bog_kode'] == bog_kode and not row['afleveret_dato']:
            return True
    return False

# Decorator

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Du skal være logget ind som admin")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template_string('''
    <h2>Velkommen til Biblioteket</h2>
    <form method="POST" action="/udlaan">
        <h3>Udlån</h3>
        <input name="bruger" placeholder="Brugerkode" required><br>
        <input name="bog" placeholder="Bogkode" required><br>
        <input type="submit" value="Udlån">
    </form>
    <form method="POST" action="/aflevering">
        <h3>Aflevering</h3>
        <input name="bog" placeholder="Bogkode" required><br>
        <input type="submit" value="Aflever">
    </form>
    <a href="/udlaan-oversigt">Se dine aktuelle udlån</a><br>
    <a href="/admin">Adminside</a>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}<p>{{ message }}</p>{% endfor %}
      {% endif %}
    {% endwith %}
    ''')

@app.route('/udlaan', methods=['POST'])
def udlaan():
    bruger = request.form['bruger']
    bog = request.form['bog']

    if not find_in_csv(BRUGERE_CSV, 'kode', bruger):
        flash("Bruger ikke fundet")
    elif not find_in_csv(BOEGER_CSV, 'kode', bog):
        flash("Bog ikke fundet")
    elif bog_udlaant(bog):
        flash("Bog er allerede udlånt")
    else:
        append_csv(UDLAAN_CSV, ['bruger_kode', 'bog_kode', 'udlaan_dato', 'afleveret_dato'], {
            'bruger_kode': bruger,
            'bog_kode': bog,
            'udlaan_dato': datetime.datetime.now().isoformat(),
            'afleveret_dato': ''
        })
        flash("Udlån registreret")
    return redirect(url_for('index'))

@app.route('/aflevering', methods=['POST'])
def aflevering():
    bog = request.form['bog']
    rows = read_csv(UDLAAN_CSV)
    updated = False
    for row in rows:
        if row['bog_kode'] == bog and not row['afleveret_dato']:
            row['afleveret_dato'] = datetime.datetime.now().isoformat()
            updated = True
            break
    if updated:
        write_csv(UDLAAN_CSV, ['bruger_kode', 'bog_kode', 'udlaan_dato', 'afleveret_dato'], rows)
        flash("Aflevering registreret")
    else:
        flash("Bog er ikke udlånt")
    return redirect(url_for('index'))

@app.route('/udlaan-oversigt', methods=['GET', 'POST'])
def udlaan_oversigt():
    if request.method == 'POST':
        bruger = request.form['bruger']
        udlaan = [r for r in read_csv(UDLAAN_CSV) if r['bruger_kode'] == bruger and not r['afleveret_dato']]
        boeger = {r['kode']: r['titel'] for r in read_csv(BOEGER_CSV)}

        html = '<h2>Dine udlån</h2><ul>'
        for r in udlaan:
            dato = datetime.datetime.fromisoformat(r['udlaan_dato'])
            overskredet = (datetime.datetime.now() - dato).days > 30
            titel = boeger.get(r['bog_kode'], r['bog_kode'])
            html += f'<li>{titel} udlånt {dato.strftime("%Y-%m-%d")} {"(for sent)" if overskredet else ""}</li>'
        html += '</ul><a href="/">Tilbage</a>'
        return html
    return render_template_string('''
        <form method="post">
            <input name="bruger" placeholder="Brugerkode" required><br>
            <input type="submit" value="Se udlån">
        </form>
        <a href="/">Tilbage</a>
    ''')

@app.route('/admin')
@admin_required
def admin():
    return render_template_string('''
        <h2>Admin</h2>
        <ul>
            <li><a href="/admin/oversigt">Brugere og bøger</a></li>
            <li><a href="/admin/opret-bruger">Opret bruger</a></li>
            <li><a href="/admin/opret-bog">Opret bog</a></li>
            <li><a href="/admin/logout">Log ud</a></li>
        </ul>
    ''')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        flash("Forkert login")
    return render_template_string('''
        <form method="post">
            <input name="username" placeholder="Brugernavn" required><br>
            <input name="password" type="password" placeholder="Kodeord" required><br>
            <input type="submit" value="Log ind">
        </form>
        <a href="/">Tilbage</a>
    ''')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash("Logget ud")
    return redirect(url_for('index'))

@app.route('/admin/opret-bruger', methods=['GET', 'POST'])
@admin_required
def opret_bruger():
    if request.method == 'POST':
        kode, navn = request.form['kode'], request.form['navn']
        if find_in_csv(BRUGERE_CSV, 'kode', kode):
            flash("Brugeren findes allerede")
        else:
            append_csv(BRUGERE_CSV, ['kode', 'navn'], {'kode': kode, 'navn': navn})
            flash("Bruger oprettet")
        return redirect(url_for('admin'))
    return render_template_string('''
        <form method="post">
            <input name="kode" placeholder="Stregkode" required><br>
            <input name="navn" placeholder="Navn" required><br>
            <input type="submit" value="Opret">
        </form>
        <a href="/admin">Tilbage</a>
    ''')

@app.route('/admin/opret-bog', methods=['GET', 'POST'])
@admin_required
def opret_bog():
    if request.method == 'POST':
        kode, titel = request.form['kode'], request.form['titel']
        if find_in_csv(BOEGER_CSV, 'kode', kode):
            flash("Bogen findes allerede")
        else:
            append_csv(BOEGER_CSV, ['kode', 'titel'], {'kode': kode, 'titel': titel})
            flash("Bog oprettet")
        return redirect(url_for('admin'))
    return render_template_string('''
        <form method="post">
            <input name="kode" placeholder="Stregkode" required><br>
            <input name="titel" placeholder="Titel" required><br>
            <input type="submit" value="Opret">
        </form>
        <a href="/admin">Tilbage</a>
    ''')

@app.route('/admin/oversigt')
@admin_required
def admin_oversigt():
    brugere = read_csv(BRUGERE_CSV)
    boeger = read_csv(BOEGER_CSV)
    return render_template_string('''
        <h2>Brugere</h2>
        <ul>{% for b in brugere %}<li>{{ b['navn'] }} — {{ b['kode'] }}</li>{% endfor %}</ul>
        <h2>Bøger</h2>
        <ul>{% for b in boeger %}<li>{{ b['titel'] }} — {{ b['kode'] }}</li>{% endfor %}</ul>
        <a href="/admin">Tilbage</a>
    ''', brugere=brugere, boeger=boeger)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
