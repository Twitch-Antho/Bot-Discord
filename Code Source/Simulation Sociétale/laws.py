import sqlite3

conn = sqlite3.connect("society.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS laws (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    active INTEGER
)
""")

conn.commit()

def propose_law(title):
    cursor.execute("INSERT INTO laws (title, active) VALUES (?, 0)", (title,))
    conn.commit()
    return cursor.lastrowid

def activate_law(law_id):
    cursor.execute("UPDATE laws SET active=1 WHERE id=?", (law_id,))
    conn.commit()
