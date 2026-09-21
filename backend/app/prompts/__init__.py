PROMPT_VERSION = "v1.1"

CLAIM_EXTRACTION_PROMPT = """You are a technical due diligence analyst. Extract specific technical and business claims from the pitch deck text below.

Rules:
- Only extract claims explicitly stated or clearly implied in the source text.
- Do NOT invent claims not present in the deck.
- Categorize each claim as one of: product, technology, scalability, performance, ip, security, market, business, other.
- Include the source page number for each claim.
- Return valid JSON array with objects: {{"text": "...", "category": "...", "source_page": N}}

Pitch deck text:
{text}
"""

EVIDENCE_MAPPING_PROMPT = """For the claim below, identify supporting evidence from the pitch deck.

Claim: {claim_text}
Category: {category}
Source page: {source_page}

Pitch deck text:
{text}

Rules:
- Only cite text present in the deck. Never invent external sources.
- Classify each evidence item as: direct, indirect, missing, or contradictory.
- Include source_page for each evidence item.
- If insufficient evidence exists, include a missing-type item explaining the gap.

Return valid JSON array: {{"text": "...", "evidence_type": "...", "source_page": N}}
"""
