from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SupportLevel(str, Enum):
    STRONG = "strong"
    PARTIAL = "partial"
    WEAK = "weak"
    MISSING = "missing"


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), unique=True)
    support_score: Mapped[float] = mapped_column(Float, nullable=False)
    support_level: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_strength: Mapped[float] = mapped_column(Float, default=0.0)
    source_traceability: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_pages: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    source_page_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_status: Mapped[str] = mapped_column(String(32), default="deck_only")
    evidence_relevance: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_sufficiency: Mapped[float] = mapped_column(Float, default=0.0)
    specificity: Mapped[float] = mapped_column(Float, default=0.0)
    contradictory_penalty: Mapped[float] = mapped_column(Float, default=0.0)
    missing_info_penalty: Mapped[float] = mapped_column(Float, default=0.0)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_override_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    claim: Mapped["Claim"] = relationship(back_populates="assessment")
