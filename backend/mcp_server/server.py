"""
WordQuest 9 - Official Model Context Protocol (MCP) Server
Built with the Official MCP Python SDK (`mcp.server.fastmcp.FastMCP`).

Exposes standardized MCP Resources and MCP Tools for Tiếng Anh 9 (Global Success)
learning content, hybrid quiz generation, attempt recording, weakness analytics,
and Notebook JSON data ingestion.
"""

import json
import os
import sys
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

BACKEND_DIR = Path(__file__).resolve().parents[1]
SHARED_DIR = BACKEND_DIR / "shared"
QUIZ_DIR = BACKEND_DIR / "services" / "quiz_engine_service"
for p in (SHARED_DIR, QUIZ_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from wordquest_shared.config import settings
from wordquest_shared.database import SessionLocal, init_db
from wordquest_shared.ingestion import ingest_notebook_data
from wordquest_shared.models import (
    QuestionBank,
    QuizAttempt,
    QuizSession,
    StudentMistake,
    StudentVocabProgress,
    Unit,
    User,
    Vocabulary,
    WordForm,
)
from wordquest_shared.security import calculate_level
from generator import (
    compute_mistake_key,
    generate_hybrid_unit_questions,
    generate_mistake_revenge_questions,
    select_warmup_vocabs,
)

mcp = FastMCP(
    name="WordQuest9-MCP",
    host="0.0.0.0",
    port=int(os.getenv("PORT") or os.getenv("MCP_SERVER_PORT", str(settings.mcp_server_port))),
)


# =====================================================================
# MCP RESOURCES (Read-only standardized data views)
# =====================================================================

@mcp.resource("wordquest://units")
def resource_units() -> str:
    """List all Tiếng Anh 9 Global Success units with vocabulary and question counts."""
    init_db()
    db = SessionLocal()
    try:
        units = db.execute(select(Unit).order_by(Unit.unit_number)).scalars().all()
        v_counts = dict(
            db.execute(select(Vocabulary.unit_id, func.count(Vocabulary.id)).group_by(Vocabulary.unit_id)).all()
        )
        q_counts = dict(
            db.execute(select(QuestionBank.unit_id, func.count(QuestionBank.id)).group_by(QuestionBank.unit_id)).all()
        )
        payload = [
            {
                "unit_number": u.unit_number,
                "title": u.title,
                "title_vi": u.title_vi,
                "realm_name": u.realm_name,
                "vocab_count": int(v_counts.get(u.id, 0)),
                "question_count": int(q_counts.get(u.id, 0)),
            }
            for u in units
        ]
        return json.dumps(payload, ensure_ascii=False, indent=2)
    finally:
        db.close()


@mcp.resource("wordquest://units/{unit_id}/vocab")
def resource_unit_vocab(unit_id: int) -> str:
    """Retrieve all vocabulary entries and word forms for a specific Unit (1-12)."""
    init_db()
    db = SessionLocal()
    try:
        vocabs = (
            db.execute(
                select(Vocabulary)
                .options(selectinload(Vocabulary.word_forms))
                .where(Vocabulary.unit_id == int(unit_id))
                .order_by(Vocabulary.word)
            )
            .scalars()
            .all()
        )
        payload = [
            {
                "id": v.id,
                "unit": v.unit_id,
                "word": v.word,
                "pos": v.pos,
                "ipa": v.ipa,
                "meaning_vi": v.meaning_vi,
                "example_en": v.example_en,
                "example_vi": v.example_vi,
                "word_forms": [
                    {"word": wf.word, "pos": wf.pos, "meaning_vi": wf.meaning_vi}
                    for wf in v.word_forms
                ],
            }
            for v in vocabs
        ]
        return json.dumps(payload, ensure_ascii=False, indent=2)
    finally:
        db.close()


@mcp.resource("wordquest://word-forms/{word}")
def resource_word_forms(word: str) -> str:
    """Look up the complete Word Family (noun/verb/adj/adv) for an English word."""
    init_db()
    db = SessionLocal()
    try:
        kw = word.strip().lower()
        vocabs = (
            db.execute(
                select(Vocabulary)
                .options(selectinload(Vocabulary.word_forms))
                .where(func.lower(Vocabulary.word) == kw)
            )
            .scalars()
            .all()
        )
        forms = []
        for v in vocabs:
            forms.append({"word": v.word, "pos": v.pos, "meaning_vi": v.meaning_vi, "unit": v.unit_id})
            for wf in v.word_forms:
                forms.append({"word": wf.word, "pos": wf.pos, "meaning_vi": wf.meaning_vi, "unit": v.unit_id})
        if not forms:
            wfs = db.execute(select(WordForm).where(func.lower(WordForm.word) == kw)).scalars().all()
            for wf in wfs:
                forms.append({"word": wf.word, "pos": wf.pos, "meaning_vi": wf.meaning_vi})
        return json.dumps({"query": word, "word_forms": forms}, ensure_ascii=False, indent=2)
    finally:
        db.close()


@mcp.resource("wordquest://units/{unit_id}/questions/{question_type}")
def resource_unit_questions(unit_id: int, question_type: str) -> str:
    """Fetch curated Notebook question bank items by Unit and question_type (or 'all')."""
    init_db()
    db = SessionLocal()
    try:
        stmt = select(QuestionBank).where(QuestionBank.unit_id == int(unit_id))
        if question_type.strip().lower() != "all":
            stmt = stmt.where(QuestionBank.question_type == question_type.strip())
        rows = db.execute(stmt).scalars().all()
        payload = [
            {
                "id": q.id,
                "unit": q.unit_id,
                "target_word": q.target_word,
                "question_type": q.question_type,
                "prompt_text": q.prompt_text,
                "correct_answer": q.correct_answer,
                "distractors": q.distractors,
                "explanation_vi": q.explanation_vi,
            }
            for q in rows
        ]
        return json.dumps(payload, ensure_ascii=False, indent=2)
    finally:
        db.close()


@mcp.resource("wordquest://students/{user_id}/mistakes")
def resource_student_mistakes(user_id: str) -> str:
    """Retrieve a student's Mistake Vault (unresolved & resolved mistake items)."""
    init_db()
    db = SessionLocal()
    try:
        rows = (
            db.execute(
                select(StudentMistake)
                .where(StudentMistake.user_id == user_id)
                .order_by(StudentMistake.is_resolved.asc(), StudentMistake.mistake_count.desc())
            )
            .scalars()
            .all()
        )
        payload = [
            {
                "id": m.id,
                "unit_id": m.unit_id,
                "target_word": m.target_word,
                "question_type": m.question_type,
                "prompt_text": m.prompt_text,
                "correct_answer": m.correct_answer,
                "mistake_count": m.mistake_count,
                "consecutive_correct_revenge": m.consecutive_correct_revenge,
                "is_resolved": m.is_resolved,
                "last_wrong_at": m.last_wrong_at.isoformat() if m.last_wrong_at else None,
            }
            for m in rows
        ]
        return json.dumps(payload, ensure_ascii=False, indent=2)
    finally:
        db.close()


# =====================================================================
# MCP TOOLS (Standardized executable actions)
# =====================================================================

@mcp.tool()
def generate_quiz_session(
    user_id: str,
    unit_id: int | None = 1,
    mode: Literal["sudden_death", "practice", "mistake_revenge"] = "sudden_death",
    question_count: int = 20,
    warmup_count: int = 6,
) -> dict:
    """
    Generate and persist a gamified WordQuest 9 quiz session combining Flashcard Warm-up
    (5-7 target words) and 20 hybrid questions (curated Notebook bank + dynamic listening/translation).
    """
    init_db()
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if not user:
            return {"error": f"User {user_id} not found"}

        if mode == "mistake_revenge":
            questions = generate_mistake_revenge_questions(db, user_id, unit_id, question_count)
            warmup_vocabs = []
            initial_status = "in_progress"
            lives = 999
        else:
            if unit_id is None:
                return {"error": "unit_id is required for sudden_death or practice mode"}
            warmup_vocabs = select_warmup_vocabs(db, user_id, unit_id, warmup_count)
            questions = generate_hybrid_unit_questions(db, unit_id, warmup_vocabs, question_count)
            initial_status = "warmup" if warmup_vocabs else "in_progress"
            lives = 1 if mode == "sudden_death" else 999

        if not questions:
            return {"error": "No questions available for the requested parameters."}

        session = QuizSession(
            user_id=user_id,
            unit_id=unit_id,
            mode=mode,
            status=initial_status,
            warmup_vocab_ids=[v.id for v in warmup_vocabs],
            questions_payload=questions,
            current_index=0,
            total_questions=len(questions),
            lives_remaining=lives,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        return {
            "session_id": session.id,
            "mode": session.mode,
            "status": session.status,
            "unit_id": session.unit_id,
            "warmup_words": [v.word for v in warmup_vocabs],
            "total_questions": session.total_questions,
            "question_type_breakdown": _count_by_type(questions),
        }
    finally:
        db.close()


def _count_by_type(questions: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for q in questions:
        qt = q["question_type"]
        counts[qt] = counts.get(qt, 0) + 1
    return counts


@mcp.tool()
def record_attempt_result(
    user_id: str,
    target_word: str,
    question_type: str,
    prompt_text: str,
    selected_answer: str,
    correct_answer: str,
    unit_id: int | None = None,
    explanation_vi: str = "",
    distractors: list[str] | None = None,
) -> dict:
    """
    Record an individual student answer attempt, update XP/Vocabulary Mastery,
    and automatically insert or update the Mistake Vault if incorrect (or progress resolution if correct).
    """
    init_db()
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if not user:
            return {"error": f"User {user_id} not found"}

        is_correct = selected_answer.strip().lower() == correct_answer.strip().lower()
        vocab = db.execute(
            select(Vocabulary).where(func.lower(Vocabulary.word) == target_word.strip().lower())
        ).scalar_one_or_none()

        # Update vocab progress
        if vocab:
            vp = db.execute(
                select(StudentVocabProgress).where(
                    StudentVocabProgress.user_id == user_id,
                    StudentVocabProgress.vocabulary_id == vocab.id,
                )
            ).scalar_one_or_none()
            if not vp:
                vp = StudentVocabProgress(user_id=user_id, vocabulary_id=vocab.id)
                db.add(vp)
            vp.times_seen += 1
            if is_correct:
                vp.times_correct += 1
                vp.consecutive_correct += 1
                vp.mastery_level = min(3, max(vp.mastery_level, vp.consecutive_correct))
            else:
                vp.times_wrong += 1
                vp.consecutive_correct = 0
                vp.mastery_level = min(vp.mastery_level, 1)

        m_key = compute_mistake_key(target_word, question_type, prompt_text)
        existing_mistake = db.execute(
            select(StudentMistake).where(
                StudentMistake.user_id == user_id,
                StudentMistake.mistake_key == m_key,
            )
        ).scalar_one_or_none()

        mistake_status = "none"
        if is_correct:
            user.xp += 15
            user.level = calculate_level(user.xp)
            if existing_mistake and not existing_mistake.is_resolved:
                existing_mistake.consecutive_correct_revenge += 1
                if existing_mistake.consecutive_correct_revenge >= settings.mistake_mastery_threshold:
                    existing_mistake.is_resolved = True
                    mistake_status = "resolved"
                else:
                    mistake_status = f"revenge_progress:{existing_mistake.consecutive_correct_revenge}/{settings.mistake_mastery_threshold}"
        else:
            if existing_mistake:
                existing_mistake.mistake_count += 1
                existing_mistake.consecutive_correct_revenge = 0
                existing_mistake.is_resolved = False
                mistake_status = f"repeated_mistake:{existing_mistake.mistake_count}"
            else:
                db.add(
                    StudentMistake(
                        user_id=user_id,
                        mistake_key=m_key,
                        unit_id=unit_id or (vocab.unit_id if vocab else None),
                        vocabulary_id=vocab.id if vocab else None,
                        target_word=target_word,
                        question_type=question_type,
                        prompt_text=prompt_text,
                        correct_answer=correct_answer,
                        distractors=distractors or [],
                        explanation_vi=explanation_vi,
                    )
                )
                mistake_status = "recorded_new"

        db.commit()
        return {
            "is_correct": is_correct,
            "user_xp": user.xp,
            "user_level": user.level,
            "mistake_status": mistake_status,
        }
    finally:
        db.close()


@mcp.tool()
def get_student_weaknesses(user_id: str, limit: int = 15) -> dict:
    """
    Analyze a student's weak vocabulary words, most frequently missed question types,
    and active items in their Mistake Vault for targeted review recommendations.
    """
    init_db()
    db = SessionLocal()
    try:
        unresolved = (
            db.execute(
                select(StudentMistake)
                .where(StudentMistake.user_id == user_id, StudentMistake.is_resolved.is_(False))
                .order_by(StudentMistake.mistake_count.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )
        by_type: dict[str, int] = {}
        for m in unresolved:
            by_type[m.question_type] = by_type.get(m.question_type, 0) + m.mistake_count

        return {
            "user_id": user_id,
            "unresolved_count": len(unresolved),
            "weakest_question_types": dict(sorted(by_type.items(), key=lambda kv: kv[1], reverse=True)),
            "top_weak_items": [
                {
                    "id": m.id,
                    "unit_id": m.unit_id,
                    "target_word": m.target_word,
                    "question_type": m.question_type,
                    "mistake_count": m.mistake_count,
                    "revenge_streak": m.consecutive_correct_revenge,
                    "mastery_threshold": settings.mistake_mastery_threshold,
                }
                for m in unresolved
            ],
        }
    finally:
        db.close()


@mcp.tool()
def import_notebook_data(
    data_dir: str | None = None,
    unit_filter: int | None = None,
    dry_run: bool = False,
) -> dict:
    """
    Scan data/vocab/unit_X_vocab.json and data/questions/unit_X_questions.json,
    validate against JSON Schemas, and UPSERT into PostgreSQL.
    """
    init_db()
    db = SessionLocal()
    try:
        result = ingest_notebook_data(
            db=db,
            data_dir=data_dir,
            unit_filter=unit_filter,
            dry_run=dry_run,
        )
        return result.model_dump()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    mcp.run(transport=transport)
