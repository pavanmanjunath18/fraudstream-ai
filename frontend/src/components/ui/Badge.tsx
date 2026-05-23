import { cn, riskBg, decisionBg } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  className?: string;
}

export function RiskBadge({ level }: { level: string }) {
  return (
    <span className={cn("badge", riskBg(level))}>
      {level}
    </span>
  );
}

export function DecisionBadge({ decision }: { decision: string }) {
  return (
    <span className={cn("badge font-semibold", decisionBg(decision))}>
      {decision}
    </span>
  );
}

export function Badge({ children, className }: BadgeProps) {
  return (
    <span className={cn("badge", className)}>{children}</span>
  );
}
