import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listAssets, listEvents, listExposures, getHealth, seedDemo, getFleetHealthSummary, getBadActors, getFleetAnalytics } from "../api/endpoints";
import { Card } from "../components/Card";
import { Table, Th, Td } from "../components/Table";
import { format } from "date-fns";
import { Button } from "../components/Button";
import { useState, useMemo } from "react";
import { Alert } from "../components/Alert";
import { MetricTooltip, StatWithTooltip } from "../components/MetricTooltip";
import { useNavigate } from "react-router-dom";

export default function Dashboard() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 200 }) });
  const { data: events } = useQuery({ queryKey: ["events"], queryFn: () => listEvents({ limit: 200 }) });
  const { data: exposures } = useQuery({ queryKey: ["exposures"], queryFn: () => listExposures({ limit: 200 }) });
  const { data: health, isLoading: healthLoading } = useQuery({ queryKey: ["health"], queryFn: getHealth });
  const [seedSuccess, setSeedSuccess] = useState(false);

  const { data: fleetHealth } = useQuery({
    queryKey: ["fleet-health"],
    queryFn: () => getFleetHealthSummary({ limit: 50 }),
  });

  const { data: badActors } = useQuery({
    queryKey: ["bad-actors"],
    queryFn: () => getBadActors({ top_n: 5 }),
  });

  const { data: fleetAnalytics } = useQuery({
    queryKey: ["fleet-analytics-home"],
    queryFn: () => getFleetAnalytics({ limit: 50 }),
  });

  const seedMutation = useMutation({
    mutationFn: () => seedDemo({ reset: true }),
    onSuccess: () => {
      setSeedSuccess(true);
      ["assets", "events", "exposures", "failure-modes", "event-details", "parts", "health", "fleet-health", "bad-actors", "fleet-analytics-home"].forEach((key) =>
        queryClient.invalidateQueries({ queryKey: [key] })
      );
      setTimeout(() => setSeedSuccess(false), 3000);
    },
  });

  const totalHours = exposures?.reduce((sum, log) => sum + (log.hours ?? 0), 0) ?? 0;
  const failureCount = events?.filter((e) => e.event_type === "failure").length ?? 0;
  const backendOnline = health?.status === "ok";

  const fleetSummary = useMemo(() => {
    if (!fleetHealth || fleetHealth.length === 0) return null;
    const avgScore = fleetHealth.reduce((s, h) => s + h.score, 0) / fleetHealth.length;
    const critical = fleetHealth.filter((h) => h.grade === "D" || h.grade === "F").length;
    const healthy = fleetHealth.filter((h) => h.grade === "A" || h.grade === "B").length;
    return { avgScore, critical, healthy, total: fleetHealth.length };
  }, [fleetHealth]);

  const fleetFailurePattern = useMemo(() => {
    if (!fleetAnalytics || fleetAnalytics.length === 0) return null;
    let wearOut = 0, infantMortality = 0, random = 0;
    for (const a of fleetAnalytics) {
      if (a.weibull) {
        if (a.weibull.shape > 1) wearOut++;
        else if (a.weibull.shape < 1) infantMortality++;
        else random++;
      }
    }
    const total = wearOut + infantMortality + random;
    if (total === 0) return null;
    const dominant = wearOut >= infantMortality && wearOut >= random ? "Wear-out" :
                     infantMortality >= random ? "Infant mortality" : "Random";
    return { dominant, wearOut, infantMortality, random, total };
  }, [fleetAnalytics]);

  const recentFailures = useMemo(() => {
    if (!events) return [];
    return events
      .filter((e) => e.event_type === "failure")
      .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
      .slice(0, 5);
  }, [events]);

  const hasData = (assets?.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      {/* Onboarding — only when empty */}
      {!hasData && backendOnline && (
        <Card className="border-accent-500/30 bg-accent-900/10">
          <div className="text-center py-6 space-y-3">
            <div className="text-4xl">🚀</div>
            <h2 className="text-xl font-display text-white">Welcome to RELIABASE</h2>
            <p className="text-sm text-slate-400 max-w-md mx-auto">
              No assets configured yet. Seed demo data to explore reliability analytics, or add your own assets via the Configuration pages.
            </p>
            <div className="flex justify-center gap-3">
              <Button onClick={() => seedMutation.mutate()} disabled={seedMutation.isPending}>
                {seedMutation.isPending ? "Seeding..." : "Seed Demo Data"}
              </Button>
              <Button variant="ghost" onClick={() => navigate("/config/assets")}>Add Assets Manually</Button>
            </div>
            {seedSuccess && <Alert tone="success">Demo data seeded! Insights are loading.</Alert>}
            {seedMutation.isError && <Alert tone="danger">Failed to seed. Is the backend running?</Alert>}
          </div>
        </Card>
      )}

      {!backendOnline && !healthLoading && (
        <Alert tone="danger">
          Backend is offline. Start the server: <code className="bg-slate-800 px-2 py-0.5 rounded text-xs">uvicorn reliabase.api.main:app --host 127.0.0.1 --port 8000 --reload</code>
        </Alert>
      )}

      {hasData && (
        <>
          {/* ─── Fleet Health Score Banner ─── */}
          {fleetSummary && (
            <div className="rounded-xl border border-slate-800/80 bg-gradient-to-r from-ink-800/80 to-ink-900/60 p-6">
              <div className="flex items-center justify-between flex-wrap gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h2 className="text-sm uppercase tracking-[0.2em] text-slate-500">Fleet Health Score</h2>
                    <MetricTooltip
                      label="Fleet Health Score"
                      what="Weighted average health score across all monitored assets, combining reliability, OEE, downtime, and repair trends."
                      why="Provides a single number to assess overall fleet condition. Declining scores signal systemic issues requiring attention."
                      basis="Composite index derived from availability, failure frequency, repair effectiveness, and production quality — core RAM (Reliability, Availability, Maintainability) principles."
                      interpret="80+ is healthy fleet. 60-80 needs targeted improvements. Below 60 indicates systemic reliability problems requiring root cause analysis."
                    />
                  </div>
                  <div className="flex items-baseline gap-3">
                    <span className={`text-5xl font-bold ${
                      fleetSummary.avgScore >= 80 ? "text-emerald-400" :
                      fleetSummary.avgScore >= 60 ? "text-amber-400" : "text-red-400"
                    }`}>
                      {fleetSummary.avgScore.toFixed(0)}
                    </span>
                    <span className="text-slate-400 text-sm">/ 100</span>
                  </div>
                </div>
                <div className="flex gap-6 text-center">
                  <div>
                    <div className="text-2xl font-bold text-emerald-400">{fleetSummary.healthy}</div>
                    <div className="text-xs text-slate-500">Healthy (A/B)</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-red-400">{fleetSummary.critical}</div>
                    <div className="text-xs text-slate-500">Critical (D/F)</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold text-slate-300">{fleetSummary.total}</div>
                    <div className="text-xs text-slate-500">Total Assets</div>
                  </div>
                </div>
                <Button variant="ghost" onClick={() => navigate("/analytics")}>
                  View All Assets →
                </Button>
              </div>
            </div>
          )}

          {/* ─── Critical KPIs ─── */}
          <div className="grid gap-4 grid-cols-1 md:grid-cols-4">
            <StatWithTooltip
              label="Total Failures"
              value={`${failureCount}`}
              valueClass={failureCount > 0 ? "text-red-400" : "text-emerald-400"}
              tooltip={{
                what: "Count of all failure events recorded across the fleet.",
                why: "Failures drive downtime, cost, and risk. Tracking total failures reveals whether reliability is improving or degrading over time.",
                basis: "Fundamental reliability metric — failure count is the numerator in failure rate (λ = failures / operating hours), the inverse of MTBF.",
                interpret: "Lower is better. Compare period-over-period. Rising failure counts despite stable hours indicate degrading reliability.",
              }}
            />
            <StatWithTooltip
              label="Exposure Hours"
              value={`${totalHours.toLocaleString()}`}
              tooltip={{
                what: "Total accumulated operating hours across all assets.",
                why: "Operating time is the denominator for every time-based reliability metric. Without accurate exposure data, MTBF and failure rates are meaningless.",
                basis: "Operating time (T) is fundamental to reliability: R(t) = e^(-λt). Every reliability calculation depends on accurate time-in-service.",
                interpret: "Track growth rate. Sudden drops may indicate assets taken offline. Ensure all assets are logging exposure consistently.",
              }}
            />
            <StatWithTooltip
              label="Fleet MTBF"
              value={failureCount > 0 ? `${(totalHours / failureCount).toFixed(0)} h` : "∞"}
              tooltip={{
                what: "Mean Time Between Failures — average hours of operation between consecutive failures, calculated fleet-wide.",
                why: "MTBF is the most widely used reliability metric. It directly estimates how often you can expect failures to occur.",
                basis: "MTBF = Total Operating Hours / Number of Failures. For exponential distributions, MTBF = 1/λ. Higher MTBF means more reliable operation.",
                interpret: "Higher is better. Compare against industry benchmarks. Fleet MTBF smooths out individual asset variation to show systemic reliability.",
              }}
            />
            <StatWithTooltip
              label="Assets Tracked"
              value={`${assets?.length ?? 0}`}
              tooltip={{
                what: "Total number of assets registered in the system with active monitoring.",
                why: "Coverage matters — untracked assets introduce blind spots in fleet reliability assessments.",
                basis: "Complete coverage enables proper fleet-level statistics. Sample bias from partial tracking distorts MTBF, availability, and failure rate calculations.",
                interpret: "Ensure this matches your actual fleet size. Missing assets can inflate fleet health scores artificially.",
              }}
            />
          </div>

          {/* ─── Two Column: Worst Performers + Failure Pattern ─── */}
          <div className="grid gap-4 md:grid-cols-2">
            {badActors && badActors.length > 0 && (
              <Card
                title="Worst Performers"
                actions={
                  <MetricTooltip
                    label="Bad Actors"
                    what="Assets ranked by a composite unreliability score combining failure count, total downtime, and availability."
                    why="The Pareto principle applies to reliability: a small number of bad actors typically drive the majority of downtime and cost."
                    basis="Composite scoring normalizes failures, downtime hours, and availability (1 - A) into a single rank. Based on the 80/20 rule common in maintenance engineering."
                    interpret="Focus improvement efforts on the top 2-3 bad actors for maximum ROI. Click an asset to navigate to its deep-dive analysis."
                  />
                }
              >
                <div className="space-y-2">
                  {badActors.map((ba, idx) => (
                    <button
                      key={ba.asset_id}
                      onClick={() => navigate(`/analytics/asset/${ba.asset_id}`)}
                      className="w-full flex items-center gap-3 rounded-lg border border-slate-800/50 bg-ink-900/50 px-4 py-3 hover:border-accent-500/30 hover:bg-ink-800/50 transition text-left"
                    >
                      <span className={`text-lg font-bold w-6 ${idx === 0 ? "text-red-400" : idx === 1 ? "text-orange-400" : "text-amber-400"}`}>
                        {idx + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-white truncate">{ba.asset_name}</div>
                        <div className="text-xs text-slate-500">{ba.failure_count} failures · {ba.total_downtime_hours.toFixed(1)}h downtime</div>
                      </div>
                      <div className="text-right">
                        <div className={`text-sm font-semibold ${ba.availability < 0.9 ? "text-red-400" : "text-amber-400"}`}>
                          {(ba.availability * 100).toFixed(1)}%
                        </div>
                        <div className="text-[10px] text-slate-500">availability</div>
                      </div>
                    </button>
                  ))}
                </div>
              </Card>
            )}

            <div className="space-y-4">
              {fleetFailurePattern && (
                <Card
                  title="Dominant Failure Pattern"
                  actions={
                    <MetricTooltip
                      label="Failure Pattern"
                      what="Classifies assets' failure behavior using the Weibull shape parameter (β): infant mortality (β<1), random (β≈1), or wear-out (β>1)."
                      why="The failure pattern determines the correct maintenance strategy. Wear-out failures respond to time-based PM; random failures do not."
                      basis="Weibull distribution shape parameter (β) maps directly to the bathtub curve regions — the standard tool for classifying failure behavior in reliability engineering."
                      interpret="Wear-out dominant → PM schedules are effective. Infant mortality → investigate installation/commissioning. Random → consider condition-based monitoring."
                    />
                  }
                >
                  <div className="flex items-center gap-6">
                    <div className="text-center flex-1">
                      <div className={`text-3xl font-bold ${
                        fleetFailurePattern.dominant === "Wear-out" ? "text-amber-400" :
                        fleetFailurePattern.dominant === "Infant mortality" ? "text-red-400" : "text-blue-400"
                      }`}>
                        {fleetFailurePattern.dominant}
                      </div>
                      <div className="text-xs text-slate-500 mt-1">across {fleetFailurePattern.total} assets with Weibull fits</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-2 mt-4">
                    <div className="bg-ink-900/50 rounded p-2 text-center">
                      <div className="text-lg font-semibold text-amber-400">{fleetFailurePattern.wearOut}</div>
                      <div className="text-[10px] text-slate-500">Wear-out (β{">"} 1)</div>
                    </div>
                    <div className="bg-ink-900/50 rounded p-2 text-center">
                      <div className="text-lg font-semibold text-red-400">{fleetFailurePattern.infantMortality}</div>
                      <div className="text-[10px] text-slate-500">Infant (β{"<"} 1)</div>
                    </div>
                    <div className="bg-ink-900/50 rounded p-2 text-center">
                      <div className="text-lg font-semibold text-blue-400">{fleetFailurePattern.random}</div>
                      <div className="text-[10px] text-slate-500">Random (β ≈ 1)</div>
                    </div>
                  </div>
                </Card>
              )}

              {fleetHealth && fleetHealth.length > 0 && assets && assets.length > 0 && (
                <Card
                  title="Asset Health Map"
                  actions={
                    <MetricTooltip
                      label="Health Map"
                      what="Visual grid showing each asset's composite health score (0-100) and letter grade."
                      why="Enables instant identification of which assets need attention without reading tables."
                      basis="Grades: A (90-100) excellent, B (80-89) good, C (70-79) fair, D (60-69) poor, F (<60) critical. Based on composite RAM scoring."
                      interpret="Red/orange tiles need immediate investigation. Click any tile to go to the asset deep-dive."
                    />
                  }
                >
                  <div className="grid gap-1.5 grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6">
                    {fleetHealth.map((hi, idx) => {
                      const asset = assets[idx];
                      const name = asset?.name ?? `Asset ${idx + 1}`;
                      const assetId = asset?.id;
                      return (
                        <button
                          key={idx}
                          onClick={() => assetId && navigate(`/analytics/asset/${assetId}`)}
                          className={`rounded-lg p-2 text-center border transition hover:ring-1 hover:ring-accent-500/40 cursor-pointer ${
                            hi.grade === "A" ? "bg-emerald-900/20 border-emerald-500/30" :
                            hi.grade === "B" ? "bg-green-900/20 border-green-500/30" :
                            hi.grade === "C" ? "bg-amber-900/20 border-amber-500/30" :
                            hi.grade === "D" ? "bg-orange-900/20 border-orange-500/30" :
                            "bg-red-900/20 border-red-500/30"
                          }`}
                        >
                          <div className="text-[10px] text-slate-400 truncate" title={name}>{name}</div>
                          <div className={`text-xl font-bold mt-0.5 ${
                            hi.grade === "A" ? "text-emerald-400" :
                            hi.grade === "B" ? "text-green-400" :
                            hi.grade === "C" ? "text-amber-400" :
                            hi.grade === "D" ? "text-orange-400" : "text-red-400"
                          }`}>
                            {hi.score.toFixed(0)}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </Card>
              )}
            </div>
          </div>

          {/* ─── Recent Failures ─── */}
          <Card
            title="Recent Failures"
            actions={
              <div className="flex items-center gap-2">
                <MetricTooltip
                  label="Recent Failures"
                  what="Chronological list of the most recent failure events across all assets."
                  why="Failure events drive reliability metrics. Monitoring recent failures enables rapid response and trend detection."
                  basis="Every failure is a data point for Weibull analysis, MTBF calculation, and root cause investigation. Timely awareness enables corrective action before cascade failures."
                  interpret="Look for clustering (multiple failures in short time), repeated assets, or repeated failure modes — these signal systemic issues."
                />
                <Button variant="ghost" size="sm" onClick={() => navigate("/analytics")}>
                  All Assets →
                </Button>
              </div>
            }
          >
            {recentFailures.length > 0 ? (
              <Table>
                <thead>
                  <tr>
                    <Th>Timestamp</Th>
                    <Th>Asset</Th>
                    <Th>Downtime</Th>
                    <Th>Description</Th>
                  </tr>
                </thead>
                <tbody>
                  {recentFailures.map((evt) => {
                    const assetName = assets?.find((a) => a.id === evt.asset_id)?.name;
                    return (
                      <tr key={evt.id} className="odd:bg-ink-900 cursor-pointer hover:bg-ink-800/50" onClick={() => navigate(`/analytics/asset/${evt.asset_id}`)}>
                        <Td>{format(new Date(evt.timestamp), "yyyy-MM-dd HH:mm")}</Td>
                        <Td className="text-accent-400">{assetName ?? `#${evt.asset_id}`}</Td>
                        <Td>
                          <span className={`font-medium ${(evt.downtime_minutes ?? 0) > 60 ? "text-red-400" : "text-slate-300"}`}>
                            {evt.downtime_minutes ?? 0} min
                          </span>
                        </Td>
                        <Td className="text-slate-300">{evt.description ?? "—"}</Td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
            ) : (
              <div className="text-sm text-slate-400 py-4 text-center">
                No failures recorded yet.
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
