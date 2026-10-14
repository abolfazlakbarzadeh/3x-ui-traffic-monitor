import { Navigate, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api/client";
import LoginPage from "./pages/LoginPage";
import OverviewPage from "./pages/OverviewPage";
import UsersPage from "./pages/UsersPage";
import UserDetailPage from "./pages/UserDetailPage";
import SettingsPage from "./pages/SettingsPage";
import Shell from "./components/Shell";

export default function App() {
  const me = useQuery({
    queryKey: ["me"],
    queryFn: api.me,
    retry: false,
    // Only refetch when login explicitly invalidateQueries(["me"]).
    // Prevents logout → clear/refetch races from restoring the session.
    staleTime: Infinity,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  if (me.isPending) {
    return (
      <div className="grid min-h-screen place-items-center bg-panel-bg text-primary">
        <div className="flex items-center gap-2 text-sm">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          Loading panel…
        </div>
      </div>
    );
  }

  if (me.isError || me.data == null) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Shell user={me.data}>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/users/:serverId/:email" element={<UserDetailPage />} />
        <Route
          path="/settings"
          element={me.data.role === "admin" ? <SettingsPage /> : <Navigate to="/" replace />}
        />
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  );
}
