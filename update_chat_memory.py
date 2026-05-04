from tools import get_connection

conn = get_connection()
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE chat_memory ADD COLUMN chat_id TEXT DEFAULT 'default'")
    print("chat_id column added.")
except Exception as e:
    print("chat_id may already exist:", e)

conn.commit()
conn.close()