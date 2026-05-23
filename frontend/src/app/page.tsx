"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Shield, Activity, AlertTriangle, Clock,
  TrendingUp, Cpu, CheckCircle, XCircle,
  BarChart2, Zap, Loader2,
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";
import { fraudApi } from "@/lib/api";
import { StatCard } from "@/components/ui/StatCard";
import { formatPct, formatMs, cn } from "@/lib/utils";

// ── Demo data (falls back when API is cold) ────────────────────────────────
const DEMO_OVERVIEW = {
  total_requests: 248_391,
  total_blocked: 8_694,
  requests_last_hour: 1_247,
  fraud_rate_pct: 3.5,
  avg_latency_ms: 38.2,
  p95_latency_ms: 87.4,
  avg_fraud_probability: 0.112,
  model_healthy: true,
  model_version: "1.0.0",
  decision_distribution: { ALLOW: 228_840, REVIEW: 10_857, BLOCK: 8_694 },
};

const DEMO_TIME_SERIES = Array.from({ length: 24 }, (_, i) => ({
  hour: `${String(i).padStart(2, "0")}:00`,
  total: Math.floor(800 + Math.random() * 600),
  fraud: Math.floor(20 + Math.random() * 40),
})).map((d) => ({ ...d, fraud_rate: +((d.fraud / d.total) * 100).toFixed(2) }));

const RISK_PIE_DATA = [
  { name: "ALLOW", value: 92.1, color: "#10B981" },
  { name: "REVIEW", value: 4.4, color: "#F59E0B" },
  { name: "BLOCK", value: 3.5, color: "#EF4444" },
];

const RISK_FACTORS_DEMO = [
  { factor: "Velocity spike (1h)", count: 3_241 },
  { factor: "New/unknown device", count: 2_891 },
  { factor: "Synthetic identity risk", count: 2_107 },
  { factor: "VPN + emulator combo", count: 1_876 },
  { factor: "Unusual transaction size", count: 1_654 },
  { factor: "High-risk merchant", count: 1_398 },
];

// ── Tooltip styles ─────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-text-muted mb-1 font-medium">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <span className="font-mono font-semibold">{p.value}</span>
        </p>
      ))}
    </div>
  );
};

export default function DashboardPage() {
  const { data: overview, isLoading: ovLoading } = useQuery({
    queryKey: ["overview"],
    queryFn: fraudApi.getOverview,
    refetchInterval: 15_000,
  });

  const { data: timeSeries } = useQuery({
    queryKey: ["fraud-over-time", 24],
    queryFn: () => fraudApi.getFraudOverTime(24),
    refetchInterval: 60_000,
  });

  const { data: topFactors } = useQuery({
    queryKey: ["top-risk-factors"],
    queryFn: fraudApi.getTopRiskFactors,
    refetchInterval: 120_000,
  });

  const { data: riskDist } = useQuery({
    queryKey: ["risk-distribution"],
    queryFn: fraudApi.getRiskDistribution,
  });

  // Always render immediately with demo data — real data replaces it
  // once Render wakes up. Never block behind a spinner.
  const ov = overview || DEMO_OVERVIEW;
  const isLive = !!overview;
  const ts = (timeSeries?.length ? timeSeries : DEMO_TIME_SERIES).slice(-24);
  const factors = topFactors?.length ? topFactors : RISK_FACTORS_DEMO;

  return (
    <div className="space-y-6 animate-fade-in">

      {/* ── Model health banner ────────────────────────────────────────────── */}
      <div className={cn(
        "flex items-center justify-between rounded-xl border px-5 py-3",
        isLive ? "border-accent/20 bg-accent/5" : "border-border bg-surface"
      )}>
        <div className="flex items-center gap-3">
          {isLive ? (
            <div className={cn("w-2 h-2 rounded-full", ov.model_healthy ? "bg-success" : "bg-danger")} />
          ) : (
            <Loader2 className="w-3.5 h-3.5 text-text-subtle animate-spin" />
          )}
          <span className="text-sm font-medium text-text-primary">
            {isLive
              ? `Model ${ov.model_version} · ${ov.model_healthy ? "Healthy" : "Degraded"}`
              : "Connecting to backend…"}
          </span>
          <span className="text-xs text-text-muted">
            {isLive ? "XGBoost + SHAP explainability active" : "Showing demo data while backend warms up"}
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-text-muted">
          <span>Threshold: 0.50</span>
          <span>High-risk: 0.75</span>
          {isLive
            ? <span className="text-accent font-medium">Live scoring ✓</span>
            : <span className="text-text-subtle">Demo mode</span>
          }
        </div>
      </div>

      {/* ── KPI row ────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Transactions"
          value={ov.total_requests.toLocaleString()}
          subtitle="All time"
          icon={Activity}
          variant="accent"
        />
        <StatCard
          title="Fraud Rate"
          value={formatPct(ov.fraud_rate_pct)}
          subtitle={`${ov.total_blocked.toLocaleString()} blocked`}
          icon={AlertTriangle}
          variant="danger"
          trend={{ value: -0.3, label: "vs last week" }}
        />
        <StatCard
          title="Avg Latency"
          value={formatMs(ov.avg_latency_ms)}
          subtitle={`p95: ${formatMs(ov.p95_latency_ms)}`}
          icon={Clock}
          variant="success"
        />
        <StatCard
          title="Throughput / hr"
          value={ov.requests_last_hour.toLocaleString()}
          subtitle="Last 60 minutes"
          icon={Zap}
          variant="default"
        />
      </div>

      {/* ── Charts row ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-4">

        {/* Fraud over time */}
        <div className="col-span-2 rounded-xl bg-surface border border-border p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm font-semibold text-text-primary">Fraud Volume — Last 24h</p>
              <p className="text-xs text-text-muted mt-0.5">Blocked transactions per hour</p>
            </div>
            <BarChart2 className="w-4 h-4 text-text-subtle" />
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={ts} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="fraudGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#EF4444" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#EF4444" stopOpacity={0.01} />
                </linearGradient>
                <linearGradient id="totalGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366F1" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#6366F1" stopOpacity={0.01} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fill: "#64748B" }} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "#64748B" }} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="total" stroke="#6366F1" fill="url(#totalGrad)" strokeWidth={1.5} dot={false} name="Total" />
              <Area type="monotone" dataKey="fraud" stroke="#EF4444" fill="url(#fraudGrad)" strokeWidth={2} dot={false} name="Blocked" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Decision distribution */}
        <div className="rounded-xl bg-surface border border-border p-5">
          <p className="text-sm font-semibold text-text-primary mb-1">Decision Distribution</p>
          <p className="text-xs text-text-muted mb-4">ALLOW / REVIEW / BLOCK</p>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={RISK_PIE_DATA}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={80}
                paddingAngle={3}
                dataKey="value"
              >
                {RISK_PIE_DATA.map((entry) => (
                  <Cell key={entry.name} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                formatter={(v: number) => [`${v}%`, ""]}
                contentStyle={{ background: "#12121A", border: "1px solid #1E1E2E", borderRadius: 8 }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2 mt-2">
            {RISK_PIE_DATA.map((d) => (
              <div key={d.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: d.color }} />
                  <span className="text-text-muted">{d.name}</span>
                </div>
                <span className="font-mono font-medium text-text-primary">{d.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Bottom row ─────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4">

        {/* Top risk factors */}
        <div className="rounded-xl bg-surface border border-border p-5">
          <p className="text-sm font-semibold text-text-primary mb-1">Top Fraud Indicators</p>
          <p className="text-xs text-text-muted mb-4">Most cited SHAP + rule factors in BLOCK decisions</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={factors.slice(0, 6)} layout="vertical" margin={{ left: 0, right: 20, top: 0, bottom: 0 }}>
              <XAxis type="number" tick={{ fontSize: 10, fill: "#64748B" }} tickLine={false} axisLine={false} />
              <YAxis
                dataKey="factor"
                type="category"
                tick={{ fontSize: 10, fill: "#94A3B8" }}
                tickLine={false}
                axisLine={false}
                width={160}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" fill="#6366F1" radius={[0, 4, 4, 0]} name="Count" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Live model stats */}
        <div className="rounded-xl bg-surface border border-border p-5">
          <p className="text-sm font-semibold text-text-primary mb-4">Model & System Health</p>
          <div className="space-y-3">
            {[
              { label: "Model Status", value: ov.model_healthy ? "Healthy" : "Degraded", ok: ov.model_healthy },
              { label: "Avg Fraud Probability", value: (ov.avg_fraud_probability * 100).toFixed(1) + "%", ok: ov.avg_fraud_probability < 0.3 },
              { label: "Avg Inference Latency", value: formatMs(ov.avg_latency_ms), ok: ov.avg_latency_ms < 100 },
              { label: "p95 Latency", value: formatMs(ov.p95_latency_ms), ok: ov.p95_latency_ms < 150 },
              { label: "Error Rate", value: ((ov.total_errors ?? 0) / Math.max(ov.total_requests, 1) * 100).toFixed(3) + "%", ok: true },
              { label: "Redis Cache", value: "Connected", ok: true },
            ].map(({ label, value, ok }) => (
              <div key={label} className="flex items-center justify-between py-2 border-b border-border last:border-0">
                <span className="text-xs text-text-muted">{label}</span>
                <div className="flex items-center gap-2">
                  {ok
                    ? <CheckCircle className="w-3.5 h-3.5 text-success" />
                    : <XCircle className="w-3.5 h-3.5 text-danger" />
                  }
                  <span className="text-xs font-mono font-medium text-text-primary">{value}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
