"""Initialize database schema for Sentinel Rat Dashboard."""

from __future__ import annotations

import logging
import os
import time
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from dashboard.db.database import engine, Base
from dashboard.db.model import Camera, User, Detection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def wait_for_db(retries: int = 30, delay: float = 1.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            logger.info("Database is ready")
            return
        except OperationalError as exc:
            logger.warning("Waiting for database (%s/%s): %s", attempt, retries, exc)
            time.sleep(delay)
    raise RuntimeError("Database not ready after retries")


def init_db() -> None:
    wait_for_db()

    with engine.connect() as conn:
        # enable PostGIS extension
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        conn.commit()

    Base.metadata.create_all(bind=engine)

    logger.info("Database initialized successfully")


if __name__ == "__main__":
    init_db()
