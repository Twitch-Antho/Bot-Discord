from database import cursor, conn

def create_case(accused_id, reason):
    cursor.execute(
        "INSERT INTO cases (accused, reason, status) VALUES (?, ?, ?)",
        (accused_id, reason, "OPEN")
    )
    conn.commit()
    return cursor.lastrowid

def close_case(case_id, verdict):
    cursor.execute(
        "UPDATE cases SET status=? WHERE id=?",
        (verdict, case_id)
    )
    conn.commit()
