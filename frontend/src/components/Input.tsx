import type { InputHTMLAttributes } from "react";
import clsx from "clsx";

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export function Input({ label, hint, error, className, ...props }: Props) {
  return (
    <label className="block text-sm text-slate-200 space-y-1">
      {label && <span className="text-slate-300">{label}</span>}
      <input
        className={clsx(
          "w-full rounded-md border bg-ink-900 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-accent-400 focus:ring-2 focus:ring-accent-400/40",
          error ? "border-red-500" : "border-slate-700",
          className,
        )}
        {...props}
      />
      {(hint || error) && (
        <span className={clsx("text-xs", error ? "text-red-400" : "text-slate-400")}>{error ?? hint}</span>
      )}
    </label>
  );
}
