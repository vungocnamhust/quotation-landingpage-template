from __future__ import annotations

from sqlalchemy import BigInteger, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import JSONB


JSON_VARIANT = JSON().with_variant(JSONB(astext_type=Text()), "postgresql")
BIGINT_PK_VARIANT = BigInteger().with_variant(Integer(), "sqlite")
