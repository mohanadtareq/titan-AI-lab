import sqlite3
import os
from dotenv import load_dotenv
load_dotenv()

from database import supabase

# مسار قاعدة البيانات القديمة
OLD_DB = r"C:\Users\Lenovo\titan_lab\backups\titan_lab_20260422_011029.db"

def migrate():
    if not os.path.exists(OLD_DB):
        print("لم يتم العثور على قاعدة البيانات القديمة")
        return

    conn = sqlite3.connect(OLD_DB)
    c = conn.cursor()
    c.execute("SELECT room, role, model, content, timestamp, archived FROM messages ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()

    print(f"وُجد {len(rows)} رسالة للنقل...")

    for row in rows:
        room, role, model, content, timestamp, archived = row
        supabase.table("messages").insert({
            "room": room,
            "role": role,
            "model": model,
            "content": content,
            "timestamp": timestamp,
            "archived": archived
        }).execute()

    print(f"✅ تم نقل {len(rows)} رسالة إلى Supabase")

migrate()