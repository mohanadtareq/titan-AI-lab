import requests
from parameters import GOLDEN_PARAMETERS, SYSTEM_PROMPT

OPENROUTER_API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}

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