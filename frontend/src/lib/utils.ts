import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(amount);
}

export function formatPct(value: number, decimals = 2): string {
  return `${value.toFixed(decimals)}%`;
}

export function formatMs(ms: number): string {
  return `${ms.toFixed(1)}ms`;
}

export function riskColor(level: string): string {
  switch (level?.toUpperCase()) {
    case "HIGH": return "text-danger";
    case "MEDIUM": return "text-warning";
    case "LOW": return "text-info";
    case "MINIMAL": return "text-success";
    default: return "text-text-muted";
  }
}

export function riskBg(level: string): string {
  switch (level?.toUpperCase()) {
    case "HIGH": return "bg-danger/10 text-danger border-danger/20";
    case "MEDIUM": return "bg-warning/10 text-warning border-warning/20";
    case "LOW": return "bg-info/10 text-info border-info/20";
    case "MINIMAL": return "bg-success/10 text-success border-success/20";
    default: return "bg-surface-2 text-text-muted border-border";
  }
}

export function decisionBg(decision: string): string {
  switch (decision?.toUpperCase()) {
    case "BLOCK": return "bg-danger/10 text-danger border-danger/20";
    case "REVIEW": return "bg-warning/10 text-warning border-warning/20";
    case "ALLOW": return "bg-success/10 text-success border-success/20";
    default: return "bg-surface-2 text-text-muted border-border";
  }
}

export function truncateId(id: string, len = 12): string {
  if (!id) return "";
  return id.length > len ? id.slice(0, len) + "…" : id;
}
