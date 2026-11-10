import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";

import { Shell } from "./components/Shell";
import { AuthProvider, useAuth } from "./lib/auth";
import { Analytics } from "./pages/Analytics";
import { Ask } from "./pages/Ask";
import { AuthCallback } from "./pages/AuthCallback";
import { Discover } from "./pages/Discover";
import { Graph } from "./pages/Graph";
import { Home } from "./pages/Home";
import { Learning } from "./pages/Learning";
import { Library } from "./pages/Library";
import { Login } from "./pages/Login";
import { ProjectPage } from "./pages/Project";
import { Projects } from "./pages/Projects";
import { Research } from "./pages/Research";
import { Settings } from "./pages/Settings";
import { Shared } from "./pages/Shared";
import { Write } from "./pages/Write";
import { Spinner } from "./ui";
import { ToastProvider } from "./ui/toast";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}><Spinner /></div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <HashRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/auth/callback" element={<AuthCallback />} />
              <Route path="/shared/:token" element={<Shared />} />
              <Route element={<RequireAuth><Shell /></RequireAuth>}>
                <Route path="/" element={<Home />} />
                <Route path="/discover" element={<Discover />} />
                <Route path="/library" element={<Library />} />
                <Route path="/projects" element={<Projects />} />
                <Route path="/projects/:id" element={<ProjectPage />} />
                <Route path="/ask" element={<Ask />} />
                <Route path="/research" element={<Research />} />
                <Route path="/graph" element={<Graph />} />
                <Route path="/write" element={<Write />} />
                <Route path="/write/:id" element={<Write />} />
                <Route path="/learning" element={<Learning />} />
                <Route path="/analytics" element={<Analytics />} />
                <Route path="/settings" element={<Settings />} />
                {/* 舊版路徑：對話併入提問頁、趨勢併入探索頁 */}
                <Route path="/conversations" element={<Navigate to="/ask" replace />} />
                <Route path="/trends" element={<Navigate to="/discover?tab=trends" replace />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </HashRouter>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  );
}
