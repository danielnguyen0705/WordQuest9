# Hướng Dẫn Deploy WordQuest 9 Lên Web Thực Tế

Hệ thống hỗ trợ 2 mô hình triển khai:
1. **Docker Compose All-in-One** (Local hoặc VPS Ubuntu/Debian với 8 container độc lập: Postgres, 4 Microservices, API Gateway, MCP Server, Next.js Frontend).
2. **Cloud Serverless / PaaS** (Frontend trên Vercel/Netlify, Backend API & MCP Server trên Render/Railway, Database trên Neon/Supabase PostgreSQL).

---

## Cách 1: Chạy Đầy Đủ Microservices Bằng Docker Compose (1 Lệnh)

```bash
cd WordQuest9
cp .env.example .env
docker compose up --build -d
```

Sau khi khởi chạy:
- **Frontend Web App:** http://localhost:3000
- **API Gateway & Swagger Docs:** http://localhost:8000/docs
- **Identity Service:** http://localhost:8001/docs
- **Vocabulary Service:** http://localhost:8002/docs
- **Quiz Engine Service:** http://localhost:8003/docs
- **Progress Service:** http://localhost:8004/docs
- **MCP Server (Streamable HTTP):** http://localhost:8005/mcp

---

## Cách 2: Deploy Cloud Miễn Phí / Production

### Bước 1: Tạo Database PostgreSQL trên Neon hoặc Supabase
1. Tạo project mới trên [Neon.tech](https://neon.tech) hoặc [Supabase.com](https://supabase.com).
2. Lấy Connection String và đổi prefix thành `postgresql+psycopg://`:
   ```env
   DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DATABASE?sslmode=require
   ```

### Bước 2: Deploy Backend API & MCP Server lên Render hoặc Railway
- Dự án đã có sẵn file Blueprint `render.yaml` ở thư mục gốc.
- **Trên Render:** Chọn **New → Blueprint**, kết nối repo Git chứa `WordQuest9`, điền biến `DATABASE_URL` (từ Neon/Supabase) và `CORS_ORIGINS` (URL Vercel/Netlify).
  - API chạy ở chế độ `GATEWAY_MODE=embedded` để gộp mượt toàn bộ 4 microservices trong 1 container tiết kiệm chi phí (hoặc deploy tách 4 container với `GATEWAY_MODE=proxy`).
  - Hệ thống tự động khởi tạo bảng và nạp toàn bộ 12 Units từ thư mục `data/` ngay khi boot!
- **Trên Railway:** Tạo 2 services trỏ cùng `backend/Dockerfile` (1 cho API Gateway, 1 cho MCP Server) + 1 PostgreSQL plugin có sẵn trên Railway.

### Bước 3: Deploy Frontend Next.js lên Vercel hoặc Netlify
1. Import thư mục `frontend/` vào [Vercel](https://vercel.com) hoặc [Netlify](https://netlify.com).
2. Cấu hình biến môi trường:
   ```env
   NEXT_PUBLIC_API_URL=https://<your-backend-api-domain>
   ```
3. Deploy! Cập nhật lại `CORS_ORIGINS` trên Backend để chứa domain frontend vừa tạo.
