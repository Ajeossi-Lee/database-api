from typing import List, Optional
from uuid import UUID as UUIDType

from sqlalchemy import ARRAY, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import INT8RANGE, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import IdMixin, TimestampMixin


class Gene(IdMixin, TimestampMixin, Base):
    """基因。染色体、转录本、蛋白质模型补齐后再建立外键。"""

    __tablename__ = "genes"

    chromosome_id: Mapped[UUIDType] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    symbol: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # 同义词
    synonyms: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String(100)), default=[], nullable=True
    )
    # 1 为正链，-1 为负链
    strand: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # 基因组坐标区间
    genomic_coordinates: Mapped[Optional[dict]] = mapped_column(INT8RANGE, nullable=True)
    # 注释信息
    annotations: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    functional_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<Gene(id={self.id}, name='{self.name}', chromosome_id={self.chromosome_id})>"
