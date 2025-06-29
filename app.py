# Flask app med CSV i stedet for SQLite
import csv
import os
from flask import Flask, request, render_template_string, redirect, url_for, flash, session
from functools import wraps
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'hemmelig_nogler'

DATA_DIR = 'data'
BRUGERE_FIL = os.path.join(DATA_DIR, 'brugere.csv')
BOEGER_FIL = os.path.join(DATA_DIR, 'boeger.csv')
UDLAAN_FIL = os.path.join(DATA_DIR, 'udlaan.csv')

os.makedirs(DATA_DIR, exist_ok=True)

# Initialiser filer hvis de ikke findes
for fil, headers in [
    (BRUGERE_FIL, ['kode', 'navn']),
    (BOEGER_FIL, ['kode', 'titel']),
    (UDLAAN_FIL, ['id', 'bruger_kode', 'bog_kode', 'udlaan_dato', 'afleveret_dato'])
]:
    if not os.path.exists(fil):
        with open(fil, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)

# Hjælpere

def hent_csv(fil):
    with open(fil, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def skriv_csv(fil, rows, fieldnames):
    with open(fil, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def append_csv(fil, row, fieldnames):
    with open(fil, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow(row)

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
    return render_template_string("""
    <h1>Bibliotek</h1>
    <form method="POST" action="/udlaan">
        <input name="bruger" placeholder="Bruger stregkode"><br>
        <input name="bog" placeholder="Bog stregkode"><br>
        <input type="submit" value="Udlån">
    </form>

    <form method="POST" action="/aflevering">
        <input name="bog" placeholder="Bog stregkode"><br>
        <input type="submit" value="Aflever">
    </form>

    <form method="GET" action="/udlaan-oversigt">
        <input name="bruger" placeholder="Bruger stregkode"><br>
        <input type="submit" value="Se udlån">
    </form>
    <a href="/admin">Admin</a>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        {% for message in messages %}<p>{{ message }}</p>{% endfor %}
      {% endif %}
    {% endwith %}
    """)

@app.route('/udlaan', methods=['POST'])
def udlaan():
    bruger = request.form['bruger']
    bog = request.form['bog']

    brugere = hent_csv(BRUGERE_FIL)
    boeger = hent_csv(BOEGER_FIL)
    udlaan = hent_csv(UDLAAN_FIL)

    if not any(b['kode'] == bruger for b in brugere):
        flash("Bruger findes ikke")
        return redirect(url_for('index'))
    if not any(b['kode'] == bog for b in boeger):
        flash("Bog findes ikke")
        return redirect(url_for('index'))
    if any(u['bog_kode'] == bog and u['afleveret_dato'] == '' for u in udlaan):
        flash("Bog er allerede udlånt")
        return redirect(url_for('index'))

    ny_id = str(max([int(u['id']) for u in udlaan] + [0]) + 1)
    append_csv(UDLAAN_FIL, {
        'id': ny_id,
        'bruger_kode': bruger,
        'bog_kode': bog,
        'udlaan_dato': datetime.now().isoformat(),
        'afleveret_dato': ''
    }, ['id', 'bruger_kode', 'bog_kode', 'udlaan_dato', 'afleveret_dato'])
    flash("Udlån registreret")
    return redirect(url_for('index'))

@app.route('/aflevering', methods=['POST'])
def aflevering():
    bog = request.form['bog']
    udlaan = hent_csv(UDLAAN_FIL)
    opdateret = False
    for u in udlaan:
        if u['bog_kode'] == bog and u['afleveret_dato'] == '':
            u['afleveret_dato'] = datetime.now().isoformat()
            opdateret = True
    if opdateret:
        skriv_csv(UDLAAN_FIL, udlaan, ['id', 'bruger_kode', 'bog_kode', 'udlaan_dato', 'afleveret_dato'])
        flash("Aflevering registreret")
    else:
        flash("Bog er ikke udlånt")
    return redirect(url_for('index'))

@app.route('/udlaan-oversigt')
def udlaan_oversigt():
    bruger_kode = request.args.get('bruger')
    if not bruger_kode:
        return redirect(url_for('index'))
    udlaan = hent_csv(UDLAAN_FIL)
    boeger = {b['kode']: b['titel'] for b in hent_csv(BOEGER_FIL)}
    resultater = []
    nu = datetime.now()
    for u in udlaan:
        if u['bruger_kode'] == bruger_kode and u['afleveret_dato'] == '':
            dato = datetime.fromisoformat(u['udlaan_dato'])
            forfalden = dato + timedelta(days=30) < nu
            resultater.append((boeger.get(u['bog_kode'], u['bog_kode']), u['udlaan_dato'], forfalden))

    html = '<h2>Dine udlån</h2><ul>'
    for titel, dato, forfalden in resultater:
        html += f'<li>{titel} ({dato[:10]})' + (' - <b>Forfalden</b>' if forfalden else '') + '</li>'
    html += '</ul><a href="/">Tilbage</a>'
    return html

@app.route('/admin', methods=['GET'])
@admin_required
def admin():
    brugere = hent_csv(BRUGERE_FIL)
    boeger = hent_csv(BOEGER_FIL)
    html = """
    <h2>Adminside</h2>
    <form method='POST' action='/admin/opret-bruger'>
        <input name='kode' placeholder='Stregkode'><input name='navn' placeholder='Navn'>
        <input type='submit' value='Opret bruger'>
    </form>
    <form method='POST' action='/admin/opret-bog'>
        <input name='kode' placeholder='Bogkode'><input name='titel' placeholder='Titel'>
        <input type='submit' value='Opret bog'>
    </form>
    <h3>Brugere</h3><input onkeyup='filter("bruger")' id='filter-bruger'>
    <ul id='bruger'>"""
    for b in brugere:
        html += f"<li>{b['kode']} - {b['navn']}</li>"
    html += """</ul>
    <h3>Bøger</h3><input onkeyup='filter("bog")' id='filter-bog'>
    <ul id='bog'>"""
    for b in boeger:
        html += f"<li>{b['kode']} - {b['titel']}</li>"
    html += """</ul>
    <a href='/admin/logout'>Log ud</a>
    <script>
        function filter(id) {
            let input = document.getElementById('filter-' + id).value.toLowerCase();
            document.querySelectorAll('#' + id + ' li').forEach(li => {
                li.style.display = li.textContent.toLowerCase().includes(input) ? '' : 'none';
            });
        }
    </script>
    """
    return html

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'admin':
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Forkert login')
    return '''
        <h2>Login</h2>
        <form method="post">
            <input name="username"><input type="password" name="password">
            <input type="submit" value="Log ind">
        </form>
    '''

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash("Logget ud")
    return redirect(url_for('index'))

@app.route('/admin/opret-bruger', methods=['POST'])
@admin_required
def opret_bruger():
    append_csv(BRUGERE_FIL, {
        'kode': request.form['kode'],
        'navn': request.form['navn']
    }, ['kode', 'navn'])
    return redirect(url_for('admin'))

@app.route('/admin/opret-bog', methods=['POST'])
@admin_required
def opret_bog():
    append_csv(BOEGER_FIL, {
        'kode': request.form['kode'],
        'titel': request.form['titel']
    }, ['kode', 'titel'])
    return redirect(url_for('admin'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
