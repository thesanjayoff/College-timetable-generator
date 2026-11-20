import { useState } from "react";
import { Link, Outlet } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { NavLinks } from "./NavLinks";

export function AppLayout() {
  const { user, logout } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-950">
      {/* Desktop sidebar */}
      <aside className="thin-scrollbar hidden w-60 shrink-0 overflow-y-auto border-r border-slate-200 bg-white px-3 py-4 lg:block dark:border-slate-800 dark:bg-slate-900">
        <Link to="/" className="mb-5 flex items-center gap-2 px-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
            TT
          </span>
          <span className="text-sm font-semibold text-slate-900 dark:text-slate-50">Timetable Admin</span>
        </Link>
        <NavLinks />
      </aside>

      {/* Mobile nav overlay */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/40" onClick={() => setMobileNavOpen(false)} aria-hidden="true" />
          <div className="thin-scrollbar relative h-full w-64 overflow-y-auto bg-white px-3 py-4 shadow-xl dark:bg-slate-900">
            <div className="mb-5 flex items-center justify-between px-2">
              <span className="text-sm font-semibold text-slate-900 dark:text-slate-50">Timetable Admin</span>
              <button
                aria-label="Close menu"
                onClick={() => setMobileNavOpen(false)}
                className="rounded-md p-1 text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                ✕
              </button>
            </div>
            <NavLinks onNavigate={() => setMobileNavOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-h-screen flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
          <button
            aria-label="Open menu"
            onClick={() => setMobileNavOpen(true)}
            className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
            </svg>
          </button>
          <div className="flex-1" />
          <Link
            to="/profile"
            className="flex items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-200">
              {user?.name?.slice(0, 1).toUpperCase() ?? "?"}
            </span>
            <span className="hidden text-left sm:block">
              <span className="block font-medium text-slate-800 dark:text-slate-100">{user?.name}</span>
              <span className="block text-xs capitalize text-slate-500 dark:text-slate-400">{user?.role}</span>
            </span>
          </Link>
          <button
            onClick={logout}
            className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            Log out
          </button>
        </header>

        <main className="flex-1 px-4 py-5 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-6xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
