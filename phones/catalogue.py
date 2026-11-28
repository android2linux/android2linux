#!/usr/bin/env python3
"""Regenerates the phone table and the hardware tables from every phones/<id>/phone.json.

Usage: python3 phones/catalogue.py
  - phones/README.md: the lines between the CATALOGUE markers and the hardware matrix between the
    HARDWARE markers
  - phones/<id>/README.md: the hardware table between its HARDWARE markers, if it has them
  - phones/catalogue.json: every phone and its systems, with the hardware by area

The hardware areas and statuses below are the one list both the guides index and every phone use.
"""
import json
import pathlib
import sys

AREAS = [
    ('display', 'Display, backlight'),
    ('touch', 'Touch'),
    ('gpu', 'GPU'),
    ('wifi', 'Wi-Fi'),
    ('bluetooth', 'Bluetooth'),
    ('modem', 'Modem (data, SMS, calls)'),
    ('audio', 'Audio (speaker, microphones, earpiece, headphones)'),
    ('charging', 'Charging'),
    ('battery', 'Battery gauge'),
    ('suspend', 'Suspend'),
    ('usb', 'USB (networking, roles)'),
    ('cameras', 'Cameras'),
    ('sensors', 'Sensors, rotation'),
    ('gps', 'GPS, NFC, fingerprint'),
    ('buttons', 'Buttons, vibration, headset jack'),
]
AREA_IDS = [area for area, _ in AREAS]
AREA_LABELS = dict(AREAS)
SHORT_LABELS = {
    'display': 'Display', 'touch': 'Touch', 'gpu': 'GPU', 'wifi': 'Wi-Fi',
    'bluetooth': 'Bluetooth', 'modem': 'Modem', 'audio': 'Audio', 'charging': 'Charging',
    'battery': 'Battery', 'suspend': 'Suspend', 'usb': 'USB', 'cameras': 'Cameras',
    'sensors': 'Sensors', 'gps': 'GPS', 'buttons': 'Buttons',
}
STATUSES = ('works', 'partial', 'broken', 'reported', 'untested')


def fail(message):
    print(f"phones/catalogue.py: {message}", file=sys.stderr)
    sys.exit(1)


def replace_block(text, start, end, body):
    before, rest = text.split(start, 1)
    _, after = rest.split(end, 1)
    return f"{before}{start}\n{body}\n{end}{after}"


def system_entry(system):
    entry = {}
    for key in ('name', 'version', 'status', 'checked', 'notes'):
        if key in system:
            entry[key] = system[key]
    if 'hardware' in system:
        entry['hardware'] = system['hardware']
    return entry


here = pathlib.Path(__file__).resolve().parent
rows = []
matrix_rows = []
entries = []

for manifest in sorted(here.glob('*/phone.json')):
    phone = json.loads(manifest.read_text())
    systems = phone.get('systems', [])

    for system in systems:
        hardware = system.get('hardware')
        if hardware is None:
            continue
        for area, entry in hardware.items():
            if area not in AREA_IDS:
                fail(f"{manifest}: unknown hardware area '{area}'")
            status = entry.get('status')
            if status not in STATUSES:
                fail(f"{manifest}: unknown status '{status}' for '{area}' "
                     f"(use one of: {', '.join(STATUSES)})")

    linux = '; '.join(
        f"{s['name']} {s.get('version', '')}".strip() + f": {s['status']}" if s['name'] != 'none' else s['status']
        for s in systems) or 'not tried'
    checked = max((s.get('checked', '') for s in systems), default='')
    rows.append(f"| [{phone['vendor']} {phone['model']}]({manifest.parent.name}/) | `{phone['codename']}` | {phone['soc']} | {linux} | {checked} |")

    for system in systems:
        hardware = system.get('hardware')
        if not hardware:
            continue
        label = f"{phone['vendor']} {phone['model']} (`{phone['codename']}`), {system['name']} {system.get('version', '')}".strip()
        cells = [hardware.get(area, {}).get('status', '') for area in AREA_IDS]
        matrix_rows.append(f"| {label} | {' | '.join(cells)} |")

    entries.append({
        'id': phone['id'],
        'vendor': phone['vendor'],
        'model': phone['model'],
        'codename': phone['codename'],
        'family': phone.get('family', ''),
        'soc': phone.get('soc', ''),
        'systems': [system_entry(s) for s in systems],
    })

    readme = manifest.parent / 'README.md'
    if readme.exists():
        text = readme.read_text()
        start, end = '<!-- HARDWARE:START -->', '<!-- HARDWARE:END -->'
        if start in text and end in text:
            with_hardware = [s for s in systems if s.get('hardware')]
            header = '| | ' + ' | '.join(
                f"{s['name']} {s.get('version', '')}".strip() for s in with_hardware) + ' |'
            separator = '|---|' + '|'.join('---' for _ in with_hardware) + '|'
            table_rows = [header, separator]
            for area in AREA_IDS:
                cells = []
                for system in with_hardware:
                    entry = system['hardware'].get(area, {})
                    cell = entry.get('status', '')
                    if entry.get('notes'):
                        cell += f": {entry['notes']}"
                    if entry.get('guide'):
                        cell += f" ([guide](../../skills/android2linux/references/guides/{entry['guide']}))"
                    if entry.get('fix'):
                        cell += f" ([fix]({entry['fix']}/))"
                    cells.append(cell)
                table_rows.append(f"| {AREA_LABELS[area]} | {' | '.join(cells)} |")
            readme.write_text(replace_block(text, start, end, '\n'.join(table_rows)))

table = ['| Phone | Codename | Chip | Linux | Last checked |', '|---|---|---|---|---|', *rows]
readme = here / 'README.md'
text = readme.read_text()
start, end = '<!-- CATALOGUE:START -->', '<!-- CATALOGUE:END -->'
text = replace_block(text, start, end, '\n'.join(table))

matrix_header = '| Phone, system | ' + ' | '.join(SHORT_LABELS[area] for area in AREA_IDS) + ' |'
matrix_separator = '|---|' + '|'.join('---' for _ in AREA_IDS) + '|'
matrix = [matrix_header, matrix_separator, *matrix_rows]
start, end = '<!-- HARDWARE:START -->', '<!-- HARDWARE:END -->'
if start in text and end in text:
    text = replace_block(text, start, end, '\n'.join(matrix))
readme.write_text(text)

(here / 'catalogue.json').write_text(
    json.dumps({'phones': entries}, ensure_ascii=False, indent=2) + '\n')
print(f"{len(rows)} phone(s) in the catalogue")
