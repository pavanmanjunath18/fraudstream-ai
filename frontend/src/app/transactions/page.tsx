"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Filter, ChevronDown, ArrowUpRight } from "lucide-react";
import { fraudApi } from "@/lib/api";
import { RiskBadge, DecisionBadge } from "@/components/ui/Badge";
import { LoadingSpinner, SkeletonRow } from "@/components/ui/LoadingSpinner";
import { cn, truncateId, formatMs } from "@/lib/utils";

// Demo seed for when API is cold
const DEMO_TRANSACTIONS = Array.from({ length: 40 }, (_, i) => {
  const risks = ["MINIMAL", "LOW", "MEDIUM", "HIGH"];
  const decisions = ["ALLOW", "ALLOW", "ALLOW", "REVIEW", "BLOCK"];
  const risk = risks[Math.floor(Math.random() * risks.length)];
  const decision = risk === "HIGH" ? "BLOCK" : risk === "MEDIUM" ? "REVIEW" : "ALLOW";
  return {
    transaction_id: `TXN_${Math.random().toString(36).substr(2, 14).toUpperCase()}`,
    fraud_probability: +(Math.random() * (risk === "HIGH" ? 1 : risk === "MEDIUM" ? 0.75 : 0.5)).toFixed(4),
    risk_level: risk,
    decision,
    top_risk_factors: risk === "HIGH"
      ? ["Velocity spike", "New device", "Geo mismatch"]
      : risk === "MEDIUM"
      ? ["Unusual amount", "VPN detected"]
      : [],
    latency_ms: +(20 + Math.random() * 80).toFixed(1),
    created_at: new Date(Date.now() - i * 45_000).toISOString(),
  };
});

const RISK_LEVELS = ["ALL", "HIGH", "MEDIUM", "LOW", "MINIMAL"];
const DECISIONS = ["ALL", "BLOCK", "REVIEW", "ALLOW"];

export default function TransactionsPage() {
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [decisionFilter, setDecisionFilter] = useState("ALL");
  const [search, setSearch] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["prediction-history", riskFilter !== "ALL" ? riskFilter : undefined],
    queryFn: () => fraudApi.getPredictionHistory(100, riskFilter !== "ALL" ? riskFilter : undefined),
    refetchInterval: 10_000,
  });

  const rows = (data?.length ? data : DEMO_TRANSACTIONS).filter((r: any) => {
    if (decisionFilter !== "ALL" && r.decision !== decisionFilter) return false;
    if (search && !r.transaction_id.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-5 animate-fade-in">

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-subtle" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search transaction ID…"
            className="w-full pl-9 pr-3 py-2 bg-surface border border-border rounded-lg text-sm text-text-primary placeholder:text-text-subtle focus:outline-none focus:border-accent/50 transition-colors"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">Risk:</span>
          <div className="flex gap-1">
            {RISK_LEVELS.map((r) => (
              <button
                key={r}
                onClick={() => setRiskFilter(r)}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                  riskFilter === r
                    ? "bg-accent/15 text-accent border border-accent/20"
                    : "text-text-muted hover:text-text-primary hover:bg-surface-2 border border-transparent"
                )}
              >
                {r}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-text-muted">Decision:</span>
          <div className="flex gap-1">
            {DECISIONS.map((d) => (
              <button
                key={d}
                onClick={() => setDecisionFilter(d)}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                  decisionFilter === d
                    ? "bg-accent/15 text-accent border border-accent/20"
                    : "text-text-muted hover:text-text-primary hover:bg-surface-2 border border-transparent"
                )}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        <div className="ml-auto text-xs text-text-muted font-mono">
          {rows.length.toLocaleString()} transactions
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl bg-surface border border-border overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface-2">
                {["Transaction ID", "Fraud Prob.", "Risk Level", "Decision", "Top Factors", "Latency", "Time"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-text-subtle uppercase tracking-wider">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {isLoading
                ? Array.from({ length: 8 }).map((_, i) => (
                    <tr key={i}><td colSpan={7}><SkeletonRow /></td></tr>
                  ))
                : rows.map((row: any) => (
                    <tr key={row.transaction_id} className="table-row-hover transition-colors">
                      <td className="px-4 py-3">
                        <span className="font-mono text-xs text-text-primary">
                          {truncateId(row.transaction_id, 16)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-surface-2 rounded-full overflow-hidden">
                            <div
                              className={cn(
                                "h-full rounded-full",
                                row.fraud_probability > 0.75 ? "bg-danger" :
                                row.fraud_probability > 0.5 ? "bg-warning" :
                                row.fraud_probability > 0.25 ? "bg-info" : "bg-success"
                              )}
                              style={{ width: `${row.fraud_probability * 100}%` }}
                            />
                          </div>
                          <span className="font-mono text-xs text-text-primary">
                            {(row.fraud_probability * 100).toFixed(1)}%
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <RiskBadge level={row.risk_level} />
                      </td>
                      <td className="px-4 py-3">
                        <DecisionBadge decision={row.decision} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {(row.top_risk_factors || []).slice(0, 2).map((f: string, i: number) => (
                            <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-surface-2 text-text-muted border border-border">
                              {f}
                            </span>
                          ))}
                          {(row.top_risk_factors || []).length > 2 && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-2 text-text-subtle">
                              +{row.top_risk_factors.length - 2}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={cn(
                          "font-mono text-xs",
                          (row.latency_ms || 0) > 100 ? "text-warning" : "text-success"
                        )}>
                          {formatMs(row.latency_ms || 0)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-text-subtle">
                        {row.created_at
                          ? new Date(row.created_at).toLocaleTimeString()
                          : "–"}
                      </td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
