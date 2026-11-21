#!/usr/bin/env python3
"""Regenerates the phone table in phones/README.md from every phones/<id>/phone.json.

Usage: python3 phones/catalogue.py   (rewrites the lines between the two CATALOGUE markers)
"""
import json
import pathlib

here = pathlib.Path(__file__).resolve().parent
rows = []
for manifest in sorted(here.glob('*/phone.json')):
    phone = json.loads(manifest.read_text())
    systems = phone.get('systems', [])
    linux = '; '.join(
        f"{s['name']} {s.get('version', '')}".strip() + f": {s['status']}" if s['name'] != 'none' else s['status']
        for s in systems) or 'not tried'
    checked = max((s.get('checked', '') for s in systems), default='')
    rows.append(f"| [{phone['vendor']} {phone['model']}]({manifest.parent.name}/) | `{phone['codename']}` | {phone['soc']} | {linux} | {checked} |")

table = ['| Phone | Codename | Chip | Linux | Last checked |', '|---|---|---|---|---|', *rows]
readme = here / 'README.md'
text = readme.read_text()
start, end = '<!-- CATALOGUE:START -->', '<!-- CATALOGUE:END -->'
before, rest = text.split(start, 1)
_, after = rest.split(end, 1)
readme.write_text(f"{before}{start}\n{chr(10).join(table)}\n{end}{after}")
print(f"{len(rows)} phone(s) in the catalogue")
