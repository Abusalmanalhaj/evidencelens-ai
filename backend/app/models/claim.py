from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClaimCategory(str, Enum):
    PRODUCT = "product"
    TECHNOLOGY = "technology"
    SCALABILITY = "scalability"
    PERFORMANCE = "performance"
    IP = "ip"
    SECURITY = "security"
    MARKET = "market"
    BUSINESS = "business"
    OTHER = "other"


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    analysis_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("analysis_runs.id", ondelete="SET NULL"), nullable=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), default=ClaimCategory.OTHER.value)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_pages: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    claim_basis: Mapped[str | None] = mapped_column(String(32), nullable=True)
    claim_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ai_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    human_category: Mapped[str | None] = mapped_column(String(32), nullable=True)
    requires_review: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="claims")
    analysis_run: Mapped["AnalysisRun | None"] = relationship(back_populates="claims")
    evidence_items: Mapped[list["Evidence"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
    assessment: Mapped["Assessment | None"] = relationship(
        back_populates="claim", cascade="all, delete-orphan", uselist=False
    )
    review_feedback: Mapped[list["ReviewFeedback"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )
