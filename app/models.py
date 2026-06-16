import sqlite3
from flask import g, current_app

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(database_path):
    conn = sqlite3.connect(database_path)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_name TEXT NOT NULL,
            zip_name TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            zip_size INTEGER DEFAULT 0,
            mime_type TEXT DEFAULT 'unknown',
            file_hash TEXT DEFAULT '',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def insert_file(original_name, zip_name, file_size, zip_size, mime_type, file_hash):
    db = get_db()
    db.execute(
        'INSERT INTO files (original_name, zip_name, file_size, zip_size, mime_type, file_hash) VALUES (?, ?, ?, ?, ?, ?)',
        (original_name, zip_name, file_size, zip_size, mime_type, file_hash)
    )
    db.commit()
    return db.execute('SELECT last_insert_rowid()').fetchone()[0]

def get_all_files():
    db = get_db()
    return db.execute('SELECT * FROM files ORDER BY uploaded_at DESC').fetchall()

def get_file(file_id):
    db = get_db()
    return db.execute('SELECT * FROM files WHERE id = ?', (file_id,)).fetchone()

def delete_file_record(file_id):
    db = get_db()
    db.execute('DELETE FROM files WHERE id = ?', (file_id,))
    db.commit()
