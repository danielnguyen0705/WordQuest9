"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { FlashcardDeck } from "@/components/FlashcardDeck";
import { QuizArena } from "@/components/QuizArena";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { SessionState } from "@/types/game";

export default function PlayUnitPage({ params }: { params: Promise<{ unit: string }> }) {
  const { unit } = use(params);
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const isRevenge = unit === "revenge";
  const unitNumber = isRevenge ? null : Number(unit);
  const requestedMode = isRevenge
    ? "mistake_revenge"
    : searchParams.get("mode") === "practice"
      ? "practice"
      : "sudden_death";
  const revengeUnitFilter = isRevenge && searchParams.get("unit") ? Number(searchParams.get("unit")) : null;

  const [session, setSession] = useState<SessionState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/auth");
      return;
    }
    if (!user) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .startSession({
        unit_id: isRevenge ? revengeUnitFilter : unitNumber,
        mode: requestedMode,
        question_count: 20,
        warmup_count: isRevenge ? 0 : 6,
        skip_warmup: isRevenge,
      })
      .then((s) => {
        if (!cancelled) setSession(s);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Không thể khởi tạo phiên chơi.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [authLoading, user, isRevenge, unitNumber, requestedMode, revengeUnitFilter, router]);

  const handleCompleteWarmup = async () => {
    if (!session) return;
    try {
      const updated = await api.startChallenge(session.session_id);
      setSession(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không thể bắt đầu thử thách.");
    }
  };

  return (
    <div className="min-h-screen pb-20">
      <Navbar />
      <main className="mx-auto max-w-4xl px-4 pt-6">
        <div className="mb-5">
          <Link
            href={isRevenge ? "/mistakes" : "/map"}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-slate-400 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" /> {isRevenge ? "Quay lại Kho Lỗi Sai" : "Quay lại Bản Đồ 12 Unit"}
          </Link>
        </div>

        {loading ? (
          <div className="rounded-3xl border border-slate-800 bg-slate-900/70 py-24 text-center text-slate-300">
            ⚔️ Đang chuẩn bị thẻ từ vựng &amp; sinh bộ đề 20 câu hỏi biến thiên...
          </div>
        ) : error ? (
          <div className="rounded-3xl border border-rose-500/40 bg-rose-950/30 p-8 text-center">
            <p className="text-base font-bold text-rose-200">{error}</p>
            <Link
              href="/map"
              className="mt-5 inline-block rounded-xl bg-slate-800 px-5 py-2.5 text-xs font-bold text-white hover:bg-slate-700"
            >
              Về Bản Đồ
            </Link>
          </div>
        ) : session && session.status === "warmup" ? (
          <FlashcardDeck
            cards={session.warmup_cards}
            unitNumber={session.unit_id}
            mode={session.mode}
            onCompleteWarmup={handleCompleteWarmup}
          />
        ) : session ? (
          <QuizArena initialSession={session} />
        ) : null}
      </main>
    </div>
  );
}
