import io
from xml.sax.saxutils import escape
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.claim import Claim
from app.models.project import Project
from app.services.assessment_service import explain_evidence_relation
from app.workflows.heuristic_extractor import classify_claim_basis


async def generate_report_pdf(db: AsyncSession, project_id: int) -> bytes:
    project = await db.get(Project, project_id)
    if not project:
        raise ValueError("Project not found")

    result = await db.execute(
        select(Claim)
        .where(Claim.project_id == project_id)
        .options(selectinload(Claim.evidence_items), selectinload(Claim.assessment))
        .order_by(Claim.id)
    )
    claims = result.scalars().all()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=18, spaceAfter=12)
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    small = ParagraphStyle("Small", parent=body, fontSize=9, textColor=colors.grey)

    story = []
    story.append(Paragraph("EvidenceLens AI — Due Diligence Report", title_style))
    story.append(Paragraph(f"<b>Startup:</b> {project.name}", body))
    if project.sector:
        story.append(Paragraph(f"<b>Sector:</b> {project.sector}", body))
    if project.stage:
        story.append(Paragraph(f"<b>Stage:</b> {project.stage}", body))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", body))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Methodology", h2))
    story.append(Paragraph(
        "This report analyzes deduplicated technical and business claims from the uploaded pitch deck. "
        "Support scores reflect how well the deck provides evidence for each claim — not whether "
        "claims are objectively verified. Page location, relevance, and sufficiency are separate measures; "
        "repeated deck recaps do not count as independent verification. Plans, proposed revenue, and external "
        "fact claims require validation beyond the deck. The support formula is 0.35 evidence strength + "
        "0.20 relevance + 0.20 traceability + 0.10 sufficiency + 0.15 specificity, less penalties.",
        body,
    ))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(f"Claims Summary ({len(claims)} total)", h2))
    if not claims:
        story.append(Paragraph("No claims have been extracted yet.", body))
    else:
        for i, claim in enumerate(claims, 1):
            assessment = claim.assessment
            level = assessment.support_level if assessment else "unknown"
            score = f"{assessment.support_score:.2f}" if assessment else "N/A"
            basis = classify_claim_basis(claim.text)
            basis_label = {
                "stated_plan": "Stated plan; not proof of readiness or traction",
                "proposed_revenue_model": "Proposed revenue model; not demonstrated revenue",
                "external_fact_claim": "External fact claim; requires verification",
                "deck_assertion": "Deck assertion; not independently verified",
            }[basis]
            story.append(Paragraph(f"<b>{i}. [{escape(claim.category.upper())}] {escape(claim.text[:300])}</b>", body))
            claim_pages = ", ".join(str(page) for page in (claim.source_pages or [claim.source_page] if claim.source_page else [])) or "N/A"
            evidence_pages = ", ".join(str(page) for page in (assessment.evidence_pages if assessment else [])) or "N/A"
            verification = assessment.verification_status.replace("_", " ") if assessment else "unknown"
            story.append(Paragraph(
                f"Support: {level} ({score}) | Original claim page: {claim.source_page or 'N/A'} | "
                f"Claim occurrences: {claim_pages} | Evidence pages: {evidence_pages} | Verification: {verification}",
                small,
            ))
            story.append(Paragraph(f"Basis: {escape(basis_label)}", small))
            if assessment:
                story.append(Paragraph(escape(assessment.explanation[:600]), small))
            if False:
                story.append(Paragraph(
                    f"  • [{ev.evidence_type}] p.{ev.source_page}: {ev.text[:150]}...",
                    small,
                ))
            for ev in claim.evidence_items[:3]:
                evidence_relation = explain_evidence_relation(
                    claim.text,
                    {"text": ev.text, "evidence_type": ev.evidence_type},
                )
                story.append(Paragraph(
                    f"[{escape(ev.evidence_type)}] p.{ev.source_page or 'N/A'}: "
                    f"&quot;{escape(ev.text[:500])}&quot;",
                    small,
                ))
                story.append(Paragraph(
                    f"Evidence assessment: {escape(evidence_relation)}",
                    small,
                ))
            story.append(Spacer(1, 0.1 * inch))

    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("Limitations", h2))
    story.append(Paragraph(
        "Analysis is limited to content present in the uploaded pitch deck. "
        "No external verification was performed. Scores indicate evidence support, not factual truth.",
        body,
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
