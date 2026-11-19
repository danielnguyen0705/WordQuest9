from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from wordquest_shared.database import get_db
from wordquest_shared.models import Unit, UnitProgress, User
from wordquest_shared.schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserProfileResponse,
)
from wordquest_shared.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
    xp_progress_in_level,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Identity & Profile"])


def serialize_user(user: User) -> UserProfileResponse:
    level, xp_in_lvl, xp_next = xp_progress_in_level(user.xp)
    return UserProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        avatar=user.avatar,
        xp=user.xp,
        level=level,
        xp_in_level=xp_in_lvl,
        xp_for_next_level=xp_next,
        streak_days=user.streak_days,
        longest_streak=user.longest_streak,
        current_combo=user.current_combo,
        best_combo=user.best_combo,
        created_at=user.created_at,
    )


def ensure_initial_unit_progress(db: Session, user_id: str) -> None:
    units = db.execute(select(Unit).order_by(Unit.unit_number)).scalars().all()
    if not units:
        return
    existing_ids = set(
        db.execute(select(UnitProgress.unit_id).where(UnitProgress.user_id == user_id)).scalars().all()
    )
    for u in units:
        if u.id not in existing_ids:
            db.add(
                UnitProgress(
                    user_id=user_id,
                    unit_id=u.id,
                    is_unlocked=(u.unit_number == 1),
                )
            )
    db.flush()


def touch_daily_streak(user: User) -> None:
    today = date.today()
    if user.last_active_date is None:
        user.streak_days = 1
    elif user.last_active_date == today:
        pass
    elif user.last_active_date == today - timedelta(days=1):
        user.streak_days += 1
    else:
        user.streak_days = 1
    if user.streak_days > user.longest_streak:
        user.longest_streak = user.streak_days
    user.last_active_date = today


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.execute(
        select(User).where(
            or_(
                User.username == payload.username.strip().lower(),
                User.email == payload.email.strip().lower(),
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tên đăng nhập hoặc email đã được sử dụng.",
        )

    user = User(
        username=payload.username.strip().lower(),
        email=payload.email.strip().lower(),
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        avatar=payload.avatar,
        streak_days=1,
        longest_streak=1,
        last_active_date=date.today(),
    )
    db.add(user)
    db.flush()
    ensure_initial_unit_progress(db, user.id)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.username)
    return AuthResponse(access_token=token, user=serialize_user(user))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    identifier = payload.username.strip().lower()
    user = db.execute(
        select(User).where(or_(User.username == identifier, User.email == identifier))
    ).scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tên đăng nhập hoặc mật khẩu.",
        )

    touch_daily_streak(user)
    ensure_initial_unit_progress(db, user.id)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.username)
    return AuthResponse(access_token=token, user=serialize_user(user))


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    # Stateless JWT logout acknowledgment; frontend clears stored token
    return {"status": "logged_out", "username": current_user.username}


@router.get("/me", response_model=UserProfileResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return serialize_user(current_user)


@router.patch("/me", response_model=UserProfileResponse)
def update_profile(
    display_name: str | None = None,
    avatar: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if display_name and len(display_name.strip()) >= 2:
        current_user.display_name = display_name.strip()[:80]
    if avatar and len(avatar.strip()) >= 2:
        current_user.avatar = avatar.strip()[:50]
    db.commit()
    db.refresh(current_user)
    return serialize_user(current_user)
