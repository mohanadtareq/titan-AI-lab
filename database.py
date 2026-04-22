try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
import streamlit as st
import shutil
from datetime import datetime
from supabase import create_client, ClientOptions

# قراءة المفاتيح بأمان
SUPABASE_URL = st.secrets.get("SUPABASE_URL", 
               os.getenv("SUPABASE_URL", ""))
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", 
               os.getenv("SUPABASE_KEY", ""))

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY,
    options=ClientOptions(
        postgrest_client_timeout=10,
        storage_client_timeout=10,
    )
)
# ━━━ النسخ الاحتياطي المحلي (اختياري) ━━━
BACKUP_DIR = "backups"

def init_db():
    """لا نحتاج إنشاء جدول — موجود في Supabase"""
    pass

def save_message(room, role, content, model=None):
    """حفظ رسالة في Supabase"""
    supabase.table("messages").insert({
        "room": room,
        "role": role,
        "model": model,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "archived": 0
    }).execute()

def load_messages(room):
    """تحميل الرسائل النشطة من Supabase"""
    result = supabase.table("messages") \
        .select("role, model, content, timestamp") \
        .eq("room", room) \
        .eq("archived", 0) \
        .order("id") \
        .execute()
    return [(r["role"], r["model"], r["content"], r["timestamp"])
            for r in result.data]

def archive_room(room):
    """أرشفة محادثة غرفة"""
    supabase.table("messages") \
        .update({"archived": 1}) \
        .eq("room", room) \
        .eq("archived", 0) \
        .execute()

def restore_room(room):
    """استعادة محادثة مؤرشفة"""
    supabase.table("messages") \
        .update({"archived": 0}) \
        .eq("room", room) \
        .execute()

def get_history_for_api(room):
    """إرجاع التاريخ بصيغة API"""
    rows = load_messages(room)
    return [{"role": r, "content": c} for r, _, c, _ in rows]

def get_backup_list():
    """قائمة النسخ الاحتياطية المحلية"""
    if not os.path.exists(BACKUP_DIR):
        return []
    return sorted([
        f for f in os.listdir(BACKUP_DIR)
        if f.endswith(".db")
    ], reverse=True)

def restore_from_backup(backup_filename):
    """استعادة نسخة احتياطية"""
    pass