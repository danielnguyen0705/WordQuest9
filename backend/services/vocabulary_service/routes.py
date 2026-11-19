from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from wordquest_shared.database import get_db
from wordquest_shared.ingestion import ingest_notebook_data
from wordquest_shared.models import QuestionBank, Unit, Vocabulary, WordForm
from wordquest_shared.schemas import (
    ImportDataRequest,
    ImportDataResult,
    QuestionBankItemSchema,
    UnitSummarySchema,
    VocabularyItemSchema,
    WordFormSchema,
)

router = APIRouter(prefix="/api/v1/content", tags=["Vocabulary & Content"])


@router.get("/units", response_model=list[UnitSummarySchema])
def list_units(db: Session = Depends(get_db)):
    units = db.execute(select(Unit).order_by(Unit.unit_number)).scalars().all()
    vocab_counts = dict(
        db.execute(select(Vocabulary.unit_id, func.count(Vocabulary.id)).group_by(Vocabulary.unit_id)).all()
    )
    q_counts = dict(
        db.execute(select(QuestionBank.unit_id, func.count(QuestionBank.id)).group_by(QuestionBank.unit_id)).all()
    )
    return [
        UnitSummarySchema(
            id=u.id,
            unit_number=u.unit_number,
            title=u.title,
            title_vi=u.title_vi,
            realm_name=u.realm_name,
            description=u.description,
            theme_color=u.theme_color,
            icon=u.icon,
            required_xp=u.required_xp,
            vocab_count=int(vocab_counts.get(u.id, 0)),
            question_count=int(q_counts.get(u.id, 0)),
        )
        for u in units
    ]


@router.get("/units/{unit_id}/vocab", response_model=list[VocabularyItemSchema])
def get_unit_vocabulary(
    unit_id: int,
    search: str | None = Query(default=None),
    pos: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    unit = db.get(Unit, unit_id)
    if not unit:
        raise HTTPException(status_code=404, detail=f"Unit {unit_id} không tồn tại.")

    stmt = (
        select(Vocabulary)
        .options(selectinload(Vocabulary.word_forms))
        .where(Vocabulary.unit_id == unit_id)
        .order_by(Vocabulary.word)
    )
    if pos:
        stmt = stmt.where(Vocabulary.pos == pos.strip().lower())
    vocabs = db.execute(stmt).scalars().all()
    if search:
        kw = search.strip().lower()
        vocabs = [
            v
            for v in vocabs
            if kw in v.word.lower() or kw in v.meaning_vi.lower()
        ]

    return [
        VocabularyItemSchema(
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
        for v in vocabs
    ]


@router.get("/word-forms/{word}", response_model=list[WordFormSchema])
def lookup_word_forms(word: str, db: Session = Depends(get_db)):
    kw = word.strip().lower()
    vocabs = db.execute(
        select(Vocabulary)
        .options(selectinload(Vocabulary.word_forms))
        .where(func.lower(Vocabulary.word) == kw)
    ).scalars().all()

    results: list[WordFormSchema] = []
    seen: set[tuple[str, str]] = set()
    for v in vocabs:
        if (v.word.lower(), v.pos) not in seen:
            results.append(WordFormSchema(word=v.word, pos=v.pos, meaning_vi=v.meaning_vi))
            seen.add((v.word.lower(), v.pos))
        for wf in v.word_forms:
            if (wf.word.lower(), wf.pos) not in seen:
                results.append(WordFormSchema(id=wf.id, word=wf.word, pos=wf.pos, meaning_vi=wf.meaning_vi))
                seen.add((wf.word.lower(), wf.pos))

    if not results:
        wfs = db.execute(
            select(WordForm).where(func.lower(WordForm.word) == kw)
        ).scalars().all()
        for wf in wfs:
            results.append(WordFormSchema(id=wf.id, word=wf.word, pos=wf.pos, meaning_vi=wf.meaning_vi))

    return results


@router.get("/units/{unit_id}/questions", response_model=list[QuestionBankItemSchema])
def get_unit_questions(
    unit_id: int,
    question_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(QuestionBank).where(QuestionBank.unit_id == unit_id)
    if question_type:
        stmt = stmt.where(QuestionBank.question_type == question_type.strip())
    stmt = stmt.limit(limit)
    rows = db.execute(stmt).scalars().all()
    return [
        QuestionBankItemSchema(
            id=q.id,
            unit_id=q.unit_id,
            vocabulary_id=q.vocabulary_id,
            target_word=q.target_word,
            question_type=q.question_type,
            prompt_text=q.prompt_text,
            correct_answer=q.correct_answer,
            distractors=list(q.distractors or []),
            explanation_vi=q.explanation_vi,
            source=q.source,
        )
        for q in rows
    ]


@router.post("/import", response_model=ImportDataResult)
def trigger_data_import(payload: ImportDataRequest, db: Session = Depends(get_db)):
    return ingest_notebook_data(
        db=db,
        data_dir=payload.data_dir,
        unit_filter=payload.unit_filter,
        dry_run=payload.dry_run,
    )
