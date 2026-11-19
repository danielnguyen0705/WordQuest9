"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { CheckCircle2, Flame, ShieldAlert, Swords, Volume2 } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { speakEnglish } from "@/components/SoundController";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { MistakeItem } from "@/types/game";

export default function MistakeVaultPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  const [mistakes, setMistakes] = useState<MistakeItem[]>([]);
  const [filter, setFilter] = useState<"unresolved" | "resolved" | "all">("unresolved");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/auth");
      return;
    }
    if (user) {
      api
        .getMistakes(true)
        .then(setMistakes)
        .finally(() => setLoading(false));
    }
  }, [authLoading, user, router]);

  const unresolvedCount = mistakes.filter((m) => !m.is_resolved).length;
  const resolvedCount = mistakes.filter((m) => m.is_resolved).length;

  const visible = mistakes.filter((m) => {
    if (filter === "unresolved") return !m.is_resolved;
    if (filter === "resolved") return m.is_resolved;
    return true;
  });

  return (
    <div className="min-h-screen pb-20">
      <Navbar unresolvedMistakes={unresolvedCount} />

      <main className="mx-auto max-w-5xl px-4 pt-8">
        <div className="flex flex-col justify-between gap-5 rounded-3xl border border-rose-500/35 bg-gradient-to-r from-[#281326] via-[#1a1735] to-[#121936] p-6 shadow-2xl sm:flex-row sm:items-center">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-rose-400">
              <ShieldAlert className="h-4 w-4" /> Sổ Tay Lỗi Sai Cá Nhân (Mistake Vault)
            </div>
            <h1 className="mt-1 text-2xl font-black text-white sm:text-3xl">Kho Lỗi Sai &amp; Phục Thù</h1>
            <p className="mt-1.5 text-xs text-slate-300">
              Mọi câu bạn làm sai đều được lưu tại đây. Trả lời đúng liên tiếp trong chế độ{" "}
              <strong className="text-amber-300">Phục Thù</strong> để đánh dấu &ldquo;Đã khắc phục&rdquo;!
            </p>
          </div>

          <Link
            href="/play/revenge"
            className={`rpg-btn flex shrink-0 items-center justify-center gap-2 rounded-2xl px-6 py-4 text-sm font-black shadow-xl ${
              unresolvedCount > 0
                ? "bg-gradient-to-r from-rose-500 to-amber-400 text-slate-950 shadow-rose-500/30 hover:brightness-110"
                : "pointer-events-none bg-slate-800 text-slate-500"
            }`}
          >
            <Swords className="h-5 w-5" />
            {unresolvedCount > 0 ? `LUYỆN LẠI ${unresolvedCount} CÂU SAI` : "KHÔNG CÓ CÂU SAI"}
          </Link>
        </div>

        {/* Filter Tabs */}
        <div className="mt-6 flex flex-wrap gap-2">
          {[
            { id: "unresolved", label: `Chưa khắc phục (${unresolvedCount})` },
            { id: "resolved", label: `Đã khắc phục (${resolvedCount})` },
            { id: "all", label: `Tất cả (${mistakes.length})` },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setFilter(t.id as "unresolved" | "resolved" | "all")}
              className={`rounded-xl px-4 py-2 text-xs font-bold transition ${
                filter === t.id
                  ? "bg-indigo-600 text-white shadow"
                  : "border border-slate-700 bg-slate-900/70 text-slate-400 hover:text-white"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Mistake Cards */}
        {loading ? (
          <div className="py-16 text-center text-slate-400">Đang tải Kho Lỗi Sai...</div>
        ) : visible.length === 0 ? (
          <div className="mt-8 rounded-3xl border border-slate-800 bg-slate-900/50 p-12 text-center">
            <CheckCircle2 className="mx-auto h-12 w-12 text-emerald-400" />
            <h3 className="mt-3 text-lg font-extrabold text-white">Tuyệt vời! Sổ tay đang rất sạch</h3>
            <p className="mt-1 text-xs text-slate-400">
              Không có mục nào trong danh sách lọc hiện tại. Hãy tiếp tục chinh phục các Unit trên bản đồ!
            </p>
          </div>
        ) : (
          <div className="mt-6 space-y-4">
            {visible.map((m) => (
              <div
                key={m.id}
                className={`rounded-2xl border p-5 ${
                  m.is_resolved
                    ? "border-emerald-500/35 bg-emerald-950/20"
                    : "border-rose-500/30 bg-slate-900/80"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => speakEnglish(m.target_word)}
                      className="flex items-center gap-1.5 rounded-xl bg-indigo-600/30 px-3 py-1 text-sm font-black text-white hover:bg-indigo-600/50"
                    >
                      <Volume2 className="h-4 w-4 text-cyan-300" /> {m.target_word}
                    </button>
                    {m.unit_id && (
                      <span className="rounded-lg bg-slate-800 px-2.5 py-1 text-xs font-bold text-slate-300">
                        Unit {m.unit_id}
                      </span>
                    )}
                    <span className="rounded-lg bg-slate-800 px-2.5 py-1 text-xs font-semibold text-amber-300">
                      {m.question_type}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-rose-500/20 px-3 py-0.5 text-xs font-bold text-rose-300">
                      Sai {m.mistake_count} lần
                    </span>
                    {m.is_resolved ? (
                      <span className="flex items-center gap-1 rounded-full bg-emerald-500/20 px-3 py-0.5 text-xs font-bold text-emerald-300">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Đã khắc phục
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 rounded-full bg-amber-500/20 px-3 py-0.5 text-xs font-bold text-amber-200">
                        <Flame className="h-3.5 w-3.5" /> Chuỗi đúng: {m.consecutive_correct_revenge}/
                        {m.mastery_threshold}
                      </span>
                    )}
                  </div>
                </div>

                <p className="mt-3 text-sm font-bold text-slate-100">{m.prompt_text}</p>
                <div className="mt-2 text-xs text-emerald-300">
                  <strong>Đáp án đúng:</strong> {m.correct_answer}
                </div>
                {m.explanation_vi && <p className="mt-1.5 text-xs text-slate-400">{m.explanation_vi}</p>}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
