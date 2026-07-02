import sqlite3
from pathlib import Path

db_path = Path('instance/plex_catalog.db').resolve()
print('DB', db_path)
print('Exists', db_path.exists())
print('Size', db_path.stat().st_size if db_path.exists() else 'N/A')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT poster_filename FROM catalog_items WHERE poster_filename IS NOT NULL AND poster_filename != '' LIMIT 20")
rows = [r[0] for r in cur.fetchall()]
print('DB poster count sample', len(rows))
for fn in rows:
    p = Path('static/images/posters') / fn
    print(fn, 'exists=' , p.exists(), 'size=', p.stat().st_size if p.exists() else 'MISSING')
conn.close()
