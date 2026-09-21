from datetime import datetime

from app.schemas.claim import ClaimOut, EvidenceOut


def test_evidence_response_does_not_require_claim_fields():
    evidence = EvidenceOut.model_validate(
        {
            "id": 1,
            "text": "Supporting excerpt",
            "evidence_type": "direct",
            "source_page": 2,
            "is_relevant": True,
            "human_marked_relevant": None,
            "created_at": datetime.now(),
        }
    )

    assert evidence.source_page == 2


def test_claim_response_owns_claim_metadata():
    claim = ClaimOut.model_validate(
        {
            "id": 1,
            "project_id": 1,
            "text": "A stated plan",
            "category": "business",
            "source_page": 5,
            "source_pages": [5, 9],
            "claim_basis": "stated_plan",
            "claim_kind": "plan",
            "ai_category": "business",
            "human_category": None,
            "requires_review": False,
            "evidence_items": [],
            "assessment": None,
            "created_at": datetime.now(),
        }
    )

    assert claim.source_pages == [5, 9]
    assert claim.claim_basis == "stated_plan"
