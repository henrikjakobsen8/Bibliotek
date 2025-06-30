import csv
import os
from datetime import datetime

BRUGERFIL = 'data/brugere.csv'
BOGFIL = 'data/boeger.csv'
UDLAANFIL = 'data/udlaan.csv'

# Hjælpefunktioner
def _read_csv(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def _write_csv(filepath, fieldnames, rows):
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

# Brugere
def find_bruger(kode):
    return any(row['kode'] == kode for row in _read_csv(BRUGERFIL))

def opret_bruger(kode, navn):
    if find_bruger(kode):
        return False
    rows = _read_csv(BRUGERFIL)
    rows.append({'kode': kode, 'navn': navn})
    _write_csv(BRUGERFIL, ['kode', 'navn'], rows)
    return True

def hent_alle_brugere():
    return _read_csv(BRUGERFIL)

# Bøger
def find_bog(kode):
    return any(row['kode'] == kode for row in _read_csv(BOGFIL))

def opret_bog(kode, titel, forfatter, placering):
    if find_bog(kode):
        return False
    rows = _read_csv(BOGFIL)
    rows.append({
        'kode': kode,
        'titel': titel,
        'forfatter': forfatter,
        'placering': placering
    })
    _write_csv(BOGFIL, ['kode', 'titel', 'forfatter', 'placering'], rows)
    return True

def hent_alle_boeger():
    return _read_csv(BOGFIL)

# Udlån
def bog_udlaant(bog_kode):
    for row in _read_csv(UDLAANFIL):
        if row['bog'] == bog_kode and not row.get('afleveret'):
            return True
    return False

def registrer_udlaan(bruger_kode, bog_kode):
    rows = _read_csv(UDLAANFIL)
    rows.append({
        'bruger': bruger_kode,
        'bog': bog_kode,
        'dato': datetime.now().isoformat(),
        'afleveret': ''
    })
    _write_csv(UDLAANFIL, ['bruger', 'bog', 'dato', 'afleveret'], rows)

def registrer_aflevering(bog_kode):
    rows = _read_csv(UDLAANFIL)
    updated = False
    for row in rows:
        if row['bog'] == bog_kode and not row.get('afleveret'):
            row['afleveret'] = datetime.now().isoformat()
            updated = True
            break
    if updated:
        _write_csv(UDLAANFIL, ['bruger', 'bog', 'dato', 'afleveret'], rows)
    return updated

def hent_udlaan_for_bruger(bruger_kode):
    return [
        row for row in _read_csv(UDLAANFIL)
        if row['bruger'] == bruger_kode and not row.get('afleveret')
    ]

def hent_alle_udlaan():
    """Returnér alle udlån (også dem der er afleveret)"""
    return _read_csv(UDLAANFIL)

def slet_bruger(kode):
    rows = [r for r in _read_csv(BRUGERFIL) if r['kode'] != kode]
    _write_csv(BRUGERFIL, ['kode', 'navn'], rows)

def slet_bog(kode):
    # Først tjek om bogen er udlånt
    for row in _read_csv(UDLAANFIL):
        if row['bog'] == kode and not row.get('afleveret'):
            return False  # Bogen er stadig udlånt

    # Hvis ikke udlånt, slet fra bogfilen
    rows = [r for r in _read_csv(BOGFIL) if r['kode'] != kode]
    _write_csv(BOGFIL, ['kode', 'titel'], rows)
    return True

def hent_udlaan_med_brugernavn_og_bogtitel():
    udlaan = _read_csv(UDLAANFIL)
    brugere = {b['kode']: b['navn'] for b in _read_csv(BRUGERFIL)}
    boeger = {b['kode']: b['titel'] for b in _read_csv(BOGFIL)}

    # Tilføj navn og titel til udlaan rækkerne
    for row in udlaan:
        row['brugernavn'] = brugere.get(row['bruger'], 'Ukendt bruger')
        row['bogtitel'] = boeger.get(row['bog'], 'Ukendt bog')

    return udlaan
