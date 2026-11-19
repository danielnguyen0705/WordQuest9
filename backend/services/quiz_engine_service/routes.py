from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from wordquest_shared.config import settings
from wordquest_shared.database import get_db
from wordquest_shared.models import (
    QuizAttempt,
    QuizSession,
    StudentMistake,
    StudentVocabProgress,
    Unit,
    UnitProgress,
    User,
    Vocabulary,
)
from wordquest_shared.schemas import (
    PublicQuizQuestion,
    SessionStateResponse,
    StartSessionRequest,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    VocabularyItemSchema,
    WordFormSchema,
)
from wordquest_shared.security import calculate_level, get_current_user

from generator import (
    compute_mistake_key,
    generate_hybrid_unit_questions,
    generate_mistake_revenge_questions,
    reshuffle_session_questions,
    select_warmup_vocabs,
)

router = APIRouter(prefix="/api/v1/quiz", tags=["Quiz & Game Engine"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_public_question(q: dict[str, Any]) -> PublicQuizQuestion:
    return PublicQuizQuestion(
        index=q["index"],
        question_uid=q["question_uid"],
        question_bank_id=q.get("question_bank_id"),
        vocabulary_id=q.get("vocabulary_id"),
        unit_id=q.get("unit_id"),
        target_word=q["target_word"],
        question_type=q["question_type"],
        prompt_text=q["prompt_text"],
        audio_text=q.get("audio_text"),
        ipa=q.get("ipa"),
        input_mode=q.get("input_mode", "mcq"),
        options=list(q.get("options", [])),
        source=q.get("source", "notebook"),
        mistake_id=q.get("mistake_id"),
    )


def _serialize_vocab(v: Vocabulary) -> VocabularyItemSchema:
    return VocabularyItemSchema(
        id=v.id,
        unit_id=v.unit_id,
        word=v.word,
        pos=v.pos,
        ipa=v.ipa,
        meaning_vi=v.meaning_vi,
        example_en=v.example_en,
        example_vi=v.example_vi,
        word_forms=[
            WordFormSchema(id=wf.id, word=wf.word, pos=wf.pos, meaning_vi=wf.meaning_vi)
            for wf in v.word_forms
        ],
    )


def _build_session_state(db: Session, session: QuizSession) -> SessionStateResponse:
    warmup_cards: list[VocabularyItemSchema] = []
    if session.warmup_vocab_ids:
        vocabs = (
            db.execute(
                select(Vocabulary)
                .options(selectinload(Vocabulary.word_forms))
                .where(Vocabulary.id.in_(session.warmup_vocab_ids))
            )
            .scalars()
            .all()
        )
        v_map = {v.id: v for v in vocabs}
        warmup_cards = [_serialize_vocab(v_map[vid]) for vid in session.warmup_vocab_ids if vid in v_map]

    current_q = None
    if session.status == "in_progress" and 0 <= session.current_index < len(session.questions_payload):
        current_q = _to_public_question(session.questions_payload[session.current_index])

    return SessionStateResponse(
        session_id=session.id,
        unit_id=session.unit_id,
        mode=session.mode,
        status=session.status,
        current_index=session.current_index,
        total_questions=session.total_questions,
        correct_count=session.correct_count,
        wrong_count=session.wrong_count,
        lives_remaining=session.lives_remaining,
        reset_count=session.reset_count,
        xp_earned=session.xp_earned,
        warmup_cards=warmup_cards,
        current_question=current_q,
    )


@router.post("/sessions", response_model=SessionStateResponse)
def start_quiz_session(
    payload: StartSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.mode == "mistake_revenge":
        questions = generate_mistake_revenge_questions(
            db=db,
            user_id=current_user.id,
            unit_id=payload.unit_id,
            max_questions=payload.question_count,
        )
        if not questions:
            raise HTTPException(
                status_code=400,
                detail="Kho Lỗi Sai hiện đang trống! Bạn chưa có câu sai nào cần phục thù.",
            )
        session = QuizSession(
            user_id=current_user.id,
            unit_id=payload.unit_id,
            mode="mistake_revenge",
            status="in_progress",
            warmup_vocab_ids=[],
            questions_payload=questions,
            current_index=0,
            total_questions=len(questions),
            lives_remaining=999,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return _build_session_state(db, session)

    if payload.unit_id is None:
        raise HTTPException(status_code=400, detail="Cần chọn Unit để bắt đầu ải.")

    unit = db.get(Unit, payload.unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail=f"Unit {payload.unit_id} không tồn tại.")

    warmup_vocabs = select_warmup_vocabs(
        db=db,
        user_id=current_user.id,
        unit_id=payload.unit_id,
        warmup_count=0 if payload.skip_warmup else payload.warmup_count,
    )
    questions = generate_hybrid_unit_questions(
        db=db,
        unit_id=payload.unit_id,
        warmup_vocabs=warmup_vocabs,
        question_count=payload.question_count,
    )
    if not questions:
        raise HTTPException(
            status_code=400,
            detail=f"Unit {payload.unit_id} chưa có dữ liệu từ vựng hoặc câu hỏi. Hãy nạp dữ liệu từ Notebook trước!",
        )

    initial_status = "in_progress" if (payload.skip_warmup or not warmup_vocabs) else "warmup"
    lives = 1 if payload.mode == "sudden_death" else 999

    session = QuizSession(
        user_id=current_user.id,
        unit_id=payload.unit_id,
        mode=payload.mode,
        status=initial_status,
        warmup_vocab_ids=[v.id for v in warmup_vocabs],
        questions_payload=questions,
        current_index=0,
        total_questions=len(questions),
        lives_remaining=lives,
    )
    db.add(session)

    # Ensure unit_progress record exists & bump attempt counter
    up = db.execute(
        select(UnitProgress).where(
            UnitProgress.user_id == current_user.id,
            UnitProgress.unit_id == payload.unit_id,
        )
    ).scalar_one_or_none()
    if not up:
        up = UnitProgress(
            user_id=current_user.id,
            unit_id=payload.unit_id,
            is_unlocked=True,
            total_attempts=1,
        )
        db.add(up)
    else:
        up.total_attempts += 1

    db.commit()
    db.refresh(session)
    return _build_session_state(db, session)


@router.get("/sessions/{session_id}", response_model=SessionStateResponse)
def get_quiz_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.get(QuizSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chơi.")
    return _build_session_state(db, session)


@router.post("/sessions/{session_id}/start-challenge", response_model=SessionStateResponse)
def start_challenge_phase(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.get(QuizSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chơi.")
    if session.status == "warmup":
        session.status = "in_progress"
        session.current_index = 0
        db.commit()
        db.refresh(session)
    return _build_session_state(db, session)


def _record_vocab_progress(db: Session, user_id: str, vocab_id: int | None, is_correct: bool) -> None:
    if not vocab_id:
        return
    vp = db.execute(
        select(StudentVocabProgress).where(
            StudentVocabProgress.user_id == user_id,
            StudentVocabProgress.vocabulary_id == vocab_id,
        )
    ).scalar_one_or_none()
    if not vp:
        vp = StudentVocabProgress(
            user_id=user_id,
            vocabulary_id=vocab_id,
            times_seen=0,
            times_correct=0,
            times_wrong=0,
            consecutive_correct=0,
            mastery_level=0,
        )
        db.add(vp)
    vp.times_seen += 1
    vp.last_reviewed_at = _utcnow()
    if is_correct:
        vp.times_correct += 1
        vp.consecutive_correct += 1
        if vp.consecutive_correct >= 3:
            vp.mastery_level = 3
        elif vp.consecutive_correct == 2:
            vp.mastery_level = max(vp.mastery_level, 2)
        else:
            vp.mastery_level = max(vp.mastery_level, 1)
    else:
        vp.times_wrong += 1
        vp.consecutive_correct = 0
        vp.mastery_level = min(vp.mastery_level, 1)


def _upsert_mistake(db: Session, user_id: str, q: dict[str, Any]) -> StudentMistake:
    m_key = compute_mistake_key(q["target_word"], q["question_type"], q["prompt_text"])
    existing = db.execute(
        select(StudentMistake).where(
            StudentMistake.user_id == user_id,
            StudentMistake.mistake_key == m_key,
        )
    ).scalar_one_or_none()

    if existing:
        existing.mistake_count += 1
        existing.consecutive_correct_revenge = 0
        existing.is_resolved = False
        existing.resolved_at = None
        existing.last_wrong_at = _utcnow()
        return existing

    mistake = StudentMistake(
        user_id=user_id,
        mistake_key=m_key,
        unit_id=q.get("unit_id"),
        vocabulary_id=q.get("vocabulary_id"),
        question_bank_id=q.get("question_bank_id"),
        target_word=q["target_word"],
        question_type=q["question_type"],
        prompt_text=q["prompt_text"],
        correct_answer=q["correct_answer"],
        distractors=list(q.get("distractors", [])),
        explanation_vi=q.get("explanation_vi", ""),
        mistake_count=1,
        consecutive_correct_revenge=0,
        is_resolved=False,
        last_wrong_at=_utcnow(),
    )
    db.add(mistake)
    db.flush()
    return mistake


def _advance_mistake_revenge(
    db: Session, user_id: str, q: dict[str, Any]
) -> tuple[bool, int | None]:
    """Increment consecutive correct streak for a mistake item; mark resolved at threshold."""
    mistake: StudentMistake | None = None
    if q.get("mistake_id"):
        mistake = db.get(StudentMistake, q["mistake_id"])
    if mistake is None:
        m_key = compute_mistake_key(q["target_word"], q["question_type"], q["prompt_text"])
        mistake = db.execute(
            select(StudentMistake).where(
                StudentMistake.user_id == user_id,
                StudentMistake.mistake_key == m_key,
                StudentMistake.is_resolved.is_(False),
            )
        ).scalar_one_or_none()
    if not mistake or mistake.user_id != user_id or mistake.is_resolved:
        return False, None

    mistake.consecutive_correct_revenge += 1
    if mistake.consecutive_correct_revenge >= settings.mistake_mastery_threshold:
        mistake.is_resolved = True
        mistake.resolved_at = _utcnow()
        return True, mistake.consecutive_correct_revenge
    return False, mistake.consecutive_correct_revenge


@router.post("/sessions/{session_id}/answer", response_model=SubmitAnswerResponse)
def submit_answer(
    session_id: str,
    payload: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.get(QuizSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên chơi.")
    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Phiên chơi này đã hoàn thành.")
    if session.status == "warmup":
        session.status = "in_progress"

    if payload.question_index != session.current_index:
        raise HTTPException(
            status_code=409,
            detail=f"Câu hỏi hiện tại là câu số {session.current_index + 1}, không khớp với chỉ số gửi lên.",
        )

    questions = list(session.questions_payload)
    if session.current_index >= len(questions):
        raise HTTPException(status_code=400, detail="Không còn câu hỏi nào trong phiên này.")

    q = questions[session.current_index]
    selected_clean = payload.selected_answer.strip()
    correct_clean = q["correct_answer"].strip()
    is_correct = selected_clean.lower() == correct_clean.lower()

    # Record attempt in audit log
    db.add(
        QuizAttempt(
            session_id=session.id,
            user_id=current_user.id,
            unit_id=q.get("unit_id"),
            vocabulary_id=q.get("vocabulary_id"),
            question_bank_id=q.get("question_bank_id"),
            question_type=q["question_type"],
            target_word=q["target_word"],
            prompt_text=q["prompt_text"],
            selected_answer=selected_clean,
            correct_answer=correct_clean,
            is_correct=is_correct,
            response_time_ms=payload.response_time_ms,
        )
    )

    # Update vocabulary mastery
    _record_vocab_progress(db, current_user.id, q.get("vocabulary_id"), is_correct)

    # Update user daily streak
    today = date.today()
    if current_user.last_active_date != today:
        if current_user.last_active_date == today - timedelta(days=1):
            current_user.streak_days += 1
        elif current_user.last_active_date is None:
            current_user.streak_days = 1
        else:
            current_user.streak_days = 1
        current_user.longest_streak = max(current_user.longest_streak, current_user.streak_days)
        current_user.last_active_date = today

    xp_gained = 0
    triggered_reset = False
    session_completed = False
    unit_unlocked: int | None = None
    mistake_recorded = False
    mistake_resolved = False
    revenge_streak: int | None = None
    session_summary: dict[str, Any] | None = None

    if is_correct:
        session.correct_count += 1
        current_user.current_combo += 1
        current_user.best_combo = max(current_user.best_combo, current_user.current_combo)

        # XP calculation with combo bonus
        xp_gained = 15 + min(current_user.current_combo, 10) * 2
        if session.mode == "sudden_death":
            xp_gained += 5
        elif session.mode == "mistake_revenge":
            xp_gained += 10

        session.xp_earned += xp_gained
        current_user.xp += xp_gained
        current_user.level = calculate_level(current_user.xp)

        # Track mistake vault resolution progress
        mistake_resolved, revenge_streak = _advance_mistake_revenge(db, current_user.id, q)

        session.current_index += 1
        if session.current_index >= session.total_questions:
            # Completed entire 20/20 session!
            session.status = "completed"
            session.completed_at = _utcnow()
            session_completed = True

            clear_bonus = 100 if session.mode == "sudden_death" else 40
            session.xp_earned += clear_bonus
            current_user.xp += clear_bonus
            current_user.level = calculate_level(current_user.xp)
            xp_gained += clear_bonus

            # Update UnitProgress & unlock next unit on Sudden-Death clear (or 80%+ practice)
            if session.unit_id:
                up = db.execute(
                    select(UnitProgress).where(
                        UnitProgress.user_id == current_user.id,
                        UnitProgress.unit_id == session.unit_id,
                    )
                ).scalar_one_or_none()
                if not up:
                    up = UnitProgress(
                        user_id=current_user.id,
                        unit_id=session.unit_id,
                        is_unlocked=True,
                    )
                    db.add(up)
                up.best_score = max(up.best_score, session.correct_count)
                if session.mode == "sudden_death" and session.correct_count == session.total_questions:
                    up.is_completed = True
                    up.stages_cleared += 1
                    up.badge_earned = True
                    up.completed_at = _utcnow()

                    # Unlock next Unit!
                    next_unit_id = session.unit_id + 1
                    if db.get(Unit, next_unit_id):
                        next_up = db.execute(
                            select(UnitProgress).where(
                                UnitProgress.user_id == current_user.id,
                                UnitProgress.unit_id == next_unit_id,
                            )
                        ).scalar_one_or_none()
                        if not next_up:
                            db.add(
                                UnitProgress(
                                    user_id=current_user.id,
                                    unit_id=next_unit_id,
                                    is_unlocked=True,
                                )
                            )
                            unit_unlocked = next_unit_id
                        elif not next_up.is_unlocked:
                            next_up.is_unlocked = True
                            unit_unlocked = next_unit_id

            session_summary = {
                "total_questions": session.total_questions,
                "correct_count": session.correct_count,
                "wrong_count": session.wrong_count,
                "reset_count": session.reset_count,
                "xp_earned": session.xp_earned,
                "new_level": current_user.level,
                "unit_unlocked": unit_unlocked,
                "mode": session.mode,
            }
    else:
        # Wrong answer!
        session.wrong_count += 1
        current_user.current_combo = 0
        _upsert_mistake(db, current_user.id, q)
        mistake_recorded = True

        if session.mode == "sudden_death":
            # HARDCORE SUDDEN-DEATH 1-LIFE RULE:
            # Instant death -> Reset back to Q1 with freshly reshuffled questions AND A/B/C/D options!
            triggered_reset = True
            session.reset_count += 1
            session.current_index = 0
            session.correct_count = 0
            session.lives_remaining = 1
            session.questions_payload = reshuffle_session_questions(questions)
            session.status = "in_progress"
        else:
            # Practice / Mistake Revenge: move forward without resetting
            session.current_index += 1
            if session.current_index >= session.total_questions:
                session.status = "completed"
                session.completed_at = _utcnow()
                session_completed = True
                session_summary = {
                    "total_questions": session.total_questions,
                    "correct_count": session.correct_count,
                    "wrong_count": session.wrong_count,
                    "reset_count": session.reset_count,
                    "xp_earned": session.xp_earned,
                    "new_level": current_user.level,
                    "unit_unlocked": None,
                    "mode": session.mode,
                }

    db.commit()
    db.refresh(session)

    next_q = None
    if not session_completed and 0 <= session.current_index < len(session.questions_payload):
        next_q = _to_public_question(session.questions_payload[session.current_index])

    return SubmitAnswerResponse(
        session_id=session.id,
        is_correct=is_correct,
        correct_answer=correct_clean,
        explanation_vi=q.get("explanation_vi", ""),
        xp_gained=xp_gained,
        combo=current_user.current_combo,
        lives_remaining=session.lives_remaining,
        triggered_reset=triggered_reset,
        reset_count=session.reset_count,
        session_completed=session_completed,
        unit_unlocked=unit_unlocked,
        mistake_recorded=mistake_recorded,
        mistake_resolved=mistake_resolved,
        revenge_streak=revenge_streak,
        revenge_target=settings.mistake_mastery_threshold,
        next_question=next_q,
        session_summary=session_summary,
    )
