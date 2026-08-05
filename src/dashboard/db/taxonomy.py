"""CRUD helpers for the taxonomy table"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .data_model import Taxonomy
from dashboard.db.crud import CRUDBase
from . import utils


class TaxonomyCRUD(CRUDBase[Taxonomy]):
    """CRUD helper for the taxonomy table."""

    # inherit all methods from CRUDBase
    def __init__(self):
        super().__init__(Taxonomy)


# create instance of TaxonomyCRUD to be used in other modules
taxonomy_crud = TaxonomyCRUD()
