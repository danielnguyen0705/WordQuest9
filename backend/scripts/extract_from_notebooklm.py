#!/usr/bin/env python3
"""
Automated NotebookLM Extractor for WordQuest 9 ("TIẾNG ANH 9" - Global Success).
Queries NotebookLM via `notebooklm_tools.core.client.NotebookLMClient` (or CLI),
parses & normalizes JSON arrays against WordQuest 9 schemas, and merges/writes:
  - data/vocab/unit_X_vocab.json
  - data/questions/unit_X_questions.json
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

NOTEBOOK_ID = "c32c6f77-c38a-43d0-a39f-782feadc87e2"
VALID_POS = {"noun", "verb", "adj", "adv", "phrase", "prep", "conj", "pron"}
POS_ALIASES = {
    "n": "noun",
    "n.": "noun",
    "noun": "noun",
    "np": "noun",
    "noun phrase": "phrase",
    "v": "verb",
    "v.": "verb",
    "verb": "verb",
    "vp": "phrase",
    "phrasal verb": "phrase",
    "phr.v": "phrase",
    "phr v": "phrase",
    "adj": "adj",
    "adj.": "adj",
    "adjective": "adj",
    "adv": "adv",
    "adv.": "adv",
    "adverb": "adv",
    "prep": "prep",
    "prep.": "prep",
    "preposition": "prep",
    "conj": "conj",
    "conjunction": "conj",
    "pron": "pron",
    "pronoun": "pron",
    "phrase": "phrase",
    "idiom": "phrase",
    "collocation": "phrase",
}

UNIT_TITLES = {
    1: "Local Community",
    2: "City Life",
    3: "Healthy Living for Teens",
    4: "Remembering the Past",
    5: "Our Experiences",
    6: "Vietnamese Lifestyle: Then and Now",
    7: "Natural Wonders of the World",
    8: "Tourism",
    9: "World Englishes",
    10: "Planet Earth",
    11: "Electronic Devices",
    12: "Career Choices",
}

VALID_QTYPES = {
    "translation_en_vi",
    "translation_vi_en",
    "contextual_mcq",
    "word_form",
    "listening",
}


def normalize_pos(raw: str) -> str:
    clean = str(raw or "noun").strip().lower().split("/")[0].split(",")[0].strip("() ")
    return POS_ALIASES.get(clean, clean if clean in VALID_POS else "noun")


def extract_json_array(raw_text: str) -> list:
    """Extract a JSON array from NotebookLM response (which may wrap JSON in markdown or JSON envelope)."""
    text = raw_text.strip()
    # CLI sometimes wraps response in {"value": {"answer": "..."}}
    try:
        envelope = json.loads(text)
        if isinstance(envelope, dict):
            if "value" in envelope and isinstance(envelope["value"], dict) and "answer" in envelope["value"]:
                text = envelope["value"]["answer"]
            elif "answer" in envelope:
                text = envelope["answer"]
        elif isinstance(envelope, list):
            return envelope
    except Exception:
        pass

    # Strip NotebookLM inline citation markers like [1], [2, 3] ONLY outside or carefully if breaking JSON
    # First try direct fenced JSON extraction
    fenced = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    candidates = fenced + [text]
    for cand in candidates:
        s = cand.strip()
        start = s.find("[")
        end = s.rfind("]")
        if start != -1 and end != -1 and end > start:
            snippet = s[start : end + 1]
            try:
                parsed = json.loads(snippet)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                # Try repairing trailing commas or citation markers right after strings
                repaired = re.sub(r",\s*([}\]])", r"\1", snippet)
                try:
                    parsed = json.loads(repaired)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    # Try salvage complete JSON objects inside the array if truncated
                    objs = []
                    for m in re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", repaired):
                        try:
                            objs.append(json.loads(m.group(0)))
                        except Exception:
                            pass
                    if objs:
                        return objs
    return []


def run_nlm_query(nlm_python: str, notebook_id: str, prompt: str, timeout: int = 120) -> str:
    cmd = [
        nlm_python,
        "-m",
        "notebooklm_tools.cli.main",
        "notebook",
        "query",
        notebook_id,
        prompt,
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"nlm query failed ({proc.returncode}): {proc.stderr[:400]}")
    return proc.stdout


def sanitize_vocab_items(raw_items: list, unit_num: int) -> list[dict]:
    unit_title = UNIT_TITLES.get(unit_num, f"Unit {unit_num}")
    cleaned: list[dict] = []
    seen_words: set[str] = set()
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        word = str(item.get("word", "")).strip()
        meaning_vi = str(item.get("meaning_vi", "")).strip()
        if not word or not meaning_vi:
            continue
        key = word.lower()
        if key in seen_words:
            continue
        seen_words.add(key)

        wfs_clean = []
        seen_wf = set()
        for wf in item.get("word_forms") or []:
            if not isinstance(wf, dict):
                continue
            wfw = str(wf.get("word", "")).strip()
            wfm = str(wf.get("meaning_vi", "")).strip()
            wfp = normalize_pos(wf.get("pos", "noun"))
            if wfp not in {"noun", "verb", "adj", "adv", "phrase", "prep"}:
                wfp = "noun"
            if wfw and wfm and (wfw.lower(), wfp) not in seen_wf:
                seen_wf.add((wfw.lower(), wfp))
                wfs_clean.append({"word": wfw, "pos": wfp, "meaning_vi": wfm})

        cleaned.append(
            {
                "unit": unit_num,
                "unit_title": str(item.get("unit_title") or unit_title).strip(),
                "word": word,
                "pos": normalize_pos(item.get("pos", "noun")),
                "ipa": str(item.get("ipa") or f"/{word}/").strip(),
                "meaning_vi": meaning_vi,
                "example_en": str(item.get("example_en") or f"We learned the word '{word}' in Unit {unit_num}.").strip(),
                "example_vi": str(item.get("example_vi") or f"Chúng em đã học từ '{word}' ({meaning_vi}) trong Unit {unit_num}.").strip(),
                "word_forms": wfs_clean,
            }
        )
    return cleaned


def sanitize_question_items(raw_items: list, unit_num: int) -> list[dict]:
    cleaned: list[dict] = []
    seen_prompts: set[str] = set()
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        q_type = str(item.get("question_type", "")).strip()
        if q_type not in VALID_QTYPES:
            continue
        target_word = str(item.get("target_word", "")).strip()
        prompt_text = str(item.get("prompt_text", "")).strip()
        correct = str(item.get("correct_answer", "")).strip()
        explanation = str(item.get("explanation_vi", "")).strip() or f"Đáp án đúng là \"{correct}\"."
        raw_dist = item.get("distractors") or []
        if not target_word or not prompt_text or not correct or not isinstance(raw_dist, list):
            continue

        dist_clean = []
        seen_opt = {correct.lower()}
        for d in raw_dist:
            ds = str(d).strip()
            if ds and ds.lower() not in seen_opt:
                seen_opt.add(ds.lower())
                dist_clean.append(ds)
        if len(dist_clean) < 3:
            continue

        pk = f"{q_type}|{prompt_text.lower()}"
        if pk in seen_prompts:
            continue
        seen_prompts.add(pk)

        cleaned.append(
            {
                "unit": unit_num,
                "target_word": target_word,
                "question_type": q_type,
                "prompt_text": prompt_text,
                "correct_answer": correct,
                "distractors": dist_clean[:3],
                "explanation_vi": explanation,
            }
        )
    return cleaned


def merge_vocab(existing_path: Path, new_items: list[dict]) -> list[dict]:
    existing = []
    if existing_path.exists():
        try:
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    merged_map = {item["word"].strip().lower(): item for item in existing}
    for item in new_items:
        key = item["word"].strip().lower()
        if key not in merged_map:
            merged_map[key] = item
        else:
            # Enrich word_forms if new item has additional ones
            cur_wfs = merged_map[key].get("word_forms", [])
            cur_keys = {(w["word"].lower(), w["pos"]) for w in cur_wfs}
            for wf in item.get("word_forms", []):
                if (wf["word"].lower(), wf["pos"]) not in cur_keys:
                    cur_wfs.append(wf)
                    cur_keys.add((wf["word"].lower(), wf["pos"]))
            merged_map[key]["word_forms"] = cur_wfs
    return sorted(merged_map.values(), key=lambda x: x["word"].lower())


def merge_questions(existing_path: Path, new_items: list[dict]) -> list[dict]:
    existing = []
    if existing_path.exists():
        try:
            existing = json.loads(existing_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    merged_map = {f"{q['question_type']}|{q['prompt_text'].strip().lower()}": q for q in existing}
    for q in new_items:
        key = f"{q['question_type']}|{q['prompt_text'].strip().lower()}"
        if key not in merged_map:
            merged_map[key] = q
    return list(merged_map.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Tiếng Anh 9 Vocab & Questions from NotebookLM.")
    parser.add_argument("--nlm-python", required=True, help="Path to Python executable with notebooklm_tools")
    parser.add_argument("--data-dir", required=True, help="Path to WordQuest9/data directory")
    parser.add_argument("--units", type=str, default="1,2,3,4,5,6,7,8,9,10,11,12", help="Comma-separated units")
    parser.add_argument("--skip-questions", action="store_true")
    parser.add_argument("--skip-vocab", action="store_true")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    vocab_dir = data_dir / "vocab"
    q_dir = data_dir / "questions"
    vocab_dir.mkdir(parents=True, exist_ok=True)
    q_dir.mkdir(parents=True, exist_ok=True)

    units = [int(x.strip()) for x in args.units.split(",") if x.strip()]

    for u in units:
        title = UNIT_TITLES.get(u, f"Unit {u}")
        print(f"\n=== Extracting Unit {u}: {title} ===", flush=True)

        if not args.skip_vocab:
            vocab_prompt = (
                f"Dựa trên tài liệu TIẾNG ANH 9 (SGK Global Success và các phiếu bài tập GS9), "
                f"hãy trích xuất TỐI ĐA (ít nhất 35 đến 50 từ) TOÀN BỘ từ vựng, cụm danh từ, cụm động từ (phrasal verbs) "
                f"và thành ngữ quan trọng xuất hiện trong Unit {u} ({title}) từ tất cả các phần "
                f"(Getting Started, A Closer Look 1 & 2, Communication, Skills 1 & 2, Looking Back). "
                f"Trả về DUY NHẤT một mảng JSON hợp lệ (không giải thích thêm, không có citation [1]) với đúng các trường: "
                f"unit (số {u}), unit_title (\"{title}\"), word (từ gốc), pos (chỉ dùng 1 trong: noun, verb, adj, adv, phrase), "
                f"ipa (phiên âm), meaning_vi (nghĩa tiếng Việt chuẩn SGK lớp 9), example_en (câu ví dụ sát bài học), "
                f"example_vi (dịch nghĩa ví dụ), word_forms (mảng các biến thể từ loại gồm word, pos, meaning_vi)."
            )
            try:
                out = run_nlm_query(args.nlm_python, NOTEBOOK_ID, vocab_prompt)
                raw_v = extract_json_array(out)
                clean_v = sanitize_vocab_items(raw_v, u)
                v_path = vocab_dir / f"unit_{u}_vocab.json"
                if clean_v:
                    merged_v = merge_vocab(v_path, clean_v)
                    v_path.write_text(json.dumps(merged_v, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"  [OK] Unit {u} vocab: extracted {len(clean_v)}, total saved = {len(merged_v)}", flush=True)
                else:
                    print(f"  [WARN] Unit {u} vocab returned 0 parsed items. Preview: {out[:200]}", flush=True)
            except Exception as exc:
                print(f"  [ERR] Unit {u} vocab failed: {exc}", flush=True)
            time.sleep(1.5)

        if not args.skip_questions:
            q_prompt = (
                f"Dựa trên toàn bộ từ vựng của Unit {u} ({title}) trong tài liệu TIẾNG ANH 9, "
                f"hãy tạo bộ 32 đến 40 câu hỏi trắc nghiệm và điền từ chất lượng cao "
                f"(chia đều cho 4 dạng: translation_en_vi, translation_vi_en, contextual_mcq, word_form). "
                f"Yêu cầu: câu hỏi bám sát ngữ cảnh SGK Tiếng Anh 9, mảng distractors có ĐÚNG 3 đáp án nhiễu cùng từ loại "
                f"và có tính phân loại cao, phần word_form phải có chỗ trống ___ và từ gốc viết HOA trong ngoặc đơn (ví dụ: (PRESERVE)). "
                f"Trả về DUY NHẤT một mảng JSON hợp lệ (không giải thích ngoài JSON, không có citation) với đúng các trường: "
                f"unit (số {u}), target_word, question_type (translation_en_vi | translation_vi_en | contextual_mcq | word_form), "
                f"prompt_text, correct_answer, distractors (mảng 3 chuỗi), explanation_vi."
            )
            try:
                out = run_nlm_query(args.nlm_python, NOTEBOOK_ID, q_prompt)
                raw_q = extract_json_array(out)
                clean_q = sanitize_question_items(raw_q, u)
                q_path = q_dir / f"unit_{u}_questions.json"
                if clean_q:
                    merged_q = merge_questions(q_path, clean_q)
                    q_path.write_text(json.dumps(merged_q, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"  [OK] Unit {u} questions: extracted {len(clean_q)}, total saved = {len(merged_q)}", flush=True)
                else:
                    print(f"  [WARN] Unit {u} questions returned 0 parsed items. Preview: {out[:200]}", flush=True)
            except Exception as exc:
                print(f"  [ERR] Unit {u} questions failed: {exc}", flush=True)
            time.sleep(1.5)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
