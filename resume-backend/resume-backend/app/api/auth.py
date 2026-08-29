"""Registration, login, refresh-token rotation and profile management."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.config import settings
from app.deps import CurrentUser, DbSession
from app.ratelimit import auth_ip_limit
from app.models import RefreshToken, User
from app.schemas import (
    AccountDelete,
    MessageOut,
    PasswordChange,
    RefreshRequest,
    TokenPair,
    UserLogin,
    UserOut,
    UserRegister,
    UserUpdate,
)
from app.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    needs_rehash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_INVALID_CREDENTIALS = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect email or password",
    headers={"WWW-Authenticate": "Bearer"},
)


async def _issue_tokens(db: DbSession, user: User) -> TokenPair:
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh.token),
            expires_at=refresh.expires_at,
        )
    )
    await db.commit()
    return TokenPair(
        access_token=access.token,
        refresh_token=refresh.token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post(
    "/register",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
    dependencies=[Depends(auth_ip_limit)],
)
async def register(payload: UserRegister, db: DbSession) -> TokenPair:
    email = payload.email.lower().strip()
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        target_role=payload.target_role,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()
    return await _issue_tokens(db, user)


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Exchange credentials for tokens",
    dependencies=[Depends(auth_ip_limit)],
)
async def login(payload: UserLogin, db: DbSession) -> TokenPair:
    email = payload.email.lower().strip()
    user = await db.scalar(select(User).where(User.email == email))

    # Always run a verification so timing doesn't reveal whether the email exists.
    stored_hash = user.password_hash if user else hash_password("dummy-password-for-timing")
    if not verify_password(payload.password, stored_hash) or user is None:
        raise _INVALID_CREDENTIALS
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="This account is disabled."
        )

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    user.last_login_at = datetime.now(timezone.utc)
    return await _issue_tokens(db, user)


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Rotate a refresh token",
    dependencies=[Depends(auth_ip_limit)],
)
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    try:
        claims = decode_token(payload.refresh_token, "refresh")
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    digest = hash_token(payload.refresh_token)
    record = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == digest))
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is not recognised."
        )
    if not record.is_active:
        # A revoked token being replayed means the token may have leaked; drop
        # every session for this user rather than just refusing this one.
        await _revoke_all(db, record.user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This refresh token is no longer valid. Please sign in again.",
        )

    user = await db.get(User, claims["sub"])
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Account is unavailable."
        )

    record.revoked_at = datetime.now(timezone.utc)  # single-use rotation
    return await _issue_tokens(db, user)


async def _revoke_all(db: DbSession, user_id: str) -> int:
    tokens = (
        await db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
            )
        )
    ).all()
    now = datetime.now(timezone.utc)
    for token in tokens:
        token.revoked_at = now
    await db.commit()
    return len(tokens)


@router.post("/logout", response_model=MessageOut, summary="Revoke all refresh tokens")
async def logout(user: CurrentUser, db: DbSession) -> MessageOut:
    count = await _revoke_all(db, user.id)
    return MessageOut(detail=f"Signed out. {count} session(s) revoked.")


@router.post(
    "/logout-others",
    response_model=MessageOut,
    summary="Sign out every other device",
)
async def logout_others(
    payload: RefreshRequest, user: CurrentUser, db: DbSession
) -> MessageOut:
    """Revokes every active session except the one presenting this refresh token."""
    digest = hash_token(payload.refresh_token)
    current = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == digest,
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This session could not be identified. Sign in again first.",
        )
    others = (
        await db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.id != current.id,
            )
        )
    ).all()
    now = datetime.now(timezone.utc)
    for token in others:
        token.revoked_at = now
    await db.commit()
    return MessageOut(detail=f"Signed out {len(others)} other session(s).")


@router.get("/me", response_model=UserOut, summary="Current profile")
async def me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserOut, summary="Update profile")
async def update_me(payload: UserUpdate, user: CurrentUser, db: DbSession) -> User:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(user, field, value.strip() if isinstance(value, str) else value)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/change-password", response_model=MessageOut, summary="Change password")
async def change_password(
    payload: PasswordChange, user: CurrentUser, db: DbSession
) -> MessageOut:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect."
        )
    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    count = await _revoke_all(db, user.id)
    return MessageOut(detail=f"Password updated. {count} other session(s) signed out.")


@router.delete("/me", response_model=MessageOut, summary="Delete your account and all data")
async def delete_me(payload: AccountDelete, user: CurrentUser, db: DbSession) -> MessageOut:
    """Deletes the user plus every resume, analysis and session they own."""
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect."
        )
    email = user.email
    await db.delete(user)
    await db.commit()
    return MessageOut(detail=f"The account {email} and all its data have been deleted.")
