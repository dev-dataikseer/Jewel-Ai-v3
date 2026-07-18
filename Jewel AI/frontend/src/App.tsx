import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { useAuth } from "@/hooks/useAuth";

const StudioPage = lazy(() =>
  import("@/pages/StudioPage").then((m) => ({ default: m.StudioPage })),
);
const HistoryPage = lazy(() =>
  import("@/pages/HistoryPage").then((m) => ({ default: m.HistoryPage })),
);
const RatesPage = lazy(() =>
  import("@/pages/RatesPage").then((m) => ({ default: m.RatesPage })),
);
const AdminPage = lazy(() =>
  import("@/pages/AdminPage").then((m) => ({ default: m.AdminPage })),
);
const SharePage = lazy(() =>
  import("@/pages/SharePage").then((m) => ({ default: m.SharePage })),
);

function PageFallback() {
  return (
    <div className="min-h-screen grid place-items-center text-sm text-slate-500 font-sans">
      Loading...
    </div>
  );
}

function AdminGuard({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated, isAdmin } = useAuth();
  if (isLoading) {
    return (
      <div className="min-h-screen grid place-items-center text-sm text-slate-500">
        Loading...
      </div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isLoading, isAuthenticated } = useAuth();
  if (isLoading) {
    return (
      <div className="min-h-screen grid place-items-center text-sm text-slate-500 font-sans">
        Loading...
      </div>
    );
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Suspense fallback={<PageFallback />}>
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
          path="/rates"
          element={
            <AuthGuard>
              <RatesPage />
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
        <Route path="/share/:token" element={<SharePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
