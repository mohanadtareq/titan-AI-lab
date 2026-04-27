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
                      get_history_for_api,
                      get_backup_list, restore_from_backup)

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
    def evaluate_idea_parallel(idea, room_context):
    """لجنة تحكيم ثلاثية بالتوازي"""
    import concurrent.futures

    api_key = st.secrets.get("OPENROUTER_API_KEY",
              os.getenv("OPENROUTER_API_KEY", ""))
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    judges = [
        {
            "model": "deepseek/deepseek-chat-v3-0324:free",
            "role": "القاضي الأول — خبير الجدوى التقنية",
            "prompt": f"""أنت خبير تقني. قيّم هذه الفكرة من ناحية الجدوى التقنية فقط.
الفكرة: {idea}
أعطِ:
- تقييم الجدوى: X/10
- هل ممكنة تقنياً؟
- أكبر تحدٍّ تقني؟
كن مختصراً — ٥ أسطر كحد أقصى."""
        },
        {
            "model": "deepseek/deepseek-r1-zero:free",
            "role": "القاضي الثاني — مراجع الأدبيات",
            "prompt": f"""أنت خبير في الأدبيات العلمية. قيّم هذه الفكرة من ناحية الجدة فقط.
الفكرة: {idea}
أعطِ:
- تقييم الجدة: X/10
- هل موجودة في الأدبيات؟
- أقرب بحث موجود؟
كن مختصراً — ٥ أسطر كحد أقصى."""
        },
        {
            "model": "meta-llama/llama-4-maverick:free",
            "role": "القاضي الثالث — محلل الأثر",
            "prompt": f"""أنت خبير في تقييم الأثر والتطبيق. قيّم هذه الفكرة من ناحية الأثر فقط.
الفكرة: {idea}
أعطِ:
- تقييم الأثر: X/10
- ما الفائدة الحقيقية إذا نجحت؟
- هل السوق أو المجتمع يحتاجها؟
كن مختصراً — ٥ أسطر كحد أقصى."""
        },
    ]

    def call_judge(judge):
        try:
            response = requests.post(
                API_URL,
                headers=headers,
                json={
                    "model": judge["model"],
                    "messages": [
                        {"role": "system", "content": room_context},
                        {"role": "user", "content": judge["prompt"]}
                    ]
                },
                timeout=60
            )
            if response.status_code == 200:
                return judge["role"], response.json()['choices'][0]['message']['content']
            else:
                return judge["role"], f"❌ خطأ {response.status_code}"
        except Exception as e:
            return judge["role"], f"❌ انتهت المهلة: {str(e)[:50]}"

    # استدعاء الثلاثة بالتوازي
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(call_judge, j): j for j in judges}
        for future in concurrent.futures.as_completed(futures):
            role, result = future.result()
            results[role] = result

    return results


def get_final_verdict(idea, judges_results, room_context):
    """القاضي الرابع — الحكم النهائي"""
    api_key = st.secrets.get("OPENROUTER_API_KEY",
              os.getenv("OPENROUTER_API_KEY", ""))
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    judges_summary = "\n\n".join([
        f"{role}:\n{result}"
        for role, result in judges_results.items()
    ])

    prompt = f"""
أنت القاضي الرئيسي. لديك آراء ٣ قضاة حول هذه الفكرة:

الفكرة: {idea}

آراء القضاة:
{judges_summary}

بناءً على هذه الآراء، أصدر حكماً نهائياً بهذا الشكل بالضبط:

━━━ حكم لجنة التحكيم ━━━
📋 الفكرة: [اسم مختصر]
1️⃣ الجدوى التقنية: X/10
2️⃣ الجدة والأصالة: X/10
3️⃣ الأثر والتطبيق: X/10
⭐ النتيجة الإجمالية: X/10
━━━ الحكم النهائي ━━━
[✅ أو ⏳ أو ❌ أو 🔮] [جملة واحدة]
━━━ التبرير ━━━
[سطران فقط — موضوعي وحاد]
━━━ التوصية ━━━
[ماذا تفعل بهذه الفكرة؟ سطر واحد]
"""

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json={
                "model": "qwen/qwen3-235b-a22b:free",
                "messages": [
                    {"role": "system", "content": room_context},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=60
        )
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"❌ خطأ في الحكم النهائي: {response.text[:200]}"
    except Exception as e:
        return f"❌ انتهت المهلة: {str(e)[:100]}"
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
with st.sidebar:
    st.divider()
    st.markdown("### 💾 النسخ الاحتياطية")
    st.caption("تُحفظ تلقائياً على OneDrive عند تشغيل المختبر")

    backups = get_backup_list()
    if backups:
        st.caption(f"متاح: {len(backups)} نسخة")
        selected_backup = st.selectbox(
            "استعادة نسخة:",
            backups,
            label_visibility="collapsed"
        )
        if st.button("⏪ استعادة", use_container_width=True):
            if restore_from_backup(selected_backup):
                st.success("تم الاستعادة — أعد التشغيل")
    else:
        st.caption("تعمل عند تشغيل المختبر محلياً فقط")
    st.caption("The Super Team © 2026")

current  = ROOMS[st.session_state.current_room]
room_key = st.session_state.current_room
messages = load_messages(room_key)

st.divider()
# ━━━ عرض المحادثة المحفوظة ━━━
if messages:
    for role, model, content, timestamp in messages:
        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        else:
            with st.chat_message("assistant"):
                model_name = next(
                    (k for k, v in MODELS.items() if v == model), model
                )
                st.caption(f"🤖 {model_name} — {timestamp[:16]}")
                st.markdown(content)
else:
    st.info(f"ابدأ محادثتك في غرفة {room_key}")

# ━━━ صندوق الإدخال ━━━
# غرفة Idea Validation لها واجهة خاصة
if room_key == "💡 Idea Validation":
    st.divider()
    st.markdown("### 💡 اطرح فكرتك على لجنة التحكيم")
    st.caption("٣ نماذج مجانية تقيّم بالتوازي ثم قاضٍ رابع يصدر الحكم")

    idea_input = st.text_area(
        "الفكرة:",
        placeholder="مثال: استخدام الغرافين كمستشعر حراري في الأقمار الصناعية",
        height=100,
        key="idea_input"
    )

    if st.button("⚖️ ابدأ جلسة التحكيم", type="primary"):
        if idea_input.strip():
            save_message(room_key, "user", idea_input)

            with st.chat_message("user"):
                st.markdown(f"**الفكرة المطروحة:** {idea_input}")

            # المرحلة الأولى — القضاة الثلاثة بالتوازي
            st.markdown("#### 🏛️ المرحلة الأولى — لجنة القضاة")
            with st.spinner("القضاة الثلاثة يدرسون الفكرة بالتوازي..."):
                judges_results = evaluate_idea_parallel(
                    idea_input, current["context"]
                )

            # عرض آراء القضاة
            cols = st.columns(3)
            for i, (role, result) in enumerate(judges_results.items()):
                with cols[i]:
                    with st.expander(f"📋 {role}", expanded=True):
                        st.markdown(result)

            # المرحلة الثانية — الحكم النهائي المجاني
            st.markdown("#### ⚖️ المرحلة الثانية — الحكم النهائي")
            with st.spinner("القاضي الرئيسي يجمع الآراء..."):
                verdict = get_final_verdict(
                    idea_input, judges_results, current["context"]
                )

            with st.chat_message("assistant"):
                st.markdown(verdict)

                if "✅" in verdict:
                    st.success("✅ الفكرة اجتازت لجنة التحكيم!")
                elif "❌" in verdict:
                    st.error("❌ الفكرة لم تجتز لجنة التحكيم")
                elif "⏳" in verdict:
                    st.warning("⏳ فكرة واعدة — تحتاج تطوير")
                elif "🔮" in verdict:
                    st.info("🔮 فكرة مستقبلية — احتفظ بها")

            # حفظ الحكم
            full_result = f"آراء القضاة:\n{judges_results}\n\nالحكم النهائي:\n{verdict}"
            save_message(room_key, "assistant", full_result, "jury-panel:free")

            # زر المراجعة المدفوعة
            st.divider()
            st.markdown("#### 🔍 مراجعة إضافية بنموذج قوي (اختياري)")
            st.caption("ادفع فقط للأفكار التي تستحق — رأي Claude أو MiMo")

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🤖 اعرض على Claude", type="secondary"):
                    st.session_state.review_idea = idea_input
                    st.session_state.review_verdict = verdict
                    st.session_state.show_paid_review = "claude"
                    st.rerun()
            with col_b:
                if st.button("🤖 اعرض على MiMo", type="secondary"):
                    st.session_state.review_idea = idea_input
                    st.session_state.review_verdict = verdict
                    st.session_state.show_paid_review = "mimo"
                    st.rerun()

            st.rerun()
        else:
            st.warning("اكتب فكرتك أولاً")

    # عرض المراجعة المدفوعة إذا طُلبت
    if st.session_state.get("show_paid_review"):
        model_choice = st.session_state.show_paid_review
        model_id = "anthropic/claude-sonnet-4.6" if model_choice == "claude" else "xiaomi/mimo-v2-pro"
        model_name = "Claude Sonnet 4.6" if model_choice == "claude" else "MiMo V2 Pro"

        st.markdown(f"#### 💰 رأي {model_name}")
        with st.spinner(f"{model_name} يراجع حكم اللجنة..."):
            paid_review = ask_model(
                f"""لجنة تحكيم مجانية قيّمت هذه الفكرة:
الفكرة: {st.session_state.review_idea}
حكم اللجنة: {st.session_state.review_verdict}

هل توافق على حكم اللجنة؟ أضف رأيك النقدي في ٥ أسطر فقط.""",
                model_id,
                current["context"],
                room_key
            )

        with st.chat_message("assistant"):
            st.markdown(f"**{model_name}:** {paid_review}")

        save_message(room_key, "assistant", paid_review, model_id)
        st.session_state.show_paid_review = None
        st.rerun()

else:
    # الغرف الأخرى — صندوق الإدخال العادي
    question = st.chat_input("اكتب سؤالك البحثي...")

    if question:
        save_message(room_key, "user", question)
        with st.chat_message("user"):
            st.markdown(question)
        selected_model_id = MODELS[st.session_state.selected_model]
        with st.chat_message("assistant"):
            with st.spinner("جاري التحليل..."):
                answer = ask_model(
                    question, selected_model_id,
                    current["context"], room_key
                )
            st.caption(f"🤖 {st.session_state.selected_model}")
            st.markdown(answer)
        save_message(room_key, "assistant", answer, selected_model_id)
        st.rerun()

# تأكد من تحديث البيانات عند كل تغيير
if "last_room" not in st.session_state:
    st.session_state.last_room = room_key
if st.session_state.last_room != room_key:
    st.session_state.last_room = room_key
    st.rerun()

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