from app.workflows.heuristic_extractor import extract_claims_heuristic, map_evidence_heuristic

SAMPLE_PAGES = [
    {"page": 1, "text": "Our AI platform delivers 10x faster inference than competitors."},
    {"page": 2, "text": "We have 3 patents on our proprietary algorithm. SOC2 compliant security."},
]

SAMPLE_TEXT = "\n".join(p["text"] for p in SAMPLE_PAGES)


def test_extract_claims_heuristic():
    claims = extract_claims_heuristic(SAMPLE_TEXT, SAMPLE_PAGES)
    assert len(claims) >= 1
    assert all("text" in c and "category" in c for c in claims)
    assert claims[0]["source_page"] == 1


def test_extract_claims_uses_actual_page_for_deck_markers():
    pages = [
        {"page": 1, "text": "Company overview and team."},
        {"page": 5, "text": "Our platform delivers 10x faster tours for customers."},
    ]
    deck_text = "\n\n".join(f"[Page {p['page']}]\n{p['text']}" for p in pages)
    claims = extract_claims_heuristic(deck_text, pages)
    assert claims[0]["source_page"] == 5


def test_map_evidence_heuristic():
    claim = {"text": "Our AI platform delivers 10x faster inference", "source_page": 1}
    evidence = map_evidence_heuristic(claim, SAMPLE_PAGES)
    assert len(evidence) >= 1
    assert all("evidence_type" in e for e in evidence)
