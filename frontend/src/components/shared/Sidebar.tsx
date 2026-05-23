"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Activity,
  BarChart3,
  Brain,
  TrendingDown,
  Server,
  Shield,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Risk Dashboard", icon: LayoutDashboard },
  { href: "/transactions", label: "Transaction Feed", icon: Activity },
  { href: "/analytics", label: "Fraud Analytics", icon: BarChart3 },
  { href: "/explainability", label: "Explainability", icon: Brain },
  { href: "/drift", label: "Drift Monitor", icon: TrendingDown },
  { href: "/infrastructure", label: "Infrastructure", icon: Server },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-60 shrink-0 border-r border-border bg-surface flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-accent/20 border border-accent/30 flex items-center justify-center">
            <Shield className="w-4 h-4 text-accent" />
          </div>
          <div>
            <p className="font-semibold text-sm text-text-primary leading-none">FraudStream</p>
            <p className="text-[10px] text-text-muted mt-0.5 leading-none">AI Risk Platform</p>
          </div>
        </div>
      </div>

      {/* Status indicator */}
      <div className="px-5 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="ping-slow absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
          </span>
          <span className="text-xs text-text-muted">System operational</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        <p className="px-2 py-1.5 text-[10px] font-semibold text-text-subtle uppercase tracking-widest mb-1">
          Intelligence
        </p>
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-150",
                active
                  ? "bg-accent/15 text-accent border border-accent/20 font-medium"
                  : "text-text-muted hover:text-text-primary hover:bg-surface-2"
              )}
            >
              <Icon className={cn("w-4 h-4 shrink-0", active ? "text-accent" : "")} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-border">
        <div className="flex items-center gap-2 text-xs text-text-subtle">
          <Zap className="w-3 h-3 text-accent" />
          <span>v1.0.0 · XGBoost · SHAP</span>
        </div>
      </div>
    </aside>
  );
}
