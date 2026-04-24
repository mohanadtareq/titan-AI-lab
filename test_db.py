# test_db.py
from dotenv import load_dotenv
load_dotenv()
from database import load_messages

rooms = [
    "🔬 Graphene Nanoring",
    "⚡ Graphene THz Diode", 
    "🏗️ Titan Series"
]

for room in rooms:
    msgs = load_messages(room)
    print(f"{room}: {len(msgs)} رسالة")
    if msgs:
        print(f"  أول رسالة: {msgs[0][2][:50]}")