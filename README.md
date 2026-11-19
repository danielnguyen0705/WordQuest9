# ⚔️ Word Quest 9 — Vượt Ải Từ Vựng Tiếng Anh 9 (Global Success)

Ứng dụng web học từ vựng **Tiếng Anh 9 hiện hành (Global Success, Units 1 – 12)** theo phong cách **Gamified Vocabulary RPG / Dungeon Run**, xây dựng trên kiến trúc **Microservices (FastAPI) + Official MCP Server + Next.js 15 + PostgreSQL**.

## ✨ Tính năng nổi bật
- **Bản Đồ 12 Vùng Đất (Units 1 – 12):** Hơn **540 từ vựng** kèm IPA, nghĩa tiếng Việt, ví dụ ngữ cảnh, **Word Family** và hơn **520+ câu hỏi** được trích xuất trực tiếp từ bộ tài liệu Tiếng Anh 9 Global Success.
- **Phiên chơi 2 Giai đoạn (~20 câu hỏi):**
  1. **Nạp thẻ Flashcard 3D:** Lật thẻ mượt với Framer Motion, phát âm chuẩn US/UK (có tốc độ chậm) qua Web Speech API, hiển thị Word Family & tự đánh giá.
  2. **Đấu trường 20 câu hỏi biến thiên (5 dạng bài):** Nghe chọn từ (`listening`), Dịch Anh–Việt (`translation_en_vi`), Dịch Việt–Anh (`translation_vi_en`), Trắc nghiệm ngữ cảnh (`contextual_mcq`) và Biến đổi từ loại (`word_form` — hỗ trợ cả chọn A/B/C/D lẫn chế độ tự gõ đáp án).
- **Chế độ Sinh Tử 1 Mạng (Hardcore Sudden-Death — Mặc định):** Sai bất kỳ 1 câu nào → lập tức hồi sinh từ câu 1 với **toàn bộ 20 câu và đáp án A/B/C/D được xáo trộn lại** chống học vẹt. Vượt trọn vẹn 20/20 mới nhận huy hiệu & mở khóa Unit kế tiếp. (Có kèm chế độ **Luyện Tập Tự Do** không reset).
- **Kho Lỗi Sai & Chế độ Phục Thù (Mistake Vault):** Mọi câu làm sai tự động ghi vào sổ tay cá nhân. Vào chế độ **Phục Thù** trả lời đúng liên tiếp đạt ngưỡng thành thạo mới được đánh dấu *"Đã khắc phục"*.
- **Tài khoản & Lưu trữ Bền vững:** Đăng ký / Đăng nhập JWT + bcrypt, lưu trọn đời XP, Level, Streak, Combo, tiến độ Unit & Kho Lỗi Sai trên PostgreSQL.
- **Tách biệt Dữ liệu & Chuẩn MCP:** Không hardcode từ vựng. Hỗ trợ nạp dữ liệu JSON (`unit_X_vocab.json`, `unit_X_questions.json`) qua CLI, REST API hoặc MCP Tool `import_notebook_data`.

## 🚀 Khởi chạy nhanh

### 1. Bằng Docker Compose (Full Microservices + PostgreSQL + MCP + Frontend)
```bash
cp .env.example .env
docker compose up --build -d
```

### 2. Chạy Local Development (Windows PowerShell)
```powershell
.\scripts\dev-local.ps1
```

### 3. Nạp / Cập nhật học liệu JSON từ Notebook "TIẾNG ANH 9"
Xem hướng dẫn bộ Prompt chuẩn tại [docs/NOTEBOOK_EXTRACTION_GUIDE.md](./docs/NOTEBOOK_EXTRACTION_GUIDE.md), sau đó chạy:
```bash
python backend/scripts/import_notebook_data.py --data-dir data
```

## 📚 Tài liệu đi kèm
- [Kiến trúc Microservices & MCP](./docs/ARCHITECTURE.md)
- [Bộ Prompt trích xuất Notebook "TIẾNG ANH 9"](./docs/NOTEBOOK_EXTRACTION_GUIDE.md)
- [Hướng dẫn Deploy lên Web](./docs/DEPLOYMENT.md)
- [Tài liệu MCP Server](./backend/mcp_server/README.md)
