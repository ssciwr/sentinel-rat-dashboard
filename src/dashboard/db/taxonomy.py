"""CRUD helpers for the taxonomy table"""

from dashboard.db.crud import CRUDBase

from .data_model import Taxonomy


class TaxonomyCRUD(CRUDBase[Taxonomy]):
    """CRUD helper for the taxonomy table."""

    # inherit all methods from CRUDBase
    def __init__(self):
        super().__init__(Taxonomy)


# create instance of TaxonomyCRUD to be used in other modules
taxonomy_crud = TaxonomyCRUD()
