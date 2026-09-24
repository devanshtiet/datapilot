"""
app/database/session.py
========================
SQLAlchemy session factory — stubbed until Mission 3.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mission 3: uncomment and configure when DATABASE_URL is set.
# ---------------------------------------------------------------------------
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from config.settings import settings
#
# _engine = create_engine(settings.database_url, pool_pre_ping=True)
# SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
#
# def get_session():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


def get_session():  # type: ignore[return]
    """Stub — raises NotImplementedError until Mission 3 wires the DB."""
    raise NotImplementedError(
        "Database session is not configured yet. Set DATABASE_URL and activate Mission 3 code."
    )
