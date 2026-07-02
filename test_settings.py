import requests
import sqlite3
import time
import os
from cryptography.fernet import Fernet

BASE = 'http://127.0.0.1:5000'
TEST_URL = 'http://example-plex.local:32400'
TEST_TOKEN = 'TEST_TOKEN_ABC123'
LIB_NAME = 'Movies'

# POST to /settings
r = requests.post(f'{BASE}/settings', data={'plex_url': TEST_URL, 'plex_token': TEST_TOKEN, 'library_name': LIB_NAME})
print('POST status:', r.status_code)

# wait a moment for DB commit
time.sleep(0.5)

# read DB
db_path = os.path.join('instance', 'plex_catalog.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('SELECT id, plex_url, plex_token_enc, library_name FROM settings ORDER BY id DESC LIMIT 1')
row = cur.fetchone()
conn.close()
print('DB row:', row)

# decrypt token
key_path = os.path.join('instance', 'secret.key')
with open(key_path, 'rb') as f:
    key = f.read()
fernet = Fernet(key)
if row and row[2]:
    try:
        dec = fernet.decrypt(row[2].encode('utf-8')).decode('utf-8')
        print('Decrypted token:', dec)
    except Exception as e:
        print('Decryption failed:', e)
else:
    print('No token stored')
