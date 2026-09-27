import sys
sys.path.insert(0, r"c:\SIH\backend")
from app.db.session import engine
from sqlalchemy import inspect

insp = inspect(engine)
tables = insp.get_table_names()
print("=== TABLES IN POSTGRESQL ===")
for t in sorted(tables):
    if t in ["assessments", "assessment_questions", "assessment_attempts", "answers", "competency_results", "skill_gaps", "questions", "competencies"]:
        print(f"\nTABLE: {t}")
        for c in insp.get_columns(t):
            print(f"   {c['name']}: {c['type']} (nullable={c['nullable']})")
        fks = insp.get_foreign_keys(t)
        if fks:
            for fk in fks:
                print(f"   FK: {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")
        uqs = insp.get_unique_constraints(t)
        if uqs:
            for uq in uqs:
                print(f"   UQ: {uq['name']} ({uq['column_names']})")

enums = insp.get_enums()
print("\n=== ENUMS IN POSTGRESQL ===")
for e in enums:
    print(f"{e['name']}: {e['labels']}")
