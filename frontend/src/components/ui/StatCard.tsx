import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: LucideIcon;
  trend?: { value: number; label: string };
  variant?: "default" | "danger" | "success" | "warning" | "accent";
  className?: string;
}

const VARIANT_STYLES = {
  default: "border-border",
  danger: "border-danger/20 glow-danger",
  success: "border-success/20 glow-success",
  warning: "border-warning/20",
  accent: "border-accent/20 glow-accent",
};

const ICON_STYLES = {
  default: "bg-surface-2 text-text-muted",
  danger: "bg-danger/10 text-danger",
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-warning",
  accent: "bg-accent/10 text-accent",
};

export function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  variant = "default",
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl bg-surface border p-5 flex flex-col gap-3 transition-all duration-200",
        VARIANT_STYLES[variant],
        className
      )}
    >
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium text-text-muted uppercase tracking-wider">{title}</p>
        {Icon && (
          <div className={cn("p-2 rounded-lg", ICON_STYLES[variant])}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      <div>
        <p className="text-2xl font-bold text-text-primary font-mono">{value}</p>
        {subtitle && (
          <p className="text-xs text-text-muted mt-1">{subtitle}</p>
        )}
      </div>

      {trend && (
        <div className="flex items-center gap-1.5">
          <span
            className={cn(
              "text-xs font-medium",
              trend.value > 0 ? "text-danger" : "text-success"
            )}
          >
            {trend.value > 0 ? "↑" : "↓"} {Math.abs(trend.value).toFixed(1)}%
          </span>
          <span className="text-xs text-text-subtle">{trend.label}</span>
        </div>
      )}
    </div>
  );
}
