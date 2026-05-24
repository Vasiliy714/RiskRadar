from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Issuer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "issuers"

    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)

    country_code: Mapped[str | None] = mapped_column(String(2))
    sector: Mapped[str | None] = mapped_column(String(128))
