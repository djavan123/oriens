import sqlite3, os

db_path = os.path.join("data", "pos.db")
con = sqlite3.connect(db_path)
cur = con.cursor()

statements = [
    "ALTER TABLE projects ADD COLUMN context_id INTEGER",
    "CREATE INDEX IF NOT EXISTS ix_projects_context_id ON projects (context_id)",
    "ALTER TABLE tasks ADD COLUMN context_id INTEGER",
    "CREATE INDEX IF NOT EXISTS ix_tasks_context_id ON tasks (context_id)",
    "CREATE INDEX IF NOT EXISTS ix_missions_context_id ON missions (context_id)",
    "CREATE INDEX IF NOT EXISTS ix_contexts_id ON contexts (id)",
]

for sql in statements:
    try:
        cur.execute(sql)
        print(f"OK: {sql[:60]}")
    except sqlite3.OperationalError as e:
        print(f"SKIP ({e}): {sql[:60]}")

con.commit()
con.close()
print("Done.")
