import hashlib
import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import QuestionBank, Unit, Vocabulary, WordForm
from .schemas import ImportDataResult


def compute_question_hash(unit_id: int, question_type: str, prompt_text: str, correct_answer: str) -> str:
    raw = f"{unit_id}|{question_type.strip().lower()}|{prompt_text.strip().lower()}|{correct_answer.strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _load_schema(schema_path: Path) -> Draft202012Validator:
    with schema_path.open("r", encoding="utf-8") as f:
        schema = json.load(f)
    return Draft202012Validator(schema)


def _extract_unit_num_from_filename(filename: str) -> int | None:
    match = re.search(r"unit_(\d+)_", filename)
    return int(match.group(1)) if match else None


def ingest_notebook_data(
    db: Session,
    data_dir: str | Path | None = None,
    unit_filter: int | None = None,
    dry_run: bool = False,
) -> ImportDataResult:
    base = Path(data_dir or settings.data_dir).resolve()
    schema_dir = base / "schema"
    vocab_dir = base / "vocab"
    questions_dir = base / "questions"
    catalog_path = base / "units_catalog.json"

    errors: list[str] = []
    units_upserted = 0
    vocab_files_processed = 0
    vocab_upserted = 0
    word_forms_upserted = 0
    question_files_processed = 0
    questions_upserted = 0

    # 1. Upsert Units catalog
    if catalog_path.exists():
        with catalog_path.open("r", encoding="utf-8") as f:
            catalog = json.load(f)
        for item in catalog:
            unit_num = int(item["unit_number"])
            if unit_filter is not None and unit_num != unit_filter:
                continue
            if not dry_run:
                existing = db.get(Unit, unit_num)
                if existing:
                    existing.title = item["title"]
                    existing.title_vi = item.get("title_vi", "")
                    existing.realm_name = item.get("realm_name", "")
                    existing.description = item.get("description", "")
                    existing.theme_color = item.get("theme_color", "#10b981")
                    existing.icon = item.get("icon", "book")
                    existing.required_xp = int(item.get("required_xp", 0))
                else:
                    db.add(
                        Unit(
                            id=unit_num,
                            unit_number=unit_num,
                            title=item["title"],
                            title_vi=item.get("title_vi", ""),
                            realm_name=item.get("realm_name", ""),
                            description=item.get("description", ""),
                            theme_color=item.get("theme_color", "#10b981"),
                            icon=item.get("icon", "book"),
                            required_xp=int(item.get("required_xp", 0)),
                        )
                    )
            units_upserted += 1
        if not dry_run:
            db.flush()

    vocab_validator = _load_schema(schema_dir / "vocab.schema.json")
    question_validator = _load_schema(schema_dir / "questions.schema.json")

    # 2. Scan & UPSERT vocabularies + word_forms
    if vocab_dir.exists():
        for vf in sorted(vocab_dir.glob("unit_*_vocab.json")):
            file_unit = _extract_unit_num_from_filename(vf.name)
            if unit_filter is not None and file_unit != unit_filter:
                continue
            try:
                with vf.open("r", encoding="utf-8") as f:
                    items = json.load(f)
            except Exception as exc:
                errors.append(f"{vf.name}: Invalid JSON ({exc})")
                continue

            val_errs = list(vocab_validator.iter_errors(items))
            if val_errs:
                for ve in val_errs[:5]:
                    errors.append(f"{vf.name}: Schema error at {list(ve.path)} - {ve.message}")
                continue

            vocab_files_processed += 1
            for entry in items:
                unit_num = int(entry["unit"])
                if not dry_run:
                    unit_obj = db.get(Unit, unit_num)
                    if not unit_obj:
                        unit_obj = Unit(
                            id=unit_num,
                            unit_number=unit_num,
                            title=entry["unit_title"],
                        )
                        db.add(unit_obj)
                        db.flush()
                        units_upserted += 1

                    word_clean = entry["word"].strip()
                    existing_vocab = db.execute(
                        select(Vocabulary).where(
                            Vocabulary.unit_id == unit_num,
                            Vocabulary.word == word_clean,
                        )
                    ).scalar_one_or_none()

                    if existing_vocab:
                        existing_vocab.pos = entry["pos"].strip()
                        existing_vocab.ipa = entry["ipa"].strip()
                        existing_vocab.meaning_vi = entry["meaning_vi"].strip()
                        existing_vocab.example_en = entry["example_en"].strip()
                        existing_vocab.example_vi = entry["example_vi"].strip()
                        vocab_obj = existing_vocab
                    else:
                        vocab_obj = Vocabulary(
                            unit_id=unit_num,
                            word=word_clean,
                            pos=entry["pos"].strip(),
                            ipa=entry["ipa"].strip(),
                            meaning_vi=entry["meaning_vi"].strip(),
                            example_en=entry["example_en"].strip(),
                            example_vi=entry["example_vi"].strip(),
                        )
                        db.add(vocab_obj)
                        db.flush()

                    vocab_upserted += 1

                    for wf in entry.get("word_forms", []):
                        wf_word = wf["word"].strip()
                        wf_pos = wf["pos"].strip()
                        existing_wf = db.execute(
                            select(WordForm).where(
                                WordForm.vocabulary_id == vocab_obj.id,
                                WordForm.word == wf_word,
                                WordForm.pos == wf_pos,
                            )
                        ).scalar_one_or_none()
                        if existing_wf:
                            existing_wf.meaning_vi = wf["meaning_vi"].strip()
                        else:
                            db.add(
                                WordForm(
                                    vocabulary_id=vocab_obj.id,
                                    word=wf_word,
                                    pos=wf_pos,
                                    meaning_vi=wf["meaning_vi"].strip(),
                                )
                            )
                        word_forms_upserted += 1
                else:
                    vocab_upserted += 1
                    word_forms_upserted += len(entry.get("word_forms", []))

            if not dry_run:
                db.flush()

    # Build lookup map (unit_id, word.lower()) -> vocabulary.id
    vocab_lookup: dict[tuple[int, str], int] = {}
    if not dry_run:
        for v in db.execute(select(Vocabulary)).scalars().all():
            vocab_lookup[(v.unit_id, v.word.strip().lower())] = v.id

    # 3. Scan & UPSERT question_bank
    if questions_dir.exists():
        for qf in sorted(questions_dir.glob("unit_*_questions.json")):
            file_unit = _extract_unit_num_from_filename(qf.name)
            if unit_filter is not None and file_unit != unit_filter:
                continue
            try:
                with qf.open("r", encoding="utf-8") as f:
                    q_items = json.load(f)
            except Exception as exc:
                errors.append(f"{qf.name}: Invalid JSON ({exc})")
                continue

            val_errs = list(question_validator.iter_errors(q_items))
            if val_errs:
                for ve in val_errs[:5]:
                    errors.append(f"{qf.name}: Schema error at {list(ve.path)} - {ve.message}")
                continue

            question_files_processed += 1
            for q in q_items:
                unit_num = int(q["unit"])
                target_word = q["target_word"].strip()
                q_type = q["question_type"].strip()
                prompt_text = q["prompt_text"].strip()
                correct_answer = q["correct_answer"].strip()
                distractors = [d.strip() for d in q["distractors"]]
                explanation_vi = q["explanation_vi"].strip()
                c_hash = compute_question_hash(unit_num, q_type, prompt_text, correct_answer)

                if not dry_run:
                    vocab_id = vocab_lookup.get((unit_num, target_word.lower()))
                    existing_q = db.execute(
                        select(QuestionBank).where(QuestionBank.content_hash == c_hash)
                    ).scalar_one_or_none()
                    if existing_q:
                        existing_q.vocabulary_id = vocab_id
                        existing_q.target_word = target_word
                        existing_q.distractors = distractors
                        existing_q.explanation_vi = explanation_vi
                    else:
                        db.add(
                            QuestionBank(
                                unit_id=unit_num,
                                vocabulary_id=vocab_id,
                                target_word=target_word,
                                question_type=q_type,
                                prompt_text=prompt_text,
                                correct_answer=correct_answer,
                                distractors=distractors,
                                explanation_vi=explanation_vi,
                                source="notebook",
                                content_hash=c_hash,
                            )
                        )
                questions_upserted += 1

    if not dry_run:
        db.commit()

    return ImportDataResult(
        dry_run=dry_run,
        units_upserted=units_upserted,
        vocab_files_processed=vocab_files_processed,
        vocab_upserted=vocab_upserted,
        word_forms_upserted=word_forms_upserted,
        question_files_processed=question_files_processed,
        questions_upserted=questions_upserted,
        errors=errors,
    )
