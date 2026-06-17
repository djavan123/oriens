import sqlite3, os
con = sqlite3.connect(os.path.join("data", "pos.db"))
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weekly_directives'")
print("table exists:", bool(cur.fetchone()))
cur.execute("SELECT * FROM weekly_directives")
rows = cur.fetchall()
print("rows:", rows)
con.close()
