import type { ButtonHTMLAttributes } from "react";
import clsx from "clsx";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost";
}

export function Button({ className, variant = "primary", ...props }: Props) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-accent-400/80",
        variant === "primary"
          ? "bg-accent-500 text-ink-900 hover:bg-accent-400"
          : "text-slate-200 hover:bg-slate-800 border border-slate-700",
        className,
      )}
      {...props}
    />
  );
}
