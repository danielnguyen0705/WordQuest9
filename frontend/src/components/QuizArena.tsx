"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowRight,
  Award,
  CheckCircle2,
  Flame,
  Heart,
  Keyboard,
  ListChecks,
  RotateCcw,
  Shield,
  Skull,
  Sparkles,
  Trophy,
  Volume2,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { PublicQuizQuestion, SessionState, SubmitAnswerResponse } from "@/types/game";
import { soundFX, speakEnglish } from "@/components/SoundController";

interface QuizArenaProps {
  initialSession: SessionState;
}

const QUESTION_TYPE_META: Record<
  string,
  { label: string; color: string; hint: string }
> = {
  listening: {
    label: "🎧 Nghe & Chọn Từ",
    color: "bg-cyan-500/20 text-cyan-300 border-cyan-400/40",
    hint: "Nhấn loa để nghe phát âm tiếng Anh chuẩn và chọn đáp án đúng.",
  },
  translation_en_vi: {
    label: "🇬🇧→🇻🇳 Dịch Anh – Việt",
    color: "bg-indigo-500/20 text-indigo-300 border-indigo-400/40",
    hint: "Chọn nghĩa tiếng Việt sát SGK Tiếng Anh 9 nhất.",
  },
  translation_vi_en: {
    label: "🇻🇳→🇬🇧 Dịch Việt – Anh",
    color: "bg-violet-500/20 text-violet-300 border-violet-400/40",
    hint: "Chọn hoặc gõ từ tiếng Anh tương ứng.",
  },
  contextual_mcq: {
    label: "📖 Trắc Nghiệm Ngữ Cảnh",
    color: "bg-emerald-500/20 text-emerald-300 border-emerald-400/40",
    hint: "Đọc kỹ câu ví dụ và chọn từ phù hợp nhất điền vào chỗ trống.",
  },
  word_form: {
    label: "⚡ Biến Đổi Từ Loại (Word Form)",
    color: "bg-amber-500/20 text-amber-300 border-amber-400/40",
    hint: "Chú ý từ gốc trong ngoặc và chia đúng Danh/Động/Tính/Trạng từ.",
  },
};

export function QuizArena({ initialSession }: QuizArenaProps) {
  const router = useRouter();
  const { refreshUser } = useAuth();

  const [sessionId] = useState(initialSession.session_id);
  const [mode] = useState(initialSession.mode);
  const [unitId] = useState(initialSession.unit_id);
  const [question, setQuestion] = useState<PublicQuizQuestion | null>(initialSession.current_question);
  const [totalQuestions] = useState(initialSession.total_questions);
  const [correctCount, setCorrectCount] = useState(initialSession.correct_count);
  const [lives, setLives] = useState(initialSession.lives_remaining);
  const [resetCount, setResetCount] = useState(initialSession.reset_count);
  const [xpEarned, setXpEarned] = useState(initialSession.xp_earned);
  const [combo, setCombo] = useState(0);

  const [submitting, setSubmitting] = useState(false);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [typingMode, setTypingMode] = useState(false);
  const [typedText, setTypedText] = useState("");
  const [feedback, setFeedback] = useState<SubmitAnswerResponse | null>(null);
  const [victorySummary, setVictorySummary] = useState<SubmitAnswerResponse["session_summary"]>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const questionStartRef = useRef<number>(Date.now());

  // Auto-speak listening questions when a new question loads
  useEffect(() => {
    questionStartRef.current = Date.now();
    if (question?.question_type === "listening" && question.audio_text) {
      const t = setTimeout(() => {
        speakEnglish(question.audio_text!, { rate: 0.92 });
      }, 250);
      return () => clearTimeout(t);
    }
  }, [question?.question_uid]);

  const handleSubmit = async (answerText: string) => {
    if (!question || submitting || feedback) return;
    const trimmed = answerText.trim();
    if (!trimmed) return;

    setSubmitting(true);
    setSelectedOption(trimmed);
    setErrorMsg(null);
    const elapsed = Math.max(0, Date.now() - questionStartRef.current);

    try {
      const res = await api.submitAnswer(sessionId, {
        question_index: question.index,
        selected_answer: trimmed,
        response_time_ms: elapsed,
      });

      setFeedback(res);
      setCombo(res.combo);
      setLives(res.lives_remaining);
      setResetCount(res.reset_count);
      setXpEarned((prev) => prev + res.xp_gained);

      if (res.is_correct) {
        setCorrectCount((c) => c + 1);
        if (res.session_completed) {
          soundFX.victory();
        } else {
          soundFX.correct();
        }
      } else if (res.triggered_reset) {
        soundFX.suddenDeathReset();
      } else {
        soundFX.wrong();
      }

      if (res.session_completed && res.session_summary) {
        setVictorySummary(res.session_summary);
        refreshUser();
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Không thể gửi câu trả lời.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleProceed = () => {
    if (!feedback) return;
    if (feedback.session_completed) {
      setVictorySummary(feedback.session_summary);
      refreshUser();
      return;
    }
    if (feedback.triggered_reset) {
      setCorrectCount(0);
    }
    setQuestion(feedback.next_question);
    setFeedback(null);
    setSelectedOption(null);
    setTypedText("");
    setTypingMode(false);
  };

  // Victory / Completion Screen
  if (victorySummary) {
    const perfect = victorySummary.correct_count === victorySummary.total_questions;
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        className="mx-auto max-w-xl rounded-3xl border-2 border-amber-400/50 bg-gradient-to-b from-[#1a2447] to-[#0c1228] p-8 text-center shadow-2xl"
      >
        <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-emerald-400 text-slate-950 shadow-xl shadow-amber-500/30">
          <Trophy className="h-10 w-10" />
        </div>
        <h2 className="mt-5 text-3xl font-black text-white">
          {mode === "mistake_revenge"
            ? "HOÀN THÀNH PHỤC THÙ!"
            : perfect
              ? "CHINH PHỤC ẢI THÀNH CÔNG!"
              : "HOÀN THÀNH PHIÊN LUYỆN TẬP!"}
        </h2>
        <p className="mt-2 text-sm text-slate-300">
          {mode === "sudden_death"
            ? `Bạn đã vượt qua trọn vẹn ${victorySummary.total_questions}/${victorySummary.total_questions} câu ở chế độ Sinh Tử 1 Mạng!`
            : `Kết quả: ${victorySummary.correct_count}/${victorySummary.total_questions} câu đúng.`}
        </p>

        {victorySummary.unit_unlocked && (
          <div className="mt-5 rounded-2xl border border-emerald-400/50 bg-emerald-500/15 p-4 text-emerald-200">
            <div className="flex items-center justify-center gap-2 font-extrabold">
              <Award className="h-5 w-5 text-amber-300" />
              ĐÃ MỞ KHÓA VÙNG ĐẤT MỚI: UNIT {victorySummary.unit_unlocked}!
            </div>
          </div>
        )}

        <div className="mt-6 grid grid-cols-3 gap-3">
          <div className="rounded-2xl border border-slate-700/80 bg-slate-900/70 p-4">
            <div className="text-xs font-semibold text-slate-400">Tổng XP</div>
            <div className="mt-1 text-2xl font-black text-amber-400">+{victorySummary.xp_earned}</div>
          </div>
          <div className="rounded-2xl border border-slate-700/80 bg-slate-900/70 p-4">
            <div className="text-xs font-semibold text-slate-400">Cấp Độ</div>
            <div className="mt-1 text-2xl font-black text-emerald-400">Lv.{victorySummary.new_level}</div>
          </div>
          <div className="rounded-2xl border border-slate-700/80 bg-slate-900/70 p-4">
            <div className="text-xs font-semibold text-slate-400">Lần Hồi Sinh</div>
            <div className="mt-1 text-2xl font-black text-rose-400">{victorySummary.reset_count}</div>
          </div>
        </div>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <button
            onClick={() => router.push("/map")}
            className="rpg-btn flex-1 rounded-2xl bg-gradient-to-r from-emerald-400 to-teal-400 py-3.5 text-sm font-black text-slate-950"
          >
            🗺️ Về Bản Đồ 12 Unit
          </button>
          <button
            onClick={() => router.push("/mistakes")}
            className="rpg-btn flex-1 rounded-2xl border border-rose-400/40 bg-rose-500/15 py-3.5 text-sm font-bold text-rose-200 hover:bg-rose-500/25"
          >
            🔥 Mở Kho Lỗi Sai
          </button>
        </div>
      </motion.div>
    );
  }

  if (!question) return null;

  const qMeta = QUESTION_TYPE_META[question.question_type] || QUESTION_TYPE_META.contextual_mcq;
  const progressPct = Math.round(((question.index + (feedback?.is_correct ? 1 : 0)) / totalQuestions) * 100);
  const supportsTyping =
    question.question_type === "word_form" || question.question_type === "translation_vi_en";

  return (
    <div className="mx-auto max-w-3xl">
      {/* Top Arena HUD */}
      <div className="mb-5 rounded-2xl border border-indigo-500/30 bg-slate-900/85 p-4 shadow-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {mode === "sudden_death" ? (
              <span className="flex items-center gap-1.5 rounded-full border border-rose-500/50 bg-rose-500/20 px-3 py-1 text-xs font-black text-rose-300">
                <Skull className="h-3.5 w-3.5" /> SINH TỬ 1 MẠNG
              </span>
            ) : mode === "mistake_revenge" ? (
              <span className="flex items-center gap-1.5 rounded-full border border-amber-500/50 bg-amber-500/20 px-3 py-1 text-xs font-black text-amber-300">
                <Flame className="h-3.5 w-3.5" /> PHỤC THÙ LỖI SAI
              </span>
            ) : (
              <span className="flex items-center gap-1.5 rounded-full border border-sky-500/50 bg-sky-500/20 px-3 py-1 text-xs font-black text-sky-300">
                <Shield className="h-3.5 w-3.5" /> LUYỆN TẬP TỰ DO
              </span>
            )}
            {unitId && (
              <span className="rounded-full bg-slate-800 px-2.5 py-1 text-xs font-bold text-slate-300">
                Unit {unitId}
              </span>
            )}
          </div>

          <div className="flex items-center gap-4 text-xs font-extrabold">
            <div className="flex items-center gap-1 text-rose-400" title="Mạng sống">
              <Heart className="h-4 w-4 fill-rose-500" />
              <span>{mode === "sudden_death" ? `${lives}/1` : "∞"}</span>
            </div>
            <div className="flex items-center gap-1 text-amber-400" title="Chuỗi trả lời đúng">
              <Flame className="h-4 w-4 fill-amber-400" />
              <span>x{combo}</span>
            </div>
            <div className="flex items-center gap-1 text-emerald-400">
              <Sparkles className="h-4 w-4" />
              <span>+{xpEarned} XP</span>
            </div>
            {mode === "sudden_death" && resetCount > 0 && (
              <div className="flex items-center gap-1 text-slate-400" title="Số lần hồi sinh">
                <RotateCcw className="h-3.5 w-3.5" />
                <span>{resetCount}</span>
              </div>
            )}
          </div>
        </div>

        {/* Question Progress Bar */}
        <div className="mt-3.5">
          <div className="mb-1 flex items-center justify-between text-xs font-bold">
            <span className="text-slate-300">
              Câu {question.index + 1} / {totalQuestions}
            </span>
            <span className="text-emerald-400">{progressPct}% vượt ải</span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-800">
            <motion.div
              animate={{ width: `${progressPct}%` }}
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-emerald-400 to-amber-400"
            />
          </div>
        </div>
      </div>

      {/* Question Card */}
      <AnimatePresence mode="wait">
        <motion.div
          key={`${question.question_uid}-${resetCount}`}
          initial={{ opacity: 0, y: 18 }}
          animate={
            feedback && !feedback.is_correct
              ? { opacity: 1, y: 0, x: [0, -10, 10, -8, 8, 0] }
              : { opacity: 1, y: 0, x: 0 }
          }
          exit={{ opacity: 0, y: -14 }}
          transition={{ duration: 0.3 }}
          className="rounded-3xl border border-indigo-400/25 bg-gradient-to-b from-[#151e3d] to-[#0f162e] p-6 shadow-2xl sm:p-8"
        >
          {/* Question Type Badge & Input Mode Toggle */}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className={`rounded-full border px-3 py-1 text-xs font-bold ${qMeta.color}`}>
              {qMeta.label}
            </span>
            {supportsTyping && !feedback && (
              <button
                type="button"
                onClick={() => setTypingMode((t) => !t)}
                className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/80 px-3 py-1 text-xs font-semibold text-slate-300 hover:border-amber-400/60 hover:text-amber-200"
              >
                {typingMode ? (
                  <>
                    <ListChecks className="h-3.5 w-3.5" /> Chuyển sang chọn A/B/C/D
                  </>
                ) : (
                  <>
                    <Keyboard className="h-3.5 w-3.5" /> Thử sức gõ đáp án
                  </>
                )}
              </button>
            )}
          </div>

          <p className="mt-2 text-xs text-slate-400">{qMeta.hint}</p>

          {/* Listening Audio Console */}
          {(question.question_type === "listening" || question.audio_text) && (
            <div className="mt-5 flex flex-wrap items-center gap-3 rounded-2xl border border-cyan-500/30 bg-cyan-950/30 p-4">
              <button
                type="button"
                onClick={() => speakEnglish(question.audio_text || question.target_word, { rate: 0.92 })}
                className="rpg-btn flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-2.5 text-sm font-black text-slate-950 shadow-lg shadow-cyan-500/30 hover:bg-cyan-400"
              >
                <Volume2 className="h-5 w-5" />
                {question.question_type === "listening" ? "Phát âm thanh từ vựng" : "Nghe phát âm"}
              </button>
              <button
                type="button"
                onClick={() => speakEnglish(question.audio_text || question.target_word, { rate: 0.65 })}
                className="rpg-btn rounded-xl border border-cyan-400/40 bg-slate-900/70 px-3.5 py-2.5 text-xs font-bold text-cyan-200 hover:bg-slate-800"
              >
                🐢 Nghe chậm (0.65x)
              </button>
              {question.ipa && question.question_type !== "listening" && (
                <span className="font-mono text-sm text-cyan-300">{question.ipa}</span>
              )}
            </div>
          )}

          {/* Prompt Text */}
          <h3 className="mt-6 text-xl font-extrabold leading-relaxed text-white sm:text-2xl">
            {question.prompt_text}
          </h3>

          {errorMsg && (
            <div className="mt-4 rounded-xl border border-rose-500/50 bg-rose-500/15 px-4 py-2.5 text-sm text-rose-200">
              {errorMsg}
            </div>
          )}

          {/* Answer Input: Typing OR 4 Options A/B/C/D */}
          {typingMode && supportsTyping ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSubmit(typedText);
              }}
              className="mt-6 flex flex-col gap-3 sm:flex-row"
            >
              <input
                type="text"
                value={typedText}
                onChange={(e) => setTypedText(e.target.value)}
                disabled={submitting || !!feedback}
                placeholder="Nhập từ tiếng Anh chính xác..."
                autoFocus
                className="flex-1 rounded-2xl border-2 border-indigo-400/40 bg-slate-950/80 px-4 py-3.5 text-base font-bold text-white outline-none focus:border-emerald-400"
              />
              <button
                type="submit"
                disabled={submitting || !!feedback || !typedText.trim()}
                className="rpg-btn rounded-2xl bg-emerald-500 px-6 py-3.5 text-sm font-black text-slate-950 disabled:opacity-50"
              >
                Kiểm Tra
              </button>
            </form>
          ) : (
            <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {question.options.map((opt, idx) => {
                const letter = ["A", "B", "C", "D"][idx] || String(idx + 1);
                const isSelected = selectedOption?.toLowerCase() === opt.toLowerCase();
                const isCorrectOpt = feedback?.correct_answer.toLowerCase() === opt.toLowerCase();

                let btnStyle =
                  "border-slate-700/90 bg-slate-900/75 text-slate-100 hover:border-indigo-400 hover:bg-indigo-950/60";
                if (feedback) {
                  if (isCorrectOpt) {
                    btnStyle = "border-emerald-400 bg-emerald-500/25 text-emerald-100 ring-2 ring-emerald-400/40";
                  } else if (isSelected && !feedback.is_correct) {
                    btnStyle = "border-rose-500 bg-rose-500/25 text-rose-100 ring-2 ring-rose-500/40";
                  } else {
                    btnStyle = "border-slate-800 bg-slate-900/40 text-slate-500";
                  }
                }

                return (
                  <button
                    key={`${opt}-${idx}`}
                    type="button"
                    disabled={submitting || !!feedback}
                    onClick={() => handleSubmit(opt)}
                    className={`rpg-btn flex items-center gap-3.5 rounded-2xl border-2 px-4 py-4 text-left font-bold transition ${btnStyle}`}
                  >
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-slate-800/90 text-xs font-black text-indigo-300">
                      {letter}
                    </span>
                    <span className="text-sm sm:text-base">{opt}</span>
                  </button>
                );
              })}
            </div>
          )}

          {/* Instant Feedback Panel */}
          {feedback && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              className={`mt-6 rounded-2xl border-2 p-5 ${
                feedback.is_correct
                  ? "border-emerald-500/50 bg-emerald-950/40"
                  : "border-rose-500/60 bg-rose-950/50"
              }`}
            >
              <div className="flex items-start gap-3">
                {feedback.is_correct ? (
                  <CheckCircle2 className="mt-0.5 h-6 w-6 shrink-0 text-emerald-400" />
                ) : (
                  <XCircle className="mt-0.5 h-6 w-6 shrink-0 text-rose-400" />
                )}
                <div className="flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h4
                      className={`text-base font-black ${
                        feedback.is_correct ? "text-emerald-300" : "text-rose-300"
                      }`}
                    >
                      {feedback.is_correct
                        ? `CHÍNH XÁC! +${feedback.xp_gained} XP`
                        : feedback.triggered_reset
                          ? "💀 BỊ HẠ GỤC! CHẾ ĐỘ SINH TỬ 1 MẠNG"
                          : "CHƯA CHÍNH XÁC!"}
                    </h4>

                    {feedback.mistake_resolved ? (
                      <span className="rounded-full bg-amber-400/20 px-3 py-0.5 text-xs font-black text-amber-300">
                        🏆 ĐÃ KHẮC PHỤC LỖI SAI!
                      </span>
                    ) : feedback.revenge_streak ? (
                      <span className="rounded-full bg-indigo-500/25 px-3 py-0.5 text-xs font-bold text-indigo-200">
                        🔥 Phục thù: {feedback.revenge_streak}/{feedback.revenge_target} lần đúng liên tiếp
                      </span>
                    ) : null}
                  </div>

                  {!feedback.is_correct && (
                    <p className="mt-1.5 text-sm font-bold text-white">
                      Đáp án đúng:{" "}
                      <span className="rounded-lg bg-emerald-500/20 px-2 py-0.5 text-emerald-300">
                        {feedback.correct_answer}
                      </span>
                    </p>
                  )}

                  <p className="mt-2 text-sm leading-relaxed text-slate-200">{feedback.explanation_vi}</p>

                  {feedback.triggered_reset && (
                    <div className="mt-3 rounded-xl border border-rose-400/40 bg-rose-900/40 p-3 text-xs font-semibold text-rose-200">
                      ⚠️ Lỗi sai này đã được lưu vào <strong>Kho Lỗi Sai</strong> của bạn. Để vượt ải thực sự
                      (chống học vẹt), toàn bộ 20 câu hỏi và vị trí đáp án A/B/C/D đã được xáo trộn mới hoàn toàn!
                    </div>
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={handleProceed}
                className={`rpg-btn mt-4 flex w-full items-center justify-center gap-2 rounded-xl py-3.5 text-sm font-black shadow-lg ${
                  feedback.triggered_reset
                    ? "bg-gradient-to-r from-rose-500 to-orange-500 text-white"
                    : "bg-gradient-to-r from-emerald-400 to-teal-400 text-slate-950"
                }`}
              >
                {feedback.triggered_reset ? (
                  <>
                    <RotateCcw className="h-4 w-4" /> HỒI SINH &amp; CHƠI LẠI TỪ CÂU 1 (ĐÃ XÁO TRỘN)
                  </>
                ) : feedback.session_completed ? (
                  <>
                    <Trophy className="h-4 w-4" /> XEM TỔNG KẾT CHIẾN THẮNG
                  </>
                ) : (
                  <>
                    CÂU TIẾP THEO <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </motion.div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
