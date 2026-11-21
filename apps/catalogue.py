#!/usr/bin/env python3
"""Regenerates the app table in apps/README.md from every apps/<id>/app.json.

Usage: python3 apps/catalogue.py   (rewrites the lines between the two CATALOGUE markers)
"""
import json
import pathlib

here = pathlib.Path(__file__).resolve().parent
rows = []
for manifest in sorted(here.glob('*/app.json')):
    app = json.loads(manifest.read_text())
    tested = app.get('tested', [])
    last = tested[-1] if tested else {}
    where = f"{last.get('device', '?')}, {last.get('os', '?')} ({last.get('date', '?')})" if last else 'not tested yet'
    rows.append(f"| [{app['name']}]({manifest.parent.name}/) | {app.get('description', '')} | {app.get('status', '?')} | {where} |")

table = ['| App | What it is | Status | Last tested on |', '|---|---|---|---|', *rows]
readme = here / 'README.md'
text = readme.read_text()
start, end = '<!-- CATALOGUE:START -->', '<!-- CATALOGUE:END -->'
before, rest = text.split(start, 1)
_, after = rest.split(end, 1)
readme.write_text(f"{before}{start}\n{chr(10).join(table)}\n{end}{after}")
print(f"{len(rows)} app(s) in the catalogue")
