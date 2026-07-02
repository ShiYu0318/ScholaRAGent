import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Box, Spinner } from "@primer/react";
import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";

import { Shell } from "./components/Shell";
import { AuthProvider, useAuth } from "./lib/auth";
import { AppThemeProvider } from "./theme";
import { AuthCallback } from "./pages/AuthCallback";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { Placeholder } from "./pages/Placeholder";

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
              <Route
                element={
                  <RequireAuth>
                    <Shell />
                  </RequireAuth>
                }
              >
                <Route path="/" element={<Home />} />
                <Route path="/ask" element={<Placeholder titleKey="nav.ask" />} />
                <Route path="/conversations" element={<Placeholder titleKey="nav.conversations" />} />
                <Route path="/research" element={<Placeholder titleKey="nav.research" />} />
                <Route path="/write" element={<Placeholder titleKey="nav.write" />} />
                <Route path="/graph" element={<Placeholder titleKey="nav.graph" />} />
                <Route path="/library" element={<Placeholder titleKey="nav.library" />} />
                <Route path="/trends" element={<Placeholder titleKey="nav.trends" />} />
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
