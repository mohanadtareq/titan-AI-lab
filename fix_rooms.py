from dotenv import load_dotenv
load_dotenv()

from database import supabase

fixes = [
    ("Graphene Nanoring",  "🔬 Graphene Nanoring"),
    ("Graphene THz Diode", "⚡ Graphene THz Diode"),
    ("Titan Series",       "🏗️ Titan Series"),
]

for old_name, new_name in fixes:
    result = supabase.table("messages") \
        .update({"room": new_name}) \
        .eq("room", old_name) \
        .execute()
    print(f"✓ {old_name} → {new_name}")

print("✅ تم التحديث")

result = supabase.table("messages").select("room").execute()
rooms = set(r["room"] for r in result.data)
for r in rooms:
    print(repr(r))