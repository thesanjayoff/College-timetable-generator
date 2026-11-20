import { NavLink } from "react-router-dom";
import { navGroups } from "./navConfig";
import { useAuth } from "../../context/AuthContext";

export function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();

  return (
    <nav className="flex flex-col gap-5">
      {navGroups.map((group) => {
        const items = group.items.filter((item) => !item.roles || (user && item.roles.includes(user.role)));
        if (items.length === 0) return null;
        return (
          <div key={group.label}>
            <p className="mb-1.5 px-2 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
              {group.label}
            </p>
            <ul className="space-y-0.5">
              {items.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.to === "/"}
                    onClick={onNavigate}
                    className={({ isActive }) =>
                      `flex items-center gap-2.5 rounded-md px-2 py-1.5 text-sm font-medium transition ${
                        isActive
                          ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300"
                          : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                      }`
                    }
                  >
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded bg-slate-100 text-[10px] font-semibold text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                      {item.abbr}
                    </span>
                    <span className="truncate">{item.label}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}
