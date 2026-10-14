import { useState, type ReactNode } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { useTheme } from "../theme/ThemeProvider";

const NAV = [
  { to: "/", label: "Dashboard", icon: DashboardIcon, end: true, adminOnly: false },
  { to: "/users", label: "Clients", icon: UsersIcon, end: false, adminOnly: false },
  { to: "/settings", label: "Settings", icon: SettingsIcon, end: false, adminOnly: true },
] as const;

export default function Shell({
  user,
  children,
}: {
  user: { username: string; role: string };
  children: ReactNode;
}) {
  const { theme, toggleTheme } = useTheme();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const width = collapsed ? 72 : 220;
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  async function handleLogout() {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await api.logout();
    } catch {
      // Fall through — local sign-out still runs
    } finally {
      // Cancel in-flight /me, drop other caches, then park me as null.
      // Do NOT queryClient.clear() — that remounts ["me"] and refetches while
      // Shell is still mounted; a successful refetch sends /login → /.
      await queryClient.cancelQueries({ queryKey: ["me"] });
      queryClient.removeQueries({
        predicate: (q) => q.queryKey[0] !== "me",
      });
      queryClient.setQueryData(["me"], null);
      setLoggingOut(false);
      // App switches to the logged-out route tree; sync the URL without
      // relying on navigate() after Shell unmounts.
      window.history.replaceState(null, "", "/login");
      navigate("/login", { replace: true });
    }
  }

  return (
    <div className="flex min-h-screen bg-panel-bg">
      <aside
        className="sticky top-0 hidden h-screen shrink-0 flex-col bg-sider text-white transition-[width] duration-200 md:flex"
        style={{ width }}
      >
        <div className="flex h-14 items-center gap-2 border-b border-white/10 px-4">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-primary text-xs font-bold">
            3X
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <Link to="/" className="block truncate text-sm font-semibold tracking-wide">
                X-UI Monitor
              </Link>
              <p className="truncate text-[10px] text-white/45">traffic history</p>
            </div>
          )}
        </div>

        <nav className="flex-1 space-y-1 p-2">
          {NAV.filter((item) => !item.adminOnly || user.role === "admin").map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `sider-link ${isActive ? "is-active" : ""}`}
              title={collapsed ? item.label : undefined}
            >
              <item.icon />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        <div className="space-y-1 border-t border-white/10 p-2">
          <button
            type="button"
            className="sider-link w-full"
            onClick={toggleTheme}
            title={theme === "dark" ? "Switch to light" : "Switch to dark"}
          >
            {theme === "dark" ? <SunIcon /> : <MoonIcon />}
            {!collapsed && <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>}
          </button>
          <button
            type="button"
            className="sider-link w-full"
            onClick={handleLogout}
            disabled={loggingOut}
            title="Logout"
          >
            <LogoutIcon />
            {!collapsed && <span>{loggingOut ? "Signing out…" : "Logout"}</span>}
          </button>
          <button
            type="button"
            className="sider-link w-full"
            onClick={() => setCollapsed((c) => !c)}
          >
            <CollapseIcon flipped={collapsed} />
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/45"
            aria-label="Close menu"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute left-0 top-0 flex h-full w-[220px] flex-col bg-sider text-white shadow-popup">
            <div className="flex h-14 items-center gap-2 border-b border-white/10 px-4">
              <div className="flex h-8 w-8 items-center justify-center rounded bg-primary text-xs font-bold">
                3X
              </div>
              <span className="text-sm font-semibold">X-UI Monitor</span>
            </div>
            <nav className="flex-1 space-y-1 p-2">
              {NAV.filter((item) => !item.adminOnly || user.role === "admin").map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={() => setMobileOpen(false)}
                  className={({ isActive }) => `sider-link ${isActive ? "is-active" : ""}`}
                >
                  <item.icon />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </nav>
            <div className="space-y-1 border-t border-white/10 p-2">
              <button type="button" className="sider-link w-full" onClick={toggleTheme}>
                {theme === "dark" ? <SunIcon /> : <MoonIcon />}
                <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
              </button>
              <button
                type="button"
                className="sider-link w-full"
                onClick={handleLogout}
                disabled={loggingOut}
              >
                <LogoutIcon />
                <span>{loggingOut ? "Signing out…" : "Logout"}</span>
              </button>
            </div>
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-panel-border bg-header px-4 shadow-sm">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="xui-btn-default md:hidden"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
            >
              <MenuIcon />
            </button>
            <div>
              <p className="text-sm font-medium text-panel-text">Traffic Monitor</p>
              <p className="hidden text-xs text-panel-muted sm:block">
                Companion for 3x-ui · per-client history
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <button
              type="button"
              className="xui-btn-default"
              onClick={toggleTheme}
              aria-label="Toggle theme"
              title={theme === "dark" ? "Light mode" : "Dark mode"}
            >
              {theme === "dark" ? <SunIcon /> : <MoonIcon />}
            </button>
            <button
              type="button"
              className="xui-btn-default"
              onClick={handleLogout}
              disabled={loggingOut}
              aria-label="Logout"
              title="Logout"
            >
              <LogoutIcon />
              <span className="hidden sm:inline">{loggingOut ? "Signing out…" : "Logout"}</span>
            </button>
            <span className="hidden rounded-full bg-primary-soft px-2.5 py-0.5 text-xs text-primary sm:inline">
              {user.role}
            </span>
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-sider text-xs font-semibold text-white">
              {user.username.slice(0, 2).toUpperCase()}
            </div>
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}

function DashboardIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="7" height="9" rx="1" />
      <rect x="14" y="3" width="7" height="5" rx="1" />
      <rect x="14" y="12" width="7" height="9" rx="1" />
      <rect x="3" y="16" width="7" height="5" rx="1" />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="3" />
      <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
    </svg>
  );
}

function UsersIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function CollapseIcon({ flipped }: { flipped: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className={flipped ? "rotate-180" : ""}
    >
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 14.5A8.5 8.5 0 1 1 9.5 3a7 7 0 0 0 11.5 11.5z" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
    </svg>
  );
}

function LogoutIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}
