from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.mixins import IdMixin, TimestampMixin


class Gene(IdMixin, TimestampMixin, Base):
    """Gene model."""

    __tablename__ = "genes"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    def __repr__(self):
        return f"<Gene(id={self.id}, name='{self.name}')>"