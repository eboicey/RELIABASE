import { useState, useRef, useEffect, type ReactNode } from "react";

interface Props {
  /** Short label for the metric */
  label: string;
  /** What this metric shows */
  what: string;
  /** Why this metric matters */
  why: string;
  /** First-principles basis (reliability / manufacturing / business) */
  basis: string;
  /** How to interpret and apply this metric */
  interpret: string;
  /** Optional children to render inline before the icon */
  children?: ReactNode;
}

export function MetricTooltip({ label, what, why, basis, interpret, children }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <span className="inline-flex items-center gap-1 relative" ref={ref}>
      {children}
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-slate-700/80 hover:bg-accent-500/30 text-slate-400 hover:text-accent-300 text-[10px] font-bold leading-none transition cursor-help shrink-0"
        aria-label={`Explain: ${label}`}
      >
        ?
      </button>
      {open && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-72 bg-ink-800 border border-slate-700 rounded-lg shadow-xl shadow-black/40 p-3 text-left">
          <div className="text-xs font-semibold text-accent-300 mb-1.5">{label}</div>
          <div className="space-y-1.5 text-[11px] leading-relaxed text-slate-300">
            <div>
              <span className="font-medium text-slate-200">What: </span>
              {what}
            </div>
            <div>
              <span className="font-medium text-slate-200">Why it matters: </span>
              {why}
            </div>
            <div>
              <span className="font-medium text-slate-200">Basis: </span>
              {basis}
            </div>
            <div>
              <span className="font-medium text-slate-200">Interpretation: </span>
              {interpret}
            </div>
          </div>
          {/* Arrow */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-[6px] border-r-[6px] border-t-[6px] border-l-transparent border-r-transparent border-t-slate-700" />
        </div>
      )}
    </span>
  );
}

/**
 * A Stat card with built-in metric tooltip.
 */
interface StatWithTooltipProps {
  label: string;
  value: string;
  hint?: string;
  tooltip: {
    what: string;
    why: string;
    basis: string;
    interpret: string;
  };
  /** Optional accent color class for the value */
  valueClass?: string;
}

export function StatWithTooltip({ label, value, hint, tooltip, valueClass }: StatWithTooltipProps) {
  return (
    <div className="rounded-lg border border-slate-800/70 bg-ink-800/50 px-4 py-3">
      <div className="flex items-center gap-1.5">
        <p className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</p>
        <MetricTooltip label={label} {...tooltip} />
      </div>
      <p className={`text-2xl font-semibold ${valueClass ?? "text-white"}`}>{value}</p>
      {hint && <p className="text-xs text-slate-400">{hint}</p>}
    </div>
  );
}
