import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

export const metadata: Metadata = {
  title: "Word Quest 9 — Vượt Ải Từ Vựng Tiếng Anh 9 (Global Success)",
  description:
    "Ứng dụng web học từ vựng Tiếng Anh 9 Global Success theo phong cách RPG vượt ải sinh tử 20 câu, Flashcard tương tác, 5 dạng bài tập & Kho Lỗi Sai cá nhân.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body className="antialiased selection:bg-emerald-400/30 selection:text-emerald-200">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
