# Hướng dẫn Trích xuất Học liệu từ Notebook "TIẾNG ANH 9" (Global Success)

WordQuest 9 áp dụng nguyên tắc **tách biệt hoàn toàn dữ liệu học liệu khỏi mã nguồn**. Toàn bộ từ vựng và ngân hàng câu hỏi của từng Unit (Units 1 – 12) được lưu dưới dạng JSON tại:
- `data/vocab/unit_X_vocab.json`
- `data/questions/unit_X_questions.json`

Để xuất dữ liệu **vừa nhiều, vừa sát SGK Tiếng Anh 9 Global Success** mà không bị giới hạn độ dài câu trả lời (output truncation), hãy chạy tách **2 bước cho mỗi Unit** trên Notebook `"TIẾNG ANH 9"` (NotebookLM).

---

## Lệnh 1: Xuất Toàn bộ Từ vựng + Word Form của Unit [X]

Lưu kết quả JSON vào: `data/vocab/unit_[X]_vocab.json`

```text
Dựa trên tài liệu TIẾNG ANH 9, hãy trích xuất TOÀN BỘ từ vựng và cụm từ quan trọng của Unit [X]. Trả về duy nhất một mảng JSON hợp lệ (không giải thích thêm) với các trường: `unit` (số), `unit_title` (tên Unit), `word` (từ gốc), `pos` (noun/verb/adj/adv/phrase), `ipa` (phiên âm), `meaning_vi` (nghĩa tiếng Việt chuẩn SGK lớp 9), `example_en` (câu ví dụ sát bài học), `example_vi` (dịch nghĩa ví dụ), `word_forms` (mảng các biến thể từ loại gồm `word`, `pos`, `meaning_vi`).
```

---

## Lệnh 2: Xuất Ngân hàng Câu hỏi Đa dạng & Chuyên sâu của Unit [X]

Lưu kết quả JSON vào: `data/questions/unit_[X]_questions.json`  
*(Nếu Unit dài hoặc muốn đạt 50–60 câu/Unit, có thể tách làm 2 lần gọi: Lần 2A cho `translation_en_vi` + `translation_vi_en`, Lần 2B cho `contextual_mcq` + `word_form`, rồi gộp chung vào 1 mảng JSON).*

```text
Dựa trên toàn bộ từ vựng của Unit [X] trong tài liệu TIẾNG ANH 9, hãy tạo bộ 40 câu hỏi trắc nghiệm và điền từ chất lượng cao (chia đều cho 4 dạng: `translation_en_vi`, `translation_vi_en`, `contextual_mcq`, `word_form`). Yêu cầu: câu hỏi phải bám sát ngữ cảnh SGK Tiếng Anh 9, đáp án nhiễu (`distractors`) phải cùng từ loại và có tính phân loại cao (tránh đáp án ngớ ngẩn), phần `word_form` phải có từ gốc trong ngoặc và đòi hỏi chia đúng từ loại theo ngữ pháp câu. Trả về duy nhất một mảng JSON hợp lệ theo schema: `unit` (số), `target_word` (từ vựng đang kiểm tra), `question_type` (`translation_en_vi` | `translation_vi_en` | `contextual_mcq` | `word_form`), `prompt_text` (nội dung câu hỏi / câu có chỗ trống `___`), `correct_answer` (đáp án đúng), `distractors` (mảng 3 đáp án nhiễu cùng từ loại), `explanation_vi` (giải thích ngắn gọn bằng tiếng Việt tại sao chọn đáp án này và dịch nghĩa câu).
```

---

## Cách Nạp dữ liệu vào PostgreSQL (Data Ingestion Pipeline)

Sau khi đặt file `unit_X_vocab.json` vào `data/vocab/` và `unit_X_questions.json` vào `data/questions/`, bạn có **3 cách** để kiểm tra JSON Schema và tự động `UPSERT` vào cơ sở dữ liệu:

### Cách 1: Chạy Python CLI trực tiếp
```bash
# Kiểm tra và nạp toàn bộ thư mục data/
python backend/scripts/import_notebook_data.py --data-dir data

# Hoặc chỉ nạp riêng Unit 3
python backend/scripts/import_notebook_data.py --data-dir data --unit 3

# Chỉ kiểm tra hợp lệ JSON Schema (không ghi vào DB)
python backend/scripts/import_notebook_data.py --data-dir data --dry-run
```

### Cách 2: Chạy trong Docker Compose
```bash
docker compose exec vocabulary-service python /app/scripts/import_notebook_data.py --data-dir /app/data
```

### Cách 3: Gọi qua MCP Tool `import_notebook_data`
Khi kết nối bất kỳ MCP Client nào tới WordQuest 9 MCP Server (`http://localhost:8005/mcp` hoặc stdio), gọi tool:
```json
{
  "tool": "import_notebook_data",
  "arguments": {
    "data_dir": "data",
    "unit_filter": 3,
    "dry_run": false
  }
}
```

### Cách 4: Gọi REST Endpoint của Vocabulary Service
```bash
curl -X POST http://localhost:8000/api/v1/content/import \
  -H "Content-Type: application/json" \
  -d '{"unit_filter": 3, "dry_run": false}'
```
