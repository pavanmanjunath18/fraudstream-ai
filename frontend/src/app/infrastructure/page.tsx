"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { Server, Database, Zap, Clock, CheckCircle, XCircle, Cpu, HardDrive } from "lucide-react";
import { fraudApi } from "@/lib/api";
import { StatCard } from "@/components/ui/StatCard";
import { formatMs, cn } from "@/lib/utils";

// Demo time series for infra charts
const LATENCY_SERIES = Array.from({ length: 60 }, (_, i) => ({
  t: `${i}m`,
  p50: Math.floor(25 + Math.random() * 20),
  p95: Math.floor(60 + Math.random() * 40),
  p99: Math.floor(100 + Math.random() * 60),
}));

const THROUGHPUT_SERIES = Array.from({ length: 60 }, (_, i) => ({
  t: `${i}m`,
  rps: Math.floor(80 + Math.random() * 60),
  errors: Math.random() < 0.1 ? Math.floor(Math.random() * 3) : 0,
}));

const CACHE_SERIES = Array.from({ length: 30 }, (_, i) => ({
  t: `${i * 2}m`,
  hit_rate: Math.floor(88 + Math.random() * 8),
  miss_rate: Math.floor(4 + Math.random() * 8),
}));

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-text-muted mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: <span className="font-mono font-semibold">{p.value}</span>
        </p>
      ))}
    </div>
  );
};

const SERVICES = [
  { name: "FastAPI Backend", status: "healthy", latency: "38ms", uptime: "99.94%" },
  { name: "PostgreSQL", status: "healthy", latency: "3ms", uptime: "99.98%" },
  { name: "Redis Cache", status: "healthy", latency: "0.8ms", uptime: "99.99%" },
  { name: "XGBoost Model", status: "healthy", latency: "12ms", uptime: "100%" },
  { name: "SHAP Explainer", status: "healthy", latency: "8ms", uptime: "100%" },
  { name: "Celery Workers", status: "healthy", latency: "–", uptime: "99.87%" },
  { name: "Drift Scanner", status: "warning", latency: "–", uptime: "98.2%" },
];

export default function InfrastructurePage() {
  const { data: metrics } = useQuery({
    queryKey: ["infra-metrics"],
    queryFn: fraudApi.getMetrics,
    refetchInterval: 15_000,
  });

  const { data: modelInfo } = useQuery({
    queryKey: ["model-info"],
    queryFn: fraudApi.getModelInfo,
  });

  const m = metrics || {
    total_requests: 248_391,
    avg_latency_ms: 38.2,
    p95_latency_ms: 87.4,
    total_errors: 124,
    requests_last_hour: 1_247,
    model_healthy: true,
    model_version: "1.0.0",
  };

  return (
    <div className="space-y-5 animate-fade-in">

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard
          title="Avg Inference Latency"
          value={formatMs(m.avg_latency_ms)}
          subtitle="XGBoost + SHAP + rules"
          icon={Zap}
          variant="success"
        />
        <StatCard
          title="p95 Latency"
          value={formatMs(m.p95_latency_ms)}
          subtitle="Under 100ms SLO"
          icon={Clock}
          variant={m.p95_latency_ms > 100 ? "danger" : "default"}
        />
        <StatCard
          title="Requests / hr"
          value={m.requests_last_hour?.toLocaleString()}
          subtitle="Live throughput"
          icon={Server}
          variant="accent"
        />
        <StatCard
          title="Error Rate"
          value={((m.total_errors || 0) / Math.max(m.total_requests, 1) * 100).toFixed(3) + "%"}
          subtitle={`${m.total_errors || 0} total errors`}
          icon={Cpu}
          variant={(m.total_errors || 0) > 100 ? "warning" : "default"}
        />
      </div>

      {/* Service status */}
      <div className="rounded-xl bg-surface border border-border overflow-hidden">
        <div className="px-5 py-4 border-b border-border flex items-center justify-between">
          <p className="text-sm font-semibold text-text-primary">Service Status</p>
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="ping-slow absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
            </span>
            <span className="text-xs text-text-muted">Live</span>
          </div>
        </div>
        <div className="divide-y divide-border">
          {SERVICES.map((s) => (
            <div key={s.name} className="px-5 py-3.5 flex items-center justify-between table-row-hover">
              <div className="flex items-center gap-3">
                {s.status === "healthy"
                  ? <CheckCircle className="w-4 h-4 text-success" />
                  : <XCircle className="w-4 h-4 text-warning" />
                }
                <span className="text-sm text-text-primary">{s.name}</span>
              </div>
              <div className="flex items-center gap-8 text-xs">
                <div className="text-right">
                  <p className="text-text-subtle">Latency</p>
                  <p className="font-mono text-text-primary">{s.latency}</p>
                </div>
                <div className="text-right">
                  <p className="text-text-subtle">Uptime</p>
                  <p className={cn("font-mono font-medium",
                    parseFloat(s.uptime) >= 99.9 ? "text-success" : "text-warning"
                  )}>{s.uptime}</p>
                </div>
                <span className={cn(
                  "badge",
                  s.status === "healthy"
                    ? "bg-success/10 text-success border-success/20"
                    : "bg-warning/10 text-warning border-warning/20"
                )}>
                  {s.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-2 gap-4">

        {/* Latency percentiles */}
        <div className="rounded-xl bg-surface border border-border p-5">
          <p className="text-sm font-semibold text-text-primary mb-1">Inference Latency Percentiles</p>
          <p className="text-xs text-text-muted mb-4">p50 / p95 / p99 — last 60 minutes</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={LATENCY_SERIES} margin={{ left: -20, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" />
              <XAxis dataKey="t" tick={{ fontSize: 9, fill: "#64748B" }} tickLine={false} interval={9} />
              <YAxis tick={{ fontSize: 10, fill: "#64748B" }} tickLine={false} axisLine={false} unit="ms" />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="p50" stroke="#10B981" strokeWidth={2} dot={false} name="p50" />
              <Line type="monotone" dataKey="p95" stroke="#F59E0B" strokeWidth={2} dot={false} name="p95" />
              <Line type="monotone" dataKey="p99" stroke="#EF4444" strokeWidth={2} dot={false} name="p99" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Throughput */}
        <div className="rounded-xl bg-surface border border-border p-5">
          <p className="text-sm font-semibold text-text-primary mb-1">Request Throughput</p>
          <p className="text-xs text-text-muted mb-4">Requests/second · error count overlay</p>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={THROUGHPUT_SERIES} margin={{ left: -20, right: 10 }}>
              <defs>
                <linearGradient id="rpsGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366F1" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#6366F1" stopOpacity={0.01} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" />
              <XAxis dataKey="t" tick={{ fontSize: 9, fill: "#64748B" }} tickLine={false} interval={9} />
              <YAxis tick={{ fontSize: 10, fill: "#64748B" }} tickLine={false} axisLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="rps" stroke="#6366F1" fill="url(#rpsGrad)" strokeWidth={2} dot={false} name="RPS" />
              <Bar dataKey="errors" fill="#EF4444" name="Errors" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Redis cache metrics */}
      <div className="rounded-xl bg-surface border border-border p-5">
        <div className="flex items-center gap-2 mb-4">
          <HardDrive className="w-4 h-4 text-info" />
          <p className="text-sm font-semibold text-text-primary">Redis Feature Cache — Hit Rate</p>
          <span className="ml-auto text-xs text-text-muted">Avg: ~92%</span>
        </div>
        <ResponsiveContainer width="100%" height={140}>
          <AreaChart data={CACHE_SERIES} margin={{ left: -20, right: 10 }}>
            <defs>
              <linearGradient id="hitGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10B981" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#10B981" stopOpacity={0.01} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" />
            <XAxis dataKey="t" tick={{ fontSize: 9, fill: "#64748B" }} tickLine={false} interval={4} />
            <YAxis tick={{ fontSize: 10, fill: "#64748B" }} tickLine={false} axisLine={false} unit="%" domain={[80, 100]} />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="hit_rate" stroke="#10B981" fill="url(#hitGrad)" strokeWidth={2} dot={false} name="Cache Hit %" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
