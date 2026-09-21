from datetime import datetime

from pydantic import BaseModel, Field


class EvidenceOut(BaseModel):
    id: int
    text: str
    evidence_type: str
    source_page: int | None
    is_relevant: bool | None
    human_marked_relevant: bool | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AssessmentOut(BaseModel):
    id: int
    support_score: float
    support_level: str
    evidence_strength: float
    source_traceability: float
    evidence_pages: list[int] | None
    source_page_verified: bool
    verification_status: str
    evidence_relevance: float
    evidence_sufficiency: float
    specificity: float
    contradictory_penalty: float
    missing_info_penalty: float
    explanation: str
    ai_explanation: str | None
    human_override_score: float | None

    model_config = {"from_attributes": True}


class ClaimOut(BaseModel):
    id: int
    project_id: int
    text: str
    category: str
    source_page: int | None
    source_pages: list[int] | None
    claim_basis: str | None
    claim_kind: str | None
    ai_category: str | None
    human_category: str | None
    requires_review: bool
    evidence_items: list[EvidenceOut] = []
    assessment: AssessmentOut | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ClaimList(BaseModel):
    items: list[ClaimOut]
    total: int


class ClaimCategoryUpdate(BaseModel):
    category: str = Field(min_length=1, max_length=32)


class EvidenceRelevanceUpdate(BaseModel):
    is_relevant: bool
    notes: str | None = None


class ReviewFeedbackCreate(BaseModel):
    feedback_type: str
    original_value: str | None = None
    corrected_value: str | None = None
    notes: str | None = None
    evidence_id: int | None = None
