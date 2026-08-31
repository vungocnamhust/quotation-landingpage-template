from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so Base.metadata is fully populated for Alembic.
from db.models import ai_run, booking, brand, costing, ingestion, media, product, publication, quotation, quote_request, rate, rooming_heuristic, supplier, supplier_invoice, travel_style  # noqa: E402,F401
