"""CRUD helpers for the daily_analysis_result table"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .data_model import DailyAnalysisResult
from dashboard.db.crud import CRUDBase
from . import utils


class DailyAnalysisResultCRUD(CRUDBase[DailyAnalysisResult]):
    """CRUD helpers for the daily_analysis_result table"""

    # inherit all methods from CRUDBase
    def __init__(self):
        super().__init__(DailyAnalysisResult)


# create an instance of the DailyAnalysisResultCRUD class to be used in other modules
daily_analysis_result_crud = DailyAnalysisResultCRUD()
