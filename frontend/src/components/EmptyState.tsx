import type { ReactNode } from "react";
import { Button } from "./Button";

interface Props {
  title: string;
  message: string;
  ctaLabel?: string;
  onClick?: () => void;
  icon?: ReactNode;
}

export function EmptyState({ title, message, ctaLabel, onClick, icon }: Props) {
  return (
    <div className="border border-dashed border-slate-700 rounded-lg px-6 py-8 text-center text-slate-300 bg-ink-800/30">
      <div className="flex justify-center mb-3 text-2xl">{icon ?? "🧭"}</div>
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="text-sm text-slate-400 mt-1">{message}</p>
      {ctaLabel && onClick && (
        <div className="mt-4">
          <Button onClick={onClick}>{ctaLabel}</Button>
        </div>
      )}
    </div>
  );
}
