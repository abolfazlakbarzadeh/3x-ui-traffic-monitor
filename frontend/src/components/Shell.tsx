import { Link, NavLink } from "react-router-dom";
import type { ReactNode } from "react";

export default function Shell({
  user,
  children,
}: {
  user: { username: string; role: string };
  children: ReactNode;
}) {
  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 pb-10 pt-6 sm:px-6">
      <header className="mb-8 flex flex-wrap items-end justify-between gap-4 border-b border-line pb-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-leaf">self-hosted</p>
          <Link to="/" className="text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            xui traffic monitor
          </Link>
        </div>
        <nav className="flex items-center gap-4 text-sm">
          <NavLink
            to="/"
            className={({ isActive }) =>
              isActive ? "font-medium text-leaf" : "text-ink/70 hover:text-ink"
            }
            end
          >
            Overview
          </NavLink>
          <NavLink
            to="/users"
            className={({ isActive }) =>
              isActive ? "font-medium text-leaf" : "text-ink/70 hover:text-ink"
            }
          >
            Users
          </NavLink>
          <span className="font-mono text-xs text-ink/50">
            {user.username} · {user.role}
          </span>
        </nav>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  );
}
