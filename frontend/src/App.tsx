import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Box, Spinner } from "@primer/react";
import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";

import { Shell } from "./components/Shell";
import { AuthProvider, useAuth } from "./lib/auth";
import { AppThemeProvider } from "./theme";
import { Ask } from "./pages/Ask";
import { AuthCallback } from "./pages/AuthCallback";
import { Conversations } from "./pages/Conversations";
import { Graph } from "./pages/Graph";
import { Home } from "./pages/Home";
import { Library } from "./pages/Library";
import { Login } from "./pages/Login";
import { Placeholder } from "./pages/Placeholder";
import { Research } from "./pages/Research";
import { Shared } from "./pages/Shared";
import { Trends } from "./pages/Trends";
import { Write } from "./pages/Write";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={6}>
        <Spinner />
      </Box>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppThemeProvider>
        <AuthProvider>
          <HashRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/auth/callback" element={<AuthCallback />} />
              <Route path="/shared/:token" element={<Shared />} />
              <Route
                element={
                  <RequireAuth>
                    <Shell />
                  </RequireAuth>
                }
              >
                <Route path="/" element={<Home />} />
                <Route path="/ask" element={<Ask />} />
                <Route path="/conversations" element={<Conversations />} />
                <Route path="/research" element={<Research />} />
                <Route path="/write" element={<Write />} />
                <Route path="/graph" element={<Graph />} />
                <Route path="/library" element={<Library />} />
                <Route path="/trends" element={<Trends />} />
                <Route path="/learning" element={<Placeholder titleKey="nav.learning" />} />
                <Route path="/analytics" element={<Placeholder titleKey="nav.analytics" />} />
                <Route path="/settings" element={<Placeholder titleKey="nav.settings" />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </HashRouter>
        </AuthProvider>
      </AppThemeProvider>
    </QueryClientProvider>
  );
}
