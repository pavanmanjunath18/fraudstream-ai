"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import { Brain, Play, AlertCircle, CheckCircle } from "lucide-react";
import { fraudApi, type ScoringRequest } from "@/lib/api";
import { RiskBadge, DecisionBadge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";

// Simple UUID v4 — avoids adding the uuid package dependency
const uuidv4 = () =>
  "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });

// Global SHAP importance (representative of training data)
const GLOBAL_SHAP = [
  { feature: "Synthetic identity risk", importance: 0.342 },
  { feature: "Transaction velocity (1h)", importance: 0.298 },
  { feature: "Emulator detected", importance: 0.231 },
  { feature: "VPN usage", importance: 0.198 },
  { feature: "Device trust score", importance: 0.187 },
  { feature: "Unusual amount vs history", importance: 0.165 },
  { feature: "Prior chargebacks", importance: 0.148 },
  { feature: "Merchant risk score", importance: 0.131 },
  { feature: "Account age", importance: 0.112 },
  { feature: "Identity consistency", importance: 0.098 },
  { feature: "Geo velocity anomaly", importance: 0.087 },
  { feature: "Failed attempts (24h)", importance: 0.072 },
];

const DEMO_RESULT = {
  transaction_id: "TXN_DEMO001",
  prediction_id: "PRED_DEMO001",
  fraud_probability: 0.87,
  raw_ml_score: 0.79,
  risk_level: "HIGH",
  decision: "BLOCK",
  top_risk_factors: [
    "Synthetic identity risk",
    "Transaction velocity (1h)",
    "Emulator detected",
    "New/unknown device",
    "Geographic velocity anomaly",
  ],
  shap_factors: [
    { feature: "synthetic_identity_probability", label: "Synthetic identity risk", shap_value: 0.24, feature_value: 0.88, direction: "increases_risk" },
    { feature: "transactions_last_1h", label: "Transaction velocity (1h)", shap_value: 0.19, feature_value: 14, direction: "increases_risk" },
    { feature: "emulator_detected", label: "Emulator detected", shap_value: 0.15, feature_value: 1, direction: "increases_risk" },
    { feature: "known_device", label: "New/unknown device", shap_value: 0.12, feature_value: 0, direction: "increases_risk" },
    { feature: "geo_velocity_score", label: "Geo velocity anomaly", shap_value: 0.08, feature_value: 0.94, direction: "increases_risk" },
  ],
  rule_triggers: [
    { rule_id: "VPN_PLUS_EMULATOR", reason: "VPN + emulator combo detected", severity: "HIGH" },
    { rule_id: "VELOCITY_SPIKE", reason: ">10 transactions in last hour", severity: "HIGH" },
    { rule_id: "SYNTHETIC_IDENTITY", reason: "Synthetic identity probability > 70%", severity: "HIGH" },
  ],
  model_version: "1.0.0",
  latency_ms: 38.4,
};

const DEFAULT_TXN: ScoringRequest = {
  transaction_id: "",
  timestamp: new Date().toISOString(),
  account_id: "ACC_TEST001",
  merchant_id: "MER_CRYPTO01",
  amount: 4500,
  currency: "USD",
  payment_method: "crypto",
  device_id: "DEV_UNKNOWN99",
  ip_address: "185.220.101.45",
  geo_lat: 6.5244,
  geo_lon: 3.3792,
  merchant_category: "crypto",
  transaction_channel: "api",
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-surface-2 border border-border rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-text-muted mb-1">{label}</p>
      <p className="text-accent font-semibold">{payload[0]?.value?.toFixed(4)}</p>
    </div>
  );
};

export default function ExplainabilityPage() {
  const [txnInput, setTxnInput] = useState<ScoringRequest>({ ...DEFAULT_TXN });
  const [result, setResult] = useState<any>(null);
  const [scoring, setScoring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleScore = async () => {
    setScoring(true);
    setError(null);
    try {
      const payload = { ...txnInput, transaction_id: `TXN_${uuidv4().replace(/-/g, "").slice(0, 14).toUpperCase()}` };
      const res = await fraudApi.scoreTransaction(payload);
      setResult(res);
    } catch (e: any) {
      setError(e?.response?.data?.detail || "API unavailable — showing demo result");
      setResult(DEMO_RESULT);
    } finally {
      setScoring(false);
    }
  };

  const displayResult = result || null;

  return (
    <div className="grid grid-cols-5 gap-5 animate-fade-in">

      {/* Left — Transaction input + global importance */}
      <div className="col-span-2 space-y-5">

        {/* Score a transaction */}
        <div className="rounded-xl bg-surface border border-border p-5">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="w-4 h-4 text-accent" />
            <p className="text-sm font-semibold text-text-primary">Score a Transaction</p>
          </div>
          <div className="space-y-3">
            {[
              { key: "account_id", label: "Account ID" },
              { key: "merchant_id", label: "Merchant ID" },
              { key: "amount", label: "Amount (USD)", type: "number" },
              { key: "device_id", label: "Device ID" },
              { key: "ip_address", label: "IP Address" },
              { key: "merchant_category", label: "Category" },
            ].map(({ key, label, type }) => (
              <div key={key}>
                <label className="block text-xs text-text-muted mb-1">{label}</label>
                <input
                  type={type || "text"}
                  value={(txnInput as any)[key] ?? ""}
                  onChange={(e) =>
                    setTxnInput((prev) => ({
                      ...prev,
                      [key]: type === "number" ? +e.target.value : e.target.value,
                    }))
                  }
                  className="w-full px-3 py-2 bg-surface-2 border border-border rounded-lg text-xs text-text-primary font-mono focus:outline-none focus:border-accent/50 transition-colors"
                />
              </div>
            ))}
          </div>

          {error && (
            <div className="mt-3 flex items-start gap-2 p-2 rounded-lg bg-warning/10 border border-warning/20">
              <AlertCircle className="w-3.5 h-3.5 text-warning shrink-0 mt-0.5" />
              <p className="text-xs text-warning">{error}</p>
            </div>
          )}

          <button
            onClick={handleScore}
            disabled={scoring}
            className="mt-4 w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-sm font-medium transition-colors disabled:opacity-50"
          >
            <Play className={cn("w-3.5 h-3.5", scoring && "animate-spin")} />
            {scoring ? "Scoring…" : "Run Inference"}
          </button>
        </div>

        {/* Global SHAP importance */}
        <div className="rounded-xl bg-surface border border-border p-5">
          <p className="text-sm font-semibold text-text-primary mb-1">Global Feature Importance</p>
          <p className="text-xs text-text-muted mb-4">Mean |SHAP| across training data</p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={GLOBAL_SHAP} layout="vertical" margin={{ left: 0, right: 30 }}>
              <XAxis type="number" tick={{ fontSize: 9, fill: "#64748B" }} tickLine={false} axisLine={false} />
              <YAxis
                dataKey="feature"
                type="category"
                tick={{ fontSize: 10, fill: "#94A3B8" }}
                tickLine={false}
                axisLine={false}
                width={155}
              />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="importance" radius={[0, 4, 4, 0]} name="Importance">
                {GLOBAL_SHAP.map((_, i) => (
                  <Cell
                    key={i}
                    fill={i < 3 ? "#EF4444" : i < 6 ? "#F59E0B" : "#6366F1"}
                    opacity={0.8 - i * 0.04}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Right — Prediction result + SHAP waterfall */}
      <div className="col-span-3 space-y-5">
        {displayResult ? (
          <>
            {/* Score card */}
            <div className={cn(
              "rounded-xl border p-5",
              displayResult.decision === "BLOCK"
                ? "bg-danger/5 border-danger/20"
                : displayResult.decision === "REVIEW"
                ? "bg-warning/5 border-warning/20"
                : "bg-success/5 border-success/20"
            )}>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-xs text-text-muted mb-1">Fraud Probability</p>
                  <p className="text-4xl font-bold font-mono text-text-primary">
                    {(displayResult.fraud_probability * 100).toFixed(1)}%
                  </p>
                  <p className="text-xs text-text-muted mt-1">
                    ML score: {(displayResult.raw_ml_score * 100).toFixed(1)}% · Latency: {displayResult.latency_ms}ms
                  </p>
                </div>
                <div className="text-right space-y-2">
                  <div><RiskBadge level={displayResult.risk_level} /></div>
                  <div><DecisionBadge decision={displayResult.decision} /></div>
                </div>
              </div>

              {/* Score bar */}
              <div className="mt-3">
                <div className="h-2 bg-surface-2 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-700",
                      displayResult.fraud_probability > 0.75 ? "bg-danger" :
                      displayResult.fraud_probability > 0.5 ? "bg-warning" : "bg-success"
                    )}
                    style={{ width: `${displayResult.fraud_probability * 100}%` }}
                  />
                </div>
                <div className="flex justify-between mt-1">
                  <span className="text-[10px] text-text-subtle">0%</span>
                  <span className="text-[10px] text-warning">50%</span>
                  <span className="text-[10px] text-danger">75%</span>
                  <span className="text-[10px] text-text-subtle">100%</span>
                </div>
              </div>
            </div>

            {/* SHAP waterfall */}
            {displayResult.shap_factors?.length > 0 && (
              <div className="rounded-xl bg-surface border border-border p-5">
                <p className="text-sm font-semibold text-text-primary mb-1">SHAP Feature Contributions</p>
                <p className="text-xs text-text-muted mb-4">Positive values push probability toward fraud</p>
                <div className="space-y-2.5">
                  {displayResult.shap_factors.map((f: any) => (
                    <div key={f.feature} className="flex items-center gap-3">
                      <span className="text-xs text-text-muted w-44 truncate">{f.label}</span>
                      <div className="flex-1 flex items-center gap-2">
                        <div className="flex-1 h-5 bg-surface-2 rounded overflow-hidden relative">
                          <div
                            className="absolute left-0 top-0 h-full bg-danger/70 rounded"
                            style={{ width: `${Math.min(f.shap_value / 0.3, 1) * 100}%` }}
                          />
                        </div>
                        <span className="font-mono text-xs text-danger w-12 text-right">
                          +{f.shap_value.toFixed(3)}
                        </span>
                      </div>
                      <span className="font-mono text-xs text-text-subtle w-16 text-right">
                        val={typeof f.feature_value === "number" ? f.feature_value.toFixed(2) : f.feature_value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Rule triggers */}
            {displayResult.rule_triggers?.length > 0 && (
              <div className="rounded-xl bg-surface border border-border p-5">
                <p className="text-sm font-semibold text-text-primary mb-3">Rule Engine Triggers</p>
                <div className="space-y-2">
                  {displayResult.rule_triggers.map((r: any) => (
                    <div key={r.rule_id} className="flex items-start gap-3 p-3 rounded-lg bg-surface-2 border border-border">
                      <AlertCircle className={cn(
                        "w-4 h-4 mt-0.5 shrink-0",
                        r.severity === "CRITICAL" || r.severity === "HIGH" ? "text-danger" : "text-warning"
                      )} />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-text-primary">{r.reason}</p>
                        <p className="text-[10px] text-text-subtle mt-0.5 font-mono">{r.rule_id}</p>
                      </div>
                      <span className={cn(
                        "badge text-[10px]",
                        r.severity === "CRITICAL" || r.severity === "HIGH"
                          ? "bg-danger/10 text-danger border-danger/20"
                          : "bg-warning/10 text-warning border-warning/20"
                      )}>
                        {r.severity}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full min-h-[400px] rounded-xl border border-dashed border-border text-center p-8">
            <Brain className="w-12 h-12 text-text-subtle mb-3" />
            <p className="text-sm font-medium text-text-muted">Run a transaction to see SHAP explanations</p>
            <p className="text-xs text-text-subtle mt-1">Modify the inputs on the left and click Run Inference</p>
          </div>
        )}
      </div>
    </div>
  );
}
