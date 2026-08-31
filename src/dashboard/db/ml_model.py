"""CRUD helpers for the ml_model table"""

from dashboard.db.crud import CRUDBase

from .data_model import MLModel


class MLModelCRUD(CRUDBase[MLModel]):
    """CRUD helper for the ml_model table"""

    # inherit all methods from CRUDBase
    def __init__(self):
        super().__init__(MLModel)


# create instance of MLModelCRUD to be used in other modules
ml_model_crud = MLModelCRUD()
