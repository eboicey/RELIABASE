import type { ReactNode } from "react";
import clsx from "clsx";

interface Props {
  tone?: "info" | "success" | "warning" | "danger";
  children: ReactNode;
}

const toneStyles: Record<NonNullable<Props["tone"]>, string> = {
  info: "bg-slate-800 text-slate-100 border-slate-700",
  success: "bg-emerald-900/40 text-emerald-100 border-emerald-500/40",
  warning: "bg-amber-900/40 text-amber-100 border-amber-500/50",
  danger: "bg-red-900/40 text-red-100 border-red-500/50",
};

export function Alert({ tone = "info", children }: Props) {
  return <div className={clsx("rounded-lg border px-4 py-3 text-sm", toneStyles[tone])}>{children}</div>;
}
