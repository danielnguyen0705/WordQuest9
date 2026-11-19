import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    avatar: Mapped[str] = mapped_column(String(50), default="knight")
    xp: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    current_combo: Mapped[int] = mapped_column(Integer, default=0)
    best_combo: Mapped[int] = mapped_column(Integer, default=0)
    last_active_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unit_number: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    title_vi: Mapped[str] = mapped_column(String(150), default="")
    realm_name: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    theme_color: Mapped[str] = mapped_column(String(30), default="#10b981")
    icon: Mapped[str] = mapped_column(String(50), default="book")
    required_xp: Mapped[int] = mapped_column(Integer, default=0)

    vocabularies: Mapped[list["Vocabulary"]] = relationship(
        "Vocabulary", back_populates="unit", cascade="all, delete-orphan"
    )
    questions: Mapped[list["QuestionBank"]] = relationship(
        "QuestionBank", back_populates="unit", cascade="all, delete-orphan"
    )


class Vocabulary(Base):
    __tablename__ = "vocabularies"
    __table_args__ = (UniqueConstraint("unit_id", "word", name="uq_vocab_unit_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unit_id: Mapped[int] = mapped_column(Integer, ForeignKey("units.id", ondelete="CASCADE"), index=True)
    word: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    pos: Mapped[str] = mapped_column(String(30), nullable=False)
    ipa: Mapped[str] = mapped_column(String(120), default="")
    meaning_vi: Mapped[str] = mapped_column(String(255), nullable=False)
    example_en: Mapped[str] = mapped_column(Text, default="")
    example_vi: Mapped[str] = mapped_column(Text, default="")

    unit: Mapped["Unit"] = relationship("Unit", back_populates="vocabularies")
    word_forms: Mapped[list["WordForm"]] = relationship(
        "WordForm", back_populates="vocabulary", cascade="all, delete-orphan"
    )


class WordForm(Base):
    __tablename__ = "word_forms"
    __table_args__ = (UniqueConstraint("vocabulary_id", "word", "pos", name="uq_wordform_vocab_word_pos"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vocabulary_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vocabularies.id", ondelete="CASCADE"), index=True
    )
    word: Mapped[str] = mapped_column(String(120), nullable=False)
    pos: Mapped[str] = mapped_column(String(30), nullable=False)
    meaning_vi: Mapped[str] = mapped_column(String(255), nullable=False)

    vocabulary: Mapped["Vocabulary"] = relationship("Vocabulary", back_populates="word_forms")


class QuestionBank(Base):
    __tablename__ = "question_bank"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    unit_id: Mapped[int] = mapped_column(Integer, ForeignKey("units.id", ondelete="CASCADE"), index=True)
    vocabulary_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("vocabularies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_word: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    distractors: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    explanation_vi: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(50), default="notebook")
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    unit: Mapped["Unit"] = relationship("Unit", back_populates="questions")


class UnitProgress(Base):
    __tablename__ = "unit_progress"
    __table_args__ = (UniqueConstraint("user_id", "unit_id", name="uq_user_unit_progress"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[int] = mapped_column(Integer, ForeignKey("units.id", ondelete="CASCADE"), index=True)
    is_unlocked: Mapped[bool] = mapped_column(Boolean, default=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    stages_cleared: Mapped[int] = mapped_column(Integer, default=0)
    best_score: Mapped[int] = mapped_column(Integer, default=0)
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)
    badge_earned: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("units.id", ondelete="SET NULL"), nullable=True)
    mode: Mapped[str] = mapped_column(String(30), default="sudden_death")  # sudden_death | practice | mistake_revenge
    status: Mapped[str] = mapped_column(String(30), default="warmup")  # warmup | in_progress | failed_reset | completed | abandoned
    warmup_vocab_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    questions_payload: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    current_index: Mapped[int] = mapped_column(Integer, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, default=20)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    wrong_count: Mapped[int] = mapped_column(Integer, default=0)
    lives_remaining: Mapped[int] = mapped_column(Integer, default=1)
    reset_count: Mapped[int] = mapped_column(Integer, default=0)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("quiz_sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    unit_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("units.id", ondelete="SET NULL"), nullable=True)
    vocabulary_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("vocabularies.id", ondelete="SET NULL"), nullable=True
    )
    question_bank_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("question_bank.id", ondelete="SET NULL"), nullable=True
    )
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_word: Mapped[str] = mapped_column(String(120), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    selected_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StudentVocabProgress(Base):
    __tablename__ = "student_vocab_progress"
    __table_args__ = (UniqueConstraint("user_id", "vocabulary_id", name="uq_user_vocab_progress"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    vocabulary_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vocabularies.id", ondelete="CASCADE"), index=True
    )
    times_seen: Mapped[int] = mapped_column(Integer, default=0)
    times_correct: Mapped[int] = mapped_column(Integer, default=0)
    times_wrong: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_correct: Mapped[int] = mapped_column(Integer, default=0)
    mastery_level: Mapped[int] = mapped_column(Integer, default=0)  # 0=New, 1=Learning, 2=Familiar, 3=Mastered
    last_reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class StudentMistake(Base):
    __tablename__ = "student_mistakes"
    __table_args__ = (
        UniqueConstraint("user_id", "mistake_key", name="uq_user_mistake_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mistake_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    unit_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("units.id", ondelete="SET NULL"), nullable=True)
    vocabulary_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("vocabularies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question_bank_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("question_bank.id", ondelete="SET NULL"), nullable=True
    )
    target_word: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String(255), nullable=False)
    distractors: Mapped[list[str]] = mapped_column(JSON, default=list)
    explanation_vi: Mapped[str] = mapped_column(Text, default="")
    mistake_count: Mapped[int] = mapped_column(Integer, default=1)
    consecutive_correct_revenge: Mapped[int] = mapped_column(Integer, default=0)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    last_wrong_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
