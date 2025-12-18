import sqlite3

conn = sqlite3.connect("justice.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    accused INTEGER,
    reason TEXT,
    status TEXT
)
""")

conn.commit()
