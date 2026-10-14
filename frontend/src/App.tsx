import { Navigate, Route, Routes } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "./api/client";
import LoginPage from "./pages/LoginPage";
import OverviewPage from "./pages/OverviewPage";
import UsersPage from "./pages/UsersPage";
import UserDetailPage from "./pages/UserDetailPage";
import Shell from "./components/Shell";

export default function App() {
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, retry: false });

  if (me.isLoading) {
    return (
      <div className="grid min-h-screen place-items-center text-leaf">
        Loading…
      </div>
    );
  }

  if (me.isError) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  return (
    <Shell user={me.data!}>
      <Routes>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/users/:serverId/:email" element={<UserDetailPage />} />
        <Route path="/login" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Shell>
  );
}
