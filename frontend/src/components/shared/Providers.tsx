"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, useEffect, createContext, useContext } from "react";
import { wakeupBackend } from "@/lib/api";

// ── Backend status context ─────────────────────────────────────────────────
type BackendStatus = "warming" | "live" | "unreachable";
const BackendCtx = createContext<BackendStatus>("warming");
export const useBackendStatus = () => useContext(BackendCtx);

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  const [backendStatus, setBackendStatus] = useState<BackendStatus>("warming");

  // Kick off a health ping immediately on mount so Render wakes up
  // before the user interacts — makes subsequent API calls feel instant.
  useEffect(() => {
    wakeupBackend().then((ok) =>
      setBackendStatus(ok ? "live" : "unreachable")
    );
  }, []);

  return (
    <BackendCtx.Provider value={backendStatus}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </BackendCtx.Provider>
  );
}
