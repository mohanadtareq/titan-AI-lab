try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
import streamlit as st
import requests
from parameters import GOLDEN_PARAMETERS, SYSTEM_PROMPT
from rooms import ROOMS
from database import (init_db, save_message, load_messages,
                      archive_room, restore_room,
                      get_history_for_api, get_backup_list,
                      restore_from_backup)

API_URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = {
    "MiMo V2 Pro (نقد جوهري)":           "xiaomi/mimo-v2-pro",
    "Claude Sonnet 4.6 (تحليل أكاديمي)": "anthropic/claude-sonnet-4.6",
    "Qwen 3.6 Plus 🆓 (نقد منهجي)":      "qwen/qwen3.6-plus",
    "MiniMax M2.7 (ناقد صارم)":           "minimax/minimax-m2.7-20260318",
    "DeepSeek V3.2 (حسابات)":             "deepseek/deepseek-v3.2",
    "GPT-5.4 (صياغة أكاديمية)":           "openai/gpt-5.4",
    "Google: Gemma 4 31B (بحث مراجع)":         "google/gemma-4-31b-it",
}

init_db()

def ask_model(question, model, room_context, room):
    api_key = st.secrets.get("OPENROUTER_API_KEY",
              os.getenv("OPENROUTER_API_KEY", ""))
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    history = get_history_for_api(room)
    system = f"{SYSTEM_PROMPT}\n\n{room_context}"
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            *history,
            {"role": "user", "content": question}
        ]
    }
    response = requests.post(API_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        return f"❌ خطأ {response.status_code}: {response.text}"

st.set_page_config(page_title="Titan AI Lab", page_icon="⚛️", layout="wide")

st.markdown("""
    <style>
        .stApp { direction: rtl; text-align: right; }
        .stChatMessage { direction: rtl; text-align: right; }
        .stSidebar { direction: rtl; text-align: right; }
        .stSelectbox { direction: rtl; }
        .stChatInputContainer { direction: rtl; }
        h1, h2, h3, p, div { direction: rtl; text-align: right; }
    </style>
""", unsafe_allow_html=True)

if "current_room" not in st.session_state:
    st.session_state.current_room = list(ROOMS.keys())[0]
if "selected_model" not in st.session_state:
    st.session_state.selected_model = list(MODELS.keys())[0]

with st.sidebar:
    st.markdown("## ⚛️ Titan AI Lab")
    st.markdown("### 🚪 الغرف البحثية")
    st.divider()
    for room_key, room_data in ROOMS.items():
        is_active = st.session_state.current_room == room_key
        btn_label = f"{'▶ ' if is_active else ''}{room_key}"
        if st.button(btn_label, key=f"btn_{room_key}", use_container_width=True):
            st.session_state.current_room = room_key
            st.rerun()
    st.divider()
    st.markdown("### 🤖 النموذج")
    st.session_state.selected_model = st.selectbox(
        "اختر النموذج:", list(MODELS.keys()), label_visibility="collapsed"
    )
    st.divider()
    backups = get_backup_list()
    if backups:
        st.markdown("### 💾 النسخ الاحتياطية")
        st.caption(f"متاح: {len(backups)} نسخة")
    st.caption("The Super Team © 2026")

current  = ROOMS[st.session_state.current_room]
room_key = st.session_state.current_room
messages = load_messages(room_key)

st.markdown(f"## {room_key}")
st.caption(current["description"])

if "Graphene" in room_key:
    with st.expander("🔬 المعاملات الذهبية"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Vg", f"{GOLDEN_PARAMETERS['Vg']} V")
        c1.metric("D",  f"{GOLDEN_PARAMETERS['D']} nm")
        c2.metric("f",  f"{GOLDEN_PARAMETERS['f']} THz")
        c2.metric("Q",  f"{GOLDEN_PARAMETERS['Q']}")
        c3.metric("η",  f"{GOLDEN_PARAMETERS['eta']}%")
        c3.metric("Purcell", f"{GOLDEN_PARAMETERS['Purcell']:.2e}")

st.divider()

if messages:
    for role, model, content, timestamp in messages:
        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        else:
            with st.chat_message("assistant"):
                model_name = next((k for k, v in MODELS.items() if v == model), model)
                st.caption(f"🤖 {model_name} — {timestamp[:16]}")
                st.markdown(content)
else:
    st.info(f"ابدأ محادثتك في غرفة {room_key}")

question = st.chat_input("اكتب سؤالك البحثي...")

if question:
    save_message(room_key, "user", question)
    with st.chat_message("user"):
        st.markdown(question)
    selected_model_id = MODELS[st.session_state.selected_model]
    with st.chat_message("assistant"):
        with st.spinner("جاري التحليل..."):
            answer = ask_model(question, selected_model_id, current["context"], room_key)
        st.caption(f"🤖 {st.session_state.selected_model}")
        st.markdown(answer)
    save_message(room_key, "assistant", answer, selected_model_id)

if messages:
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗃️ أرشفة هذه الغرفة", type="secondary"):
            archive_room(room_key)
            st.success("تم أرشفة المحادثة")
            st.rerun()
    with col2:
        if st.button("♻️ استعادة المؤرشف", type="secondary"):
            restore_room(room_key)
            st.success("تم استعادة المحادثة")
            st.rerun()