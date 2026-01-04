interface Props {
  label: string;
  value: string;
  hint?: string;
}

export function Stat({ label, value, hint }: Props) {
  return (
    <div className="rounded-lg border border-slate-800/70 bg-ink-800/50 px-4 py-3">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className="text-2xl font-semibold text-white">{value}</p>
      {hint && <p className="text-xs text-slate-400">{hint}</p>}
    </div>
  );
}
