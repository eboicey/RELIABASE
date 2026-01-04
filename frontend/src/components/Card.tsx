import type { ReactNode } from "react";
import clsx from "clsx";

interface Props {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Card({ title, description, actions, children, className }: Props) {
  return (
    <div className={clsx("border border-slate-800/80 bg-ink-800/50 rounded-xl shadow-lg shadow-black/30", className)}>
      {(title || description || actions) && (
        <div className="px-5 pt-5 pb-3 flex items-start justify-between gap-4">
          <div>
            {title && <h2 className="text-lg font-semibold text-white">{title}</h2>}
            {description && <p className="text-sm text-slate-400 mt-1">{description}</p>}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </div>
      )}
      <div className="px-5 pb-5">{children}</div>
    </div>
  );
}
