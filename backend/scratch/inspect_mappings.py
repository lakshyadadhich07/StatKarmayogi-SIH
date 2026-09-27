import sys
sys.path.insert(0, '.')
from app.db.session import engine, SessionLocal
engine.echo = False
from app.models.course import Course
from app.models.course_competency import CourseCompetency
from app.models.competency import Competency

db = SessionLocal()
try:
    ccs = db.query(CourseCompetency).all()
    print(f"Total CourseCompetency rows in DB: {len(ccs)}")
    courses = {c.id: c for c in db.query(Course).all()}
    competencies = {c.id: c for c in db.query(Competency).all()}
    
    proto_ids = [
        'IGOT-PROTO-ASI-01',
        'IGOT-PROTO-IIP-01',
        'IGOT-PROTO-NAS-01',
        'IGOT-PROTO-SSD-01',
        'IGOT-PROTO-FPOS-01',
        'IGOT-PROTO-DAP-01'
    ]
    proto_courses = [c for c in courses.values() if c.igot_course_id in proto_ids]
    
    for pc in proto_courses:
        print(f"\n========================================================")
        print(f"Course PK: {pc.id} | igot_course_id: {pc.igot_course_id}")
        print(f"Title: {pc.title}")
        mappings = [m for m in ccs if m.course_id == pc.id]
        print(f"Count of mappings: {len(mappings)}")
        for m in mappings:
            c = competencies.get(m.competency_id)
            c_info = f"{c.code} ({c.name})" if c else "MISSING"
            print(f"  Mapping ID={m.id} -> comp_id={m.competency_id} [{c_info}], score={m.relevance_score}, created_at={m.created_at}")
finally:
    db.close()
