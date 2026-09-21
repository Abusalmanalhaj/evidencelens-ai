import json
import logging
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class PageText:
    page_number: int
    text: str


@dataclass
class ExtractionResult:
    pages: list[PageText]
    page_count: int
    full_text: str
    is_empty: bool
    error: str | None = None


def extract_text_from_pdf(file_path: str | Path) -> ExtractionResult:
    path = Path(file_path)
    if not path.exists():
        return ExtractionResult(pages=[], page_count=0, full_text="", is_empty=True, error="File not found")

    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        logger.exception("Failed to open PDF: %s", path)
        return ExtractionResult(pages=[], page_count=0, full_text="", is_empty=True, error=str(exc))

    pages: list[PageText] = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        pages.append(PageText(page_number=i, text=text))

    doc.close()
    full_text = "\n\n".join(
        f"[Page {p.page_number}]\n{p.text}" for p in pages if p.text
    )
    total_chars = sum(len(p.text) for p in pages)
    is_empty = total_chars < 50

    if is_empty:
        return ExtractionResult(
            pages=pages,
            page_count=len(pages),
            full_text=full_text,
            is_empty=True,
            error="PDF appears scanned or contains insufficient extractable text.",
        )

    return ExtractionResult(
        pages=pages,
        page_count=len(pages),
        full_text=full_text,
        is_empty=False,
    )


def pages_to_json(pages: list[PageText]) -> str:
    return json.dumps([{"page": p.page_number, "text": p.text} for p in pages])
