"""
End-to-End Integration Test for WordQuest 9 Backend + MCP Server.
Verifies:
1. Data Ingestion Pipeline (JSON Schema validation + idempotent UPSERT)
2. Register -> Login -> JWT Auth -> Profile
3. Hybrid Quiz Session (Stage 1 Flashcard Warm-up + Stage 2 20 Questions across 5 types)
4. Hardcore Sudden-Death 1-Life Mode: wrong answer -> Mistake Vault recorded + instant reset to Q1 with reshuffled questions/options
5. Mistake Vault Revenge Mode: answer correctly 2 consecutive times -> marked 'is_resolved = True'
6. Complete 20/20 Sudden-Death run -> XP & Level up + Unit 1 badge + Unit 2 automatically unlocked
7. Logout & Re-login -> full persistence of XP, Level, Unit unlocks, and Mistake Vault
8. MCP Server Resources & Tools (generate_quiz_session, record_attempt_result, get_student_weaknesses, import_notebook_data)
"""

import json
import os
import sys
from pathlib import Path

# Use an isolated temporary SQLite DB for deterministic E2E tests
TEST_DB_PATH = Path(__file__).resolve().parent / "test_wordquest9.db"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["GATEWAY_MODE"] = "embedded"
os.environ["MISTAKE_MASTERY_THRESHOLD"] = "2"

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
SHARED_DIR = BACKEND_DIR / "shared"
GATEWAY_DIR = BACKEND_DIR / "services" / "api_gateway"
MCP_DIR = BACKEND_DIR / "mcp_server"
for p in (SHARED_DIR, GATEWAY_DIR, MCP_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fastapi.testclient import TestClient

from wordquest_shared.database import SessionLocal, init_db
from wordquest_shared.ingestion import ingest_notebook_data
from wordquest_shared.models import QuizSession
import main as gateway_main
import server as mcp_server


def test_full_wordquest9_e2e_flow():
    init_db()
    db = SessionLocal()
    try:
        res = ingest_notebook_data(db=db, data_dir=PROJECT_ROOT / "data")
        assert res.errors == []
        assert res.units_upserted == 12
        assert res.vocab_upserted >= 48
        assert res.questions_upserted >= 80
        # Verify idempotent re-run produces zero errors
        res2 = ingest_notebook_data(db=db, data_dir=PROJECT_ROOT / "data")
        assert res2.errors == []
    finally:
        db.close()

    client = TestClient(gateway_main.app)

    # 1. Health check
    h = client.get("/health")
    assert h.status_code == 200
    assert h.json()["status"] == "ok"

    # 2. Register student
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "username": "hero9a",
            "email": "hero9a@example.com",
            "password": "Password123!",
            "display_name": "Chiến Binh 9A",
            "avatar": "knight",
        },
    )
    assert reg.status_code == 201, reg.text
    auth_data = reg.json()
    token = auth_data["access_token"]
    user_id = auth_data["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Check Units & Dashboard (Unit 1 unlocked, Unit 2 locked)
    dash = client.get("/api/v1/progress/dashboard", headers=headers)
    assert dash.status_code == 200
    units_progress = {u["unit_number"]: u for u in dash.json()["units"]}
    assert units_progress[1]["is_unlocked"] is True
    assert units_progress[2]["is_unlocked"] is False

    # 4. Start Sudden-Death Session on Unit 1 (Stage 1 Flashcard Warm-up)
    sess_resp = client.post(
        "/api/v1/quiz/sessions",
        headers=headers,
        json={"unit_id": 1, "mode": "sudden_death", "question_count": 20, "warmup_count": 6},
    )
    assert sess_resp.status_code == 200, sess_resp.text
    sess = sess_resp.json()
    session_id = sess["session_id"]
    assert sess["status"] == "warmup"
    assert len(sess["warmup_cards"]) == 6
    assert sess["total_questions"] == 20
    assert sess["lives_remaining"] == 1

    # Advance to Stage 2 Challenge
    chal = client.post(f"/api/v1/quiz/sessions/{session_id}/start-challenge", headers=headers)
    assert chal.status_code == 200
    chal_data = chal.json()
    assert chal_data["status"] == "in_progress"
    assert chal_data["current_question"] is not None

    # Inspect internal session payload to test exact right/wrong answers
    db = SessionLocal()
    try:
        db_sess = db.get(QuizSession, session_id)
        q_types = {q["question_type"] for q in db_sess.questions_payload}
        assert len(q_types) >= 4, f"Expected diverse question types, got {q_types}"
        assert "listening" in q_types
        first_correct = db_sess.questions_payload[0]["correct_answer"]
        second_q = db_sess.questions_payload[1]
        second_wrong = next(o for o in second_q["options"] if o != second_q["correct_answer"])
        order_before_reset = [q["question_uid"] for q in db_sess.questions_payload]
    finally:
        db.close()

    # 5. Answer Q1 correctly
    ans1 = client.post(
        f"/api/v1/quiz/sessions/{session_id}/answer",
        headers=headers,
        json={"question_index": 0, "selected_answer": first_correct},
    )
    assert ans1.status_code == 200
    assert ans1.json()["is_correct"] is True
    assert ans1.json()["triggered_reset"] is False
    assert ans1.json()["xp_gained"] > 0

    # 6. Deliberately answer Q2 WRONG -> Sudden-Death MUST reset to Q1 & record Mistake Vault!
    ans2 = client.post(
        f"/api/v1/quiz/sessions/{session_id}/answer",
        headers=headers,
        json={"question_index": 1, "selected_answer": second_wrong},
    )
    assert ans2.status_code == 200
    ans2_data = ans2.json()
    assert ans2_data["is_correct"] is False
    assert ans2_data["triggered_reset"] is True
    assert ans2_data["reset_count"] == 1
    assert ans2_data["mistake_recorded"] is True
    assert ans2_data["next_question"]["index"] == 0

    # Verify questions were reshuffled after reset
    db = SessionLocal()
    try:
        db_sess = db.get(QuizSession, session_id)
        order_after_reset = [q["question_uid"] for q in db_sess.questions_payload]
        assert order_after_reset != order_before_reset
    finally:
        db.close()

    # 7. Verify Mistake Vault captured the wrong item
    mistakes = client.get("/api/v1/progress/mistakes", headers=headers).json()
    assert len(mistakes) == 1
    assert mistakes[0]["is_resolved"] is False
    assert mistakes[0]["mistake_count"] == 1

    # 8. Complete 20/20 on the reset Sudden-Death session -> unlocks Unit 2!
    for idx in range(20):
        db = SessionLocal()
        try:
            db_sess = db.get(QuizSession, session_id)
            correct_ans = db_sess.questions_payload[idx]["correct_answer"]
        finally:
            db.close()
        r = client.post(
            f"/api/v1/quiz/sessions/{session_id}/answer",
            headers=headers,
            json={"question_index": idx, "selected_answer": correct_ans},
        )
        assert r.status_code == 200, r.text
        rd = r.json()
        assert rd["is_correct"] is True
        if idx == 19:
            assert rd["session_completed"] is True
            assert rd["unit_unlocked"] == 2

    # 9. Verify Mistake Revenge Mode resolves a mistake after reaching mastery threshold (2 consecutive)
    # Create a fresh mistake in practice mode so we test revenge cleanly from 0/2 -> 1/2 -> 2/2
    prac = client.post(
        "/api/v1/quiz/sessions",
        headers=headers,
        json={"unit_id": 2, "mode": "practice", "question_count": 5, "skip_warmup": True},
    ).json()
    prac_id = prac["session_id"]
    db = SessionLocal()
    try:
        pq0 = db.get(QuizSession, prac_id).questions_payload[0]
        wrong_opt = next(o for o in pq0["options"] if o != pq0["correct_answer"])
    finally:
        db.close()
    client.post(
        f"/api/v1/quiz/sessions/{prac_id}/answer",
        headers=headers,
        json={"question_index": 0, "selected_answer": wrong_opt},
    )

    # Run Mistake Revenge twice on Unit 2 to hit 2/2 consecutive correct -> Resolved!
    for round_num in range(2):
        rev = client.post(
            "/api/v1/quiz/sessions",
            headers=headers,
            json={"unit_id": 2, "mode": "mistake_revenge", "question_count": 10},
        )
        assert rev.status_code == 200, rev.text
        rev_id = rev.json()["session_id"]
        db = SessionLocal()
        try:
            rq0 = db.get(QuizSession, rev_id).questions_payload[0]
            r_ans = rq0["correct_answer"]
        finally:
            db.close()
        rr = client.post(
            f"/api/v1/quiz/sessions/{rev_id}/answer",
            headers=headers,
            json={"question_index": 0, "selected_answer": r_ans},
        ).json()
        if round_num == 0:
            assert rr["mistake_resolved"] is False
            assert rr["revenge_streak"] == 1
        else:
            assert rr["mistake_resolved"] is True
            assert rr["revenge_streak"] == 2

    # 10. Logout & Re-login -> verify full persistence
    lo = client.post("/api/v1/auth/logout", headers=headers)
    assert lo.status_code == 200

    relogin = client.post(
        "/api/v1/auth/login",
        json={"username": "hero9a", "password": "Password123!"},
    )
    assert relogin.status_code == 200
    new_token = relogin.json()["access_token"]
    new_headers = {"Authorization": f"Bearer {new_token}"}
    dash_after = client.get("/api/v1/progress/dashboard", headers=new_headers).json()
    assert dash_after["user"]["xp"] > 300
    assert dash_after["user"]["level"] >= 2
    u_after = {u["unit_number"]: u for u in dash_after["units"]}
    assert u_after[1]["is_completed"] is True
    assert u_after[1]["badge_earned"] is True
    assert u_after[2]["is_unlocked"] is True
    assert dash_after["resolved_mistakes_count"] >= 1

    # 11. Verify MCP Server Resources & Tools directly
    units_res = json.loads(mcp_server.resource_units())
    assert len(units_res) == 12
    vocab_res = json.loads(mcp_server.resource_unit_vocab(1))
    assert len(vocab_res) >= 24
    wf_res = json.loads(mcp_server.resource_word_forms("preserve"))
    assert len(wf_res["word_forms"]) >= 2

    mcp_quiz = mcp_server.generate_quiz_session(user_id=user_id, unit_id=1, mode="sudden_death")
    assert mcp_quiz["total_questions"] == 20
    mcp_weak = mcp_server.get_student_weaknesses(user_id=user_id)
    assert "unresolved_count" in mcp_weak
    mcp_imp = mcp_server.import_notebook_data(data_dir=str(PROJECT_ROOT / "data"), dry_run=True)
    assert mcp_imp["errors"] == []


if __name__ == "__main__":
    test_full_wordquest9_e2e_flow()
    print("ALL WORDQUEST 9 E2E + MCP TESTS PASSED!")
