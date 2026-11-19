import hashlib
import random
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from wordquest_shared.models import (
    QuestionBank,
    StudentMistake,
    StudentVocabProgress,
    Vocabulary,
)


def compute_mistake_key(target_word: str, question_type: str, prompt_text: str) -> str:
    raw = f"{target_word.strip().lower()}|{question_type.strip().lower()}|{prompt_text.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def shuffle_options(correct_answer: str, distractors: list[str]) -> list[str]:
    clean_correct = correct_answer.strip()
    unique_distractors: list[str] = []
    seen = {clean_correct.lower()}
    for d in distractors:
        dc = d.strip()
        if dc and dc.lower() not in seen:
            unique_distractors.append(dc)
            seen.add(dc.lower())
    options = [clean_correct] + unique_distractors[:3]
    random.shuffle(options)
    return options


def reshuffle_session_questions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Reshuffle question order and A/B/C/D options on Sudden-Death reset to prevent rote memorization."""
    cloned = [dict(q) for q in questions]
    random.shuffle(cloned)
    for idx, q in enumerate(cloned):
        q["index"] = idx
        q["options"] = shuffle_options(q["correct_answer"], q.get("distractors", []))
    return cloned


def _pick_same_pos_distractors(
    target_vocab: Vocabulary,
    pool: list[Vocabulary],
    field: str = "word",
    count: int = 3,
) -> list[str]:
    target_val = getattr(target_vocab, field).strip().lower()
    same_pos = [
        getattr(v, field).strip()
        for v in pool
        if v.id != target_vocab.id
        and v.pos == target_vocab.pos
        and getattr(v, field).strip().lower() != target_val
    ]
    random.shuffle(same_pos)
    picked: list[str] = []
    seen = {target_val}
    for cand in same_pos:
        if cand.lower() not in seen:
            picked.append(cand)
            seen.add(cand.lower())
        if len(picked) >= count:
            return picked

    others = [
        getattr(v, field).strip()
        for v in pool
        if v.id != target_vocab.id and getattr(v, field).strip().lower() != target_val
    ]
    random.shuffle(others)
    for cand in others:
        if cand.lower() not in seen:
            picked.append(cand)
            seen.add(cand.lower())
        if len(picked) >= count:
            break
    return picked


def _build_dynamic_listening_question(vocab: Vocabulary, pool: list[Vocabulary]) -> dict[str, Any]:
    ask_word = random.choice([True, False])
    if ask_word:
        distractors = _pick_same_pos_distractors(vocab, pool, field="word", count=3)
        prompt_text = "Nghe phát âm tiếng Anh và chọn đúng mặt chữ từ vựng tương ứng:"
        correct_answer = vocab.word
        explanation = f"Từ được phát âm là \"{vocab.word}\" ({vocab.ipa}) – {vocab.meaning_vi}."
    else:
        distractors = _pick_same_pos_distractors(vocab, pool, field="meaning_vi", count=3)
        prompt_text = "Nghe phát âm từ vựng tiếng Anh và chọn nghĩa tiếng Việt đúng:"
        correct_answer = vocab.meaning_vi
        explanation = f"Bạn vừa nghe từ \"{vocab.word}\" ({vocab.ipa}), nghĩa là: {vocab.meaning_vi}."

    return {
        "question_uid": str(uuid.uuid4()),
        "question_bank_id": None,
        "vocabulary_id": vocab.id,
        "unit_id": vocab.unit_id,
        "target_word": vocab.word,
        "question_type": "listening",
        "prompt_text": prompt_text,
        "audio_text": vocab.word,
        "ipa": vocab.ipa,
        "input_mode": "mcq",
        "correct_answer": correct_answer,
        "distractors": distractors,
        "options": shuffle_options(correct_answer, distractors),
        "explanation_vi": explanation,
        "source": "dynamic",
        "mistake_id": None,
    }


def _build_dynamic_translation_question(
    vocab: Vocabulary, pool: list[Vocabulary], direction: str
) -> dict[str, Any]:
    if direction == "translation_en_vi":
        distractors = _pick_same_pos_distractors(vocab, pool, field="meaning_vi", count=3)
        prompt_text = f"Chọn nghĩa tiếng Việt đúng nhất cho từ: \"{vocab.word}\""
        correct_answer = vocab.meaning_vi
    else:
        distractors = _pick_same_pos_distractors(vocab, pool, field="word", count=3)
        prompt_text = f"Chọn từ tiếng Anh tương ứng với nghĩa: \"{vocab.meaning_vi}\""
        correct_answer = vocab.word

    return {
        "question_uid": str(uuid.uuid4()),
        "question_bank_id": None,
        "vocabulary_id": vocab.id,
        "unit_id": vocab.unit_id,
        "target_word": vocab.word,
        "question_type": direction,
        "prompt_text": prompt_text,
        "audio_text": vocab.word if direction == "translation_en_vi" else None,
        "ipa": vocab.ipa if direction == "translation_en_vi" else None,
        "input_mode": "mcq",
        "correct_answer": correct_answer,
        "distractors": distractors,
        "options": shuffle_options(correct_answer, distractors),
        "explanation_vi": f"\"{vocab.word}\" ({vocab.pos}, {vocab.ipa}) nghĩa là \"{vocab.meaning_vi}\". Ví dụ: {vocab.example_en}",
        "source": "dynamic",
        "mistake_id": None,
    }


def select_warmup_vocabs(
    db: Session, user_id: str, unit_id: int, warmup_count: int = 6
) -> list[Vocabulary]:
    vocabs = (
        db.execute(
            select(Vocabulary)
            .options(selectinload(Vocabulary.word_forms))
            .where(Vocabulary.unit_id == unit_id)
        )
        .scalars()
        .all()
    )
    if not vocabs or warmup_count <= 0:
        return []

    progress_rows = (
        db.execute(
            select(StudentVocabProgress).where(
                StudentVocabProgress.user_id == user_id,
                StudentVocabProgress.vocabulary_id.in_([v.id for v in vocabs]),
            )
        )
        .scalars()
        .all()
    )
    prog_map = {p.vocabulary_id: p for p in progress_rows}

    # Prioritize unmastered and recently missed words, with randomness for freshness
    scored: list[tuple[tuple[int, int, float], Vocabulary]] = []
    for v in vocabs:
        p = prog_map.get(v.id)
        mastery = p.mastery_level if p else 0
        wrong_priority = -(p.times_wrong if p else 0)
        scored.append(((mastery, wrong_priority, random.random()), v))
    scored.sort(key=lambda x: x[0])
    return [v for _, v in scored[: min(warmup_count, len(scored))]]


def generate_hybrid_unit_questions(
    db: Session,
    unit_id: int,
    warmup_vocabs: list[Vocabulary],
    question_count: int = 20,
) -> list[dict[str, Any]]:
    vocabs = (
        db.execute(
            select(Vocabulary)
            .options(selectinload(Vocabulary.word_forms))
            .where(Vocabulary.unit_id == unit_id)
        )
        .scalars()
        .all()
    )
    vocab_by_word = {v.word.strip().lower(): v for v in vocabs}
    warmup_words = {v.word.strip().lower() for v in warmup_vocabs}

    bank_rows = (
        db.execute(select(QuestionBank).where(QuestionBank.unit_id == unit_id))
        .scalars()
        .all()
    )

    # Target blend for 20 questions across all 5 exercise types:
    # listening (4 dynamic) + contextual_mcq (5) + word_form (4) + translation_en_vi (4) + translation_vi_en (3)
    target_listening = max(2, round(question_count * 0.20))
    target_contextual = max(2, round(question_count * 0.25))
    target_word_form = max(2, round(question_count * 0.20))
    target_en_vi = max(2, round(question_count * 0.20))
    target_vi_en = max(1, question_count - (target_listening + target_contextual + target_word_form + target_en_vi))

    selected: list[dict[str, Any]] = []
    used_prompts: set[str] = set()

    def _from_bank(q: QuestionBank) -> dict[str, Any]:
        v = vocab_by_word.get(q.target_word.strip().lower())
        return {
            "question_uid": str(uuid.uuid4()),
            "question_bank_id": q.id,
            "vocabulary_id": q.vocabulary_id or (v.id if v else None),
            "unit_id": q.unit_id,
            "target_word": q.target_word,
            "question_type": q.question_type,
            "prompt_text": q.prompt_text,
            "audio_text": q.target_word if q.question_type in ("listening", "translation_en_vi") else None,
            "ipa": v.ipa if v else None,
            "input_mode": "mcq",
            "correct_answer": q.correct_answer,
            "distractors": list(q.distractors or []),
            "options": shuffle_options(q.correct_answer, list(q.distractors or [])),
            "explanation_vi": q.explanation_vi,
            "source": q.source,
            "mistake_id": None,
        }

    def _pick_bank_by_type(q_type: str, needed: int) -> None:
        candidates = [q for q in bank_rows if q.question_type == q_type]
        # Boost questions testing the warmup cards first
        prioritized = [q for q in candidates if q.target_word.strip().lower() in warmup_words]
        others = [q for q in candidates if q.target_word.strip().lower() not in warmup_words]
        random.shuffle(prioritized)
        random.shuffle(others)
        ordered = prioritized + others
        taken = 0
        for q in ordered:
            key = q.prompt_text.strip().lower()
            if key in used_prompts:
                continue
            selected.append(_from_bank(q))
            used_prompts.add(key)
            taken += 1
            if taken >= needed:
                break

    _pick_bank_by_type("contextual_mcq", target_contextual)
    _pick_bank_by_type("word_form", target_word_form)
    _pick_bank_by_type("translation_en_vi", target_en_vi)
    _pick_bank_by_type("translation_vi_en", target_vi_en)

    # Generate listening questions dynamically from warmup + unit vocabularies
    listening_candidates = list(warmup_vocabs) + [v for v in vocabs if v.id not in {w.id for w in warmup_vocabs}]
    random.shuffle(listening_candidates)
    for v in listening_candidates[:target_listening]:
        if len(vocabs) >= 4:
            q_obj = _build_dynamic_listening_question(v, vocabs)
            selected.append(q_obj)

    # Fill any remaining slots from unused bank questions first, then dynamic generation
    remaining_bank = [q for q in bank_rows if q.prompt_text.strip().lower() not in used_prompts]
    random.shuffle(remaining_bank)
    for q in remaining_bank:
        if len(selected) >= question_count:
            break
        selected.append(_from_bank(q))
        used_prompts.add(q.prompt_text.strip().lower())

    # If still fewer than question_count, generate dynamic translation/listening questions
    safety_idx = 0
    while len(selected) < question_count and vocabs:
        v = vocabs[safety_idx % len(vocabs)]
        direction = ["translation_en_vi", "translation_vi_en", "listening"][safety_idx % 3]
        if direction == "listening":
            selected.append(_build_dynamic_listening_question(v, vocabs))
        else:
            selected.append(_build_dynamic_translation_question(v, vocabs, direction))
        safety_idx += 1

    selected = selected[:question_count]
    random.shuffle(selected)
    for idx, q in enumerate(selected):
        q["index"] = idx
    return selected


def generate_mistake_revenge_questions(
    db: Session,
    user_id: str,
    unit_id: int | None = None,
    max_questions: int = 20,
) -> list[dict[str, Any]]:
    stmt = (
        select(StudentMistake)
        .where(StudentMistake.user_id == user_id, StudentMistake.is_resolved.is_(False))
        .order_by(StudentMistake.mistake_count.desc(), StudentMistake.last_wrong_at.desc())
    )
    if unit_id is not None:
        stmt = stmt.where(StudentMistake.unit_id == unit_id)

    mistakes = db.execute(stmt.limit(max_questions)).scalars().all()
    questions: list[dict[str, Any]] = []
    for m in mistakes:
        distractors = list(m.distractors or [])
        # Fallback distractors if needed
        if len(distractors) < 3 and m.unit_id:
            unit_vocabs = (
                db.execute(select(Vocabulary).where(Vocabulary.unit_id == m.unit_id))
                .scalars()
                .all()
            )
            extras = [
                v.word if m.question_type != "translation_en_vi" else v.meaning_vi
                for v in unit_vocabs
                if v.word.lower() != m.correct_answer.lower()
                and v.meaning_vi.lower() != m.correct_answer.lower()
            ]
            random.shuffle(extras)
            for ex in extras:
                if ex not in distractors and ex.lower() != m.correct_answer.lower():
                    distractors.append(ex)
                if len(distractors) >= 3:
                    break

        vocab = db.get(Vocabulary, m.vocabulary_id) if m.vocabulary_id else None
        questions.append(
            {
                "question_uid": str(uuid.uuid4()),
                "question_bank_id": m.question_bank_id,
                "vocabulary_id": m.vocabulary_id,
                "unit_id": m.unit_id,
                "target_word": m.target_word,
                "question_type": m.question_type,
                "prompt_text": m.prompt_text,
                "audio_text": m.target_word if m.question_type in ("listening", "translation_en_vi") else None,
                "ipa": vocab.ipa if vocab else None,
                "input_mode": "mcq",
                "correct_answer": m.correct_answer,
                "distractors": distractors[:3],
                "options": shuffle_options(m.correct_answer, distractors[:3]),
                "explanation_vi": m.explanation_vi,
                "source": "mistake_vault",
                "mistake_id": m.id,
            }
        )

    random.shuffle(questions)
    for idx, q in enumerate(questions):
        q["index"] = idx
    return questions
