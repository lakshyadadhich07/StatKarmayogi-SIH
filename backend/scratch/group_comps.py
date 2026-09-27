import sys
sys.path.insert(0, '.')
from app.db.session import engine, SessionLocal
engine.echo = False
from app.models.competency import Competency

db = SessionLocal()
try:
    comps = db.query(Competency).all()
    print(f"Total competencies: {len(comps)}")
    
    # Group by base name
    names = {}
    for c in comps:
        base_name = c.name.split('_')[0]
        names.setdefault(base_name, []).append(c)
        
    for k, v in sorted(names.items()):
        print(f"\nBase Name: '{k}' -> {len(v)} occurrences (Active: {sum(1 for x in v if x.is_active)}, Inactive: {sum(1 for x in v if not x.is_active)})")
        sample = v[0]
        print(f"  Sample ID={sample.id}, Code='{sample.code}', Category='{sample.category}', Active={sample.is_active}")
finally:
    db.close()
