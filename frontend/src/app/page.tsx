"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { BookOpen, Flame, Headphones, ShieldAlert, Skull, Sparkles, Swords, Trophy } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { useAuth } from "@/lib/auth-context";

export default function LandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.replace("/map");
    }
  }, [loading, user, router]);

  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 py-12 sm:py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center"
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/35 bg-emerald-500/10 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-emerald-300">
            <Sparkles className="h-3.5 w-3.5" /> SGK Tiếng Anh 9 · Global Success (Units 1 – 12)
          </div>
          <h1 className="mx-auto mt-6 max-w-4xl text-4xl font-black tracking-tight text-white sm:text-6xl">
            Học Từ Vựng Lớp 9 Như Một{" "}
            <span className="bg-gradient-to-r from-emerald-400 via-cyan-300 to-amber-300 bg-clip-text text-transparent">
              Chiến Binh Vượt Ải
            </span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-slate-300 sm:text-lg">
            Nạp thẻ Flashcard 3D có phát âm chuẩn, bước vào Đấu Trường Sinh Tử 20 câu hỏi biến thiên 5 dạng bài
            và quét sạch mọi lỗ hổng từ vựng với Kho Lỗi Sai cá nhân hóa.
          </p>

          <div className="mt-9 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/auth?tab=register"
              className="rpg-btn flex items-center gap-2 rounded-2xl bg-gradient-to-r from-emerald-400 to-teal-400 px-8 py-4 text-base font-black text-slate-950 shadow-xl shadow-emerald-500/25 hover:brightness-110"
            >
              <Swords className="h-5 w-5" /> Tạo Nhân Vật &amp; Bắt Đầu
            </Link>
            <Link
              href="/auth?tab=login"
              className="rpg-btn rounded-2xl border border-indigo-400/40 bg-indigo-600/20 px-8 py-4 text-base font-bold text-indigo-100 hover:bg-indigo-600/30"
            >
              Đã Có Tài Khoản · Đăng Nhập
            </Link>
          </div>
        </motion.div>

        <div className="mt-16 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              icon: BookOpen,
              title: "Flashcard 3D & Word Family",
              desc: "Lật thẻ học phiên âm IPA, phát âm chuẩn US/UK, ví dụ ngữ cảnh và trọn bộ họ từ (Noun/Verb/Adj/Adv).",
              color: "text-emerald-400",
            },
            {
              icon: Skull,
              title: "Sinh Tử 1 Mạng (20 Câu)",
              desc: "Sai 1 câu lập tức hồi sinh từ câu 1 với thứ tự câu & đáp án A/B/C/D xáo trộn hoàn toàn chống học vẹt.",
              color: "text-rose-400",
            },
            {
              icon: Headphones,
              title: "5 Dạng Bài Biến Thiên",
              desc: "Phối trộn Nghe chọn từ, Dịch Anh-Việt, Việt-Anh, Trắc nghiệm ngữ cảnh và Word Form sát đề thi vào 10.",
              color: "text-cyan-400",
            },
            {
              icon: ShieldAlert,
              title: "Kho Lỗi Sai & Phục Thù",
              desc: "Tự động lưu mọi câu làm sai. Trả lời đúng liên tiếp trong chế độ Phục Thù mới được xóa vết sai!",
              color: "text-amber-400",
            },
          ].map((f, i) => {
            const Icon = f.icon;
            return (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * i }}
                className="rounded-3xl border border-indigo-500/20 bg-slate-900/70 p-6 backdrop-blur"
              >
                <Icon className={`h-8 w-8 ${f.color}`} />
                <h3 className="mt-4 text-lg font-extrabold text-white">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-400">{f.desc}</p>
              </motion.div>
            );
          })}
        </div>

        <div className="mt-12 flex flex-wrap items-center justify-center gap-6 rounded-3xl border border-slate-800 bg-slate-900/50 px-6 py-5 text-sm text-slate-300">
          <span className="flex items-center gap-2 font-bold">
            <Trophy className="h-4 w-4 text-amber-400" /> Lưu vết XP, Level &amp; Huy hiệu trọn đời
          </span>
          <span className="flex items-center gap-2 font-bold">
            <Flame className="h-4 w-4 text-orange-400" /> Đồng bộ đa thiết bị với PostgreSQL
          </span>
        </div>
      </main>
    </div>
  );
}
