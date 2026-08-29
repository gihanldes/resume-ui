"""Running analyses and reading history."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.config import settings
from app.deps import CurrentUser, DbSession
from app.models import Analysis, Resume
from app.ratelimit import analyze_user_limit
from app.schemas import AnalysisOut, AnalysisSummary, AnalyzeRequest, MessageOut
from app.services.ai_review import generate_ai_review
from app.services.analyzer import ENGINE_VERSION, enrich_priorities, review
from app.services.extraction import ExtractedDocument
from app.api.resumes import get_owned_resume

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analyses"])


def _document_from_resume(resume: Resume) -> ExtractedDocument:
    """Rebuild the extraction result from what was stored at upload time."""
    meta = resume.extraction_meta or {}
    return ExtractedDocument(
        text=resume.raw_text,
        page_count=resume.page_count,
        word_count=resume.word_count,
        char_count=meta.get("char_count", len(resume.raw_text)),
        has_tables=bool(meta.get("has_tables")),
        table_count=int(meta.get("table_count", 0)),
        has_images=bool(meta.get("has_images")),
        image_count=int(meta.get("image_count", 0)),
        multi_column_pages=int(meta.get("multi_column_pages", 0)),
        has_header_footer_text=bool(meta.get("has_header_footer_text")),
        is_scanned=bool(meta.get("is_scanned")),
        chars_per_page=list(meta.get("chars_per_page", [])),
        warnings=list(meta.get("warnings", [])),
    )


def _to_out(analysis: Analysis, *, resume_filename: str | None = None) -> AnalysisOut:
    out = AnalysisOut.model_validate(analysis)
    out.resume_filename = resume_filename
    snapshot = analysis.parsed_snapshot or {}
    out.band = snapshot.get("band")
    out.verdict = snapshot.get("verdict")
    out.priorities = snapshot.get("priorities", [])
    return out


@router.post(
    "/resumes/{resume_id}/analyze",
    response_model=AnalysisOut,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze a resume",
    dependencies=[Depends(analyze_user_limit)],
)
async def analyze_resume(
    resume_id: str,
    payload: AnalyzeRequest,
    user: CurrentUser,
    db: DbSession,
) -> AnalysisOut:
    resume = await get_owned_resume(resume_id, user.id, db)
    target_role = payload.target_role or user.target_role

    analysis = Analysis(
        resume_id=resume.id,
        user_id=user.id,
        status="pending",
        target_role=target_role,
        job_description=payload.job_description,
        engine_version=ENGINE_VERSION,
    )

    try:
        result = review(
            _document_from_resume(resume),
            target_role=target_role,
            job_description=payload.job_description,
        )
    except Exception as exc:
        logger.exception("Analysis failed for resume %s", resume.id)
        analysis.status = "failed"
        analysis.error = "The resume could not be analysed. Try re-uploading the file."
        db.add(analysis)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=analysis.error
        ) from exc

    analysis.status = "complete"
    analysis.overall_score = result.score.overall
    analysis.category_scores = result.score.as_dict()["categories"]
    analysis.findings = [f.as_dict() for f in result.findings]
    analysis.keyword_report = result.keyword_report
    analysis.duration_ms = result.duration_ms
    # Keep the headline verdict and priority list alongside the parse snapshot.
    priorities, projected = enrich_priorities(result.priorities, result.score.overall)
    analysis.parsed_snapshot = {
        **result.snapshot,
        "band": result.score.band,
        "verdict": result.score.verdict,
        "priorities": priorities,
        "projected_score": projected,
        "rule_errors": result.rule_errors,
    }

    if payload.include_ai and settings.ai_available:
        outcome = await generate_ai_review(
            resume.raw_text,
            result,
            target_role=target_role,
            job_description=payload.job_description,
        )
        analysis.ai_review = outcome.review
        analysis.ai_model = outcome.model
        analysis.ai_error = outcome.error
    elif payload.include_ai:
        analysis.ai_error = (
            "AI review is not configured on this server. Set OPENAI_API_KEY to enable it."
        )

    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return _to_out(analysis, resume_filename=resume.filename)


@router.get("/analyses", response_model=list[AnalysisSummary], summary="Analysis history")
async def list_analyses(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    resume_id: str | None = Query(default=None),
) -> list[AnalysisSummary]:
    stmt = (
        select(Analysis)
        .where(Analysis.user_id == user.id)
        .options(selectinload(Analysis.resume))
        .order_by(Analysis.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if resume_id:
        stmt = stmt.where(Analysis.resume_id == resume_id)

    analyses = (await db.scalars(stmt)).all()
    out: list[AnalysisSummary] = []
    for analysis in analyses:
        summary = AnalysisSummary.model_validate(analysis)
        summary.has_ai_review = analysis.ai_review is not None
        summary.resume_filename = analysis.resume.filename if analysis.resume else None
        out.append(summary)
    return out


@router.get("/analyses/{analysis_id}", response_model=AnalysisOut, summary="Analysis detail")
async def get_analysis(analysis_id: str, user: CurrentUser, db: DbSession) -> AnalysisOut:
    analysis = await db.scalar(
        select(Analysis)
        .where(Analysis.id == analysis_id)
        .options(selectinload(Analysis.resume))
    )
    if analysis is None or analysis.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
    return _to_out(analysis, resume_filename=analysis.resume.filename if analysis.resume else None)


@router.delete("/analyses/{analysis_id}", response_model=MessageOut, summary="Delete an analysis")
async def delete_analysis(analysis_id: str, user: CurrentUser, db: DbSession) -> MessageOut:
    analysis = await db.get(Analysis, analysis_id)
    if analysis is None or analysis.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
    await db.delete(analysis)
    await db.commit()
    return MessageOut(detail="Analysis deleted.")


@router.get("/stats", response_model=dict, summary="Dashboard statistics")
async def stats(user: CurrentUser, db: DbSession) -> dict:
    resume_count = await db.scalar(
        select(func.count(Resume.id)).where(Resume.user_id == user.id)
    ) or 0
    analysis_count = await db.scalar(
        select(func.count(Analysis.id)).where(
            Analysis.user_id == user.id, Analysis.status == "complete"
        )
    ) or 0
    best = await db.scalar(
        select(func.max(Analysis.overall_score)).where(
            Analysis.user_id == user.id, Analysis.status == "complete"
        )
    )
    recent = (
        await db.scalars(
            select(Analysis.overall_score)
            .where(Analysis.user_id == user.id, Analysis.status == "complete")
            .order_by(Analysis.created_at.desc())
            .limit(2)
        )
    ).all()
    latest = recent[0] if recent else None
    previous = recent[1] if len(recent) > 1 else None

    return {
        "resume_count": resume_count,
        "analysis_count": analysis_count,
        "best_score": round(best, 1) if best is not None else None,
        "latest_score": round(latest, 1) if latest is not None else None,
        "delta": round(latest - previous, 1) if latest is not None and previous is not None else None,
    }


def _analysis_summary(analysis: Analysis) -> dict:
    snapshot = analysis.parsed_snapshot or {}
    return {
        "id": analysis.id,
        "resume_id": analysis.resume_id,
        "resume_filename": analysis.resume.filename if analysis.resume else None,
        "overall_score": round(analysis.overall_score, 1),
        "band": snapshot.get("band"),
        "created_at": analysis.created_at.isoformat(),
        "target_role": analysis.target_role,
    }


@router.get("/analyses/{analysis_id}/compare", summary="Compare a review with an earlier one")
async def compare_analysis(
    analysis_id: str,
    user: CurrentUser,
    db: DbSession,
    with_id: str | None = Query(default=None, alias="with"),
) -> dict:
    """Score deltas per category, plus which findings were resolved or introduced.

    Without ?with=, the baseline is the most recent earlier review of the same
    resume — falling back to the user's most recent earlier review of any
    resume, because a revision is usually re-uploaded as a new file.
    """
    current = await db.scalar(
        select(Analysis).where(Analysis.id == analysis_id).options(selectinload(Analysis.resume))
    )
    if current is None or current.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
    if current.status != "complete":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only completed reviews can be compared."
        )

    if with_id is not None:
        if with_id == analysis_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Pick two different reviews to compare.",
            )
        baseline = await db.scalar(
            select(Analysis).where(Analysis.id == with_id).options(selectinload(Analysis.resume))
        )
        if baseline is None or baseline.user_id != user.id or baseline.status != "complete":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The review to compare against was not found.",
            )
    else:
        base_stmt = (
            select(Analysis)
            .where(
                Analysis.user_id == user.id,
                Analysis.status == "complete",
                Analysis.id != current.id,
                Analysis.created_at < current.created_at,
            )
            .options(selectinload(Analysis.resume))
            .order_by(Analysis.created_at.desc())
            .limit(1)
        )
        baseline = await db.scalar(base_stmt.where(Analysis.resume_id == current.resume_id))
        if baseline is None:
            baseline = await db.scalar(base_stmt)
        if baseline is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No earlier review to compare against.",
            )

    current_cats = {c["category"]: c for c in (current.category_scores or [])}
    baseline_cats = {c["category"]: c for c in (baseline.category_scores or [])}
    categories = []
    for key, cat in current_cats.items():
        base = baseline_cats.get(key)
        if base is None or not cat.get("applicable") or not base.get("applicable"):
            continue
        categories.append(
            {
                "category": key,
                "label": cat.get("label", key),
                "current": round(cat.get("score", 0.0), 1),
                "baseline": round(base.get("score", 0.0), 1),
                "delta": round(cat.get("score", 0.0) - base.get("score", 0.0), 1),
            }
        )

    def _refs(findings: list | None) -> dict[str, dict]:
        return {
            f["id"]: {"id": f["id"], "title": f["title"], "severity": f["severity"]}
            for f in (findings or [])
            if f.get("severity") != "positive"
        }

    current_findings = _refs(current.findings)
    baseline_findings = _refs(baseline.findings)

    return {
        "current": _analysis_summary(current),
        "baseline": _analysis_summary(baseline),
        "delta": {
            "overall": round(current.overall_score - baseline.overall_score, 1),
            "categories": categories,
            "resolved": [r for fid, r in baseline_findings.items() if fid not in current_findings],
            "introduced": [r for fid, r in current_findings.items() if fid not in baseline_findings],
            "still_open": len(set(current_findings) & set(baseline_findings)),
        },
    }


@router.post(
    "/analyses/{analysis_id}/ai",
    response_model=AnalysisOut,
    summary="Run or refresh the AI review for an existing analysis",
    dependencies=[Depends(analyze_user_limit)],
)
async def run_ai_review(analysis_id: str, user: CurrentUser, db: DbSession) -> AnalysisOut:
    """Adds the AI layer to an analysis that ran without it, or retries a failed one."""
    analysis = await db.scalar(
        select(Analysis).where(Analysis.id == analysis_id).options(selectinload(Analysis.resume))
    )
    if analysis is None or analysis.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
    if analysis.status != "complete" or analysis.resume is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only a completed analysis can take an AI review.",
        )
    if not settings.ai_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI review is not configured on this server. Set OPENAI_API_KEY to enable it.",
        )

    # The rule pass is ~1ms; re-running it beats storing a reconstruction.
    result = review(
        _document_from_resume(analysis.resume),
        target_role=analysis.target_role,
        job_description=analysis.job_description,
    )
    outcome = await generate_ai_review(
        analysis.resume.raw_text,
        result,
        target_role=analysis.target_role,
        job_description=analysis.job_description,
    )
    analysis.ai_review = outcome.review
    analysis.ai_model = outcome.model
    analysis.ai_error = outcome.error
    await db.commit()
    await db.refresh(analysis)
    return _to_out(analysis, resume_filename=analysis.resume.filename)
