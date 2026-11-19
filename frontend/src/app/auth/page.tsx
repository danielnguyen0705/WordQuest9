"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { LogIn, Swords, UserPlus } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

const AVATARS = [
  { id: "knight", emoji: "🛡️", label: "Kỵ Sĩ" },
  { id: "mage", emoji: "🧙‍♂️", label: "Pháp Sư" },
  { id: "archer", emoji: "🏹", label: "Cung Thủ" },
  { id: "scholar", emoji: "📜", label: "Học Giả" },
];

function AuthFormContent() {
  const searchParams = useSearchParams();
  const initialTab = searchParams.get("tab") === "register" ? "register" : "login";
  const [tab, setTab] = useState<"login" | "register">(initialTab);

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [avatar, setAvatar] = useState("knight");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { loginWithToken } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (tab === "register") {
        const res = await api.register({
          username: username.trim(),
          email: email.trim(),
          password,
          display_name: displayName.trim() || username.trim(),
          avatar,
        });
        loginWithToken(res.access_token, res.user);
      } else {
        const res = await api.login({
          username: username.trim(),
          password,
        });
        loginWithToken(res.access_token, res.user);
      }
      router.push("/map");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đã có lỗi xảy ra.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto mt-10 max-w-md rounded-3xl border border-indigo-400/30 bg-[#121936]/95 p-7 shadow-2xl"
    >
      <div className="mb-6 flex rounded-2xl bg-slate-900/90 p-1">
        <button
          type="button"
          onClick={() => {
            setTab("login");
            setError(null);
          }}
          className={`flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-bold transition ${
            tab === "login" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-white"
          }`}
        >
          <LogIn className="h-4 w-4" /> Đăng Nhập
        </button>
        <button
          type="button"
          onClick={() => {
            setTab("register");
            setError(null);
          }}
          className={`flex flex-1 items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-bold transition ${
            tab === "register" ? "bg-emerald-500 text-slate-950 shadow" : "text-slate-400 hover:text-white"
          }`}
        >
          <UserPlus className="h-4 w-4" /> Đăng Ký
        </button>
      </div>

      <h1 className="text-2xl font-black text-white">
        {tab === "login" ? "Chào mừng Chiến Binh trở lại!" : "Tạo Hồ Sơ Chiến Binh Lớp 9"}
      </h1>
      <p className="mt-1 text-xs text-slate-400">
        {tab === "login"
          ? "Toàn bộ tiến độ Unit, XP và Kho Lỗi Sai sẽ được đồng bộ tự động."
          : "Mọi tiến trình học và kho lỗi sai đều được lưu bền vững theo tài khoản của bạn."}
      </p>

      {error && (
        <div className="mt-4 rounded-xl border border-rose-500/50 bg-rose-500/15 px-4 py-3 text-xs font-semibold text-rose-200">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="mt-5 space-y-4">
        <div>
          <label className="mb-1 block text-xs font-bold text-slate-300">
            {tab === "login" ? "Tên đăng nhập hoặc Email" : "Tên đăng nhập (không dấu, viết liền)"}
          </label>
          <input
            type="text"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="vd: chienbinh9a"
            className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none focus:border-emerald-400"
          />
        </div>

        {tab === "register" && (
          <>
            <div>
              <label className="mb-1 block text-xs font-bold text-slate-300">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ban@example.com"
                className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none focus:border-emerald-400"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs font-bold text-slate-300">Tên hiển thị nhân vật</label>
              <input
                type="text"
                required
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="vd: Minh Khôi 9A1"
                className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none focus:border-emerald-400"
              />
            </div>

            <div>
              <label className="mb-2 block text-xs font-bold text-slate-300">Chọn hệ nhân vật</label>
              <div className="grid grid-cols-4 gap-2">
                {AVATARS.map((av) => (
                  <button
                    key={av.id}
                    type="button"
                    onClick={() => setAvatar(av.id)}
                    className={`rounded-xl border p-2.5 text-center transition ${
                      avatar === av.id
                        ? "border-emerald-400 bg-emerald-500/20 text-white"
                        : "border-slate-700 bg-slate-900/70 text-slate-400 hover:border-slate-500"
                    }`}
                  >
                    <div className="text-2xl">{av.emoji}</div>
                    <div className="mt-1 text-[11px] font-bold">{av.label}</div>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        <div>
          <label className="mb-1 block text-xs font-bold text-slate-300">Mật khẩu (tối thiểu 6 ký tự)</label>
          <input
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-4 py-3 text-sm text-white outline-none focus:border-emerald-400"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="rpg-btn mt-2 flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-emerald-400 to-teal-400 py-3.5 text-sm font-black text-slate-950 shadow-lg shadow-emerald-500/25 disabled:opacity-60"
        >
          <Swords className="h-4 w-4" />
          {loading
            ? "Đang xử lý..."
            : tab === "login"
              ? "ĐĂNG NHẬP & VÀO BẢN ĐỒ"
              : "KHỞI TẠO NHÂN VẬT NGAY"}
        </button>
      </form>
    </motion.div>
  );
}

export default function AuthPage() {
  return (
    <div className="min-h-screen pb-16">
      <Navbar />
      <main className="px-4">
        <Suspense fallback={<div className="py-20 text-center text-slate-400">Đang tải...</div>}>
          <AuthFormContent />
        </Suspense>
      </main>
    </div>
  );
}
