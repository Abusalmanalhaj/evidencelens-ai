from typing import TypedDict


class ClaimItem(TypedDict):
    text: str
    category: str
    source_page: int | None
    source_pages: list[int]
    claim_basis: str
    claim_kind: str
    duplicate_pages: list[int]
    duplicate_excerpts: list[dict]


class EvidenceItem(TypedDict):
    text: str
    evidence_type: str
    source_page: int | None


class AssessedClaim(TypedDict):
    claim: ClaimItem
    evidence: list[EvidenceItem]
    assessment: dict


class AnalysisState(TypedDict):
    deck_text: str
    pages: list[dict]
    claims: list[ClaimItem]
    assessed_claims: list[AssessedClaim]
    model_name: str
    prompt_version: str
    error: str | None
    llm_available: bool
    llm_api_key: str | None
    llm_fallback_reason: str | None
