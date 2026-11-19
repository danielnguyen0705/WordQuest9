"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { BookOpen, Search, Volume2 } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { speakEnglish } from "@/components/SoundController";
import { api } from "@/lib/api";
import type { VocabularyItem } from "@/types/game";

function VocabularyBrowser() {
  const searchParams = useSearchParams();
  const initialUnit = Number(searchParams.get("unit")) || 1;
  const [unitId, setUnitId] = useState(initialUnit);
  const [search, setSearch] = useState("");
  const [posFilter, setPosFilter] = useState("");
  const [items, setItems] = useState<VocabularyItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .getUnitVocab(unitId, search || undefined, posFilter || undefined)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [unitId, search, posFilter]);

  return (
    <main className="mx-auto max-w-6xl px-4 pt-8">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-400">
            <BookOpen className="h-4 w-4" /> Sổ Tay Từ Vựng &amp; Word Family
          </div>
          <h1 className="mt-1 text-2xl font-black text-white sm:text-3xl">
            Kho Từ Vựng Tiếng Anh 9 · Unit {unitId}
          </h1>
        </div>
        <div className="text-xs font-bold text-slate-400">Hiển thị {items.length} mục từ</div>
      </div>

      {/* Unit Pills 1-12 */}
      <div className="mt-5 flex flex-wrap gap-1.5">
        {Array.from({ length: 12 }, (_, i) => i + 1).map((u) => (
          <button
            key={u}
            onClick={() => setUnitId(u)}
            className={`rounded-xl px-3.5 py-1.5 text-xs font-extrabold transition ${
              unitId === u
                ? "bg-emerald-400 text-slate-950 shadow-lg shadow-emerald-500/20"
                : "border border-slate-700 bg-slate-900/70 text-slate-300 hover:border-indigo-400"
            }`}
          >
            Unit {u}
          </button>
        ))}
      </div>

      {/* Search & POS Filter */}
      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-3.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm từ tiếng Anh hoặc nghĩa tiếng Việt..."
            className="w-full rounded-xl border border-slate-700 bg-slate-900/80 py-2.5 pl-10 pr-4 text-sm text-white outline-none focus:border-emerald-400"
          />
        </div>
        <select
          value={posFilter}
          onChange={(e) => setPosFilter(e.target.value)}
          className="rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-2.5 text-sm font-semibold text-slate-200 outline-none focus:border-emerald-400"
        >
          <option value="">Tất cả từ loại</option>
          <option value="noun">Danh từ (noun)</option>
          <option value="verb">Động từ (verb)</option>
          <option value="adj">Tính từ (adj)</option>
          <option value="adv">Trạng từ (adv)</option>
          <option value="phrase">Cụm từ / Phrasal Verb</option>
        </select>
      </div>

      {/* Vocab Grid */}
      {loading ? (
        <div className="py-16 text-center text-slate-400">Đang tải từ vựng Unit {unitId}...</div>
      ) : items.length === 0 ? (
        <div className="mt-8 rounded-3xl border border-slate-800 bg-slate-900/60 p-10 text-center text-sm text-slate-400">
          Chưa có từ vựng nào khớp cho Unit {unitId}. Bạn có thể nạp thêm bằng script{" "}
          <code className="text-emerald-300">import_notebook_data.py</code>.
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
          {items.map((v) => (
            <div
              key={v.id}
              className="rounded-2xl border border-indigo-500/20 bg-slate-900/80 p-5 transition hover:border-emerald-400/40"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-xl font-black text-white">{v.word}</h3>
                    <span className="rounded-md bg-indigo-500/20 px-2 py-0.5 text-[11px] font-bold uppercase text-indigo-300">
                      {v.pos}
                    </span>
                  </div>
                  <div className="mt-0.5 font-mono text-xs text-emerald-300">{v.ipa}</div>
                </div>
                <button
                  type="button"
                  onClick={() => speakEnglish(v.word)}
                  title="Nghe phát âm"
                  className="rpg-btn rounded-xl bg-indigo-600/30 p-2.5 text-cyan-300 hover:bg-indigo-600/50"
                >
                  <Volume2 className="h-4 w-4" />
                </button>
              </div>

              <div className="mt-3 text-base font-bold text-amber-200">{v.meaning_vi}</div>

              {v.example_en && (
                <div className="mt-3 rounded-xl bg-slate-950/60 p-3 text-xs">
                  <p className="font-medium text-slate-200">{v.example_en}</p>
                  <p className="mt-1 text-slate-400">{v.example_vi}</p>
                </div>
              )}

              {v.word_forms.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {v.word_forms.map((wf, i) => (
                    <span
                      key={i}
                      className="rounded-lg border border-amber-500/25 bg-amber-500/10 px-2 py-0.5 text-[11px] text-amber-200"
                    >
                      <strong className="text-white">{wf.word}</strong> ({wf.pos}): {wf.meaning_vi}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </main>
  );
}

export default function VocabularyPage() {
  return (
    <div className="min-h-screen pb-20">
      <Navbar />
      <Suspense fallback={<div className="py-20 text-center text-slate-400">Đang tải...</div>}>
        <VocabularyBrowser />
      </Suspense>
    </div>
  );
}
