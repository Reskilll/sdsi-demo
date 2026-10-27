import { forwardRef } from "react";
import { cn } from "@/utils/cn";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options: SelectOption[];
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, options, placeholder, className, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="mb-1.5 block text-sm font-medium text-slate-700">{label}</label>
        )}
        <select
          ref={ref}
          className={cn(
            "w-full rounded-lg border bg-white px-3.5 py-2.5 text-sm text-slate-900 transition-colors duration-200",
            "focus:outline-none focus:ring-2 focus:ring-offset-0",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            error
              ? "border-red-300 focus:border-red-400 focus:ring-red-500/20"
              : "border-slate-300 focus:border-indigo-400 focus:ring-indigo-500/20",
            className,
          )}
          {...props}
        >
          {placeholder && (
            <option value="" className="text-slate-400">{placeholder}</option>
          )}
          {options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        {error && <p className="mt-1.5 text-xs font-medium text-red-600">{error}</p>}
      </div>
    );
  },
);

Select.displayName = "Select";