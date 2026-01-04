import type { ReactNode } from "react";
import clsx from "clsx";

interface TableProps {
  children: ReactNode;
  className?: string;
}

export function Table({ children, className }: TableProps) {
  return (
    <div className={clsx("overflow-x-auto border border-slate-800/70 rounded-lg", className)}>
      <table className="min-w-full divide-y divide-slate-800 text-sm">{children}</table>
    </div>
  );
}

interface HeaderProps {
  children: ReactNode;
}
export function Th({ children }: HeaderProps) {
  return <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">{children}</th>;
}

interface CellProps {
  children: ReactNode;
  className?: string;
}
export function Td({ children, className }: CellProps) {
  return <td className={clsx("px-4 py-3 text-sm text-slate-100", className)}>{children}</td>;
}
