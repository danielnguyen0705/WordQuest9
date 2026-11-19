# WordQuest 9 MCP Server

Official Model Context Protocol (MCP) Server built with the Official MCP Python SDK (`mcp`).

## Exposed MCP Resources
- `wordquest://units` — List all Tiếng Anh 9 Units (1–12) with vocab & question bank counts.
- `wordquest://units/{unit_id}/vocab` — Full vocabulary + IPA + Vietnamese meaning + examples + Word Family for a Unit.
- `wordquest://word-forms/{word}` — Word Family lookup for any English word.
- `wordquest://units/{unit_id}/questions/{question_type}` — Curated Notebook question bank filtered by Unit and type (`all`, `translation_en_vi`, `translation_vi_en`, `contextual_mcq`, `word_form`, `listening`).
- `wordquest://students/{user_id}/mistakes` — Student Mistake Vault (unresolved & resolved mistakes).

## Exposed MCP Tools
- `generate_quiz_session(user_id, unit_id, mode, question_count, warmup_count)` — Creates a hybrid Flashcard Warm-up + 20-question session (`sudden_death` | `practice` | `mistake_revenge`).
- `record_attempt_result(user_id, target_word, question_type, prompt_text, selected_answer, correct_answer, ...)` — Records an answer, updates XP/mastery, and tracks/resolves Mistake Vault entries.
- `get_student_weaknesses(user_id, limit)` — Returns weakest words & question types for targeted review.
- `import_notebook_data(data_dir, unit_filter, dry_run)` — Validates JSON files against JSON Schema and UPSERTs into PostgreSQL.

## Running
```bash
# HTTP Streamable transport (default in Docker Compose, port 8005)
MCP_TRANSPORT=streamable-http python backend/mcp_server/server.py

# Stdio transport (for local MCP clients like Claude Desktop / Antigravity)
MCP_TRANSPORT=stdio python backend/mcp_server/server.py
```
