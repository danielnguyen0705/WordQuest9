"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, RotateCw, Sparkles, Swords, Volume2 } from "lucide-react";
import type { VocabularyItem } from "@/types/game";
import { soundFX, speakEnglish } from "@/components/SoundController";

interface FlashcardDeckProps {
  cards: VocabularyItem[];
  unitNumber: number | null;
  mode: string;
  onCompleteWarmup: () => void;
}

const POS_BADGE: Record<string, string> = {
  noun: "bg-sky-500/20 text-sky-300 border-sky-400/30",
  verb: "bg-emerald-500/20 text-emerald-300 border-emerald-400/30",
  adj: "bg-amber-500/20 text-amber-300 border-amber-400/30",
  adv: "bg-purple-500/20 text-purple-300 border-purple-400/30",
  phrase: "bg-pink-500/20 text-pink-300 border-pink-400/30",
};

export function FlashcardDeck({ cards, unitNumber, mode, onCompleteWarmup }: FlashcardDeckProps) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [reviewedIds, setReviewedIds] = useState<Set<number>>(new Set());
  const [accent, setAccent] = useState<"en-US" | "en-GB">("en-US");

  const card = cards[index];
  if (!card) {
    return (
      <div className="text-center py-12">
        <button
          onClick={onCompleteWarmup}
          className="rpg-btn rounded-2xl bg-emerald-500 px-8 py-4 font-extrabold text-slate-950"
        >
          Vào Thử Thách 20 Câu Ngay!
        </button>
      </div>
    );
  }

  const handleFlip = () => {
    soundFX.flip();
    setFlipped((f) => !f);
  };

  const handleMark = (knowWell: boolean) => {
    const nextReviewed = new Set(reviewedIds);
    nextReviewed.add(card.id);
    setReviewedIds(nextReviewed);
    if (knowWell) soundFX.correct();

    if (index + 1 < cards.length) {
      setFlipped(false);
      setIndex((i) => i + 1);
    } else {
      setFlipped(false);
    }
  };

  const allReviewed = reviewedIds.size >= cards.length;

  return (
    <div className="mx-auto max-w-2xl">
      {/* Phase Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-indigo-500/30 bg-slate-900/80 px-5 py-3.5">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-400">
            <Sparkles className="h-4 w-4" /> Giai đoạn 1 · Nạp Thẻ Từ Vựng (Warm-up)
          </div>
          <h2 className="mt-0.5 text-lg font-extrabold text-white">
            Unit {unitNumber} · Thẻ {index + 1} / {cards.length}
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setAccent((a) => (a === "en-US" ? "en-GB" : "en-US"))}
            className="rounded-lg border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs font-bold text-slate-200 hover:border-indigo-400"
          >
            Giọng: {accent === "en-US" ? "🇺🇸 US" : "🇬🇧 UK"}
          </button>
          <button
            type="button"
            onClick={onCompleteWarmup}
            className="rounded-lg border border-emerald-500/40 bg-emerald-500/15 px-3 py-1 text-xs font-bold text-emerald-300 hover:bg-emerald-500/25"
          >
            Bỏ qua nạp thẻ →
          </button>
        </div>
      </div>

      {/* Progress Dots */}
      <div className="mb-5 flex gap-1.5">
        {cards.map((c, idx) => (
          <button
            key={c.id}
            onClick={() => {
              setIndex(idx);
              setFlipped(false);
            }}
            className={`h-2 flex-1 rounded-full transition-all ${
              idx === index
                ? "bg-amber-400 shadow-[0_0_10px_#f59e0b]"
                : reviewedIds.has(c.id)
                  ? "bg-emerald-500"
                  : "bg-slate-700"
            }`}
          />
        ))}
      </div>

      {/* 3D Flip Card */}
      <div className="perspective-1000 relative h-[390px] w-full cursor-pointer select-none" onClick={handleFlip}>
        <motion.div
          animate={{ rotateY: flipped ? 180 : 0 }}
          transition={{ duration: 0.45, type: "spring", stiffness: 220, damping: 22 }}
          className="preserve-3d relative h-full w-full"
        >
          {/* FRONT */}
          <div className="backface-hidden absolute inset-0 flex flex-col items-center justify-between rounded-3xl border-2 border-indigo-400/35 bg-gradient-to-br from-[#162044] via-[#121936] to-[#0c1228] p-7 shadow-2xl">
            <div className="flex w-full items-center justify-between">
              <span
                className={`rounded-full border px-3 py-1 text-xs font-bold uppercase ${
                  POS_BADGE[card.pos] || "bg-slate-700 text-slate-200 border-slate-600"
                }`}
              >
                {card.pos}
              </span>
              <span className="text-xs font-medium text-slate-400">Nhấn vào thẻ để lật mặt sau</span>
            </div>

            <div className="flex flex-col items-center text-center">
              <h3 className="text-4xl font-black tracking-tight text-white sm:text-5xl">{card.word}</h3>
              <p className="mt-3 font-mono text-lg text-emerald-300">{card.ipa}</p>

              <div className="mt-6 flex items-center gap-3" onClick={(e) => e.stopPropagation()}>
                <button
                  type="button"
                  onClick={() => speakEnglish(card.word, { lang: accent, rate: 0.95 })}
                  className="rpg-btn flex items-center gap-2 rounded-2xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500"
                >
                  <Volume2 className="h-4 w-4" /> Nghe phát âm
                </button>
                <button
                  type="button"
                  onClick={() => speakEnglish(card.word, { lang: accent, rate: 0.65 })}
                  className="rpg-btn rounded-2xl border border-slate-600 bg-slate-800 px-3.5 py-2.5 text-xs font-bold text-slate-200 hover:border-emerald-400"
                >
                  🐢 Chậm
                </button>
              </div>
            </div>

            <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-300">
              <RotateCw className="h-3.5 w-3.5" /> Lật xem nghĩa, ví dụ & Word Family
            </div>
          </div>

          {/* BACK */}
          <div className="backface-hidden rotate-y-180 absolute inset-0 flex flex-col justify-between overflow-y-auto rounded-3xl border-2 border-emerald-400/45 bg-gradient-to-br from-[#0e2929] via-[#111c36] to-[#0b1024] p-7 shadow-2xl">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-extrabold text-emerald-300">
                  {card.word} <span className="font-mono font-normal text-slate-400">{card.ipa}</span>
                </span>
                <span className="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-bold text-emerald-300">
                  {card.pos}
                </span>
              </div>

              <div className="mt-4 rounded-2xl border border-emerald-500/30 bg-emerald-950/40 p-4">
                <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-400">
                  Nghĩa tiếng Việt (SGK Tiếng Anh 9)
                </div>
                <div className="mt-1 text-2xl font-extrabold text-white">{card.meaning_vi}</div>
              </div>

              <div className="mt-4 rounded-2xl border border-slate-700/70 bg-slate-900/70 p-4">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-300">
                    Ví dụ ngữ cảnh
                  </span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      speakEnglish(card.example_en, { lang: accent, rate: 0.92 });
                    }}
                    className="flex items-center gap-1 text-xs font-semibold text-indigo-300 hover:text-white"
                  >
                    <Volume2 className="h-3.5 w-3.5" /> Đọc câu
                  </button>
                </div>
                <p className="mt-1.5 text-sm font-medium text-slate-100">{card.example_en}</p>
                <p className="mt-1 text-xs text-slate-400">{card.example_vi}</p>
              </div>

              {card.word_forms.length > 0 && (
                <div className="mt-4">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-amber-400">
                    Họ từ (Word Family)
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {card.word_forms.map((wf, i) => (
                      <span
                        key={i}
                        className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-200"
                      >
                        <strong className="text-white">{wf.word}</strong> ({wf.pos}): {wf.meaning_vi}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>

      {/* Self-assessment & Advance Controls */}
      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={() => handleMark(false)}
          className="rpg-btn flex-1 rounded-2xl border border-amber-500/40 bg-amber-500/15 py-3.5 text-sm font-bold text-amber-200 hover:bg-amber-500/25"
        >
          🔄 Lưu ý từ này, xem tiếp
        </button>
        <button
          type="button"
          onClick={() => handleMark(true)}
          className="rpg-btn flex-1 flex items-center justify-center gap-2 rounded-2xl border border-emerald-400/50 bg-emerald-500/20 py-3.5 text-sm font-bold text-emerald-200 hover:bg-emerald-500/30"
        >
          <CheckCircle2 className="h-4 w-4" /> Đã nhớ kỹ!
        </button>
      </div>

      {/* Enter Battle CTA */}
      <div className="mt-6">
        <button
          type="button"
          onClick={onCompleteWarmup}
          className={`rpg-btn flex w-full items-center justify-center gap-2.5 rounded-2xl py-4 text-base font-black shadow-xl transition ${
            allReviewed
              ? "bg-gradient-to-r from-emerald-400 via-teal-400 to-cyan-400 text-slate-950 shadow-emerald-500/30 hover:brightness-110"
              : "border border-indigo-400/40 bg-indigo-600/80 text-white hover:bg-indigo-500"
          }`}
        >
          <Swords className="h-5 w-5" />
          {mode === "sudden_death"
            ? "BẮT ĐẦU VƯỢT ẢI SINH TỬ (20 CÂU · 1 MẠNG)!"
            : "BẮT ĐẦU LUYỆN TẬP 20 CÂU HỎI!"}
        </button>
      </div>
    </div>
  );
}
