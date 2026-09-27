import sys
sys.path.insert(0, '.')
from app.db.session import engine, SessionLocal
engine.echo = False
from app.models.course import Course
from app.models.course_competency import CourseCompetency
from app.models.competency import Competency

db = SessionLocal()
try:
    c = db.query(Course).filter(Course.id == 93).first()
    print(f"Course: {c.title} (PK: {c.id})")
    mappings = db.query(CourseCompetency).filter(CourseCompetency.course_id == c.id).all()
    print(f"Total mappings: {len(mappings)}")
    for m in mappings:
        comp = db.query(Competency).filter(Competency.id == m.competency_id).first()
        print(f"  Mapping {m.id} -> comp_id={m.competency_id} ({comp.code}: {comp.name}), score={m.relevance_score}")
finally:
    db.close()
