"""Initialize database schema for Sentinel Rat Dashboard."""

from __future__ import annotations

import logging
import os
import time
from urllib.parse import urlparse

import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CREATE_EXTENSION_SQL = "CREATE EXTENSION IF NOT EXISTS postgis;"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS analysis_results (
    id SERIAL PRIMARY KEY,
    detection_id VARCHAR(50) NOT NULL,
    image_path TEXT NOT NULL,
    animals_detected INTEGER NOT NULL,
    species JSONB NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_INDEX_DETECTION_ID = """
CREATE INDEX IF NOT EXISTS idx_analysis_results_detection_id
    ON analysis_results (detection_id);
"""

CREATE_INDEX_DETECTED_AT = """
CREATE INDEX IF NOT EXISTS idx_analysis_results_detected_at
    ON analysis_results (detected_at);
"""


def _build_dsn() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        parsed = urlparse(database_url)
        return (
            f"host={parsed.hostname or 'db'} "
            f"port={parsed.port or 5432} "
            f"dbname={parsed.path.lstrip('/') or 'sentinel_db'} "
            f"user={parsed.username or 'sentinel_user'} "
            f"password={parsed.password or 'sentinel_pass'}"
        )
    return (
        f"host={os.environ.get('POSTGRES_HOST', 'db')} "
        f"port={os.environ.get('POSTGRES_PORT', '5432')} "
        f"dbname={os.environ.get('POSTGRES_DB', 'sentinel_db')} "
        f"user={os.environ.get('POSTGRES_USER', 'sentinel_user')} "
        f"password={os.environ.get('POSTGRES_PASSWORD', 'sentinel_pass')}"
    )


def wait_for_db(dsn: str, retries: int = 30, delay: float = 1.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(dsn)
            conn.close()
            logger.info("Database is ready")
            return
        except Exception as exc:
            logger.warning("Waiting for database (%s/%s): %s", attempt, retries, exc)
            time.sleep(delay)
    raise RuntimeError("Database not ready after retries")


def init_db(dsn: str) -> None:
    wait_for_db(dsn)
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_EXTENSION_SQL)
            cur.execute(CREATE_TABLE_SQL)
            cur.execute(CREATE_INDEX_DETECTION_ID)
            cur.execute(CREATE_INDEX_DETECTED_AT)
        logger.info("Database initialized")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db(_build_dsn())
