import type { ButtonHTMLAttributes } from "react";
import clsx from "clsx";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "ghost";
  size?: "md" | "sm";
}

export function Button({ className, variant = "primary", size = "md", ...props }: Props) {
  const sizeClasses = size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3 py-2 text-sm";
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center rounded-md font-medium transition focus:outline-none focus:ring-2 focus:ring-accent-400/80",
        sizeClasses,
        variant === "primary"
          ? "bg-accent-500 text-ink-900 hover:bg-accent-400"
          : "text-slate-200 hover:bg-slate-800 border border-slate-700",
        className,
      )}
      {...props}
    />
  );
}
