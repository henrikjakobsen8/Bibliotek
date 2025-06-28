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

# HTML Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Bibliotek System</title>
</head>
<body>
    <h1>Bibliotek System</h1>
    <form method="POST" action="/udlaan">
        <h3>Udlån</h3>
        Scan bruger: <input name="bruger" required><br>
        Scan bog: <input name="bog" required><br>
        <button type="submit">Udlån</button>
    </form>

    <form method="POST" action="/aflevering">
        <h3>Aflevering</h3>
        Scan bog: <input name="bog" required><br>
        <button type="submit">Aflever</button>
    </form>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul>
        {% for message in messages %}
          <li>{{ message }}</li>
        {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
