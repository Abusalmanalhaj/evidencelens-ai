from app.models.assessment import SupportLevel
from app.services.assessment_service import assess_claim, compute_support_level


def test_compute_support_level():
    assert compute_support_level(0.8) == SupportLevel.STRONG.value
    assert compute_support_level(0.6) == SupportLevel.PARTIAL.value
    assert compute_support_level(0.3) == SupportLevel.WEAK.value
    assert compute_support_level(0.1) == SupportLevel.MISSING.value


def test_assess_claim_no_evidence():
    result = assess_claim("Our platform is 10x faster", [], source_page=1)
    assert result["support_score"] == 0.0
    assert result["support_level"] == SupportLevel.MISSING.value
    assert "No supporting evidence" in result["explanation"]


def test_assess_claim_with_direct_evidence():
    evidence = [
        {"text": "Benchmark shows 10x improvement", "evidence_type": "direct", "source_page": 3},
        {"text": "Uses optimized inference engine", "evidence_type": "indirect", "source_page": 3},
    ]
    result = assess_claim("Our platform delivers 10x faster AI inference", evidence, source_page=3)
    assert result["support_score"] > 0.3
    assert result["evidence_strength"] > 0
    assert "not whether the claim is objectively verified" in result["explanation"]
