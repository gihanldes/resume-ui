"""Resume upload, listing and deletion."""

from __future__ import annotations

from pathlib import PurePath

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete, func, select

from app.config import settings
from app.deps import CurrentUser, DbSession
from app.models import Analysis, Resume
from app.ratelimit import upload_user_limit
from app.schemas import MessageOut, ResumeDetail, ResumeOut, ResumeRename
from app.services.extraction import ExtractionError, extract_document, text_hash

router = APIRouter(prefix="/resumes", tags=["resumes"])

_MAX_MB = settings.max_upload_bytes / (1024 * 1024)


async def _decorate(db: DbSession, resumes: list[Resume]) -> list[ResumeOut]:
    """Attach analysis counts and the latest score without an N+1 query."""
    if not resumes:
        return []
    ids = [r.id for r in resumes]
    rows = (
        await db.execute(
            select(Analysis.resume_id, func.count(Analysis.id), func.max(Analysis.created_at))
            .where(Analysis.resume_id.in_(ids))
            .group_by(Analysis.resume_id)
        )
    ).all()
    counts = {resume_id: count for resume_id, count, _ in rows}

    latest_scores: dict[str, float] = {}
    latest = (
        await db.execute(
            select(Analysis.resume_id, Analysis.overall_score, Analysis.created_at)
            .where(Analysis.resume_id.in_(ids), Analysis.status == "complete")
            .order_by(Analysis.resume_id, Analysis.created_at.desc())
        )
    ).all()
    for resume_id, score, _ in latest:
        latest_scores.setdefault(resume_id, score)

    out: list[ResumeOut] = []
    for resume in resumes:
        item = ResumeOut.model_validate(resume)
        item.analysis_count = counts.get(resume.id, 0)
        item.latest_score = latest_scores.get(resume.id)
        out.append(item)
    return out


@router.post(
    "",
    response_model=ResumeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a resume",
    dependencies=[Depends(upload_user_limit)],
)
async def upload_resume(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(..., description="PDF, DOCX or TXT resume"),
) -> ResumeOut:
    filename = PurePath(file.filename or "resume").name
    suffix = PurePath(filename).suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"'{suffix or 'unknown'}' files aren't supported. Upload one of: "
                f"{', '.join(sorted(settings.allowed_extensions))}."
            ),
        )

    # Read at most one byte over the limit so an oversized body can't balloon memory.
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is larger than the {_MAX_MB:.0f} MB limit.",
        )

    count = await db.scalar(select(func.count(Resume.id)).where(Resume.user_id == user.id)) or 0
    if count >= settings.max_resumes_per_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"You've reached the limit of {settings.max_resumes_per_user} stored "
                "resumes. Delete an older one to upload another."
            ),
        )

    try:
        document = extract_document(filename, data)
    except ExtractionError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    resume = Resume(
        user_id=user.id,
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        file_size=len(data),
        text_hash=text_hash(document.text),
        raw_text=document.text,
        page_count=document.page_count,
        word_count=document.word_count,
        extraction_meta=document.meta(),
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)
    return ResumeOut.model_validate(resume)


@router.get("", response_model=list[ResumeOut], summary="List your resumes")
async def list_resumes(user: CurrentUser, db: DbSession) -> list[ResumeOut]:
    resumes = (
        await db.scalars(
            select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc())
        )
    ).all()
    return await _decorate(db, list(resumes))


async def get_owned_resume(resume_id: str, user_id: str, db: DbSession) -> Resume:
    resume = await db.get(Resume, resume_id)
    if resume is None or resume.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found.")
    return resume


@router.get("/{resume_id}", response_model=ResumeDetail, summary="Resume detail")
async def get_resume(resume_id: str, user: CurrentUser, db: DbSession) -> ResumeDetail:
    resume = await get_owned_resume(resume_id, user.id, db)
    decorated = (await _decorate(db, [resume]))[0]
    return ResumeDetail(
        **decorated.model_dump(),
        raw_text=resume.raw_text,
        extraction_meta=resume.extraction_meta,
    )


@router.patch("/{resume_id}", response_model=ResumeOut, summary="Rename a resume")
async def rename_resume(
    resume_id: str, payload: ResumeRename, user: CurrentUser, db: DbSession
) -> ResumeOut:
    resume = await get_owned_resume(resume_id, user.id, db)
    resume.filename = payload.filename
    await db.commit()
    await db.refresh(resume)
    decorated = (await _decorate(db, [resume]))[0]
    return decorated


@router.delete("/{resume_id}", response_model=MessageOut, summary="Delete a resume")
async def delete_resume(resume_id: str, user: CurrentUser, db: DbSession) -> MessageOut:
    resume = await get_owned_resume(resume_id, user.id, db)
    await db.delete(resume)
    await db.commit()
    return MessageOut(detail=f"Deleted '{resume.filename}' and its analyses.")
