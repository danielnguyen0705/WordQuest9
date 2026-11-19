export interface UserProfile {
  id: string;
  username: string;
  email: string;
  display_name: string;
  avatar: string;
  xp: number;
  level: number;
  xp_in_level: number;
  xp_for_next_level: number;
  streak_days: number;
  longest_streak: number;
  current_combo: number;
  best_combo: number;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface WordForm {
  id?: number | null;
  word: string;
  pos: string;
  meaning_vi: string;
}

export interface VocabularyItem {
  id: number;
  unit_id: number;
  word: string;
  pos: string;
  ipa: string;
  meaning_vi: string;
  example_en: string;
  example_vi: string;
  word_forms: WordForm[];
}

export interface UnitProgress {
  unit_id: number;
  unit_number: number;
  title: string;
  title_vi: string;
  realm_name: string;
  description: string;
  theme_color: string;
  icon: string;
  vocab_count: number;
  question_count: number;
  is_unlocked: boolean;
  is_completed: boolean;
  stages_cleared: number;
  best_score: number;
  total_attempts: number;
  badge_earned: boolean;
  mastered_vocab_count: number;
}

export interface RecentSession {
  session_id: string;
  unit_id: number | null;
  mode: "sudden_death" | "practice" | "mistake_revenge";
  status: string;
  correct_count: number;
  wrong_count: number;
  total_questions: number;
  reset_count: number;
  xp_earned: number;
  started_at: string | null;
  completed_at: string | null;
}

export interface DashboardOverview {
  user: UserProfile;
  units: UnitProgress[];
  total_vocab_mastered: number;
  total_vocab_seen: number;
  unresolved_mistakes_count: number;
  resolved_mistakes_count: number;
  recent_sessions: RecentSession[];
}

export type QuestionType =
  | "translation_en_vi"
  | "translation_vi_en"
  | "listening"
  | "contextual_mcq"
  | "word_form";

export interface PublicQuizQuestion {
  index: number;
  question_uid: string;
  question_bank_id?: number | null;
  vocabulary_id?: number | null;
  unit_id?: number | null;
  target_word: string;
  question_type: QuestionType;
  prompt_text: string;
  audio_text?: string | null;
  ipa?: string | null;
  input_mode: "mcq" | "typing";
  options: string[];
  source: string;
  mistake_id?: number | null;
}

export interface SessionState {
  session_id: string;
  unit_id: number | null;
  mode: "sudden_death" | "practice" | "mistake_revenge";
  status: "warmup" | "in_progress" | "completed" | "failed_reset";
  current_index: number;
  total_questions: number;
  correct_count: number;
  wrong_count: number;
  lives_remaining: number;
  reset_count: number;
  xp_earned: number;
  warmup_cards: VocabularyItem[];
  current_question: PublicQuizQuestion | null;
}

export interface SubmitAnswerResponse {
  session_id: string;
  is_correct: boolean;
  correct_answer: string;
  explanation_vi: string;
  xp_gained: number;
  combo: number;
  lives_remaining: number;
  triggered_reset: boolean;
  reset_count: number;
  session_completed: boolean;
  unit_unlocked: number | null;
  mistake_recorded: boolean;
  mistake_resolved: boolean;
  revenge_streak: number | null;
  revenge_target: number;
  next_question: PublicQuizQuestion | null;
  session_summary: {
    total_questions: number;
    correct_count: number;
    wrong_count: number;
    reset_count: number;
    xp_earned: number;
    new_level: number;
    unit_unlocked: number | null;
    mode: string;
  } | null;
}

export interface MistakeItem {
  id: number;
  unit_id: number | null;
  vocabulary_id: number | null;
  target_word: string;
  question_type: QuestionType;
  prompt_text: string;
  correct_answer: string;
  explanation_vi: string;
  mistake_count: number;
  consecutive_correct_revenge: number;
  mastery_threshold: number;
  is_resolved: boolean;
  last_wrong_at: string;
  resolved_at: string | null;
}
