from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


# --- Auth & Profile ---
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=6, max_length=72)
    display_name: str = Field(min_length=2, max_length=80)
    avatar: str = Field(default="knight", max_length=50)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)  # accepts username or email
    password: str = Field(min_length=1)


class UserProfileResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str
    avatar: str
    xp: int
    level: int
    xp_in_level: int
    xp_for_next_level: int
    streak_days: int
    longest_streak: int
    current_combo: int
    best_combo: int
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse


# --- Vocabulary & Content ---
class WordFormSchema(BaseModel):
    id: int | None = None
    word: str
    pos: str
    meaning_vi: str


class VocabularyItemSchema(BaseModel):
    id: int
    unit_id: int
    word: str
    pos: str
    ipa: str
    meaning_vi: str
    example_en: str
    example_vi: str
    word_forms: list[WordFormSchema] = []


class UnitSummarySchema(BaseModel):
    id: int
    unit_number: int
    title: str
    title_vi: str
    realm_name: str
    description: str
    theme_color: str
    icon: str
    required_xp: int
    vocab_count: int = 0
    question_count: int = 0


class QuestionBankItemSchema(BaseModel):
    id: int
    unit_id: int
    vocabulary_id: int | None = None
    target_word: str
    question_type: str
    prompt_text: str
    correct_answer: str
    distractors: list[str]
    explanation_vi: str
    source: str


class ImportDataRequest(BaseModel):
    data_dir: str | None = None
    unit_filter: int | None = Field(default=None, ge=1, le=12)
    dry_run: bool = False


class ImportDataResult(BaseModel):
    dry_run: bool
    units_upserted: int
    vocab_files_processed: int
    vocab_upserted: int
    word_forms_upserted: int
    question_files_processed: int
    questions_upserted: int
    errors: list[str] = []


# --- Quiz & Game Engine ---
class StartSessionRequest(BaseModel):
    unit_id: int | None = Field(default=None, ge=1, le=12)
    mode: Literal["sudden_death", "practice", "mistake_revenge"] = "sudden_death"
    question_count: int = Field(default=20, ge=5, le=40)
    warmup_count: int = Field(default=6, ge=0, le=10)
    skip_warmup: bool = False


class PublicQuizQuestion(BaseModel):
    index: int
    question_uid: str
    question_bank_id: int | None = None
    vocabulary_id: int | None = None
    unit_id: int | None = None
    target_word: str
    question_type: Literal[
        "translation_en_vi",
        "translation_vi_en",
        "listening",
        "contextual_mcq",
        "word_form",
    ]
    prompt_text: str
    audio_text: str | None = None
    ipa: str | None = None
    input_mode: Literal["mcq", "typing"] = "mcq"
    options: list[str]
    source: str = "notebook"
    mistake_id: int | None = None


class SessionStateResponse(BaseModel):
    session_id: str
    unit_id: int | None
    mode: str
    status: str
    current_index: int
    total_questions: int
    correct_count: int
    wrong_count: int
    lives_remaining: int
    reset_count: int
    xp_earned: int
    warmup_cards: list[VocabularyItemSchema] = []
    current_question: PublicQuizQuestion | None = None


class SubmitAnswerRequest(BaseModel):
    question_index: int = Field(ge=0)
    selected_answer: str = Field(min_length=1)
    response_time_ms: int | None = Field(default=None, ge=0)


class SubmitAnswerResponse(BaseModel):
    session_id: str
    is_correct: bool
    correct_answer: str
    explanation_vi: str
    xp_gained: int
    combo: int
    lives_remaining: int
    triggered_reset: bool = False
    reset_count: int = 0
    session_completed: bool = False
    unit_unlocked: int | None = None
    mistake_recorded: bool = False
    mistake_resolved: bool = False
    revenge_streak: int | None = None
    revenge_target: int = 2
    next_question: PublicQuizQuestion | None = None
    session_summary: dict | None = None


# --- Progress & Mistake Vault ---
class MistakeItemResponse(BaseModel):
    id: int
    unit_id: int | None
    vocabulary_id: int | None
    target_word: str
    question_type: str
    prompt_text: str
    correct_answer: str
    explanation_vi: str
    mistake_count: int
    consecutive_correct_revenge: int
    mastery_threshold: int
    is_resolved: bool
    last_wrong_at: datetime
    resolved_at: datetime | None


class UnitProgressResponse(BaseModel):
    unit_id: int
    unit_number: int
    title: str
    title_vi: str
    realm_name: str
    description: str
    theme_color: str
    icon: str
    vocab_count: int
    question_count: int
    is_unlocked: bool
    is_completed: bool
    stages_cleared: int
    best_score: int
    total_attempts: int
    badge_earned: bool
    mastered_vocab_count: int


class DashboardOverviewResponse(BaseModel):
    user: UserProfileResponse
    units: list[UnitProgressResponse]
    total_vocab_mastered: int
    total_vocab_seen: int
    unresolved_mistakes_count: int
    resolved_mistakes_count: int
    recent_sessions: list[dict]
