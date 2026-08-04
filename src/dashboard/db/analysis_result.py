"""CRUD helpers for the daily_analysis_result table"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .data_model import DailyAnalysisResult
from . import utils


def add_daily_analysis_result(
    session: Session,
    *,
    camera_id: int,
    start_time: Any,
    end_time: Any,
    taxonomy_id: int,
    taxonomy_count: int,
    avg_confidence: float,
) -> DailyAnalysisResult:
    """Insert a new daily_analysis_result row and return the persisted object."""

    daily_analysis_result = DailyAnalysisResult(
        camera_id=camera_id,
        start_time=start_time,
        end_time=end_time,
        taxonomy_count=taxonomy_count,
        avg_confidence=avg_confidence,
        taxonomy_id=taxonomy_id,
    )

    session.add(daily_analysis_result)
    utils.commit(session)
    session.refresh(daily_analysis_result)

    return daily_analysis_result


def select_daily_analysis_results(session: Session) -> list[DailyAnalysisResult]:
    """Return all daily_analysis_result rows ordered by primary key."""

    statement = select(DailyAnalysisResult).order_by(DailyAnalysisResult.id)
    return list(session.execute(statement).scalars().all())


def get_daily_analysis_result(
    session: Session, daily_analysis_result_id: int
) -> DailyAnalysisResult | None:
    """Return one daily_analysis_result row by primary key."""

    return session.get(DailyAnalysisResult, daily_analysis_result_id)


def get_daily_analysis_results_by_filter(
    session: Session, **filters: Any
) -> list[DailyAnalysisResult]:
    """Return a list of daily_analysis_result rows filtered by the provided keyword arguments."""

    if not filters:
        raise ValueError(
            "At least one filter must be provided."
            "To select all analysis results, use `select_daily_analysis_results()` instead."
        )

    statement = (
        select(DailyAnalysisResult)
        .filter_by(**filters)
        .order_by(DailyAnalysisResult.id)
    )
    return list(session.execute(statement).scalars().all())


def update_daily_analysis_result(
    session: Session, daily_analysis_result_id: int, **changes: Any
) -> DailyAnalysisResult | None:
    """Update a daily_analysis_result row and return the refreshed object, or None if missing."""

    daily_analysis_result = session.get(DailyAnalysisResult, daily_analysis_result_id)
    if daily_analysis_result is None:
        return None

    if not changes:
        return daily_analysis_result

    allowed_fields = {
        "taxonomy_count",
        "avg_confidence",
    }
    unexpected_fields = set(changes.keys()) - allowed_fields
    if unexpected_fields:
        raise ValueError(
            f"Unsupported daily_analysis_result fields: {sorted(unexpected_fields)}"
        )

    for key, value in changes.items():
        setattr(daily_analysis_result, key, value)

    utils.commit(session)
    session.refresh(daily_analysis_result)

    return daily_analysis_result


def delete_daily_analysis_result(
    session: Session, daily_analysis_result_id: int
) -> bool:
    """Delete a daily_analysis_result row by primary key. Return True if deleted, False if not found."""

    daily_analysis_result = session.get(DailyAnalysisResult, daily_analysis_result_id)
    if daily_analysis_result is None:
        return False

    session.delete(daily_analysis_result)
    utils.commit(session)

    return True
