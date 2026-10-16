from typing import List, Optional
from sqlalchemy import String, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.mixins import IdMixin, TimestampMixin


class User(IdMixin, TimestampMixin, Base):
    """User model."""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    permissions: Mapped[Optional[List[str]]] = mapped_column(JSON, default=[])
    roles: Mapped[Optional[List[str]]] = mapped_column(JSON, default=[])

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"