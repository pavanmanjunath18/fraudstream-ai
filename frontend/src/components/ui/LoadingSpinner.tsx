import { cn } from "@/lib/utils";

export function LoadingSpinner({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center justify-center p-12", className)}>
      <div className="w-8 h-8 border-2 border-border border-t-accent rounded-full animate-spin" />
    </div>
  );
}

export function SkeletonRow() {
  return (
    <div className="flex gap-4 p-4 animate-pulse">
      <div className="h-4 bg-surface-2 rounded w-32" />
      <div className="h-4 bg-surface-2 rounded w-24" />
      <div className="h-4 bg-surface-2 rounded w-16" />
      <div className="h-4 bg-surface-2 rounded w-20" />
      <div className="h-4 bg-surface-2 rounded flex-1" />
    </div>
  );
}
