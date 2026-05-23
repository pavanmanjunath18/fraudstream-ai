"use client";

import { usePathname } from "next/navigation";
import { RefreshCw, Bell, Clock } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { cn } from "@/lib/utils";

const PAGE_TITLES: Record<string, string> = {
  "/": "Executive Risk Dashboard",
  "/transactions": "Real-Time Transaction Feed",
  "/analytics": "Fraud Analytics",
  "/explainability": "SHAP Explainability",
  "/drift": "Drift Monitoring",
  "/infrastructure": "Infrastructure Metrics",
};

export function TopBar() {
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [refreshing, setRefreshing] = useState(false);
  const title = PAGE_TITLES[pathname] ?? "FraudStream AI";

  const handleRefresh = async () => {
    setRefreshing(true);
    await queryClient.invalidateQueries();
    setLastRefresh(new Date());
    setTimeout(() => setRefreshing(false), 600);
  };

  return (
    <header className="h-14 border-b border-border bg-surface flex items-center justify-between px-6 shrink-0">
      <div>
        <h1 className="text-sm font-semibold text-text-primary">{title}</h1>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs text-text-subtle">
          <Clock className="w-3 h-3" />
          <span>
            Updated {lastRefresh.toLocaleTimeString()}
          </span>
        </div>

        <button
          onClick={handleRefresh}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-text-muted hover:text-text-primary hover:bg-surface-2 border border-border transition-all"
        >
          <RefreshCw className={cn("w-3 h-3", refreshing && "animate-spin")} />
          Refresh
        </button>

        <button className="relative p-2 rounded-lg hover:bg-surface-2 text-text-muted hover:text-text-primary transition-colors">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-danger" />
        </button>
      </div>
    </header>
  );
}
