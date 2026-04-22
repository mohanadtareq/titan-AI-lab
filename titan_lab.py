SYSTEM_PROMPT = "You are an expert AI assistant specializing in scientific research and analysis."

def ask_model(question, model, room_context, room):
    # قراءة المفتاح في كل مرة
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
def ask_claude(question):
    data = {
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": question
            }
        ]
    }
    
    response = requests.post(API_URL, headers=headers, json=data)
    
    if response.status_code == 200:
        result = response.json()
        return result['choices'][0]['message']['content']
    else:
        return f"Error: {response.status_code} - {response.text}"

# أول سؤال بحثي حقيقي
question = f"""
Based on our golden parameters where Vg = {GOLDEN_PARAMETERS['Vg']} V 
and D = {GOLDEN_PARAMETERS['D']} nm, what are the main theoretical 
challenges we need to address in our paper?
"""

print("=" * 50)
print("TITAN AI LAB - First Research Query")
print("=" * 50)
print(f"Question: {question}")
print("=" * 50)
print("Claude responds:")
print(ask_claude(question))
print("=" * 50)