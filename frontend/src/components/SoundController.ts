"use client";

let audioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!audioCtx) {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (Ctx) audioCtx = new Ctx();
  }
  if (audioCtx && audioCtx.state === "suspended") {
    audioCtx.resume().catch(() => {});
  }
  return audioCtx;
}

function playTone(freq: number, duration: number, type: OscillatorType = "sine", delay = 0, gainVal = 0.12) {
  const ctx = getAudioContext();
  if (!ctx) return;
  const now = ctx.currentTime + delay;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, now);
  gain.gain.setValueAtTime(gainVal, now);
  gain.gain.exponentialRampToValueAtTime(0.001, now + duration);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(now);
  osc.stop(now + duration);
}

export const soundFX = {
  correct() {
    playTone(523.25, 0.12, "triangle", 0, 0.14); // C5
    playTone(659.25, 0.14, "triangle", 0.08, 0.14); // E5
    playTone(783.99, 0.22, "triangle", 0.16, 0.14); // G5
  },
  wrong() {
    playTone(220, 0.18, "sawtooth", 0, 0.1);
    playTone(174.61, 0.28, "sawtooth", 0.14, 0.1);
  },
  suddenDeathReset() {
    playTone(260, 0.16, "sawtooth", 0, 0.12);
    playTone(200, 0.18, "sawtooth", 0.14, 0.12);
    playTone(130, 0.42, "sawtooth", 0.28, 0.14);
  },
  victory() {
    const notes = [523.25, 659.25, 783.99, 1046.5];
    notes.forEach((n, idx) => playTone(n, 0.24, "triangle", idx * 0.1, 0.15));
  },
  flip() {
    playTone(420, 0.06, "sine", 0, 0.06);
  },
};

export function speakEnglish(text: string, options?: { rate?: number; lang?: "en-US" | "en-GB" }) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  try {
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = options?.lang || "en-US";
    utter.rate = options?.rate ?? 0.95;
    const voices = window.speechSynthesis.getVoices();
    const preferred =
      voices.find((v) => v.lang === utter.lang && v.name.toLowerCase().includes("google")) ||
      voices.find((v) => v.lang === utter.lang) ||
      voices.find((v) => v.lang.startsWith("en"));
    if (preferred) utter.voice = preferred;
    window.speechSynthesis.speak(utter);
  } catch {
    // Web Speech API unavailable
  }
}
