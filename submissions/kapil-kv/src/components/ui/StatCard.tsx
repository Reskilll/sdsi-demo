import { cn } from "@/utils/cn";

interface StatCardProps {
  label: string;
  value: number | string;
  variant?: "default" | "success" | "danger" | "warning" | "info";
  className?: string;
}

export function StatCard({ label, value, variant = "default", className }: StatCardProps) {
  const variants = {
    default: "border-l-blue-500 text-blue-700 dark:text-blue-300",
    success: "border-l-green-500 text-green-700 dark:text-green-300",
    danger: "border-l-red-500 text-red-700 dark:text-red-300",
    warning: "border-l-yellow-500 text-yellow-700 dark:text-yellow-300",
    info: "border-l-purple-500 text-purple-700 dark:text-purple-300",
  };

  return (
    <div
      className={cn(
        "rounded-lg border border-[var(--border)] bg-[var(--muted)] p-4 shadow-sm",
        "border-l-4",
        variants[variant],
        className,
      )}
    >
      <p className="text-sm font-medium text-[var(--muted-foreground)]">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
    </div>
  );
}