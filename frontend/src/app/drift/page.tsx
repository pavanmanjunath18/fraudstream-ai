"use client";

import { useQuery } from "@tanstack/react-query";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Cell,
} from "recharts";
import { AlertTriangle, CheckCircle, TrendingDown, Info } from "lucide-react";
import { fraudApi } from "@/lib/api";
import { cn } from "@/lib/utils";

const DEMO_DRIFT = {
  feature_drift: [
    { feature_name: "transactions_last_1h", psi_score: 0.241, baseline_mean: 2.3, current_mean: 4.8, drift_detected: true, alert_level: "CRITICAL" },
    { feature_name: "synthetic_identity_probability", psi_score: 0.178, baseline_mean: 0.08, current_mean: 0.13, drift_detected: true, alert_level: "WARNING" },
    { feature_name: "amount", psi_score: 0.142, baseline_mean: 285, current_mean: 412, drift_detected: true, alert_level: "WARNING" },
    { feature_name: "vpn_detected", psi_score: 0.089, baseline_mean: 0.12, current_mean: 0.15, drift_detected: false, alert_level: "OK" },
    { feature_name: "device_trust_score", psi_score: 0.054, baseline_mean: 0.78, current_mean: 0.74, drift_detected: false, alert_level: "OK" },
    { feature_name: "merchant_risk_score", psi_score: 0.037, baseline_mean: 0.22, current_mean: 0.24, drift_detected: false, alert_level: "OK" },
    { feature_name: "account_age_days", psi_score: 0.023, baseline_mean: 842, current_mean: 819, drift_detected: false, alert_level: "OK" },
  ],
  prediction_drift: {
    drift_detected: true,
    psi_score: 0.156,
    baseline_fraud_rate: 0.035,
    current_fraud_rate: 0.052,
    rate_shift_pct: 48.6,
    alert_level: "WARNING",
  },
  total_features_checked: 7,
  drifted_features: 3,
};

// 30-day rolling fraud rate simulation
const FRAUD_RATE_TREND = Array.from({ length: 30 }, (_, i) => ({
  day: `Day ${i + 1}`,
  baseline: 3.5,
  current: 3.5 + Math.sin(i / 3) * 0.5 + (i > 20 ? (i - 20) * 0.08 : 0),
}));

// PSI history
const PSI_HISTORY = [
  { date: "May 1", velocity_psi: 0.04, amount_psi: 0.03, synthetic_psi: 0.06 },
  { date: "May 5", velocity_psi: 0.07, amount_psi: 0.05, synthetic_psi: 0.09 },
  { date: "May 10", velocity_psi: 0.12, amount_psi: 0.08, synthetic_psi: 0.11 },
  { date: "May 15", velocity_psi: 0.15, amount_psi: 0.10, synthetic_psi: 0.14 },
  { date: "May 18", velocity_psi: 0.19, amount_psi: 0.13, synthetic_psi: 0.16 },
  { date: "May 22", velocity_psi: 0.24, amount_psi: 0.14, synthetic_psi: 0.18 },
];

const PSI_COLORS = { velocity_psi: "#EF4444", amount_psi: "#F59E0B", synthetic_psi: "#6366F1" };

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-text-muted mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>{p.name}: <span className="font-mono font-semibold">{typeof p.value === "number" ? p.value.toFixed(3) : p.value}</span></p>
      ))}
    </div>
  );
};

const PSI_LABEL = (psi: number) =>
  psi > 0.2 ? { label: "CRITICAL", cls: "bg-danger/10 text-danger border-danger/20" }
  : psi > 0.1 ? { label: "WARNING", cls: "bg-warning/10 text-warning border-warning/20" }
  : { label: "OK", cls: "bg-success/10 text-success border-success/20" };

export default function DriftPage() {
  const { data: driftReport } = useQuery({
    queryKey: ["drift-report"],
    queryFn: fraudApi.getDriftReport,
    refetchInterval: 120_000,
  });

  const report = driftReport || DEMO_DRIFT;
  const predDrift = report.prediction_drift;

  return (
    <div className="space-y-5 animate-fade-in">

      {/* Summary banner */}
      <div className={cn(
        "flex items-center justify-between rounded-xl border px-5 py-3",
        report.drifted_features > 0
          ? "border-warning/30 bg-warning/5"
          : "border-success/30 bg-success/5"
      )}>
        <div className="flex items-center gap-3">
          {report.drifted_features > 0
            ? <AlertTriangle className="w-5 h-5 text-warning" />
            : <CheckCircle className="w-5 h-5 text-success" />
          }
          <div>
            <p className="text-sm font-semibold text-text-primary">
              {report.drifted_features} feature(s) drifting — {report.total_features_checked} checked
            </p>
            <p className="text-xs text-text-muted">
              PSI threshold: 0.10 (warning) · 0.20 (critical) · Model v{DEMO_DRIFT.prediction_drift ? "1.0.0" : "–"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-success" />
            <span className="text-text-muted">PSI &lt; 0.10</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-warning" />
            <span className="text-text-muted">0.10–0.20</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-danger" />
            <span className="text-text-muted">&gt; 0.20</span>
          </div>
        </div>
      </div>

      {/* Top row — feature drift table + PSI over time */}
      <div className="grid grid-cols-5 gap-4">
        <div className="col-span-2 rounded-xl bg-surface border border-border overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <p className="text-sm font-semibold text-text-primary">Feature PSI Scores</p>
            <p className="text-xs text-text-muted mt-0.5">Population Stability Index vs. baseline</p>
          </div>
          <div className="divide-y divide-border">
            {report.feature_drift.map((f: any) => {
              const { label, cls } = PSI_LABEL(f.psi_score);
              return (
                <div key={f.feature_name} className="px-5 py-3 flex items-center justify-between">
                  <div className="flex-1 min-w-0 mr-4">
                    <p className="text-xs font-medium text-text-primary truncate font-mono">{f.feature_name}</p>
                    <p className="text-[10px] text-text-subtle mt-0.5">
                      baseline: {f.baseline_mean} → current: {f.current_mean}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-bold text-text-primary">
                      {f.psi_score.toFixed(3)}
                    </span>
                    <span className={cn("badge text-[10px]", cls)}>{label}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="col-span-3 rounded-xl bg-surface border border-border p-5">
          <p className="text-sm font-semibold text-text-primary mb-1">PSI Trend — Last 30 Days</p>
          <p className="text-xs text-text-muted mb-4">Key feature distributions drifting over time</p>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={PSI_HISTORY} margin={{ left: -20, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#64748B" }} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "#64748B" }} tickLine={false} axisLine={false} />
              <ReferenceLine y={0.1} stroke="#F59E0B" strokeDasharray="4 2" label={{ value: "Warn", position: "right", fontSize: 9, fill: "#F59E0B" }} />
              <ReferenceLine y={0.2} stroke="#EF4444" strokeDasharray="4 2" label={{ value: "Crit", position: "right", fontSize: 9, fill: "#EF4444" }} />
              <Tooltip content={<CustomTooltip />} />
              {Object.entries(PSI_COLORS).map(([key, color]) => (
                <Line key={key} type="monotone" dataKey={key} stroke={color} strokeWidth={2} dot={{ r: 3 }} name={key.replace("_psi", "")} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Bottom row — prediction drift + fraud rate trend */}
      <div className="grid grid-cols-2 gap-4">

        {/* Prediction distribution drift */}
        <div className="rounded-xl bg-surface border border-border p-5">
          <div className="flex items-center gap-2 mb-4">
            <TrendingDown className={cn("w-4 h-4", predDrift?.drift_detected ? "text-warning" : "text-success")} />
            <p className="text-sm font-semibold text-text-primary">Prediction Distribution Drift</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {[
              { label: "Baseline Fraud Rate", value: `${((predDrift?.baseline_fraud_rate || 0.035) * 100).toFixed(1)}%` },
              { label: "Current Fraud Rate", value: `${((predDrift?.current_fraud_rate || 0.052) * 100).toFixed(1)}%`, highlight: true },
              { label: "Rate Shift", value: `+${predDrift?.rate_shift_pct?.toFixed(1)}%`, warn: true },
              { label: "Prediction PSI", value: (predDrift?.psi_score || 0).toFixed(3) },
            ].map(({ label, value, highlight, warn }) => (
              <div key={label} className="p-3 rounded-lg bg-surface-2 border border-border">
                <p className="text-[10px] text-text-muted">{label}</p>
                <p className={cn("text-lg font-bold font-mono mt-1",
                  warn ? "text-warning" : highlight ? "text-danger" : "text-text-primary"
                )}>{value}</p>
              </div>
            ))}
          </div>
          <div className={cn(
            "mt-4 flex items-start gap-2 p-3 rounded-lg border text-xs",
            predDrift?.drift_detected
              ? "bg-warning/5 border-warning/20 text-warning"
              : "bg-success/5 border-success/20 text-success"
          )}>
            <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span>
              {predDrift?.drift_detected
                ? "Fraud rate has shifted +48.6% vs. baseline. Consider scheduled retraining."
                : "Prediction distribution stable — no action required."
              }
            </span>
          </div>
        </div>

        {/* Fraud rate over time */}
        <div className="rounded-xl bg-surface border border-border p-5">
          <p className="text-sm font-semibold text-text-primary mb-1">Rolling Fraud Rate — 30 Days</p>
          <p className="text-xs text-text-muted mb-4">Current vs. baseline (3.5%)</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={FRAUD_RATE_TREND} margin={{ left: -20, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" />
              <XAxis dataKey="day" tick={{ fontSize: 9, fill: "#64748B" }} tickLine={false} interval={4} />
              <YAxis tick={{ fontSize: 10, fill: "#64748B" }} tickLine={false} axisLine={false} unit="%" />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine y={3.5} stroke="#64748B" strokeDasharray="4 2" />
              <Line type="monotone" dataKey="baseline" stroke="#64748B" strokeDasharray="4 2" dot={false} name="Baseline" strokeWidth={1} />
              <Line type="monotone" dataKey="current" stroke="#6366F1" strokeWidth={2} dot={false} name="Current" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
