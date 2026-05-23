import axios from "axios";

// In production: set NEXT_PUBLIC_API_URL to your Render backend URL
// e.g. https://fraudstream-backend.onrender.com
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" ? "" : "http://localhost:8001");

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 15_000, // generous timeout — Render free tier cold-starts in ~30s
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("fs_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const fraudApi = {
  getOverview: () => api.get("/api/analytics/overview").then((r) => r.data),
  getRecentTransactions: (limit = 50) =>
    api.get(`/api/analytics/recent-transactions?limit=${limit}`).then((r) => r.data),
  getFraudOverTime: (hours = 24) =>
    api.get(`/api/analytics/fraud-over-time?hours=${hours}`).then((r) => r.data),
  getRiskDistribution: () =>
    api.get("/api/analytics/risk-distribution").then((r) => r.data),
  getTopRiskFactors: () =>
    api.get("/api/analytics/top-risk-factors").then((r) => r.data),
  getLatencyStats: () =>
    api.get("/api/analytics/latency-stats").then((r) => r.data),
  getProbabilityDistribution: () =>
    api.get("/api/analytics/probability-distribution").then((r) => r.data),
  scoreTransaction: (txn: ScoringRequest) =>
    api.post("/api/scoring/predict", txn).then((r) => r.data),
  getPredictionHistory: (limit = 50, riskLevel?: string) =>
    api
      .get(`/api/scoring/history?limit=${limit}${riskLevel ? `&risk_level=${riskLevel}` : ""}`)
      .then((r) => r.data),
  getDriftReport: () => api.get("/api/drift/report").then((r) => r.data),
  getDriftEvents: () => api.get("/api/drift/events").then((r) => r.data),
  getHealth: () => api.get("/api/monitoring/health").then((r) => r.data),
  getMetrics: () => api.get("/api/monitoring/metrics").then((r) => r.data),
  getModelInfo: () => api.get("/api/monitoring/model-info").then((r) => r.data),
};

export interface ScoringRequest {
  transaction_id: string;
  timestamp: string;
  account_id: string;
  merchant_id: string;
  amount: number;
  currency: string;
  payment_method: string;
  device_id: string;
  ip_address: string;
  geo_lat?: number;
  geo_lon?: number;
  merchant_category?: string;
  transaction_channel?: string;
}
