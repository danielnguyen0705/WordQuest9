"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BookOpen, Flame, LogOut, Map, ShieldAlert, Swords, Trophy } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

const AVATAR_EMOJI: Record<string, string> = {
  knight: "🛡️",
  mage: "🧙‍♂️",
  archer: "🏹",
  scholar: "📜",
};

export function Navbar({ unresolvedMistakes = 0 }: { unresolvedMistakes?: number }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = async () => {
    await logout();
    router.push("/auth");
  };

  const navItems = [
    { href: "/map", label: "Bản Đồ Ải", icon: Map },
    { href: "/vocabulary", label: "Sổ Từ Vựng", icon: BookOpen },
    { href: "/mistakes", label: "Kho Lỗi Sai", icon: ShieldAlert, badge: unresolvedMistakes },
  ];

  const xpPct = user ? Math.min(100, Math.round((user.xp_in_level / Math.max(1, user.xp_for_next_level)) * 100)) : 0;

  return (
    <header className="sticky top-0 z-40 border-b border-indigo-500/20 bg-[#0b1024]/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link href={user ? "/map" : "/"} className="flex items-center gap-2.5">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-indigo-600 shadow-lg shadow-emerald-500/20">
            <Swords className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="text-base font-extrabold tracking-tight text-white">
              WORD QUEST <span className="text-emerald-400">9</span>
            </div>
            <div className="text-[11px] font-medium text-slate-400">Global Success RPG</div>
          </div>
        </Link>

        {user && (
          <nav className="hidden items-center gap-1.5 md:flex">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`relative flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-semibold transition ${
                    active
                      ? "bg-indigo-600/30 text-emerald-300 ring-1 ring-emerald-400/40"
                      : "text-slate-300 hover:bg-slate-800/70 hover:text-white"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                  {item.badge && item.badge > 0 ? (
                    <span className="ml-1 rounded-full bg-rose-500 px-1.5 py-0.5 text-[11px] font-bold text-white">
                      {item.badge}
                    </span>
                  ) : null}
                </Link>
              );
            })}
          </nav>
        )}

        <div className="flex items-center gap-3">
          {user ? (
            <>
              <div className="hidden items-center gap-3 rounded-xl border border-slate-700/80 bg-slate-900/80 px-3 py-1.5 sm:flex">
                <div className="flex items-center gap-1 text-amber-400" title="Chuỗi ngày học liên tiếp">
                  <Flame className="h-4 w-4 fill-amber-400" />
                  <span className="text-xs font-bold">{user.streak_days}d</span>
                </div>
                <div className="h-4 w-px bg-slate-700" />
                <div className="flex items-center gap-2">
                  <span className="text-lg">{AVATAR_EMOJI[user.avatar] || "🛡️"}</span>
                  <div className="min-w-[110px]">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-white truncate max-w-[85px]">{user.display_name}</span>
                      <span className="ml-1.5 flex items-center gap-0.5 font-extrabold text-amber-300">
                        <Trophy className="h-3 w-3" /> Lv.{user.level}
                      </span>
                    </div>
                    <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-emerald-400 to-amber-400 transition-all duration-500"
                        style={{ width: `${xpPct}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              <button
                onClick={handleLogout}
                title="Đăng xuất"
                className="rpg-btn flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-800/80 px-3 py-2 text-xs font-semibold text-slate-300 hover:border-rose-500/50 hover:text-rose-300"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Thoát</span>
              </button>
            </>
          ) : (
            <Link
              href="/auth"
              className="rpg-btn rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 px-4 py-2 text-sm font-bold text-slate-950 shadow-lg shadow-emerald-500/25 hover:brightness-110"
            >
              Đăng Nhập / Chiến Ngay
            </Link>
          )}
        </div>
      </div>

      {/* Mobile Nav */}
      {user && (
        <div className="flex items-center justify-around border-t border-slate-800/80 px-2 py-1.5 md:hidden">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold ${
                  active ? "bg-indigo-600/30 text-emerald-300" : "text-slate-400"
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {item.label}
                {item.badge && item.badge > 0 ? (
                  <span className="rounded-full bg-rose-500 px-1.5 text-[10px] text-white">{item.badge}</span>
                ) : null}
              </Link>
            );
          })}
        </div>
      )}
    </header>
  );
}
