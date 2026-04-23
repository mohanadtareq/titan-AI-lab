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
# ━━━ البحث التلقائي المجاني ━━━
FREE_PIPELINE = [
    ("deepseek/deepseek-chat-v3-0324:free",         "🆓 DeepSeek V3 — استكشاف"),
    ("deepseek/deepseek-r1-zero:free",               "🆓 DeepSeek R1 — تفكير منطقي"),
    ("nvidia/llama-3.1-nemotron-ultra-253b-v1:free", "🆓 Nemotron — تحليل عميق"),
    ("meta-llama/llama-4-maverick:free",             "🆓 Llama 4 Maverick — بحث"),
    ("qwen/qwen3-235b-a22b:free",                    "🆓 Qwen3 235B — نمذجة"),
]
def run_auto_research(goal, target_result, room_context, max_rounds):
    api_key = st.secrets.get("OPENROUTER_API_KEY",
              os.getenv("OPENROUTER_API_KEY", ""))
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    accumulated = ""
    pipeline = FREE_PIPELINE[:max_rounds]

    for i, (model_id, model_label) in enumerate(pipeline):
        round_num = i + 1

        if round_num == 1:
            task = "استكشف الفكرة وحدد كل المناهج الممكنة للوصول للهدف. استبعد الطرق غير الواعدة بوضوح."
        elif round_num == 2:
            task = "بناءً على الجولة السابقة، ابنِ نموذجاً رياضياً أولياً للمنهج الأقوى."
        elif round_num == 3:
            task = "حلّل النموذج الرياضي بعمق واكشف الثغرات وحسّنه."
        elif round_num == 4:
            task = "ابحث في الأدبيات العلمية عن أقرب الأبحاث الموجودة وقارنها بما توصلنا إليه."
        else:
            task = "قيّم كل ما سبق وقارنه بالهدف المستهدف. ما الذي تحقق وما الذي يحتاج مزيداً من العمل؟"

        prompt = f"""
RESEARCH GOAL: {goal}
TARGET RESULT: {target_result}
ROOM CONTEXT: {room_context}

━━━ الجولة {round_num} من {max_rounds} ━━━
{f'ما توصلنا إليه حتى الآن:{chr(10)}{accumulated}' if accumulated else ''}

مهمتك: {task}

كن دقيقاً ومختصراً. ركز على ما يقرّبنا من الهدف.
"""

        try:
            response = requests.post(
                API_URL,
                headers=headers,
                json={
                    "model": model_id,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=60
            )
            if response.status_code == 200:
                result = response.json()['choices'][0]['message']['content']
            else:
                result = f"❌ خطأ {response.status_code}: {response.text[:150]}"
        except Exception as e:
            result = f"❌ انتهت المهلة أو خطأ: {str(e)[:100]}"

        accumulated += f"\n\n[جولة {round_num} - {model_label}]:\n{result}"
        yield round_num, model_label, result
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

# ━━━ واجهة البحث التلقائي ━━━
st.divider()
st.markdown("### 🔄 البحث التلقائي")

auto_enabled = st.toggle("تفعيل البحث التلقائي 🔬", value=False)

if auto_enabled:
    st.info("٥ نماذج مجانية ستعمل بالتسلسل لتقليل الطرق الخاطئة وتقريبك من الحل")

    research_goal = st.text_area(
        "🎯 الفكرة أو السؤال البحثي:",
        placeholder="مثال: بناء معالج كمي بمليار كيوبت",
        height=80
    )

    target_result = st.text_area(
        "🏁 النتيجة المستهدفة:",
        placeholder="مثال: T1 = T2 = 1 ثانية مع معمارية قابلة للتصنيع",
        height=80
    )

    max_r = st.slider(
        "عدد الجولات:",
        min_value=2,
        max_value=5,
        value=3,
        help="كل جولة = نموذج مجاني واحد يبني على السابق"
    )

    st.caption(f"النماذج: {' → '.join([label for _, label in FREE_PIPELINE[:max_r]])}")

    if st.button("🚀 ابدأ البحث التلقائي", type="primary"):
        if research_goal.strip() and target_result.strip():
            st.markdown("---")
            st.markdown("### 🔬 جلسة البحث التلقائي")
            st.caption(f"الهدف: {target_result}")

            progress = st.progress(0)

            for round_num, model_label, result in run_auto_research(
                research_goal, target_result,
                current["context"], max_r
            ):
                progress.progress(round_num / max_r)

                with st.expander(
                    f"الجولة {round_num} — {model_label}",
                    expanded=True
                ):
                    st.markdown(result)

                save_message(
                    room_key, "user",
                    f"[بحث تلقائي - جولة {round_num}/{max_r}] {research_goal}"
                )
                save_message(
                    room_key, "assistant",
                    result,
                    model_label
                )

            progress.progress(1.0)
            st.success(f"✅ اكتمل البحث التلقائي — {max_r} جولات")
            st.balloons()
        else:
            st.warning("أدخل الفكرة والنتيجة المستهدفة أولاً")
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