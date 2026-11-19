import type {
  AuthResponse,
  DashboardOverview,
  MistakeItem,
  SessionState,
  SubmitAnswerResponse,
  UserProfile,
  VocabularyItem,
} from "@/types/game";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "wordquest9_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (!res.ok) {
    let detail = `Lỗi máy chủ (${res.status})`;
    try {
      const data = await res.json();
      if (data?.detail) {
        detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch {
      // ignore json parse failure
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export const api = {
  // Auth & Profile
  register: (payload: {
    username: string;
    email: string;
    password: string;
    display_name: string;
    avatar: string;
  }) =>
    apiFetch<AuthResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (payload: { username: string; password: string }) =>
    apiFetch<AuthResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  logout: () =>
    apiFetch<{ status: string }>("/api/v1/auth/logout", {
      method: "POST",
    }),

  getMe: () => apiFetch<UserProfile>("/api/v1/auth/me"),

  // Content & Vocabulary
  getUnitVocab: (unitId: number, search?: string, pos?: string) => {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (pos) params.set("pos", pos);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return apiFetch<VocabularyItem[]>(`/api/v1/content/units/${unitId}/vocab${qs}`);
  },

  // Progress & Mistake Vault
  getDashboard: () => apiFetch<DashboardOverview>("/api/v1/progress/dashboard"),

  getMistakes: (includeResolved = true, unitId?: number) => {
    const params = new URLSearchParams();
    params.set("include_resolved", String(includeResolved));
    if (unitId) params.set("unit_id", String(unitId));
    return apiFetch<MistakeItem[]>(`/api/v1/progress/mistakes?${params.toString()}`);
  },

  // Quiz & Game Engine
  startSession: (payload: {
    unit_id?: number | null;
    mode: "sudden_death" | "practice" | "mistake_revenge";
    question_count?: number;
    warmup_count?: number;
    skip_warmup?: boolean;
  }) =>
    apiFetch<SessionState>("/api/v1/quiz/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getSession: (sessionId: string) => apiFetch<SessionState>(`/api/v1/quiz/sessions/${sessionId}`),

  startChallenge: (sessionId: string) =>
    apiFetch<SessionState>(`/api/v1/quiz/sessions/${sessionId}/start-challenge`, {
      method: "POST",
    }),

  submitAnswer: (
    sessionId: string,
    payload: { question_index: number; selected_answer: string; response_time_ms?: number }
  ) =>
    apiFetch<SubmitAnswerResponse>(`/api/v1/quiz/sessions/${sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
