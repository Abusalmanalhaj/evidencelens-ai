from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_run import AnalysisRun
from app.models.assessment import Assessment, SupportLevel
from app.models.claim import Claim
from app.models.project import Project
from app.schemas.dashboard import CategoryBreakdown, DashboardMetrics, SupportBreakdown


async def get_dashboard_metrics(db: AsyncSession, project_id: int) -> DashboardMetrics:
    project = await db.get(Project, project_id)
    if not project:
        raise ValueError("Project not found")

    total_result = await db.execute(
        select(func.count()).select_from(Claim).where(Claim.project_id == project_id)
    )
    total_claims = total_result.scalar() or 0

    support_counts = {level.value: 0 for level in SupportLevel}
    if total_claims > 0:
        level_result = await db.execute(
            select(Assessment.support_level, func.count())
            .join(Claim, Claim.id == Assessment.claim_id)
            .where(Claim.project_id == project_id)
            .group_by(Assessment.support_level)
        )
        for level, count in level_result.all():
            support_counts[level] = count

    category_result = await db.execute(
        select(Claim.category, func.count())
        .where(Claim.project_id == project_id)
        .group_by(Claim.category)
    )
    category_breakdown = [
        CategoryBreakdown(category=cat, count=cnt) for cat, cnt in category_result.all()
    ]

    review_result = await db.execute(
        select(func.count()).select_from(Claim).where(
            Claim.project_id == project_id, Claim.requires_review.is_(True)
        )
    )
    requires_review = review_result.scalar() or 0

    strong = support_counts.get(SupportLevel.STRONG.value, 0)
    partial = support_counts.get(SupportLevel.PARTIAL.value, 0)
    weak = support_counts.get(SupportLevel.WEAK.value, 0)
    missing = support_counts.get(SupportLevel.MISSING.value, 0)

    covered = strong + partial
    evidence_coverage = (covered / total_claims * 100) if total_claims else 0.0

    run_result = await db.execute(
        select(AnalysisRun)
        .where(AnalysisRun.project_id == project_id)
        .order_by(AnalysisRun.created_at.desc())
        .limit(1)
    )
    last_run = run_result.scalar_one_or_none()

    return DashboardMetrics(
        total_claims=total_claims,
        support_breakdown=SupportBreakdown(
            strong=strong, partial=partial, weak=weak, missing=missing
        ),
        evidence_coverage=round(evidence_coverage, 1),
        category_breakdown=category_breakdown,
        requires_review_count=requires_review,
        analysis_status=project.analysis_status,
        last_run_status=last_run.status if last_run else None,
    )
