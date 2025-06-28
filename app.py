import csv
import datetime
import os
from flask import Flask, request, render_template_string, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'hemmelig_nogler'

BRUGERE_FIL = 'data/brugere.csv'
BOEGER_FIL = 'data/boeger.csv'
UDLAAN_FIL = 'data/udlaan.csv'

os.makedirs('data', exist_ok=True)

# HTML Template med designinspiration fra Vejlefjordskolen
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
            <a href="/">Start</a>
            <a href="/udlaan-oversigt">Udlånsliste</a>
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

def find_i_csv(fil, kode):
    if not os.path.exists(fil): return None
    with open(fil, newline='') as f:
        for row in csv.reader(f):
            if row and row[0] == kode:
                return row
    return None

def bog_udlaant(kode):
    if not os.path.exists(UDLAAN_FIL): return False
    with open(UDLAAN_FIL, newline='') as f:
        for row in csv.reader(f):
            if row[1] == kode and row[3] == '':
                return True
    return False

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/udlaan', methods=['POST'])
def udlaan():
    bruger = request.form['bruger']
    bog = request.form['bog']

    if not find_i_csv(BRUGERE_FIL, bruger):
        flash("Bruger ikke fundet")
        return redirect(url_for('index'))
    if not find_i_csv(BOEGER_FIL, bog):
        flash("Bog ikke fundet")
        return redirect(url_for('index'))
    if bog_udlaant(bog):
        flash("Bog er allerede udlånt")
        return redirect(url_for('index'))

    with open(UDLAAN_FIL, 'a', newline='') as f:
        csv.writer(f).writerow([bruger, bog, datetime.datetime.now().isoformat(), ''])
    flash("Udlån registreret")
    return redirect(url_for('index'))

@app.route('/aflevering', methods=['POST'])
def aflevering():
    bog = request.form['bog']
    rows = []
    found = False
    if os.path.exists(UDLAAN_FIL):
        with open(UDLAAN_FIL, newline='') as f:
            for row in csv.reader(f):
                if row[1] == bog and row[3] == '':
                    row[3] = datetime.datetime.now().isoformat()
                    found = True
                rows.append(row)
        if found:
            with open(UDLAAN_FIL, 'w', newline='') as f:
                csv.writer(f).writerows(rows)
            flash("Aflevering registreret")
        else:
            flash("Bog er ikke udlånt")
    else:
        flash("Ingen udlån registreret endnu")
    return redirect(url_for('index'))

@app.route('/udlaan-oversigt')
def udlaan_oversigt():
    udlaante = []
    if os.path.exists(UDLAAN_FIL):
        with open(UDLAAN_FIL, newline='') as f:
            for row in csv.reader(f):
                if row[3] == '':
                    bruger = find_i_csv(BRUGERE_FIL, row[0])
                    bog = find_i_csv(BOEGER_FIL, row[1])
                    udlaante.append({
                        'bruger': bruger[1] if bruger else row[0],
                        'bog': bog[1] if bog else row[1],
                        'dato': row[2][:10]
                    })
    html = '''<html><head><title>Udlånsliste</title><style>
        body { font-family: Segoe UI, sans-serif; background: #f8f9f4; color: #333; padding: 2em; }
        ul { list-style: none; padding: 0; }
        li { background: #fff; margin-bottom: 0.5em; padding: 0.5em; border-left: 4px solid #2a5d3b; }
        a { display: inline-block; margin-top: 1em; color: white; background: #2a5d3b; padding: 0.5em 1em; text-decoration: none; border-radius: 4px; }
    </style></head><body><h2>Aktuelle udlån</h2><ul>'''
    for u in udlaante:
        html += f"<li><b>{u['bog']}</b> lånt af <i>{u['bruger']}</i> den {u['dato']}</li>"
    html += '</ul><a href="/">Tilbage</a></body></html>'
    return html

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
