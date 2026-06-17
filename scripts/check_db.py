import sqlite3, os

db_path = os.path.join("data", "pos.db")
con = sqlite3.connect(db_path)
cur = con.cursor()

for t in ["missions", "projects", "tasks"]:
    cur.execute(f"PRAGMA table_info({t})")
    cols = [r[1] for r in cur.fetchall()]
    print(f"{t}: {cols}")

cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contexts'")
print("contexts exists:", bool(cur.fetchone()))
con.close()
