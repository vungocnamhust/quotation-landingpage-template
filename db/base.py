from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so Base.metadata is fully populated for Alembic.
from db.models import brand, media, publication, quotation, quote_request, rooming_heuristic, travel_style  # noqa: E402,F401
