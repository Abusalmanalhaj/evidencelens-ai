from app.services.assessment_service import assess_claim, explain_evidence_relation
from app.workflows.heuristic_extractor import (
    classify_claim_basis,
    deduplicate_claims,
    extract_claims_heuristic,
    map_evidence_heuristic,
    normalize_category,
)


def test_ecoglide_material_claim_coverage_and_pages():
    pages = [
        {"page": 1, "text": "EcoGlide offers eco-friendly immersive experiences."},
        {"page": 2, "text": "Tourist cities face environmental degradation and animal welfare issues. Today's tourists seek eco-friendly experiences."},
        {"page": 3, "text": "Zero-emission electric carriages seat up to four passengers. Book via mobile app or website."},
        {"page": 4, "text": "Vienna attracts over 7 million tourists annually. Austrian cities tighten carriage regulations."},
        {"page": 5, "text": "Initial plans for launching in Vienna. Expand to Salzburg, Innsbruck, and Hallstatt."},
        {"page": 6, "text": "Ride fares are a revenue stream. Custom touring packages are a revenue stream. Advertising is a revenue stream. Corporate private events are a revenue stream."},
        {"page": 7, "text": "Collaborating with local tourism operators, hotels, and attractions for cross-promotion."},
        {"page": 8, "text": "We aim to minimize our environmental footprint."},
        {"page": 9, "text": "EcoGlide has proven market demand and an expansion roadmap."},
        {"page": 10, "text": "Get in Touch Email contact@example.com"},
    ]
    deck_text = "\n\n".join(f"[Page {p['page']}]\n{p['text']}" for p in pages)

    claims = extract_claims_heuristic(deck_text, pages)
    text = " ".join(claim["text"].lower() for claim in claims)

    assert len(claims) >= 7
    for phrase in ("environmental", "zero-emission", "four passengers", "mobile app", "7 million", "regulations", "revenue"):
        assert phrase in text
    assert {claim["source_page"] for claim in claims} >= {2, 3, 4, 5, 6, 7, 8, 9}
    assert all(claim["source_page"] != 10 for claim in claims)
    assert any("tourists seek" in claim["text"].lower() and claim["source_page"] == 2 for claim in claims)
    assert any("launching in vienna" in claim["text"].lower() and claim["source_page"] == 5 for claim in claims)
    assert any("custom touring packages" in claim["text"].lower() and claim["source_page"] == 6 for claim in claims)


def test_evidence_keeps_exact_page_excerpt():
    pages = [
        {"page": 2, "text": "Tourists seek eco-friendly experiences."},
        {"page": 6, "text": "Ride fares, custom tours, advertising, and private events."},
    ]
    evidence = map_evidence_heuristic(
        {"text": "Ride fares and custom tours", "source_page": 6}, pages
    )
    assert evidence[0]["source_page"] == 6
    assert "Ride fares" in evidence[0]["text"]


def test_traceability_requires_verified_source_page_and_text_match():
    evidence = [{
        "text": "Vienna attracts over 7 million tourists annually.",
        "evidence_type": "direct",
        "source_page": 4,
    }]
    verified = assess_claim("Vienna attracts over 7 million tourists", evidence, 4, True)
    mismatched = assess_claim("Vienna attracts over 7 million tourists", evidence, 1, False)

    assert verified["source_traceability"] == 1.0
    assert mismatched["source_traceability"] < verified["source_traceability"]


def test_repeated_or_related_text_does_not_equal_sufficient_evidence():
    repeated = assess_claim(
        "Proven market demand in Vienna",
        [{"text": "Proven market demand in Vienna", "evidence_type": "repeated", "source_page": 9}],
        4,
        True,
    )
    related = assess_claim(
        "Proven market demand in Vienna",
        [{"text": "Vienna attracts over 7 million tourists annually.", "evidence_type": "indirect", "source_page": 4}],
        4,
        True,
    )
    assert repeated["evidence_sufficiency"] == 0.0
    assert repeated["evidence_relevance"] == 0.0
    assert related["evidence_sufficiency"] < 1.0
    assert "not independent" in explain_evidence_relation("Proven market demand in Vienna", {"text": "x", "evidence_type": "repeated"})


def test_claim_basis_distinguishes_plans_revenue_and_external_facts():
    assert classify_claim_basis("Initial plans for launching in Vienna") == "stated_plan"
    assert classify_claim_basis("Revenue streams include ride fares and advertising") == "proposed_revenue_model"
    assert classify_claim_basis("Vienna attracts over 7 million tourists annually") == "external_fact_claim"
    assert classify_claim_basis("Received formal recognition from the Government of Canada (ISED)") == "external_fact_claim"


def test_key_takeaway_recap_merges_without_becoming_independent_evidence():
    claims = deduplicate_claims([
        {
            "text": "Zero-emission electric carriages seat up to four passengers.",
            "category": "product", "source_page": 3, "source_pages": [3],
            "claim_basis": "deck_assertion", "claim_kind": "product_description",
            "duplicate_pages": [], "duplicate_excerpts": [],
        },
        {
            "text": "Key Takeaways 1 Zero-Emission Carriages Electric, quiet, and comfortable seating up to four passengers.",
            "category": "product", "source_page": 9, "source_pages": [9],
            "claim_basis": "deck_assertion", "claim_kind": "product_description",
            "duplicate_pages": [], "duplicate_excerpts": [],
        },
    ])
    assert len(claims) == 1
    assert claims[0]["source_pages"] == [3, 9]
    assert claims[0]["duplicate_excerpts"][0]["page"] == 9


def test_ecoglide_categories_use_controlled_taxonomy():
    assert normalize_category(None, "Ride Fares Book via app and website") == "business"
    assert normalize_category(None, "Event Participation Engaging with local events") == "business"
    assert normalize_category(None, "Custom Touring Packages for each city") == "business"
    assert normalize_category(None, "Zero-emission electric carriages") == "product"
    assert normalize_category("ip", "Event Participation Engaging with local events") == "business"
    assert normalize_category("technology", "Ride Fares Book via app and website") == "business"


def test_positioning_statement_is_not_a_diligence_claim():
    pages = [{"page": 1, "text": "EcoGlide: Sustainable Touring Reimagined."}]
    claims = extract_claims_heuristic("[Page 1]\n" + pages[0]["text"], pages)
    assert claims == []


def test_external_fact_support_is_capped_without_independent_verification():
    assessment = assess_claim(
        "Received formal recognition from the Government of Canada (ISED)",
        [{
            "text": "Received formal recognition from the Government of Canada (ISED) for the EcoGlide concept.",
            "evidence_type": "direct",
            "source_page": 5,
        }],
        5,
        True,
        claim_basis="external_fact_claim",
    )
    assert assessment["verification_status"] == "deck_only"
    assert assessment["support_score"] <= 0.35
    assert "independent verification" in assessment["explanation"]


def test_weakly_related_evidence_does_not_inflate_revenue_support():
    assessment = assess_claim(
        "Ride fares are priced by distance and time",
        [{
            "text": "Book via app, website, or hail on the street.",
            "evidence_type": "indirect",
            "source_page": 6,
        }],
        6,
        True,
        claim_basis="proposed_revenue_model",
    )
    assert assessment["evidence_strength"] == 0.0
    assert assessment["evidence_sufficiency"] == 0.0
