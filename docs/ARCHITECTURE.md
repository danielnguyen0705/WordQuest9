# Kiến Trúc Hệ Thống WordQuest 9

WordQuest 9 được thiết kế theo kiến trúc **Microservices + Model Context Protocol (MCP) + Tách biệt hoàn toàn Dữ liệu Học liệu**.

## 1. Sơ đồ Tổng quan

```
                        ┌───────────────────────────────┐
                        │  Next.js 15 + Tailwind + FM   │
                        │  Web Speech API + Web Audio   │
                        └───────────────┬───────────────┘
                                        │ HTTPS / JWT
                        ┌───────────────▼───────────────┐
                        │     API Gateway (:8000)       │
                        │  Proxy mode / Embedded mode   │
                        └──┬──────┬──────────┬───────┬──┘
                           │      │          │       │
          ┌────────────────▼┐  ┌──▼────────┐ │  ┌────▼─────────────┐
          │ Identity (:8001)│  │Vocab(:8002)│ │  │ Progress (:8004) │
          │ Auth/JWT/XP/Lv  │  │Units/Words │ │  │ Dashboard/Vault  │
          └────────┬────────┘  └─────┬──────┘ │  └────────┬─────────┘
                   │                 │  ┌─────▼─────────┐ │
                   │                 │  │QuizEng (:8003)│ │
                   │                 │  │20Q/1-Life/Rev │ │
                   │                 │  └───────┬───────┘ │
                   └─────────────────┴──────────┴─────────┘
                                     │ SQLAlchemy 2.0 + Alembic
                        ┌────────────▼────────────┐
                        │     PostgreSQL 16       │
                        │   (Local / Neon / SB)   │
                        └────────────▲────────────┘
                                     │
                        ┌────────────┴────────────┐
                        │   MCP Server (:8005)    │
                        │ Official MCP Python SDK │
                        │  Resources & 4 Tools    │
                        └────────────▲────────────┘
                                     │
                        ┌────────────┴────────────┐
                        │  Data Layer (data/*.json)│
                        │  12 Units Tiếng Anh 9   │
                        └─────────────────────────┘
```

## 2. Cơ sở Dữ liệu (10 bảng quan hệ)
- `users`: Tài khoản, mật khẩu hash (bcrypt), avatar RPG, XP, Level, Streak, Combo.
- `units`: Danh mục 12 Units chuẩn SGK Tiếng Anh 9 Global Success.
- `vocabularies`: Từ vựng tách biệt theo Unit (word, pos, ipa, meaning_vi, example_en, example_vi).
- `word_forms`: Họ từ (Noun/Verb/Adj/Adv) liên kết `vocabulary_id`.
- `question_bank`: Ngân hàng câu hỏi chuẩn Notebook có `content_hash` chống trùng lặp khi `UPSERT`.
- `unit_progress`: Trạng thái mở khóa, hoàn thành, huy hiệu, điểm cao nhất từng Unit của từng học sinh.
- `quiz_sessions`: Trạng thái phiên chơi (`warmup` -> `in_progress` -> `completed`), số mạng, số lần hồi sinh, payload 20 câu.
- `quiz_attempts`: Nhật ký chi tiết từng lượt trả lời.
- `student_vocab_progress`: Độ thành thạo từng từ vựng (`mastery_level` 0–3).
- `student_mistakes`: Kho Lỗi Sai (Mistake Vault) theo dõi số lần sai, chuỗi đúng liên tiếp khi Phục Thù (`consecutive_correct_revenge`) và trạng thái `is_resolved`.

## 3. Giao tiếp Chuẩn MCP (`backend/mcp_server/server.py`)
- **Resources:**
  - `wordquest://units`
  - `wordquest://units/{unit_id}/vocab`
  - `wordquest://word-forms/{word}`
  - `wordquest://units/{unit_id}/questions/{question_type}`
  - `wordquest://students/{user_id}/mistakes`
- **Tools:**
  - `generate_quiz_session`
  - `record_attempt_result`
  - `get_student_weaknesses`
  - `import_notebook_data`
