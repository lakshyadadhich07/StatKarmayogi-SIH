from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine, get_db
from app.main import app

client = TestClient(app)


def test_app_import():
    """Verify FastAPI application instance is created properly."""
    assert app is not None
    assert app.title == settings.APP_NAME


def test_read_root():
    """Verify GET / returns HTTP 200 and expected metadata."""
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["app"] == settings.APP_NAME
    assert payload["health"] == "/health"
    assert payload["docs"] == "/docs"
    assert "version" in payload


def test_health_check():
    """Verify GET /health returns HTTP 200 and {'status': 'ok'}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_loaded():
    """Verify environment configuration is loaded into Pydantic Settings."""
    assert settings.APP_NAME == "StatKarmayogi"
    assert settings.DATABASE_URL.startswith("postgresql+psycopg://")
    assert isinstance(settings.CORS_ORIGINS, list)


def test_database_configuration():
    """Verify SQLAlchemy 2.x Base, engine, and get_db are correctly instantiated."""
    assert Base.metadata is not None
    assert engine is not None
    # Verify pool pre-ping is enabled
    assert engine.pool._pre_ping is True

    # Test get_db generator yields a session (and closes cleanly)
    db_gen = get_db()
    session = next(db_gen)
    assert session is not None
    try:
        # Close generator cleanly
        next(db_gen, None)
    except StopIteration:
        pass
