import sys
sys.path.insert(0, '.')
from app.db.session import engine
engine.echo = False
from sqlalchemy import inspect

inspector = inspect(engine)
tables = inspector.get_table_names()
print(f"Total tables: {len(tables)}")
for t in sorted(tables):
    cols = [f"{c['name']} ({c['type']})" for c in inspector.get_columns(t)]
    fks = [f"{fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}" for fk in inspector.get_foreign_keys(t)]
    print(f"\nTable: {t}")
    print(f"  Columns: {', '.join(cols)}")
    if fks:
        print(f"  FKs: {', '.join(fks)}")
