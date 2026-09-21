from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_owned_project
from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.claim import Claim
from app.models.evidence import Evidence
from app.models.review_feedback import ReviewFeedback
from app.models.user import User
from app.schemas.claim import (
    ClaimCategoryUpdate,
    ClaimList,
    ClaimOut,
    EvidenceRelevanceUpdate,
    ReviewFeedbackCreate,
)
from app.services.analysis_service import get_claims_for_project

router = APIRouter(prefix="/projects/{project_id}/claims", tags=["claims"])


@router.get("", response_model=ClaimList)
async def list_claims(
    project_id: int,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_project(db, project_id, user)
    items, total = await get_claims_for_project(db, project_id, skip, limit)
    return ClaimList(items=items, total=total)


@router.get("/{claim_id}", response_model=ClaimOut)
async def get_claim(
    project_id: int,
    claim_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_project(db, project_id, user)
    result = await db.execute(
        select(Claim)
        .where(Claim.id == claim_id, Claim.project_id == project_id)
        .options(selectinload(Claim.evidence_items), selectinload(Claim.assessment))
    )
    claim = result.scalar_one_or_none()
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    return claim


@router.patch("/{claim_id}/category", response_model=ClaimOut)
async def update_claim_category(
    project_id: int,
    claim_id: int,
    payload: ClaimCategoryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_project(db, project_id, user)
    claim = await db.get(Claim, claim_id)
    if not claim or claim.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    feedback = ReviewFeedback(
        claim_id=claim_id,
        user_id=user.id,
        feedback_type="category_correction",
        original_value=claim.category,
        corrected_value=payload.category,
    )
    db.add(feedback)
    claim.human_category = payload.category
    claim.category = payload.category
    await db.flush()

    result = await db.execute(
        select(Claim)
        .where(Claim.id == claim_id)
        .options(selectinload(Claim.evidence_items), selectinload(Claim.assessment))
    )
    return result.scalar_one()


@router.patch("/{claim_id}/evidence/{evidence_id}", response_model=ClaimOut)
async def update_evidence_relevance(
    project_id: int,
    claim_id: int,
    evidence_id: int,
    payload: EvidenceRelevanceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_project(db, project_id, user)
    evidence = await db.get(Evidence, evidence_id)
    if not evidence or evidence.claim_id != claim_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    feedback = ReviewFeedback(
        claim_id=claim_id,
        user_id=user.id,
        evidence_id=evidence_id,
        feedback_type="evidence_relevance",
        original_value=str(evidence.is_relevant),
        corrected_value=str(payload.is_relevant),
        notes=payload.notes,
    )
    db.add(feedback)
    evidence.human_marked_relevant = payload.is_relevant
    evidence.is_relevant = payload.is_relevant
    await db.flush()

    result = await db.execute(
        select(Claim)
        .where(Claim.id == claim_id)
        .options(selectinload(Claim.evidence_items), selectinload(Claim.assessment))
    )
    return result.scalar_one()


@router.post("/{claim_id}/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    project_id: int,
    claim_id: int,
    payload: ReviewFeedbackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned_project(db, project_id, user)
    claim = await db.get(Claim, claim_id)
    if not claim or claim.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")

    feedback = ReviewFeedback(
        claim_id=claim_id,
        user_id=user.id,
        evidence_id=payload.evidence_id,
        feedback_type=payload.feedback_type,
        original_value=payload.original_value,
        corrected_value=payload.corrected_value,
        notes=payload.notes,
    )
    db.add(feedback)
    await db.flush()
    return {"id": feedback.id, "message": "Feedback recorded"}
