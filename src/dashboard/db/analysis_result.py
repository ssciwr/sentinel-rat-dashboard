"""CRUD helpers for the daily_analysis_result table"""

from dashboard.db.crud import CRUDBase

from .data_model import DailyAnalysisResult


class DailyAnalysisResultCRUD(CRUDBase[DailyAnalysisResult]):
    """CRUD helpers for the daily_analysis_result table"""

    # inherit all methods from CRUDBase
    def __init__(self):
        super().__init__(DailyAnalysisResult)


# create an instance of the DailyAnalysisResultCRUD class to be used in other modules
daily_analysis_result_crud = DailyAnalysisResultCRUD()
