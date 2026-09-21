from pathlib import Path

import fitz
import pytest

from app.services.pdf_service import extract_text_from_pdf


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Our platform delivers 10x faster AI inference.")
    page2 = doc.new_page()
    page2.insert_text((72, 72), "We have patented our proprietary algorithm.")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_extract_text_from_pdf(sample_pdf: Path):
    result = extract_text_from_pdf(sample_pdf)
    assert not result.is_empty
    assert result.page_count == 2
    assert "10x faster" in result.full_text
    assert len(result.pages) == 2


def test_missing_file():
    result = extract_text_from_pdf("/nonexistent/file.pdf")
    assert result.is_empty
    assert result.error is not None
