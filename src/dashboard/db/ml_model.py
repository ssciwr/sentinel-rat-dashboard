"""CRUD helpers for the ml_model table"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .data_model import MLModel
from dashboard.db.crud import CRUDBase
from . import utils


class MLModelCRUD(CRUDBase[MLModel]):
    """CRUD helper for the ml_model table"""

    # inherit all methods from CRUDBase
    def __init__(self):
        super().__init__(MLModel)


# create instance of MLModelCRUD to be used in other modules
ml_model_crud = MLModelCRUD()
