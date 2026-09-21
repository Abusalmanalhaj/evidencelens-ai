from pathlib import Path

import fitz
import pytest
from httpx import AsyncClient


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "deck.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Our platform delivers 10x faster AI inference with patented technology.")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.mark.asyncio
async def test_upload_extracts_pdf(client: AsyncClient, auth_headers: dict, sample_pdf: Path):
    project = await client.post(
        "/api/v1/projects",
        json={"name": "Upload Test"},
        headers=auth_headers,
    )
    project_id = project.json()["id"]

    with open(sample_pdf, "rb") as f:
        response = await client.post(
            f"/api/v1/projects/{project_id}/documents",
            headers=auth_headers,
            files={"file": ("deck.pdf", f, "application/pdf")},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "extracted"
    assert body["page_count"] == 1

    docs = await client.get(f"/api/v1/projects/{project_id}/documents", headers=auth_headers)
    assert docs.json()[0]["status"] == "extracted"
