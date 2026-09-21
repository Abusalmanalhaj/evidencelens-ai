from app.workflows.analysis_graph import run_analysis
from app.schemas.analysis import AnalysisStart
import app.workflows.analysis_graph as analysis_graph

SAMPLE_PAGES = [
    {"page": 1, "text": "Our AI platform delivers 10x faster inference than competitors using proprietary algorithms."},
    {"page": 2, "text": "We hold 3 patents on our core technology. SOC2 Type II certified security infrastructure."},
]
SAMPLE_TEXT = "\n\n".join(f"[Page {p['page']}]\n{p['text']}" for p in SAMPLE_PAGES)


def test_run_analysis_heuristic():
    result = run_analysis(SAMPLE_TEXT, SAMPLE_PAGES)
    assert result.get("assessed_claims")
    assert len(result["assessed_claims"]) >= 1
    item = result["assessed_claims"][0]
    assert "claim" in item
    assert "evidence" in item
    assert "assessment" in item
    assert "support_score" in item["assessment"]
    assert "heuristic" in result.get("model_name", "").lower() or result.get("model_name")


def test_per_run_api_key_is_secret_and_reaches_llm(monkeypatch):
    payload = AnalysisStart(document_id=1, api_key="sk-test-key-with-enough-length")
    assert payload.api_key.get_secret_value() == "sk-test-key-with-enough-length"
    assert "sk-test-key-with-enough-length" not in repr(payload)

    received_keys = []

    def fake_call(prompt, api_key=None):
        received_keys.append(api_key)
        if "identify supporting evidence" in prompt:
            return '[{"text": "The product is explicitly described.", "evidence_type": "direct", "source_page": 1}]'
        return '[{"text": "The product is explicitly described.", "category": "product", "source_page": 1}]'

    monkeypatch.setattr(analysis_graph, "_call_llm", fake_call)
    result = run_analysis(
        "The product is explicitly described.",
        [{"page": 1, "text": "The product is explicitly described."}],
        api_key="sk-test-key-with-enough-length",
    )

    assert received_keys == ["sk-test-key-with-enough-length", "sk-test-key-with-enough-length"]
    assert result["llm_available"] is True
