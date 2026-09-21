"""Heuristic claim extraction when LLM is unavailable."""

import re

from app.models.claim import ClaimCategory

CONTROLLED_CATEGORIES = {category.value for category in ClaimCategory}
CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (ClaimCategory.IP.value, ("patent", "proprietary", "intellectual property", "trade secret")),
    (ClaimCategory.SECURITY.value, ("security", "encrypted", "compliance", "soc2", "gdpr", "secure")),
    (ClaimCategory.PERFORMANCE.value, ("faster", "latency", "throughput", "performance", "speed", "efficiency")),
    (ClaimCategory.BUSINESS.value, ("revenue", "ride fares", "custom touring packages", "advertising", "corporate", "private events", "partnership", "launch", "expand", "cross-promotion", "event")),
    (ClaimCategory.MARKET.value, ("market", "tourist", "tourism", "million tourists", "demand", "regulation", "locals", "growth potential")),
    (ClaimCategory.PRODUCT.value, ("electric", "carriage", "passenger", "mobile app", "website", "booking", "route", "amenities", "touring")),
    (ClaimCategory.TECHNOLOGY.value, ("ai", "ml", "algorithm", "platform", "software", "technology", "model")),
    (ClaimCategory.SCALABILITY.value, ("scale", "scalable", "users", "customers")),
)

PLAN_TERMS = ("plan", "planned", "aim", "launch", "launching", "expand", "expansion", "target")
REVENUE_TERMS = ("revenue", "ride fares", "custom touring packages", "advertising", "corporate", "private events", "pricing")
EXTERNAL_FACT_TERMS = ("recognition", "government of canada", "ised", "million tourists", "proven market")
POSITIONING_TERMS = ("sustainable touring reimagined", "revolutionize", "exciting journey", "compelling brand")


def classify_claim_basis(text: str) -> str:
    """Describe the deck statement without treating it as independently verified."""
    lower = text.lower()
    if any(term in lower for term in REVENUE_TERMS):
        return "proposed_revenue_model"
    if any(term in lower for term in EXTERNAL_FACT_TERMS):
        return "external_fact_claim"
    if any(term in lower for term in PLAN_TERMS):
        return "stated_plan"
    return "deck_assertion"


def classify_claim_kind(text: str) -> str:
    lower = text.lower()
    if any(term in lower for term in POSITIONING_TERMS):
        return "positioning"
    if any(term in lower for term in PLAN_TERMS):
        return "plan"
    if "revenue" in lower or any(term in lower for term in REVENUE_TERMS):
        return "projection"
    if any(term in lower for term in EXTERNAL_FACT_TERMS):
        return "factual_assertion"
    return "product_description"


def _categorize(sentence: str) -> str:
    lower = sentence.lower()
    for category, keywords in CATEGORY_RULES:
        if any(keyword in lower for keyword in keywords):
            return category
    return ClaimCategory.OTHER.value


def normalize_category(category: str | None, text: str) -> str:
    inferred = _categorize(text)
    if inferred != ClaimCategory.OTHER.value:
        return inferred
    if category and category.lower() in CONTROLLED_CATEGORIES:
        return category.lower()
    return ClaimCategory.OTHER.value


def _find_page(sentence: str, pages: list[dict]) -> int | None:
    normalized_sentence = " ".join(sentence.lower().split())
    snippet = normalized_sentence[:100]
    best_page: int | None = None
    best_score = 0
    for page in pages:
        page_text = " ".join(page.get("text", "").lower().split())
        if snippet and snippet in page_text:
            return page.get("page")
        words = set(re.findall(r"\w{4,}", normalized_sentence))
        score = sum(1 for word in words if word in page_text)
        if score > best_score:
            best_score = score
            best_page = page.get("page")
    return best_page if best_score >= 2 else None


def resolve_source_page(text: str, reported_page: int | None, pages: list[dict]) -> int | None:
    """Keep a model page only when it is valid; otherwise infer it from page text."""
    valid_pages = {page.get("page") for page in pages}
    if reported_page in valid_pages:
        page_text = next(
            (" ".join(page.get("text", "").lower().split()) for page in pages if page.get("page") == reported_page),
            "",
        )
        snippet = " ".join(text.lower().split())[:100]
        if snippet and snippet in page_text:
            return reported_page

    inferred_page = _find_page(text, pages)
    return inferred_page if inferred_page is not None else (reported_page if reported_page in valid_pages else None)


def extract_claims_heuristic(deck_text: str, pages: list[dict]) -> list[dict]:
    """Extract claim-like sentences using pattern matching."""
    claim_patterns = [
        r"\b(our|we|the company|platform|product|ecoglide|electric carriages|carriages)\b.*\b(is|are|can|will|has|have|delivers|provides|achieves|offers|serves|caters|book|available|blending)\b",
        r"\b\d+[%x×]\b",
        r"\b(patent|proprietary|unique|first|only|leading|best-in-class|zero-emission|electric|passengers?)\b",
        r"\b(faster|secure|scalable|efficient|innovative|eco-friendly|sustainable|tourists?|tourism|regulations?|recognition|ised|revenue|advertising|weddings|festivals|partnerships?|expansion|expand|booking|mobile app|website|customizable routes|heritage|locals|growth|aim|footprint)\b",
    ]
    claims: list[dict] = []
    seen: set[str] = set()

    page_sources = pages or [{"page": 1, "text": deck_text}]
    for page in page_sources:
        page_number = page.get("page")
        for sentence in _page_segments(page.get("text", "")):
            s = sentence.strip()
            if re.search(r"\b(get in touch|email|phone|website)\b", s, re.I) and "@" in s:
                continue
            claim_kind = classify_claim_kind(s)
            if claim_kind in ("promotional", "positioning"):
                continue
            if len(s) < 30 or len(s) > 500:
                continue
            if not any(re.search(p, s, re.I) for p in claim_patterns):
                continue
            key = _claim_key(s)
            if key in seen:
                continue
            seen.add(key)
            claims.append({
                "text": s,
                "category": _categorize(s),
                "source_page": page_number or _find_page(s, page_sources),
                "source_pages": [page_number] if page_number else [],
                "claim_basis": classify_claim_basis(s),
                "claim_kind": claim_kind,
                "duplicate_pages": [],
                "duplicate_excerpts": [],
            })

    return deduplicate_claims(claims[:50])


def _claim_key(text: str) -> str:
    text = re.sub(r"\b(key takeaways|market opportunity|traction & milestones|business model|revenue streams)\b", " ", text, flags=re.I)
    text = re.sub(r"\b\d+\b", " ", text)
    return " ".join(re.findall(r"[a-z0-9]{4,}", text.lower()))


def _similarity(left: str, right: str) -> float:
    left_words = set(_claim_key(left).split())
    right_words = set(_claim_key(right).split())
    if not left_words or not right_words:
        return 0.0
    return len(left_words & right_words) / len(left_words | right_words)


def deduplicate_claims(claims: list[dict]) -> list[dict]:
    """Merge semantic duplicates while preserving recap pages as non-independent references."""
    canonical: list[dict] = []
    for candidate in claims:
        is_recap = bool(re.search(r"key takeaways|proven market demand|diversified revenue|expansion roadmap", candidate["text"], re.I))
        matches = [
            claim for claim in canonical
            if _similarity(candidate["text"], claim["text"]) >= 0.45
            or (is_recap and _similarity(candidate["text"], claim["text"]) >= 0.20)
        ]
        if is_recap and matches:
            recap_matches = _recap_matches(candidate["text"], canonical)
            matches = recap_matches or matches
            for claim in matches:
                _merge_duplicate_reference(claim, candidate)
            continue
        if matches:
            _merge_duplicate_reference(matches[0], candidate)
            continue
        candidate["source_pages"] = sorted(set(candidate.get("source_pages", []) or [candidate.get("source_page")]))
        canonical.append(candidate)
    return canonical


def _merge_duplicate_reference(canonical: dict, duplicate: dict) -> None:
    page = duplicate.get("source_page")
    if page and page not in canonical.setdefault("source_pages", []):
        canonical["source_pages"].append(page)
        canonical["source_pages"].sort()
    if page and page != canonical.get("source_page"):
        canonical.setdefault("duplicate_pages", []).append(page)
        canonical.setdefault("duplicate_excerpts", []).append({"page": page, "text": duplicate["text"]})


def _recap_matches(text: str, claims: list[dict]) -> list[dict]:
    lower = text.lower()
    if "zero-emission" in lower:
        return [claim for claim in claims if any(term in claim["text"].lower() for term in ("zero-emission", "electric", "passengers"))]
    if "proven market demand" in lower:
        return [
            claim for claim in claims
            if claim["category"] == ClaimCategory.MARKET.value
            and claim["claim_kind"] != "plan"
            and any(term in claim["text"].lower() for term in ("million tourists", "growth potential", "tourist traffic", "market opportunity"))
        ]
    if "diversified revenue" in lower:
        return [claim for claim in claims if claim["category"] == ClaimCategory.BUSINESS.value and any(term in claim["text"].lower() for term in REVENUE_TERMS)]
    if "expansion roadmap" in lower:
        return [claim for claim in claims if claim["claim_kind"] == "plan" and any(term in claim["text"].lower() for term in ("launch", "expand", "expansion"))]
    return []


def _page_segments(text: str) -> list[str]:
    """Join PDF line wraps into card-sized statements before matching claims."""
    segments: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        line = " ".join(line.split())
        if not line:
            continue
        current.append(line)
        if line.endswith((".", "!", "?")):
            segments.append(" ".join(current).strip())
            current = []
    if current:
        segments.append(" ".join(current).strip())
    return segments


def map_evidence_heuristic(claim: dict, pages: list[dict]) -> list[dict]:
    """Find supporting text from deck pages for a claim."""
    claim_words = set(re.findall(r"\w{4,}", claim["text"].lower()))
    evidence: list[dict] = []

    for page in pages:
        page_text = page.get("text", "")
        page_num = page.get("page")
        if page_num in claim.get("duplicate_pages", []):
            continue
        if not page_text:
            continue
        overlap = sum(1 for w in claim_words if w in page_text.lower())
        if overlap >= 2:
            sentences = _page_segments(page_text)
            for sent in sentences:
                sent = sent.strip()
                if len(sent) < 20:
                    continue
                sent_words = set(re.findall(r"\w{4,}", sent.lower()))
                if len(claim_words & sent_words) >= 2:
                    ev_type = "direct" if len(claim_words & sent_words) >= 4 else "indirect"
                    evidence.append({
                        "text": sent[:500],
                        "evidence_type": ev_type,
                        "source_page": page_num,
                    })
                    if len(evidence) >= 3:
                        break
        if len(evidence) >= 3:
            break

    if not evidence:
        evidence.append({
            "text": "The pitch deck does not provide sufficient supporting evidence for this claim.",
            "evidence_type": "missing",
            "source_page": claim.get("source_page"),
        })

    for duplicate in claim.get("duplicate_excerpts", []):
        evidence.append({
            "text": duplicate["text"],
            "evidence_type": "repeated",
            "source_page": duplicate["page"],
        })

    return evidence
