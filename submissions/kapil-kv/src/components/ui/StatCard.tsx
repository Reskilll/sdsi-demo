import { cn } from "@/utils/cn";

interface StatCardProps {
  label: string;
  value: number | string;
  variant?: "default" | "success" | "danger" | "warning" | "info";
  className?: string;
}

const accentBarClasses: Record<string, string> = {
  default: "before:bg-indigo-500",
  success: "before:bg-emerald-500",
  danger: "before:bg-red-500",
  warning: "before:bg-amber-500",
  info: "before:bg-sky-500",
};

const valueColorClasses: Record<string, string> = {
  default: "text-slate-900",
  success: "text-emerald-700",
  danger: "text-red-700",
  warning: "text-amber-700",
  info: "text-sky-700",
};

export function StatCard({ label, value, variant = "default", className }: StatCardProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-xl border border-slate-200 bg-white p-5",
        "before:absolute before:left-0 before:top-0 before:h-full before:w-1 before:rounded-r-full",
        accentBarClasses[variant],
        className,
      )}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </p>
      <p className={cn("mt-2 text-2xl font-bold tracking-tight", valueColorClasses[variant])}>
        {value}
      </p>
    </div>
  );
}