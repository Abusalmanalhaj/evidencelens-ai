from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EvidenceType(str, Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    MISSING = "missing"
    CONTRADICTORY = "contradictory"
    REPEATED = "repeated"


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(32), default=EvidenceType.DIRECT.value)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_relevant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    human_marked_relevant: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    claim: Mapped["Claim"] = relationship(back_populates="evidence_items")
