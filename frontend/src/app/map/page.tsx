"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  Award,
  BookOpen,
  CheckCircle2,
  Flame,
  Lock,
  Shield,
  ShieldAlert,
  Skull,
  Sparkles,
  Swords,
  Trophy,
} from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { DashboardOverview, UnitProgress } from "@/types/game";

export default function WorldMapPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [dashboard, setDashboard] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/auth");
      return;
    }
    if (user) {
      api
        .getDashboard()
        .then(setDashboard)
        .catch((e) => setError(e instanceof Error ? e.message : "Không thể tải bản đồ."))
        .finally(() => setLoading(false));
    }
  }, [authLoading, user, router]);

  if (authLoading || loading) {
    return (
      <div className="min-h-screen">
        <Navbar />
        <div className="py-24 text-center text-slate-400">Đang tải Bản Đồ 12 Vùng Đất...</div>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="min-h-screen">
        <Navbar />
        <div className="mx-auto max-w-lg py-20 text-center">
          <p className="text-rose-400">{error || "Không thể tải dữ liệu."}</p>
        </div>
      </div>
    );
  }

  const u = dashboard.user;
  const xpPct = Math.min(100, Math.round((u.xp_in_level / Math.max(1, u.xp_for_next_level)) * 100));

  return (
    <div className="min-h-screen pb-20">
      <Navbar unresolvedMistakes={dashboard.unresolved_mistakes_count} />

      <main className="mx-auto max-w-6xl px-4 pt-8">
        {/* RPG Hero Stats Banner */}
        <section className="rounded-3xl border border-indigo-400/30 bg-gradient-to-r from-[#151f42] via-[#121a36] to-[#0f242c] p-6 shadow-2xl">
          <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
            <div>
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-400">
                <Sparkles className="h-4 w-4" /> Hồ Sơ Chiến Binh Tiếng Anh 9
              </div>
              <h1 className="mt-1 text-2xl font-black text-white sm:text-3xl">
                Xin chào, {u.display_name}!{" "}
                <span className="ml-1 rounded-xl bg-amber-400/20 px-2.5 py-1 text-base text-amber-300">
                  Level {u.level}
                </span>
              </h1>
              <div className="mt-3 max-w-md">
                <div className="mb-1 flex justify-between text-xs font-bold">
                  <span className="text-slate-300">Kinh nghiệm (XP): {u.xp}</span>
                  <span className="text-emerald-300">
                    {u.xp_in_level} / {u.xp_for_next_level} XP lên cấp
                  </span>
                </div>
                <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-amber-400"
                    style={{ width: `${xpPct}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-2xl border border-slate-700/80 bg-slate-900/75 px-4 py-3 text-center">
                <Flame className="mx-auto h-5 w-5 text-amber-400" />
                <div className="mt-1 text-xl font-black text-white">{u.streak_days} ngày</div>
                <div className="text-[11px] text-slate-400">Streak</div>
              </div>
              <div className="rounded-2xl border border-slate-700/80 bg-slate-900/75 px-4 py-3 text-center">
                <Trophy className="mx-auto h-5 w-5 text-emerald-400" />
                <div className="mt-1 text-xl font-black text-white">x{u.best_combo}</div>
                <div className="text-[11px] text-slate-400">Combo Cao Nhất</div>
              </div>
              <div className="rounded-2xl border border-slate-700/80 bg-slate-900/75 px-4 py-3 text-center">
                <BookOpen className="mx-auto h-5 w-5 text-sky-400" />
                <div className="mt-1 text-xl font-black text-white">{dashboard.total_vocab_mastered}</div>
                <div className="text-[11px] text-slate-400">Từ Đã Thuộc</div>
              </div>
              <Link
                href="/mistakes"
                className="rpg-btn rounded-2xl border border-rose-500/40 bg-rose-500/15 px-4 py-3 text-center hover:bg-rose-500/25"
              >
                <ShieldAlert className="mx-auto h-5 w-5 text-rose-400" />
                <div className="mt-1 text-xl font-black text-rose-200">
                  {dashboard.unresolved_mistakes_count}
                </div>
                <div className="text-[11px] font-bold text-rose-300">Kho Lỗi Sai →</div>
              </Link>
            </div>
          </div>

          {dashboard.unresolved_mistakes_count > 0 && (
            <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-500/40 bg-rose-950/40 px-4 py-3">
              <div className="text-sm text-rose-100">
                🔥 Bạn đang có{" "}
                <strong className="text-rose-300">{dashboard.unresolved_mistakes_count} câu sai chưa khắc phục</strong>{" "}
                trong Kho Lỗi Sai!
              </div>
              <Link
                href="/play/revenge"
                className="rpg-btn rounded-xl bg-gradient-to-r from-rose-500 to-amber-500 px-4 py-2 text-xs font-black text-slate-950"
              >
                ⚔️ Phục Thù Ngay
              </Link>
            </div>
          )}
        </section>

        {/* 12 Units World Map */}
        <section className="mt-10">
          <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-2xl font-black text-white">🗺️ Lộ Trình 12 Vùng Đất (Units 1 – 12)</h2>
              <p className="mt-1 text-sm text-slate-400">
                Vượt qua trọn vẹn 20/20 câu ở chế độ <strong className="text-rose-300">Sinh Tử 1 Mạng</strong> để nhận
                Huy Hiệu &amp; mở khóa Unit tiếp theo!
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
            {dashboard.units.map((unit: UnitProgress, idx: number) => {
              const hasData = unit.vocab_count > 0;
              const canPlay = unit.is_unlocked && hasData;
              const masteryPct =
                unit.vocab_count > 0
                  ? Math.min(100, Math.round((unit.mastered_vocab_count / unit.vocab_count) * 100))
                  : 0;

              return (
                <motion.div
                  key={unit.unit_id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.04 }}
                  className={`relative flex flex-col justify-between overflow-hidden rounded-3xl border p-5 transition ${
                    unit.is_completed
                      ? "border-amber-400/50 bg-gradient-to-b from-[#1a2548] to-[#101830]"
                      : canPlay
                        ? "border-emerald-400/40 bg-gradient-to-b from-[#142042] to-[#0e152b] shadow-lg shadow-emerald-500/5"
                        : "border-slate-800 bg-slate-900/55 opacity-75"
                  }`}
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <span
                        className="rounded-xl px-3 py-1 text-xs font-black text-slate-950"
                        style={{ backgroundColor: unit.theme_color }}
                      >
                        UNIT {unit.unit_number}
                      </span>

                      {unit.badge_earned ? (
                        <span className="flex items-center gap-1 rounded-full border border-amber-400/50 bg-amber-400/15 px-2.5 py-0.5 text-xs font-bold text-amber-300">
                          <Award className="h-3.5 w-3.5" /> Đã Chinh Phục
                        </span>
                      ) : !unit.is_unlocked ? (
                        <span className="flex items-center gap-1 rounded-full bg-slate-800 px-2.5 py-0.5 text-xs font-bold text-slate-400">
                          <Lock className="h-3.5 w-3.5" /> Chưa Mở Khóa
                        </span>
                      ) : !hasData ? (
                        <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs font-bold text-slate-400">
                          Chưa nạp dữ liệu
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-bold text-emerald-300">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Sẵn Sàng
                        </span>
                      )}
                    </div>

                    <div className="mt-3 text-xs font-bold uppercase tracking-wider text-indigo-300">
                      {unit.realm_name}
                    </div>
                    <h3 className="mt-0.5 text-lg font-black text-white">{unit.title}</h3>
                    <div className="text-xs font-medium text-slate-400">{unit.title_vi}</div>
                    <p className="mt-2.5 line-clamp-2 text-xs leading-relaxed text-slate-300">
                      {unit.description}
                    </p>

                    <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
                      <span>📚 {unit.vocab_count} từ vựng</span>
                      <span>❓ {unit.question_count} câu hỏi kho</span>
                    </div>

                    {hasData && (
                      <div className="mt-3">
                        <div className="mb-1 flex justify-between text-[11px] font-semibold">
                          <span className="text-slate-400">Độ thành thạo từ vựng</span>
                          <span className="text-emerald-300">
                            {unit.mastered_vocab_count}/{unit.vocab_count} ({masteryPct}%)
                          </span>
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                          <div
                            className="h-full rounded-full bg-emerald-400"
                            style={{ width: `${masteryPct}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="mt-5 flex flex-col gap-2">
                    {canPlay ? (
                      <>
                        <Link
                          href={`/play/${unit.unit_number}?mode=sudden_death`}
                          className="rpg-btn flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-400 to-teal-400 py-2.5 text-xs font-black text-slate-950 hover:brightness-110"
                        >
                          <Skull className="h-4 w-4" /> Vượt Ải Sinh Tử (20 Câu)
                        </Link>
                        <div className="grid grid-cols-2 gap-2">
                          <Link
                            href={`/play/${unit.unit_number}?mode=practice`}
                            className="rpg-btn flex items-center justify-center gap-1 rounded-xl border border-sky-500/40 bg-sky-500/10 py-2 text-xs font-bold text-sky-200 hover:bg-sky-500/20"
                          >
                            <Shield className="h-3.5 w-3.5" /> Luyện Tự Do
                          </Link>
                          <Link
                            href={`/vocabulary?unit=${unit.unit_number}`}
                            className="rpg-btn flex items-center justify-center gap-1 rounded-xl border border-slate-700 bg-slate-800/80 py-2 text-xs font-bold text-slate-200 hover:border-indigo-400"
                          >
                            <BookOpen className="h-3.5 w-3.5" /> Xem Từ
                          </Link>
                        </div>
                      </>
                    ) : !unit.is_unlocked ? (
                      <div className="rounded-xl border border-slate-800 bg-slate-950/60 py-2.5 text-center text-xs font-semibold text-slate-500">
                        Vượt ải Unit {unit.unit_number - 1} Sinh Tử để mở khóa
                      </div>
                    ) : (
                      <div className="rounded-xl border border-slate-800 bg-slate-950/60 py-2.5 text-center text-xs font-semibold text-slate-500">
                        Nạp file unit_{unit.unit_number}_vocab.json để chơi
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </section>

        {/* Recent Sessions History */}
        {dashboard.recent_sessions.length > 0 && (
          <section className="mt-12 rounded-3xl border border-slate-800 bg-slate-900/60 p-6">
            <h3 className="flex items-center gap-2 text-lg font-black text-white">
              <Swords className="h-5 w-5 text-indigo-400" /> Lịch Sử Vượt Ải Gần Đây
            </h3>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="py-2 pr-4">Vùng đất</th>
                    <th className="py-2 pr-4">Chế độ</th>
                    <th className="py-2 pr-4">Trạng thái</th>
                    <th className="py-2 pr-4">Đúng / Tổng</th>
                    <th className="py-2 pr-4">Hồi sinh</th>
                    <th className="py-2">XP nhận</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-200">
                  {dashboard.recent_sessions.map((s) => (
                    <tr key={s.session_id}>
                      <td className="py-2.5 pr-4 font-bold">
                        {s.unit_id ? `Unit ${s.unit_id}` : "Kho Lỗi Sai"}
                      </td>
                      <td className="py-2.5 pr-4">
                        {s.mode === "sudden_death"
                          ? "💀 Sinh Tử"
                          : s.mode === "mistake_revenge"
                            ? "🔥 Phục Thù"
                            : "🛡️ Luyện Tập"}
                      </td>
                      <td className="py-2.5 pr-4">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${
                            s.status === "completed"
                              ? "bg-emerald-500/20 text-emerald-300"
                              : "bg-amber-500/20 text-amber-300"
                          }`}
                        >
                          {s.status === "completed" ? "Hoàn thành" : "Đang chơi"}
                        </span>
                      </td>
                      <td className="py-2.5 pr-4 font-bold">
                        {s.correct_count}/{s.total_questions}
                      </td>
                      <td className="py-2.5 pr-4 text-rose-300">{s.reset_count}</td>
                      <td className="py-2.5 font-extrabold text-amber-300">+{s.xp_earned} XP</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
