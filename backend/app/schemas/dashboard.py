from pydantic import BaseModel


class CategoryBreakdown(BaseModel):
    category: str
    count: int


class SupportBreakdown(BaseModel):
    strong: int
    partial: int
    weak: int
    missing: int


class DashboardMetrics(BaseModel):
    total_claims: int
    support_breakdown: SupportBreakdown
    evidence_coverage: float
    category_breakdown: list[CategoryBreakdown]
    requires_review_count: int
    analysis_status: str
    last_run_status: str | None
