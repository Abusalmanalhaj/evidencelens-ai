"""Transparent claim assessment scoring framework."""

import re

from app.models.assessment import SupportLevel
from app.models.evidence import EvidenceType


def _evidence_text_match(claim_text: str, evidence_text: str) -> float:
    claim_words = set(re.findall(r"\w{4,}", claim_text.lower()))
    evidence_words = set(re.findall(r"\w{4,}", evidence_text.lower()))
    if not claim_words or not evidence_words:
        return 0.0
    return len(claim_words & evidence_words) / len(claim_words)


def explain_evidence_relation(claim_text: str, evidence: dict) -> str:
    evidence_type = evidence.get("evidence_type")
    if evidence_type == EvidenceType.REPEATED.value:
        return "Repeats a claim elsewhere in the deck; not independent verification."
    if evidence_type == EvidenceType.MISSING.value:
        return "No supporting excerpt was found for this claim."
    match = _evidence_text_match(claim_text, evidence.get("text", ""))
    if evidence_type == EvidenceType.CONTRADICTORY.value:
        return "Conflicts with the claim and reduces support."
    if evidence_type == EvidenceType.DIRECT.value and match >= 0.5:
        return "Direct excerpt with substantial wording overlap; supports the stated claim within the deck."
    if match >= 0.25:
        return "Related excerpt with partial wording overlap; relevant context but not sufficient proof by itself."
    return "Weakly related excerpt; does not independently support the claim."


def compute_support_level(score: float) -> str:
    if score >= 0.75:
        return SupportLevel.STRONG.value
    if score >= 0.5:
        return SupportLevel.PARTIAL.value
    if score >= 0.25:
        return SupportLevel.WEAK.value
    return SupportLevel.MISSING.value


def assess_claim(
    claim_text: str,
    evidence_items: list[dict],
    source_page: int | None,
    source_page_verified: bool = True,
    claim_basis: str | None = None,
) -> dict:
    """Score deck support while keeping location, relevance, and sufficiency separate.

    Support = 0.35 qualifying evidence strength + 0.20 evidence relevance
    + 0.20 source traceability + 0.10 evidence sufficiency
    + 0.15 claim specificity - contradiction/missing penalties.
    Repeated recap excerpts and weakly related excerpts do not count as support.
    External fact claims are capped at 0.35 until independently verified.
    """
    if not evidence_items:
        return {
            "support_score": 0.0,
            "support_level": SupportLevel.MISSING.value,
            "evidence_strength": 0.0,
            "source_traceability": 0.3 if source_page and source_page_verified else 0.0,
            "evidence_pages": [],
            "source_page_verified": bool(source_page and source_page_verified),
            "verification_status": "deck_only",
            "evidence_relevance": 0.0,
            "evidence_sufficiency": 0.0,
            "specificity": _specificity_score(claim_text),
            "contradictory_penalty": 0.0,
            "missing_info_penalty": 1.0,
            "explanation": (
                "No supporting evidence was found in the pitch deck for this claim. "
                "This score reflects evidence support only, not whether the claim is objectively true."
            ),
        }

    direct = sum(1 for e in evidence_items if e["evidence_type"] == EvidenceType.DIRECT.value)
    indirect = sum(1 for e in evidence_items if e["evidence_type"] == EvidenceType.INDIRECT.value)
    repeated = sum(1 for e in evidence_items if e["evidence_type"] == EvidenceType.REPEATED.value)
    contradictory = sum(1 for e in evidence_items if e["evidence_type"] == EvidenceType.CONTRADICTORY.value)
    missing = sum(1 for e in evidence_items if e["evidence_type"] == EvidenceType.MISSING.value)
    total = len(evidence_items)

    pages = {e.get("source_page") for e in evidence_items if e.get("source_page")}
    traceable_evidence = [
        e for e in evidence_items
        if e.get("source_page")
        and e.get("evidence_type") not in (EvidenceType.MISSING.value, EvidenceType.REPEATED.value)
    ]
    page_coverage = len(traceable_evidence) / total
    text_matches = [_evidence_text_match(claim_text, e.get("text", "")) for e in traceable_evidence]
    qualified_evidence = [
        (e, match)
        for e, match in zip(traceable_evidence, text_matches)
        if (
            (e.get("evidence_type") == EvidenceType.DIRECT.value)
            or (e.get("evidence_type") == EvidenceType.INDIRECT.value and match >= 0.5)
        )
    ]
    qualified_direct = sum(1 for e, _ in qualified_evidence if e["evidence_type"] == EvidenceType.DIRECT.value)
    qualified_indirect = sum(1 for e, _ in qualified_evidence if e["evidence_type"] == EvidenceType.INDIRECT.value)
    evidence_strength = min(1.0, (qualified_direct + qualified_indirect * 0.25) / max(len(traceable_evidence), 1))
    text_match = max(
        (_evidence_text_match(claim_text, e.get("text", "")) for e in traceable_evidence),
        default=0.0,
    )
    evidence_relevance = sum(match for _, match in qualified_evidence) / max(total, 1)
    evidence_sufficiency = min(1.0, (qualified_direct + qualified_indirect * 0.25) / 2.0)
    source_traceability = (
        0.35 * float(bool(source_page and source_page_verified))
        + 0.35 * page_coverage
        + 0.30 * min(1.0, text_match)
    )
    specificity = _specificity_score(claim_text)
    contradictory_penalty = min(0.5, contradictory * 0.25)
    missing_info_penalty = min(0.5, missing * 0.2)

    raw_score = (
        evidence_strength * 0.35
        + evidence_relevance * 0.20
        + source_traceability * 0.20
        + evidence_sufficiency * 0.10
        + specificity * 0.15
        - contradictory_penalty
        - missing_info_penalty
    )
    support_score = max(0.0, min(1.0, raw_score))
    verification_status = "deck_only"
    if claim_basis == "external_fact_claim":
        # A deck assertion cannot receive a strong evidence score without external proof.
        support_score = min(support_score, 0.35)
    support_level = compute_support_level(support_score)

    explanation = (
        f"Support score {support_score:.2f} ({support_level}). "
        f"Evidence strength: {evidence_strength:.2f} ({qualified_direct} qualifying direct, {qualified_indirect} qualifying indirect). "
        f"Evidence relevance: {evidence_relevance:.2f}; sufficiency: {evidence_sufficiency:.2f}. "
        f"Source traceability: {source_traceability:.2f} (evidence pages: {sorted(pages) if pages else 'none'}). "
        f"Claim specificity: {specificity:.2f}. "
    )
    if claim_basis == "stated_plan":
        explanation += "This is a stated plan and does not demonstrate operational readiness or traction. "
    elif claim_basis == "proposed_revenue_model":
        explanation += "This is a proposed revenue model and does not demonstrate realized revenue. "
    elif claim_basis == "external_fact_claim":
        explanation += "This is only an explicit deck assertion; it requires independent verification outside the pitch deck. "
    if contradictory_penalty > 0:
        explanation += f"Contradictory evidence penalty: -{contradictory_penalty:.2f}. "
    if missing_info_penalty > 0:
        explanation += f"Missing information penalty: -{missing_info_penalty:.2f}. "
    if repeated > 0:
        explanation += f"{repeated} repeated deck recap(s) were excluded as independent evidence. "
    explanation += (
        "This assessment evaluates how well the deck supports the claim, "
        "not whether the claim is objectively verified."
    )

    return {
        "support_score": round(support_score, 3),
        "support_level": support_level,
        "evidence_strength": round(evidence_strength, 3),
        "source_traceability": round(source_traceability, 3),
        "evidence_pages": sorted(pages),
        "source_page_verified": bool(source_page and source_page_verified),
        "verification_status": verification_status,
        "evidence_relevance": round(evidence_relevance, 3),
        "evidence_sufficiency": round(evidence_sufficiency, 3),
        "specificity": round(specificity, 3),
        "contradictory_penalty": round(contradictory_penalty, 3),
        "missing_info_penalty": round(missing_info_penalty, 3),
        "explanation": explanation,
    }


def _specificity_score(claim_text: str) -> float:
    text = claim_text.lower()
    score = 0.3
    if any(c.isdigit() for c in text):
        score += 0.2
    specific_words = ["%", "x faster", "patent", "ms", "gb", "users", "revenue", "api", "latency"]
    if any(w in text for w in specific_words):
        score += 0.2
    if len(claim_text.split()) >= 8:
        score += 0.15
    return min(1.0, score)
