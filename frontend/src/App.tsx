import { Navigate, Route, Routes } from "react-router-dom";
import { StudioPage } from "@/pages/StudioPage";
import { AdminPage } from "@/pages/AdminPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { LoginPage } from "@/pages/LoginPage";
import { useAuth } from "@/hooks/useAuth";

function AdminGuard({ children }: { children: React.ReactNode }) {
  const { isLoading, isAdmin } = useAuth();
  if (isLoading) {
    return (
      <div className="min-h-screen grid place-items-center text-sm text-slate-500">Loading…</div>
    );
  }
  if (!isAdmin) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated } = useAuth();
  if (isLoading) {
    return (
      <div className="min-h-screen grid place-items-center text-sm text-slate-500">Loading...</div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <AuthGuard>
            <StudioPage />
          </AuthGuard>
        }
      />
      <Route
        path="/history"
        element={
          <AuthGuard>
            <HistoryPage />
          </AuthGuard>
        }
      />
      <Route
        path="/admin"
        element={
          <AdminGuard>
            <AdminPage />
          </AdminGuard>
        }
      />
      <Route path="/login" element={<LoginPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
