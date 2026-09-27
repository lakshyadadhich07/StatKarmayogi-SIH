import sys
sys.path.insert(0, '.')
from app.db.session import engine, SessionLocal
engine.echo = False
from app.models.competency import Competency

db = SessionLocal()
try:
    comps = db.query(Competency).all()
    # Unique by (name, category)
    seen = {}
    for c in comps:
        key = (c.name.split('_')[0], c.category)
        if key not in seen:
            seen[key] = c
            
    print(f"Unique competency definitions ({len(seen)}):")
    for (name, cat), c in seen.items():
        print(f"ID={c.id} | Name='{c.name}' | Code='{c.code}' | Category='{c.category}' | Active={c.is_active}")
        print(f"   Desc: {c.description}\n")
finally:
    db.close()
