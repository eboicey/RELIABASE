import { NavLink, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import clsx from "clsx";
import { useQuery } from "@tanstack/react-query";
import { getHealth } from "../api/endpoints";

const analyticsNav = [
  { to: "/dashboard", label: "Home", icon: "⏲" },
  { to: "/analytics", label: "All Assets", icon: "📈" },
];

const configNav = [
  { to: "/config/assets", label: "Assets", icon: "🛠" },
  { to: "/config/exposures", label: "Exposures", icon: "⏳" },
  { to: "/config/events", label: "Events", icon: "📅" },
  { to: "/config/event-details", label: "Event Details", icon: "🧩" },
  { to: "/config/failure-modes", label: "Failure Modes", icon: "⚠️" },
  { to: "/config/parts", label: "Parts", icon: "📦" },
  { to: "/config/operations", label: "Operations", icon: "🛰" },
];

interface Props {
  children: ReactNode;
}

export function Shell({ children }: Props) {
  const { data: health, isLoading: healthLoading } = useQuery({ queryKey: ["health"], queryFn: getHealth });
  const location = useLocation();

  // Determine current page title from location
  const currentTitle = (() => {
    if (location.pathname === "/dashboard") return "Home";
    if (location.pathname === "/analytics") return "All Assets";
    if (location.pathname.startsWith("/analytics/asset/")) return "Asset Deep Dive";
    const configItem = configNav.find((item) => item.to === location.pathname);
    if (configItem) return configItem.label;
    return "RELIABASE";
  })();

  const isAssetDeepDive = location.pathname.startsWith("/analytics/asset/");

  return (
    <div className="min-h-screen grid grid-cols-[260px_1fr] bg-ink-900 text-slate-100">
      <aside className="border-r border-slate-800 bg-ink-800/80 backdrop-blur flex flex-col">
        <div className="px-5 py-6 flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-accent-500/20 border border-accent-500/40 flex items-center justify-center text-accent-400 font-semibold">R</div>
          <div>
            <div className="font-display text-lg">RELIABASE</div>
            <p className="text-xs text-slate-400">Reliability analytics</p>
          </div>
        </div>

        {/* Analytics section */}
        <nav className="px-3 space-y-1">
          <div className="px-3 pt-2 pb-1 text-[10px] uppercase tracking-[0.2em] text-slate-600 font-medium">Analytics</div>
          {analyticsNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition",
                  isActive || (item.to === "/analytics" && isAssetDeepDive)
                    ? "bg-accent-500/10 text-accent-300 border border-accent-500/20"
                    : "text-slate-300 hover:text-white hover:bg-slate-800/80 border border-transparent",
                )
              }
            >
              <span aria-hidden>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Configuration section */}
        <nav className="px-3 space-y-1 pb-4">
          <div className="px-3 pt-2 pb-1 text-[10px] uppercase tracking-[0.2em] text-slate-600 font-medium">Configuration</div>
          {configNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition",
                  isActive
                    ? "bg-accent-500/10 text-accent-300 border border-accent-500/20"
                    : "text-slate-300 hover:text-white hover:bg-slate-800/80 border border-transparent",
                )
              }
            >
              <span aria-hidden>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="min-h-screen">
        <header className="sticky top-0 z-10 bg-ink-900/80 backdrop-blur border-b border-slate-800 px-8 py-4 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Reliability control room</p>
            <h1 className="text-xl font-display text-white">{currentTitle}</h1>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-400">
            <span
              className={clsx(
                "h-2 w-2 rounded-full",
                healthLoading ? "bg-amber-400 animate-pulse" : health?.status === "ok" ? "bg-emerald-400" : "bg-red-400",
              )}
            />
            <span className="hidden sm:inline">
              Backend {healthLoading ? "checking" : health?.status === "ok" ? "online" : "unreachable"}
            </span>
            <code className="px-2 py-1 bg-slate-800 rounded text-slate-200">{import.meta.env.VITE_API_URL ?? "http://localhost:8000"}</code>
          </div>
        </header>
        <div className="px-8 py-6 max-w-6xl mx-auto space-y-6">{children}</div>
      </main>
    </div>
  );
}
