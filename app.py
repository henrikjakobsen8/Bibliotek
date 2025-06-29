from flask import Flask, request, render_template_string, redirect, url_for, flash, session, g
from functools import wraps
import os
import datetime
import data_access as db

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'skift_denne_til_en_stærk_nøgle')

# HTML Template med designinspiration fra Vejlefjordskolen
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="da">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Bibliotek - Udlånssystem</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background-color: #f0f4f8; margin: 0; padding: 0; }
        header { background-color: #2a5d3b; padding: 20px; color: white; text-align: center; }
        header h1 { margin: 0; font-size: 1.8em; }
        main { padding: 20px; max-width: 600px; margin: auto; }
        form { background-color: white; padding: 20px; margin-bottom: 30px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        form h2 { margin-top: 0; font-size: 1.4em; color: #2a5d3b; }
        label { display: block; margin-top: 10px; font-weight: bold; }
        input[type="text"], select { width: 100%; padding: 10px; margin-top: 5px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 4px; }
        input[type="submit"] { background-color: #2a5d3b; color: white; border: none; padding: 10px 15px; border-radius: 4px; cursor: pointer; }
        input[type="submit"]:hover { background-color: #244e33; }
        .message { padding: 12px; background-color: #e3f7e0; border-left: 5px solid #2a5d3b; margin-bottom: 20px; border-radius: 4px; }
        a { color: #2a5d3b; text-decoration: none; display: inline-block; margin-top: 8px; }
        a:hover { text-decoration: underline; }
        .nav-links { margin-top: 20px; text-align: center; }
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
            <label for="bruger">Bruger stregkode:</label>
            <input type="text" name="bruger" id="bruger" required>
            <label for="bog">Bog stregkode:</label>
            <input type="text" name="bog" id="bog" required>
            <input type="submit" value="Udlån">
        </form>

        <form method="POST" action="/aflevering">
            <h2>Aflever bog</h2>
            <label for="bog_afl">Bog stregkode:</label>
            <input type="text" name="bog" id="bog_afl" required>
            <input type="submit" value="Aflever">
        </form>

        <div class="nav-links">
            <a href="/udlaan-oversigt">📚 Se aktuelle udlån</a><br>
            <a href="/admin">🔐 Gå til Adminside</a>
        </div>
    </main>
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
    if request.method == 'POST':
        bruger = request.form['bruger']
        udlaante = db.hent_udlaan_for_bruger(bruger)
        html = '<html>... liste med farvelægning som før ...</html>'
        return html
    return render_template_string('''<form>...</form>''')

@app.route('/admin')
@admin_required
def admin():
    return render_template_string('''<h2>Velkommen til Adminsiden</h2>...''')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username']=='admin' and request.form['password']=='admin':
            session['admin_logged_in']=True
            flash("Du er nu logget ind som admin")
            return redirect(url_for('admin'))
        else:
            flash("Forkert brugernavn eller kodeord")
            return redirect(url_for('admin_login'))
    return render_template_string('''<form>...</form>''')

@app.route('/admin/opret-bruger', methods=['GET','POST'])
@admin_required
def opret_bruger():
    if request.method == 'POST':
        if db.opret_bruger(request.form['kode'], request.form['navn']):
            flash("Bruger oprettet")
        else:
            flash("Bruger med den kode findes allerede")
        return redirect(url_for('admin'))
    return render_template_string('''<form>...</form>''')

@app.route('/admin/opret-bog', methods=['GET','POST'])
@admin_required
def opret_bog():
    if request.method == 'POST':
        if db.opret_bog(request.form['kode'], request.form['titel']):
            flash("Bog oprettet")
        else:
            flash("Bog med den kode findes allerede")
        return redirect(url_for('admin'))
    return render_template_string('''<form>...</form>''')

@app.route('/admin/oversigt')
@admin_required
def admin_oversigt():
    brugere = db.hent_alle_brugere()
    boeger = db.hent_alle_boeger()
    return render_template_string('''<html>...''', brugere=brugere, boeger=boeger)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash("Du er nu logget ud")
    return redirect(url_for('index'))

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
