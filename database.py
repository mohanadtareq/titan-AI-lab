import sqlite3
import shutil
import os
from datetime import datetime

DB_PATH = "titan_lab.db"
BACKUP_DIR = "backups"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            room        TEXT NOT NULL,
            role        TEXT NOT NULL,
            model       TEXT,
            content     TEXT NOT NULL,
            timestamp   TEXT NOT NULL,
            archived    INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    # نسخة احتياطية عند كل تشغيل
    auto_backup()

def save_message(room, role, content, model=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO messages (room, role, model, content, timestamp, archived)
        VALUES (?, ?, ?, ?, ?, 0)
    """, (room, role, model, content, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def load_messages(room):
    """تحميل الرسائل النشطة فقط"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT role, model, content, timestamp
        FROM messages
        WHERE room = ? AND archived = 0
        ORDER BY id ASC
    """, (room,))
    rows = c.fetchall()
    conn.close()
    return rows

def archive_room(room):
    """أرشفة المحادثة بدلاً من حذفها"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE messages SET archived = 1
        WHERE room = ? AND archived = 0
    """, (room,))
    conn.commit()
    conn.close()

def restore_room(room):
    """استعادة المحادثة المؤرشفة"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE messages SET archived = 0
        WHERE room = ?
    """, (room,))
    conn.commit()
    conn.close()

def get_history_for_api(room):
    """إرجاع التاريخ النشط فقط لـ API"""
    rows = load_messages(room)
    return [{"role": r, "content": c} for r, _, c, _ in rows]

def auto_backup():
    """نسخة احتياطية تلقائية عند كل تشغيل"""
    if not os.path.exists(DB_PATH):
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    # احتفظ بآخر 7 نسخ فقط
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{BACKUP_DIR}/titan_lab_{timestamp}.db"
    shutil.copy2(DB_PATH, backup_path)
    # احذف النسخ القديمة إذا تجاوزت 7
    backups = sorted([
        f for f in os.listdir(BACKUP_DIR)
        if f.endswith(".db")
    ])
    while len(backups) > 7:
        os.remove(f"{BACKUP_DIR}/{backups.pop(0)}")

def get_backup_list():
    """قائمة النسخ الاحتياطية المتاحة"""
    if not os.path.exists(BACKUP_DIR):
        return []
    return sorted([
        f for f in os.listdir(BACKUP_DIR)
        if f.endswith(".db")
    ], reverse=True)

def restore_from_backup(backup_filename):
    """استعادة نسخة احتياطية محددة"""
    backup_path = f"{BACKUP_DIR}/{backup_filename}"
    if os.path.exists(backup_path):
        shutil.copy2(backup_path, DB_PATH)
        return True
    return False