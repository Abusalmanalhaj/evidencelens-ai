"""LangGraph orchestration for claim extraction, evidence mapping, and assessment."""

import json
import logging
import re
from typing import Any

from langgraph.graph import END, StateGraph

from app.config import get_settings
from app.prompts import CLAIM_EXTRACTION_PROMPT, EVIDENCE_MAPPING_PROMPT, PROMPT_VERSION
from app.services.assessment_service import assess_claim
from app.workflows.heuristic_extractor import (
    classify_claim_basis,
    classify_claim_kind,
    deduplicate_claims,
    extract_claims_heuristic,
    map_evidence_heuristic,
    normalize_category,
    resolve_source_page,
)
from app.workflows.state import AnalysisState, AssessedClaim

logger = logging.getLogger(__name__)
settings = get_settings()


def _parse_json_array(content: str) -> list[dict]:
    content = content.strip()
    match = re.search(r"\[[\s\S]*\]", content)
    if match:
        return json.loads(match.group())
    return json.loads(content)


def _is_llm_unavailable_error(exc: Exception) -> bool:
    name = exc.__class__.__name__
    if name in ("RateLimitError", "AuthenticationError", "PermissionDeniedError", "APIStatusError"):
        return True
    msg = str(exc).lower()
    return any(
        token in msg
        for token in ("429", "quota", "insufficient_quota", "credit_balance", "invalid_api_key", "billing")
    )


def _llm_fallback_reason(exc: Exception) -> str:
    if _is_llm_unavailable_error(exc):
        return "OpenAI unavailable (quota/billing) — using heuristic analysis"
    return f"LLM error ({exc.__class__.__name__}) — using heuristic analysis"


def _call_llm(prompt: str, api_key: str | None = None) -> str:
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=api_key or settings.openai_api_key,
        temperature=0,
        max_retries=0,  # fail fast; avoid long retry loops on 429/quota errors
    )
    response = llm.invoke(prompt)
    return str(response.content)


def extract_claims_node(state: AnalysisState) -> dict[str, Any]:
    pages = state.get("pages", [])
    deck_text = state["deck_text"]
    llm_available = state.get("llm_available", settings.llm_enabled)
    api_key = state.get("llm_api_key") or settings.openai_api_key
    fallback_reason = state.get("llm_fallback_reason")

    if llm_available:
        try:
            prompt = CLAIM_EXTRACTION_PROMPT.format(text=deck_text[:12000])
            raw = _call_llm(prompt, api_key)
            claims = _parse_json_array(raw)
            claims = [
                {
                    "text": c["text"],
                    "category": normalize_category(c.get("category"), c["text"]),
                    "source_page": resolve_source_page(c["text"], c.get("source_page"), pages),
                    "source_pages": [resolve_source_page(c["text"], c.get("source_page"), pages)],
                    "claim_basis": classify_claim_basis(c["text"]),
                    "claim_kind": classify_claim_kind(c["text"]),
                    "duplicate_pages": [],
                    "duplicate_excerpts": [],
                }
                for c in claims
                if c.get("text")
            ]
            claims = [
                claim for claim in deduplicate_claims(claims)
                if claim["claim_kind"] not in ("promotional", "positioning")
            ]
            model_name = settings.openai_model
        except Exception as exc:
            reason = _llm_fallback_reason(exc)
            logger.warning("LLM claim extraction failed: %s. Falling back to heuristic.", reason)
            claims = extract_claims_heuristic(deck_text, pages)
            model_name = f"heuristic-fallback"
            llm_available = False
            fallback_reason = reason
    else:
        claims = extract_claims_heuristic(deck_text, pages)
        model_name = "heuristic (no API key)" if not settings.llm_enabled else "heuristic-fallback"
        if not settings.llm_enabled:
            fallback_reason = "No OpenAI API key configured"

    return {
        "claims": claims,
        "model_name": model_name,
        "prompt_version": PROMPT_VERSION,
        "llm_available": llm_available,
        "llm_fallback_reason": fallback_reason,
    }


def map_evidence_node(state: AnalysisState) -> dict[str, Any]:
    pages = state.get("pages", [])
    deck_text = state["deck_text"]
    assessed: list[AssessedClaim] = []
    llm_available = state.get("llm_available", settings.llm_enabled)
    api_key = state.get("llm_api_key") or settings.openai_api_key
    fallback_reason = state.get("llm_fallback_reason")
    model_name = state.get("model_name", "")

    for claim in state.get("claims", []):
        if llm_available:
            try:
                prompt = EVIDENCE_MAPPING_PROMPT.format(
                    claim_text=claim["text"],
                    category=claim.get("category", "other"),
                    source_page=claim.get("source_page"),
                    text=deck_text[:12000],
                )
                raw = _call_llm(prompt, api_key)
                evidence = _parse_json_array(raw)
                evidence = [
                    {
                        "text": e["text"],
                        "evidence_type": e.get("evidence_type", "indirect"),
                        "source_page": resolve_source_page(e["text"], e.get("source_page"), pages),
                    }
                    for e in evidence
                    if e.get("text")
                ]
            except Exception as exc:
                reason = _llm_fallback_reason(exc)
                logger.warning("LLM evidence mapping failed: %s. Using heuristic for remaining claims.", reason)
                llm_available = False
                fallback_reason = reason
                if model_name == settings.openai_model:
                    model_name = "heuristic-fallback"
                evidence = map_evidence_heuristic(claim, pages)
        else:
            evidence = map_evidence_heuristic(claim, pages)

        source_page = claim.get("source_page")
        source_page_verified = resolve_source_page(claim["text"], source_page, pages) == source_page
        assessment = assess_claim(
            claim["text"],
            evidence,
            source_page,
            source_page_verified=source_page_verified,
            claim_basis=claim.get("claim_basis"),
        )
        assessed.append({"claim": claim, "evidence": evidence, "assessment": assessment})

    return {
        "assessed_claims": assessed,
        "llm_available": llm_available,
        "llm_fallback_reason": fallback_reason,
        "model_name": model_name,
    }


def build_analysis_graph() -> StateGraph:
    graph = StateGraph(AnalysisState)
    graph.add_node("extract_claims", extract_claims_node)
    graph.add_node("map_evidence", map_evidence_node)
    graph.set_entry_point("extract_claims")
    graph.add_edge("extract_claims", "map_evidence")
    graph.add_edge("map_evidence", END)
    return graph


def run_analysis(deck_text: str, pages: list[dict], api_key: str | None = None) -> dict[str, Any]:
    graph = build_analysis_graph().compile()
    initial: AnalysisState = {
        "deck_text": deck_text,
        "pages": pages,
        "claims": [],
        "assessed_claims": [],
        "model_name": "",
        "prompt_version": PROMPT_VERSION,
        "error": None,
        "llm_available": bool(api_key or settings.openai_api_key.strip()),
        "llm_api_key": api_key,
        "llm_fallback_reason": None,
    }
    result = graph.invoke(initial)
    return dict(result)
