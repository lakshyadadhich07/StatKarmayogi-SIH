import sys
sys.path.insert(0, '.')
from app.db.session import engine, SessionLocal
engine.echo = False
from app.models.document import Document
from app.models.question import Question
from app.models.competency import Competency

db = SessionLocal()
try:
    docs = db.query(Document).all()
    print(f"Total documents: {len(docs)}")
    for d in docs:
        print(f"Doc ID={d.id}, title={d.filename}, status={d.status}")
        
    questions = db.query(Question).all()
    print(f"\nTotal questions: {len(questions)}")
    comp_ids_in_questions = set(q.competency_id for q in questions if q.competency_id)
    print(f"Competency IDs referenced in questions: {comp_ids_in_questions}")
    for cid in comp_ids_in_questions:
        c = db.query(Competency).filter(Competency.id == cid).first()
        print(f"  Comp ID {cid} -> {c.code}: {c.name}")
finally:
    db.close()
