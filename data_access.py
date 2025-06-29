import csv
import datetime
import os

DATA_DIR = 'data'

def csv_path(filename):
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, filename)

def read_csv(filename):
    path = csv_path(filename)
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def write_csv(filename, data, fieldnames):
    path = csv_path(filename)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

def append_csv(filename, row, fieldnames):
    path = csv_path(filename)
    file_exists = os.path.exists(path)
    with open(path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def find_bruger(kode):
    return next((r for r in read_csv('brugere.csv') if r['kode'] == kode), None)

def find_bog(kode):
    return next((r for r in read_csv('boeger.csv') if r['kode'] == kode), None)

def bog_udlaant(bog_kode):
    return any(r for r in read_csv('udlaan.csv')
               if r['bog_kode'] == bog_kode and not r['afleveret_dato'])

def registrer_udlaan(bruger_kode, bog_kode):
    append_csv('udlaan.csv', {
        'bruger_kode': bruger_kode,
        'bog_kode': bog_kode,
        'udlaan_dato': datetime.datetime.now().isoformat(),
        'afleveret_dato': ''
    }, ['bruger_kode', 'bog_kode', 'udlaan_dato', 'afleveret_dato'])

def registrer_aflevering(bog_kode):
    data = read_csv('udlaan.csv')
    updated = False
    for r in data:
        if r['bog_kode'] == bog_kode and not r['afleveret_dato']:
            r['afleveret_dato'] = datetime.datetime.now().isoformat()
            updated = True
            break
    if updated:
        write_csv('udlaan.csv', data,
                  ['bruger_kode', 'bog_kode', 'udlaan_dato', 'afleveret_dato'])
    return updated

def hent_udlaan_for_bruger(bruger_kode):
    return [r for r in read_csv('udlaan.csv')
            if r['bruger_kode'] == bruger_kode and not r['afleveret_dato']]

def opret_bruger(kode, navn):
    if find_bruger(kode): return False
    append_csv('brugere.csv', {'kode': kode, 'navn': navn}, ['kode', 'navn'])
    return True

def opret_bog(kode, titel):
    if find_bog(kode): return False
    append_csv('boeger.csv', {'kode': kode, 'titel': titel}, ['kode', 'titel'])
    return True

def hent_alle_brugere():
    return read_csv('brugere.csv')

def hent_alle_boeger():
    return read_csv('boeger.csv')
