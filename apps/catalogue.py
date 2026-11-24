#!/usr/bin/env python3
"""Regenerates the app table in apps/README.md and apps/catalogue.json from every apps/<id>/app.json.

Usage: python3 apps/catalogue.py   (rewrites the lines between the two CATALOGUE markers, and the JSON)

catalogue.json is for programs: an app store (LightOS's Store) or an installer reads it from the
repository instead of every folder. Each entry has the app's id, name, description, url, icon_url,
color, categories, status, whether it has an extension, and when it was last tested.
"""
import json
import pathlib

here = pathlib.Path(__file__).resolve().parent
rows = []
entries = []
for manifest in sorted(here.glob('*/app.json')):
    app = json.loads(manifest.read_text())
    tested_list = app.get('tested', [])
    entries.append({
        'id': app['id'],
        'name': app['name'],
        'description': app.get('description', ''),
        'url': app['url'],
        'icon_url': app.get('icon_url', ''),
        'color': app.get('color', ''),
        'categories': app.get('categories', []),
        'status': app.get('status', ''),
        'extension': bool(app.get('extension')),
        'tested': tested_list[-1].get('date', '') if tested_list else '',
    })
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
(here / 'catalogue.json').write_text(json.dumps({'apps': entries}, ensure_ascii=False, indent=2) + '\n')
print(f"{len(rows)} app(s) in the catalogue")
