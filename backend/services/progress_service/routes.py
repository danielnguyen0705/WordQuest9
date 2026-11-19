from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from wordquest_shared.config import settings
from wordquest_shared.database import get_db
from wordquest_shared.models import (
    QuestionBank,
    QuizSession,
    StudentMistake,
    StudentVocabProgress,
    Unit,
    UnitProgress,
    User,
    Vocabulary,
)
from wordquest_shared.schemas import (
    DashboardOverviewResponse,
    MistakeItemResponse,
    UnitProgressResponse,
    UserProfileResponse,
)
from wordquest_shared.security import get_current_user, xp_progress_in_level

router = APIRouter(prefix="/api/v1/progress", tags=["Progress & Mistake Vault"])


def _serialize_user(user: User) -> UserProfileResponse:
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


@router.get("/dashboard", response_model=DashboardOverviewResponse)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    units = db.execute(select(Unit).order_by(Unit.unit_number)).scalars().all()
    up_rows = (
        db.execute(select(UnitProgress).where(UnitProgress.user_id == current_user.id))
        .scalars()
        .all()
    )
    up_map = {up.unit_id: up for up in up_rows}

    vocab_counts = dict(
        db.execute(select(Vocabulary.unit_id, func.count(Vocabulary.id)).group_by(Vocabulary.unit_id)).all()
    )
    q_counts = dict(
        db.execute(select(QuestionBank.unit_id, func.count(QuestionBank.id)).group_by(QuestionBank.unit_id)).all()
    )

    mastered_by_unit = dict(
        db.execute(
            select(Vocabulary.unit_id, func.count(StudentVocabProgress.id))
            .join(Vocabulary, Vocabulary.id == StudentVocabProgress.vocabulary_id)
            .where(
                StudentVocabProgress.user_id == current_user.id,
                StudentVocabProgress.mastery_level >= 2,
            )
            .group_by(Vocabulary.unit_id)
        ).all()
    )

    unit_responses: list[UnitProgressResponse] = []
    for u in units:
        up = up_map.get(u.id)
        is_unlocked = up.is_unlocked if up else (u.unit_number == 1)
        unit_responses.append(
            UnitProgressResponse(
                unit_id=u.id,
                unit_number=u.unit_number,
                title=u.title,
                title_vi=u.title_vi,
                realm_name=u.realm_name,
                description=u.description,
                theme_color=u.theme_color,
                icon=u.icon,
                vocab_count=int(vocab_counts.get(u.id, 0)),
                question_count=int(q_counts.get(u.id, 0)),
                is_unlocked=is_unlocked,
                is_completed=up.is_completed if up else False,
                stages_cleared=up.stages_cleared if up else 0,
                best_score=up.best_score if up else 0,
                total_attempts=up.total_attempts if up else 0,
                badge_earned=up.badge_earned if up else False,
                mastered_vocab_count=int(mastered_by_unit.get(u.id, 0)),
            )
        )

    total_vocab_seen = (
        db.execute(
            select(func.count(StudentVocabProgress.id)).where(
                StudentVocabProgress.user_id == current_user.id
            )
        ).scalar_one()
        or 0
    )
    total_vocab_mastered = (
        db.execute(
            select(func.count(StudentVocabProgress.id)).where(
                StudentVocabProgress.user_id == current_user.id,
                StudentVocabProgress.mastery_level >= 2,
            )
        ).scalar_one()
        or 0
    )
    unresolved_mistakes = (
        db.execute(
            select(func.count(StudentMistake.id)).where(
                StudentMistake.user_id == current_user.id,
                StudentMistake.is_resolved.is_(False),
            )
        ).scalar_one()
        or 0
    )
    resolved_mistakes = (
        db.execute(
            select(func.count(StudentMistake.id)).where(
                StudentMistake.user_id == current_user.id,
                StudentMistake.is_resolved.is_(True),
            )
        ).scalar_one()
        or 0
    )

    sessions = (
        db.execute(
            select(QuizSession)
            .where(QuizSession.user_id == current_user.id)
            .order_by(QuizSession.started_at.desc())
            .limit(10)
        )
        .scalars()
        .all()
    )
    recent_sessions = [
        {
            "session_id": s.id,
            "unit_id": s.unit_id,
            "mode": s.mode,
            "status": s.status,
            "correct_count": s.correct_count,
            "wrong_count": s.wrong_count,
            "total_questions": s.total_questions,
            "reset_count": s.reset_count,
            "xp_earned": s.xp_earned,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        }
        for s in sessions
    ]

    return DashboardOverviewResponse(
        user=_serialize_user(current_user),
        units=unit_responses,
        total_vocab_mastered=int(total_vocab_mastered),
        total_vocab_seen=int(total_vocab_seen),
        unresolved_mistakes_count=int(unresolved_mistakes),
        resolved_mistakes_count=int(resolved_mistakes),
        recent_sessions=recent_sessions,
    )


@router.get("/mistakes", response_model=list[MistakeItemResponse])
def list_mistakes(
    include_resolved: bool = Query(default=True),
    unit_id: int | None = Query(default=None),
    question_type: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(StudentMistake).where(StudentMistake.user_id == current_user.id)
    if not include_resolved:
        stmt = stmt.where(StudentMistake.is_resolved.is_(False))
    if unit_id is not None:
        stmt = stmt.where(StudentMistake.unit_id == unit_id)
    if question_type:
        stmt = stmt.where(StudentMistake.question_type == question_type.strip())
    stmt = stmt.order_by(
        StudentMistake.is_resolved.asc(),
        StudentMistake.mistake_count.desc(),
        StudentMistake.last_wrong_at.desc(),
    )
    rows = db.execute(stmt).scalars().all()
    return [
        MistakeItemResponse(
            id=m.id,
            unit_id=m.unit_id,
            vocabulary_id=m.vocabulary_id,
            target_word=m.target_word,
            question_type=m.question_type,
            prompt_text=m.prompt_text,
            correct_answer=m.correct_answer,
            explanation_vi=m.explanation_vi,
            mistake_count=m.mistake_count,
            consecutive_correct_revenge=m.consecutive_correct_revenge,
            mastery_threshold=settings.mistake_mastery_threshold,
            is_resolved=m.is_resolved,
            last_wrong_at=m.last_wrong_at,
            resolved_at=m.resolved_at,
        )
        for m in rows
    ]


@router.get("/vocab-mastery")
def get_vocab_mastery(
    unit_id: int | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(StudentVocabProgress, Vocabulary)
        .join(Vocabulary, Vocabulary.id == StudentVocabProgress.vocabulary_id)
        .where(StudentVocabProgress.user_id == current_user.id)
    )
    if unit_id is not None:
        stmt = stmt.where(Vocabulary.unit_id == unit_id)
    rows = db.execute(stmt.order_by(StudentVocabProgress.mastery_level.desc())).all()
    return [
        {
            "vocabulary_id": v.id,
            "unit_id": v.unit_id,
            "word": v.word,
            "pos": v.pos,
            "ipa": v.ipa,
            "meaning_vi": v.meaning_vi,
            "times_seen": p.times_seen,
            "times_correct": p.times_correct,
            "times_wrong": p.times_wrong,
            "consecutive_correct": p.consecutive_correct,
            "mastery_level": p.mastery_level,
        }
        for p, v in rows
    ]
