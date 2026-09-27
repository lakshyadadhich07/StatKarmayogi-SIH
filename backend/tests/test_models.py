from decimal import Decimal
import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.seed import seed_roles
from app.db.session import SessionLocal, engine
from app.models import (
    Answer,
    Assessment,
    AssessmentQuestion,
    AssessmentStatus,
    Competency,
    CompetencyResult,
    Course,
    CourseCompetency,
    Document,
    DocumentChunk,
    DocumentStatus,
    GapLevel,
    ProficiencyLevel,
    Question,
    QuestionDifficulty,
    QuestionReview,
    QuestionStatus,
    Recommendation,
    RecommendationStatus,
    ReviewAction,
    Role,
    RoleName,
    SkillGap,
    User,
)

EXPECTED_TABLES = [
    "answers",
    "assessment_questions",
    "assessments",
    "competencies",
    "competency_results",
    "course_competencies",
    "courses",
    "document_chunks",
    "documents",
    "question_reviews",
    "questions",
    "recommendations",
    "roles",
    "skill_gaps",
    "users",
]


@pytest.fixture(scope="function")
def db_session():
    """Provide a transactional database session for tests, rolling back changes."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


def test_all_15_tables_exist_in_metadata():
    """Verify that exactly the 15 expected application tables exist in Base.metadata."""
    metadata_tables = sorted(Base.metadata.tables.keys())
    assert metadata_tables == sorted(EXPECTED_TABLES)


def test_all_15_tables_exist_in_database():
    """Verify that all 15 expected application tables are created in the database schema."""
    inspector = inspect(engine)
    db_tables = inspector.get_table_names()
    for table_name in EXPECTED_TABLES:
        assert table_name in db_tables, f"Missing table in database: {table_name}"


def test_role_seed_creates_exactly_4_roles(db_session: Session):
    """Verify role seed creates exactly TRAINER, SME, OFFICER, ADMIN."""
    seed_roles(db_session)
    roles = db_session.query(Role).all()
    role_names = sorted([r.name for r in roles])
    assert role_names == ["ADMIN", "OFFICER", "SME", "TRAINER"]


def test_user_email_unique_constraint(db_session: Session):
    """Verify duplicate user emails raise IntegrityError."""
    seed_roles(db_session)
    role = db_session.query(Role).filter_by(name=RoleName.OFFICER.value).first()
    assert role is not None

    user1 = User(
        name="Officer 1",
        email="test_officer@mospi.gov.in",
        password_hash="hash1",
        role_id=role.id,
    )
    db_session.add(user1)
    db_session.flush()

    user2 = User(
        name="Officer 2",
        email="test_officer@mospi.gov.in",
        password_hash="hash2",
        role_id=role.id,
    )
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_competency_code_unique_constraint(db_session: Session):
    """Verify duplicate competency codes raise IntegrityError."""
    c1 = Competency(code="STAT-AI-01", name="AI in Official Statistics")
    db_session.add(c1)
    db_session.flush()

    c2 = Competency(code="STAT-AI-01", name="Duplicate Code Competency")
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_course_igot_id_unique_constraint(db_session: Session):
    """Verify duplicate igot_course_id values raise IntegrityError."""
    c1 = Course(title="Course 1", igot_course_id="IGOT-STAT-101")
    db_session.add(c1)
    db_session.flush()

    c2 = Course(title="Course 2", igot_course_id="IGOT-STAT-101")
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_course_competency_unique_constraint(db_session: Session):
    """Verify (course_id, competency_id) duplicate raises IntegrityError."""
    course = Course(title="Sampling Design 101", igot_course_id="IGOT-SD-01")
    competency = Competency(code="STAT-SD-01", name="Sampling Design")
    db_session.add_all([course, competency])
    db_session.flush()

    cc1 = CourseCompetency(
        course_id=course.id,
        competency_id=competency.id,
        relevance_score=Decimal("0.95"),
    )
    db_session.add(cc1)
    db_session.flush()

    cc2 = CourseCompetency(
        course_id=course.id,
        competency_id=competency.id,
        relevance_score=Decimal("0.80"),
    )
    db_session.add(cc2)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_assessment_question_unique_constraint(db_session: Session):
    """Verify duplicate question assignment in same assessment raises IntegrityError."""
    seed_roles(db_session)
    officer_role = db_session.query(Role).filter_by(name=RoleName.OFFICER.value).first()
    officer = User(name="Officer", email="officer@test.in", password_hash="h", role_id=officer_role.id)
    db_session.add(officer)
    db_session.flush()

    assessment = Assessment(officer_id=officer.id, title="Test Assessment")
    question = Question(
        question_text="What is sampling?",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_option="A",
        created_by=officer.id,
    )
    db_session.add_all([assessment, question])
    db_session.flush()

    aq1 = AssessmentQuestion(assessment_id=assessment.id, question_id=question.id, question_order=1)
    db_session.add(aq1)
    db_session.flush()

    aq2 = AssessmentQuestion(assessment_id=assessment.id, question_id=question.id, question_order=2)
    db_session.add(aq2)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_answer_unique_constraint(db_session: Session):
    """Verify duplicate answer for same question in same assessment raises IntegrityError."""
    seed_roles(db_session)
    officer_role = db_session.query(Role).filter_by(name=RoleName.OFFICER.value).first()
    officer = User(name="Officer", email="officer_ans@test.in", password_hash="h", role_id=officer_role.id)
    db_session.add(officer)
    db_session.flush()

    assessment = Assessment(officer_id=officer.id, title="Assessment Answers")
    question = Question(
        question_text="Sample Q",
        option_a="A",
        option_b="B",
        option_c="C",
        option_d="D",
        correct_option="A",
        created_by=officer.id,
    )
    db_session.add_all([assessment, question])
    db_session.flush()

    a1 = Answer(assessment_id=assessment.id, question_id=question.id, selected_option="A", is_correct=True)
    db_session.add(a1)
    db_session.flush()

    a2 = Answer(assessment_id=assessment.id, question_id=question.id, selected_option="B", is_correct=False)
    db_session.add(a2)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_full_relational_lifecycle(db_session: Session):
    """Verify entity creation and relationships across the entire closed loop."""
    seed_roles(db_session)
    trainer_role = db_session.query(Role).filter_by(name=RoleName.TRAINER.value).first()
    sme_role = db_session.query(Role).filter_by(name=RoleName.SME.value).first()
    officer_role = db_session.query(Role).filter_by(name=RoleName.OFFICER.value).first()

    # 1. Users
    trainer = User(name="MoSPI Trainer", email="trainer@mospi.in", password_hash="h1", role_id=trainer_role.id)
    sme = User(name="SME Evaluator", email="sme@mospi.in", password_hash="h2", role_id=sme_role.id)
    officer = User(name="ISS Officer", email="officer_cycle@mospi.in", password_hash="h3", role_id=officer_role.id)
    db_session.add_all([trainer, sme, officer])
    db_session.flush()

    # 2. Competency
    comp = Competency(code="COMP-EDA", name="Exploratory Data Analysis", category="Data Science")
    db_session.add(comp)
    db_session.flush()

    # 3. Document and DocumentChunk
    doc = Document(
        uploaded_by=trainer.id,
        filename="mospi_manual.pdf",
        file_type="pdf",
        file_path="/uploads/mospi_manual.pdf",
        status=DocumentStatus.PROCESSED,
    )
    db_session.add(doc)
    db_session.flush()

    chunk = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        page_number=1,
        content_hash="abc123hash",
        chroma_id="vec_001",
    )
    db_session.add(chunk)
    db_session.flush()

    # 4. Question & Review
    q = Question(
        document_id=doc.id,
        competency_id=comp.id,
        source_chunk_id=chunk.id,
        question_text="What is the first step in EDA?",
        option_a="Summary statistics",
        option_b="Model deployment",
        option_c="Database backup",
        option_d="None of the above",
        correct_option="A",
        difficulty=QuestionDifficulty.EASY,
        status=QuestionStatus.APPROVED,
        created_by=trainer.id,
    )
    db_session.add(q)
    db_session.flush()

    review = QuestionReview(
        question_id=q.id,
        reviewer_id=sme.id,
        action=ReviewAction.APPROVE,
        comment="Accurate grounded question.",
    )
    db_session.add(review)
    db_session.flush()

    # 5. Assessment, Question Assignment, and Answer
    assessment = Assessment(
        officer_id=officer.id,
        title="Diagnostic Assessment 1",
        status=AssessmentStatus.COMPLETED,
        total_questions=1,
        total_correct=1,
        score_percentage=Decimal("100.00"),
    )
    db_session.add(assessment)
    db_session.flush()

    aq = AssessmentQuestion(assessment_id=assessment.id, question_id=q.id, question_order=1)
    ans = Answer(assessment_id=assessment.id, question_id=q.id, selected_option="A", is_correct=True)
    db_session.add_all([aq, ans])
    db_session.flush()

    # 6. Competency Result & Skill Gap
    comp_res = CompetencyResult(
        assessment_id=assessment.id,
        competency_id=comp.id,
        questions_attempted=1,
        questions_correct=1,
        score_percentage=Decimal("100.00"),
        proficiency_level=ProficiencyLevel.ADVANCED,
    )
    skill_gap = SkillGap(
        assessment_id=assessment.id,
        competency_id=comp.id,
        score_percentage=Decimal("45.00"),
        gap_level=GapLevel.MEDIUM,
    )
    db_session.add_all([comp_res, skill_gap])
    db_session.flush()

    # 7. Course & CourseCompetency & Recommendation
    course = Course(
        title="Official Statistics on iGOT",
        igot_course_id="IGOT-MOSPI-2026",
        course_url="https://igotkarmayogi.gov.in/course/1",
    )
    db_session.add(course)
    db_session.flush()

    cc = CourseCompetency(course_id=course.id, competency_id=comp.id, relevance_score=Decimal("0.90"))
    db_session.add(cc)
    db_session.flush()

    rec = Recommendation(
        officer_id=officer.id,
        assessment_id=assessment.id,
        competency_id=comp.id,
        course_id=course.id,
        priority=1,
        match_score=Decimal("92.50"),
        reason="Recommended to bridge EDA gap identified in Diagnostic Assessment 1.",
        status=RecommendationStatus.RECOMMENDED,
    )
    db_session.add(rec)
    db_session.flush()

    # Assert all relationships back-populate accurately
    assert len(trainer.documents) == 1
    assert trainer.documents[0].filename == "mospi_manual.pdf"
    assert len(doc.chunks) == 1
    assert doc.chunks[0].chroma_id == "vec_001"
    assert q.source_chunk.id == chunk.id
    assert len(q.reviews) == 1
    assert q.reviews[0].reviewer.email == "sme@mospi.in"
    assert len(assessment.answers) == 1
    assert assessment.answers[0].is_correct is True
    assert len(assessment.recommendations) == 1
    assert assessment.recommendations[0].course.title == "Official Statistics on iGOT"
    assert len(course.course_competencies) == 1
    assert course.course_competencies[0].competency.code == "COMP-EDA"
