import json
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.analysis_run import AnalysisRun, RunStatus
from app.models.assessment import Assessment
from app.models.claim import Claim
from app.models.document import Document, DocumentStatus
from app.models.evidence import Evidence
from app.models.project import AnalysisStatus, Project
from app.models.review_feedback import ReviewFeedback
from app.services.pdf_service import extract_text_from_pdf, pages_to_json
from app.workflows.analysis_graph import run_analysis

logger = logging.getLogger(__name__)


async def process_document_extraction(db: AsyncSession, document: Document) -> None:
    document.status = DocumentStatus.PROCESSING.value
    await db.flush()

    try:
        result = extract_text_from_pdf(document.file_path)
    except Exception as exc:
        logger.exception("Document extraction failed for %s", document.file_path)
        document.status = DocumentStatus.FAILED.value
        document.error_message = f"PDF extraction failed: {exc}"
        await db.flush()
        return

    if result.error and result.is_empty:
        document.status = DocumentStatus.FAILED.value
        document.error_message = result.error
        await db.flush()
        return

    document.extracted_text = result.full_text
    document.page_count = result.page_count
    document.status = DocumentStatus.EXTRACTED.value
    document.error_message = result.error
    await db.flush()


async def run_project_analysis(
    db: AsyncSession,
    project_id: int,
    document_id: int,
    api_key: str | None = None,
) -> AnalysisRun:
    project = await db.get(Project, project_id)
    if not project:
        raise ValueError("Project not found")

    doc_result = await db.execute(
        select(Document)
        .where(
            Document.id == document_id,
            Document.project_id == project_id,
            Document.status == DocumentStatus.EXTRACTED.value,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document or not document.extracted_text:
        raise ValueError("No extracted document available for analysis")

    project.analysis_status = AnalysisStatus.ANALYZING.value
    project.error_message = None

    run = AnalysisRun(
        project_id=project_id,
        status=RunStatus.RUNNING.value,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()

    try:
        pages = json.loads(pages_to_json_from_text(document.extracted_text))
        if not pages:
            pages = [{"page": 1, "text": document.extracted_text}]

        result = run_analysis(document.extracted_text, pages, api_key=api_key)
        assessed = result.get("assessed_claims", [])

        claim_ids = select(Claim.id).where(Claim.project_id == project_id)
        # Bulk deletes bypass ORM cascades, so remove dependent rows explicitly
        # before replacing the project's claims on a repeated analysis.
        await db.execute(delete(ReviewFeedback).where(ReviewFeedback.claim_id.in_(claim_ids)))
        await db.execute(delete(Evidence).where(Evidence.claim_id.in_(claim_ids)))
        await db.execute(delete(Assessment).where(Assessment.claim_id.in_(claim_ids)))
        await db.execute(delete(Claim).where(Claim.project_id == project_id))

        for item in assessed:
            claim_data = item["claim"]
            claim = Claim(
                project_id=project_id,
                analysis_run_id=run.id,
                text=claim_data["text"],
                category=claim_data.get("category", "other"),
                ai_category=claim_data.get("category", "other"),
                source_page=claim_data.get("source_page"),
                source_pages=claim_data.get("source_pages") or [claim_data.get("source_page")],
                claim_basis=claim_data.get("claim_basis"),
                claim_kind=claim_data.get("claim_kind"),
                requires_review=item["assessment"]["support_level"] in ("weak", "missing"),
            )
            db.add(claim)
            await db.flush()

            for ev in item["evidence"]:
                db.add(Evidence(
                    claim_id=claim.id,
                    text=ev["text"],
                    evidence_type=ev.get("evidence_type", "indirect"),
                    source_page=ev.get("source_page"),
                ))

            assessment_data = item["assessment"]
            db.add(Assessment(
                claim_id=claim.id,
                support_score=assessment_data["support_score"],
                support_level=assessment_data["support_level"],
                evidence_strength=assessment_data["evidence_strength"],
                source_traceability=assessment_data["source_traceability"],
                evidence_pages=assessment_data["evidence_pages"],
                source_page_verified=assessment_data["source_page_verified"],
                verification_status=assessment_data["verification_status"],
                specificity=assessment_data["specificity"],
                contradictory_penalty=assessment_data["contradictory_penalty"],
                missing_info_penalty=assessment_data["missing_info_penalty"],
                evidence_relevance=assessment_data["evidence_relevance"],
                evidence_sufficiency=assessment_data["evidence_sufficiency"],
                explanation=assessment_data["explanation"],
                ai_explanation=assessment_data["explanation"],
            ))

        run.status = RunStatus.COMPLETED.value
        run.claims_extracted = len(assessed)
        run.model_name = result.get("model_name")
        run.prompt_version = result.get("prompt_version")
        run.completed_at = datetime.now(timezone.utc)
        project.analysis_status = AnalysisStatus.COMPLETED.value

    except Exception as exc:
        logger.exception("Analysis failed for project %s", project_id)
        await db.rollback()
        project = await db.get(Project, project_id)
        if project:
            project.analysis_status = AnalysisStatus.FAILED.value
            project.error_message = str(exc)
        run = AnalysisRun(
            project_id=project_id,
            status=RunStatus.FAILED.value,
            error_message=str(exc),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.flush()

    return run


def pages_to_json_from_text(full_text: str) -> str:
    import re

    pages = []
    parts = re.split(r"\[Page (\d+)\]", full_text)
    if len(parts) > 1:
        for i in range(1, len(parts), 2):
            page_num = int(parts[i])
            text = parts[i + 1].strip() if i + 1 < len(parts) else ""
            pages.append({"page": page_num, "text": text})
    return json.dumps(pages)


async def get_claims_for_project(db: AsyncSession, project_id: int, skip: int = 0, limit: int = 50):
    count_result = await db.execute(
        select(Claim).where(Claim.project_id == project_id)
    )
    total = len(count_result.scalars().all())

    result = await db.execute(
        select(Claim)
        .where(Claim.project_id == project_id)
        .options(
            selectinload(Claim.evidence_items),
            selectinload(Claim.assessment),
        )
        .order_by(Claim.id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all(), total
