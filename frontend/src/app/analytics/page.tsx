"use client";

import { useQuery } from "@tanstack/react-query";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ScatterChart, Scatter, ZAxis,
  Cell,
} from "recharts";
import { fraudApi } from "@/lib/api";

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

// Demo data
const FRAUD_BY_CATEGORY = [
  { category: "Crypto", fraud_rate: 10.2, total: 4_200 },
  { category: "Gambling", fraud_rate: 12.4, total: 3_100 },
  { category: "Electronics", fraud_rate: 7.8, total: 18_400 },
  { category: "Travel", fraud_rate: 4.1, total: 22_000 },
  { category: "Subscription", fraud_rate: 3.0, total: 15_000 },
  { category: "Retail", fraud_rate: 2.1, total: 48_000 },
  { category: "Grocery", fraud_rate: 0.5, total: 62_000 },
];

const FRAUD_BY_HOUR = Array.from({ length: 24 }, (_, h) => ({
  hour: `${String(h).padStart(2, "0")}:00`,
  fraud_rate: h >= 0 && h <= 4
    ? +(5 + Math.random() * 4).toFixed(2)
    : +(1.5 + Math.random() * 2).toFixed(2),
  volume: Math.floor(400 + Math.random() * 800),
}));

const FRAUD_BY_CHANNEL = [
  { channel: "API", fraud_rate: 5.2, color: "#6366F1" },
  { channel: "Web", fraud_rate: 3.8, color: "#8B5CF6" },
  { channel: "Mobile", fraud_rate: 2.9, color: "#EC4899" },
  { channel: "In-store", fraud_rate: 1.2, color: "#10B981" },
  { channel: "ATM", fraud_rate: 2.1, color: "#F59E0B" },
];

const GEO_SCATTER = [
  { lat: 40.7, lon: -74.0, fraud: 120, city: "New York" },
  { lat: 34.0, lon: -118.2, fraud: 98, city: "Los Angeles" },
  { lat: 41.9, lon: -87.6, fraud: 76, city: "Chicago" },
  { lat: 6.5, lon: 3.4, fraud: 201, city: "Lagos" },
  { lat: 55.8, lon: 37.6, fraud: 185, city: "Moscow" },
  { lat: 50.4, lon: 30.5, fraud: 143, city: "Kyiv" },
  { lat: 1.3, lon: 103.8, fraud: 67, city: "Singapore" },
  { lat: 51.5, lon: -0.1, fraud: 54, city: "London" },
];

export default function AnalyticsPage() {
  const { data: timeSeries } = useQuery({
    queryKey: ["fraud-over-time", 72],
    queryFn: () => fraudApi.getFraudOverTime(72),
  });

  const { data: topFactors } = useQuery({
    queryKey: ["top-risk-factors"],
    queryFn: fraudApi.getTopRiskFactors,
  });

  return (
    <div className="space-y-5 animate-fade-in">

      {/* Row 1 — Fraud by merchant category + hour heatmap */}
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl bg-surface border border-border p-5">
          <p className="text-sm font-semibold text-text-primary mb-1">Fraud Rate by Merchant Category</p>
          <p className="text-xs text-text-muted mb-4">% of transactions blocked per category</p>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={FRAUD_BY_CATEGORY} margin={{ left: -20, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" />
              <XAxis dataKey="category" tick={{ fontSize: 10, fill: "#64748B" }} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "#64748B" }} tickLine={false} axisLine={false} unit="%" />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="fraud_rate" name="Fraud %" radius={[4, 4, 0, 0]}>
                {FRAUD_BY_CATEGORY.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={entry.fraud_rate > 8 ? "#EF4444" : entry.fraud_rate > 4 ? "#F59E0B" : "#6366F1"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-xl bg-surface border border-border p-5">
          <p className="text-sm font-semibold text-text-primary mb-1">Fraud Rate by Hour of Day</p>
          <p className="text-xs text-text-muted mb-4">Night-time fraud spike (00:00–04:00)</p>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={FRAUD_BY_HOUR} margin={{ left: -20, right: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" />
              <XAxis dataKey="hour" tick={{ fontSize: 9, fill: "#64748B" }} tickLine={false} interval={3} />
              <YAxis tick={{ fontSize: 10, fill: "#64748B" }} tickLine={false} axisLine={false} unit="%" />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="fraud_rate"
                stroke="#EF4444"
                strokeWidth={2}
                dot={{ fill: "#EF4444", r: 3 }}
                name="Fraud %"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row 2 — Channel breakdown + geo heatmap simulation */}
      <div className="grid grid-cols-5 gap-4">
        <div className="col-span-2 rounded-xl bg-surface border border-border p-5">
          <p className="text-sm font-semibold text-text-primary mb-4">Fraud by Payment Channel</p>
          <div className="space-y-3">
            {FRAUD_BY_CHANNEL.sort((a, b) => b.fraud_rate - a.fraud_rate).map((d) => (
              <div key={d.channel} className="flex items-center gap-3">
                <span className="text-xs text-text-muted w-16">{d.channel}</span>
                <div className="flex-1 h-5 bg-surface-2 rounded-md overflow-hidden">
                  <div
                    className="h-full rounded-md transition-all"
                    style={{
                      width: `${(d.fraud_rate / 6) * 100}%`,
                      background: d.color,
                      opacity: 0.85,
                    }}
                  />
                </div>
                <span className="text-xs font-mono font-semibold text-text-primary w-10 text-right">
                  {d.fraud_rate}%
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="col-span-3 rounded-xl bg-surface border border-border p-5">
          <p className="text-sm font-semibold text-text-primary mb-1">Fraud Hotspots by Geography</p>
          <p className="text-xs text-text-muted mb-4">Bubble size = fraud count at origin</p>
          <div className="space-y-2">
            {GEO_SCATTER.sort((a, b) => b.fraud - a.fraud).map((city) => (
              <div key={city.city} className="flex items-center gap-3">
                <div className="flex items-center gap-2 w-32">
                  <div
                    className="rounded-full bg-danger/30 border border-danger/40"
                    style={{
                      width: Math.max(8, city.fraud / 10),
                      height: Math.max(8, city.fraud / 10),
                    }}
                  />
                  <span className="text-xs text-text-muted truncate">{city.city}</span>
                </div>
                <div className="flex-1 h-2 bg-surface-2 rounded overflow-hidden">
                  <div
                    className="h-full bg-danger/60 rounded"
                    style={{ width: `${(city.fraud / 210) * 100}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-danger w-10 text-right">{city.fraud}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Row 3 — Fraud over 72h */}
      <div className="rounded-xl bg-surface border border-border p-5">
        <p className="text-sm font-semibold text-text-primary mb-1">Fraud Trend — 72 Hours</p>
        <p className="text-xs text-text-muted mb-4">Hourly blocked transactions</p>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart
            data={timeSeries?.length ? timeSeries : FRAUD_BY_HOUR}
            margin={{ left: -20, right: 10 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#1E1E2E" />
            <XAxis dataKey="hour" tick={{ fontSize: 9, fill: "#64748B" }} tickLine={false} interval={5} />
            <YAxis tick={{ fontSize: 10, fill: "#64748B" }} tickLine={false} axisLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Line type="monotone" dataKey="fraud" stroke="#EF4444" strokeWidth={2} dot={false} name="Blocked" />
            <Line type="monotone" dataKey="total" stroke="#6366F1" strokeWidth={1.5} dot={false} name="Total" strokeDasharray="4 2" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
