import logging
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.enums import RoleName
from app.models.role import Role

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_ROLES = [
    RoleName.TRAINER.value,
    RoleName.SME.value,
    RoleName.OFFICER.value,
    RoleName.ADMIN.value,
]


def seed_roles(db: Optional[Session] = None) -> List[Role]:
    """Seed the 4 system roles (TRAINER, SME, OFFICER, ADMIN) idempotently.

    Safe to run repeatedly; does not duplicate existing roles.
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    created_roles: List[Role] = []
    try:
        for role_name in SYSTEM_ROLES:
            existing = db.query(Role).filter(Role.name == role_name).first()
            if not existing:
                new_role = Role(name=role_name)
                db.add(new_role)
                created_roles.append(new_role)
                logger.info(f"Created role: {role_name}")
            else:
                logger.info(f"Role already exists: {role_name}")

        db.commit()
        return created_roles
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding roles: {e}")
        raise
    finally:
        if should_close:
            db.close()


def seed_all(db: Optional[Session] = None) -> None:
    """Run all database seed operations (roles and prototype courses)."""
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        from app.db.seed_courses import seed_courses
        logger.info("Executing role seeding...")
        seed_roles(db)
        logger.info("Executing course seeding...")
        seed_courses(db)
        logger.info("All seed operations completed successfully.")
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    logger.info("Starting database seed...")
    seed_all()
    logger.info("Database seed completed.")
