import { useQuery } from "@tanstack/react-query";
import { useMemo, Suspense, lazy } from "react";
import { listAssets, getFleetHealthSummary, getBadActors, getFleetAnalytics, getSpareDemandForecast } from "../api/endpoints";
import { Card } from "../components/Card";
import { Table, Th, Td } from "../components/Table";
import { Spinner } from "../components/Spinner";
import { MetricTooltip, StatWithTooltip } from "../components/MetricTooltip";
import { useNavigate } from "react-router-dom";

const ParetoChart = lazy(() => import("../components/charts/ParetoChart"));

export default function AllAssets() {
  const navigate = useNavigate();
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 500 }) });
  const { data: fleetHealth } = useQuery({ queryKey: ["fleet-health"], queryFn: () => getFleetHealthSummary({ limit: 50 }) });
  const { data: badActors } = useQuery({ queryKey: ["bad-actors"], queryFn: () => getBadActors({ top_n: 20 }) });
  const { data: fleetAnalytics, isLoading: fleetLoading } = useQuery({ queryKey: ["fleet-analytics"], queryFn: () => getFleetAnalytics({ limit: 50 }) });
  const { data: spareDemand } = useQuery({ queryKey: ["spare-demand"], queryFn: () => getSpareDemandForecast({ horizon_hours: 8760 }) });

  // Fleet aggregate stats
  const fleetStats = useMemo(() => {
    if (!fleetAnalytics || fleetAnalytics.length === 0) return null;
    let totalFailures = 0, totalHours = 0, totalDowntime = 0;
    const allFailureModes: Record<string, number> = {};
    for (const a of fleetAnalytics) {
      totalFailures += a.kpis.failure_count;
      totalHours += a.kpis.total_exposure_hours;
      totalDowntime += a.recent_events.reduce((s, e) => s + (e.event_type === "failure" ? e.downtime_minutes : 0), 0);
      for (const fm of a.failure_modes) {
        allFailureModes[fm.name] = (allFailureModes[fm.name] ?? 0) + fm.count;
      }
    }
    const mtbf = totalFailures > 0 ? totalHours / totalFailures : null;
    const sortedModes = Object.entries(allFailureModes)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);
    return { totalFailures, totalHours, totalDowntime, mtbf, sortedModes };
  }, [fleetAnalytics]);

  const fleetSummary = useMemo(() => {
    if (!fleetHealth || fleetHealth.length === 0) return null;
    const avgScore = fleetHealth.reduce((s, h) => s + h.score, 0) / fleetHealth.length;
    const grades = { A: 0, B: 0, C: 0, D: 0, F: 0 };
    for (const h of fleetHealth) {
      const g = h.grade as keyof typeof grades;
      if (g in grades) grades[g]++;
    }
    return { avgScore, grades, total: fleetHealth.length };
  }, [fleetHealth]);

  // Per-asset summary table data
  const assetTable = useMemo(() => {
    if (!fleetAnalytics || !assets) return [];
    return fleetAnalytics.map((fa) => {
      const asset = assets.find((a) => a.id === fa.asset_id);
      const health = fleetHealth?.find((_, idx) => assets[idx]?.id === fa.asset_id);
      return {
        id: fa.asset_id,
        name: fa.asset_name,
        type: asset?.type ?? "—",
        failures: fa.kpis.failure_count,
        hours: fa.kpis.total_exposure_hours,
        mtbf: fa.kpis.mtbf_hours,
        availability: fa.kpis.availability,
        weibullShape: fa.weibull?.shape ?? null,
        healthScore: health?.score ?? null,
        healthGrade: health?.grade ?? null,
      };
    }).sort((a, b) => b.failures - a.failures);
  }, [fleetAnalytics, assets, fleetHealth]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display text-white">All Assets — Fleet Overview</h1>
          <p className="text-sm text-slate-400 mt-1">System-wide reliability analysis across your entire fleet</p>
        </div>
      </div>

      {fleetLoading && (
        <div className="flex items-center justify-center py-12">
          <Spinner />
          <span className="ml-3 text-slate-400">Loading fleet analytics...</span>
        </div>
      )}

      {/* ─── Fleet KPIs ─── */}
      {fleetStats && fleetSummary && (
        <>
          <div className="grid gap-4 grid-cols-1 md:grid-cols-5">
            <StatWithTooltip
              label="Fleet Score"
              value={fleetSummary.avgScore.toFixed(0)}
              valueClass={fleetSummary.avgScore >= 80 ? "text-emerald-400" : fleetSummary.avgScore >= 60 ? "text-amber-400" : "text-red-400"}
              tooltip={{
                what: "Average composite health score across all assets in the fleet.",
                why: "Single number summary of overall fleet condition. Trend this number weekly/monthly to track reliability improvement programs.",
                basis: "Weighted average of per-asset scores. Each asset score combines availability, failure rate trends, OEE, and repair effectiveness.",
                interpret: "80+: fleet is healthy. 60-80: targeted improvements needed. Below 60: systemic issues — escalate to engineering leadership.",
              }}
            />
            <StatWithTooltip
              label="Total Failures"
              value={fleetStats.totalFailures.toString()}
              valueClass="text-red-400"
              tooltip={{
                what: "Sum of all failure events across every asset in the fleet.",
                why: "Primary input for fleet-level failure rate. Drives resource planning for maintenance teams.",
                basis: "Fleet failure count = Σ(asset failures). Combined with total operating hours to compute fleet MTBF.",
                interpret: "Track trend over time. Increasing failures with stable hours = degrading fleet reliability.",
              }}
            />
            <StatWithTooltip
              label="Fleet MTBF"
              value={fleetStats.mtbf ? `${fleetStats.mtbf.toFixed(0)} h` : "—"}
              tooltip={{
                what: "Fleet-wide Mean Time Between Failures — total operating hours divided by total failures across all assets.",
                why: "The most important single reliability metric. Enables maintenance staffing and spare parts planning.",
                basis: "MTBF = Σ(operating hours) / Σ(failures). Assumes failures follow a renewal process across the fleet.",
                interpret: "Higher is better. Compare against industry benchmarks for your asset class. Use per-asset MTBF below for granularity.",
              }}
            />
            <StatWithTooltip
              label="Operating Hours"
              value={fleetStats.totalHours.toLocaleString()}
              tooltip={{
                what: "Total accumulated operating hours summed across all assets.",
                why: "Denominator for all time-based fleet metrics. Required for accurate failure rate and MTBF calculation.",
                basis: "Exposure time is the foundation of reliability statistics. R(t) = e^(-t/MTBF) requires accurate time measurement.",
                interpret: "Verify this aligns with expected fleet utilization. Gaps indicate data collection issues.",
              }}
            />
            <StatWithTooltip
              label="Assets"
              value={fleetSummary.total.toString()}
              tooltip={{
                what: "Total number of assets with health scores in the fleet.",
                why: "Context for interpreting fleet-level statistics. Ensures complete coverage.",
                basis: "Statistical significance increases with sample size. Small fleets have higher variance in aggregate metrics.",
                interpret: "Confirm this matches your actual fleet. Missing assets create blind spots.",
              }}
            />
          </div>

          {/* Grade Distribution */}
          <Card
            title="Health Grade Distribution"
            actions={
              <MetricTooltip
                label="Grade Distribution"
                what="Breakdown of how many assets fall into each health grade category (A through F)."
                why="Shows the shape of reliability across your fleet — is it normally distributed or skewed toward poor health?"
                basis="Grades are derived from composite health scores: A (90+), B (80-89), C (70-79), D (60-69), F (<60)."
                interpret="Healthy fleets have most assets in A/B. A tail of D/F assets indicates bad actors that need focused attention."
              />
            }
          >
            <div className="flex gap-3 items-end h-32">
              {(["A", "B", "C", "D", "F"] as const).map((grade) => {
                const count = fleetSummary.grades[grade];
                const maxCount = Math.max(...Object.values(fleetSummary.grades), 1);
                const height = (count / maxCount) * 100;
                const colors: Record<string, string> = {
                  A: "bg-emerald-500", B: "bg-green-500", C: "bg-amber-500", D: "bg-orange-500", F: "bg-red-500",
                };
                return (
                  <div key={grade} className="flex-1 flex flex-col items-center gap-1">
                    <span className="text-xs text-slate-300 font-medium">{count}</span>
                    <div className="w-full rounded-t-md relative" style={{ height: `${Math.max(height, 4)}%` }}>
                      <div className={`absolute inset-0 rounded-t-md ${colors[grade]} opacity-80`} />
                    </div>
                    <span className="text-xs font-bold text-slate-400">{grade}</span>
                  </div>
                );
              })}
            </div>
          </Card>
        </>
      )}

      {/* ─── Asset Comparison Table ─── */}
      {assetTable.length > 0 && (
        <Card
          title="Asset Comparison"
          description="Click any asset to view its deep-dive analysis"
          actions={
            <MetricTooltip
              label="Asset Comparison"
              what="Side-by-side comparison of all assets' key reliability metrics in one table."
              why="Enables quick identification of outliers, best performers, and assets needing improvement."
              basis="MTBF, availability, and Weibull shape are the three most important per-asset reliability metrics. Together they describe how often an asset fails, how much it runs, and what type of failures occur."
              interpret="Sort by any column to find outliers. Low MTBF + low availability = top priority for root cause analysis. Weibull β > 1 means wear-out (PM helps), β < 1 means infant mortality (investigate commissioning)."
            />
          }
        >
          <Table>
            <thead>
              <tr>
                <Th>Asset</Th>
                <Th>Type</Th>
                <Th>Failures</Th>
                <Th>Hours</Th>
                <Th>MTBF (h)</Th>
                <Th>Availability</Th>
                <Th>Weibull β</Th>
                <Th>Health</Th>
              </tr>
            </thead>
            <tbody>
              {assetTable.map((row) => (
                <tr
                  key={row.id}
                  className="odd:bg-ink-900 cursor-pointer hover:bg-ink-800/50 transition"
                  onClick={() => navigate(`/analytics/asset/${row.id}`)}
                >
                  <Td className="text-accent-400 font-medium">{row.name}</Td>
                  <Td className="text-slate-400">{row.type}</Td>
                  <Td>
                    <span className={row.failures > 5 ? "text-red-400 font-medium" : ""}>{row.failures}</span>
                  </Td>
                  <Td>{row.hours.toFixed(0)}</Td>
                  <Td>{row.mtbf.toFixed(1)}</Td>
                  <Td>
                    <span className={`font-medium ${row.availability >= 0.95 ? "text-emerald-400" : row.availability >= 0.85 ? "text-amber-400" : "text-red-400"}`}>
                      {(row.availability * 100).toFixed(1)}%
                    </span>
                  </Td>
                  <Td>
                    {row.weibullShape !== null ? (
                      <span className={row.weibullShape > 1 ? "text-amber-400" : row.weibullShape < 1 ? "text-red-400" : "text-blue-400"}>
                        {row.weibullShape.toFixed(2)}
                      </span>
                    ) : "—"}
                  </Td>
                  <Td>
                    {row.healthScore !== null ? (
                      <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                        row.healthGrade === "A" ? "bg-emerald-900/50 text-emerald-400" :
                        row.healthGrade === "B" ? "bg-green-900/50 text-green-400" :
                        row.healthGrade === "C" ? "bg-amber-900/50 text-amber-400" :
                        row.healthGrade === "D" ? "bg-orange-900/50 text-orange-400" :
                        "bg-red-900/50 text-red-400"
                      }`}>
                        {row.healthScore.toFixed(0)} ({row.healthGrade})
                      </span>
                    ) : "—"}
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      )}

      {/* ─── Fleet Failure Mode Pareto ─── */}
      {fleetStats && fleetStats.sortedModes.length > 0 && (
        <Card
          title="Fleet Failure Mode Pareto"
          description="Aggregated failure modes across all assets"
          actions={
            <MetricTooltip
              label="Fleet Pareto"
              what="Ranking of failure modes by total occurrence count across the entire fleet."
              why="Identifies the most common failure modes fleet-wide. Addressing the top failure modes has the largest impact on overall reliability improvement."
              basis="Pareto analysis (80/20 rule): typically 20% of failure modes cause 80% of failures. Prioritize engineering resources on the top items."
              interpret="Address failure modes from the top down. Each mode eliminated reduces fleet failure rate proportionally. Link to root cause analysis for corrective actions."
            />
          }
        >
          <div className="grid gap-4 md:grid-cols-2">
            <Table>
              <thead>
                <tr>
                  <Th>Rank</Th>
                  <Th>Failure Mode</Th>
                  <Th>Count</Th>
                  <Th>% of Total</Th>
                </tr>
              </thead>
              <tbody>
                {fleetStats.sortedModes.slice(0, 10).map((fm, idx) => (
                  <tr key={fm.name} className="odd:bg-ink-900">
                    <Td>{idx + 1}</Td>
                    <Td>{fm.name}</Td>
                    <Td className="font-medium">{fm.count}</Td>
                    <Td className="text-slate-400">
                      {((fm.count / fleetStats.totalFailures) * 100).toFixed(1)}%
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
            <Suspense fallback={<Spinner />}>
              <ParetoChart
                labels={fleetStats.sortedModes.slice(0, 10).map((fm) => fm.name)}
                values={fleetStats.sortedModes.slice(0, 10).map((fm) => fm.count)}
              />
            </Suspense>
          </div>
        </Card>
      )}

      {/* ─── Bad Actors Detailed ─── */}
      {badActors && badActors.length > 0 && (
        <Card
          title="Bad Actor Ranking"
          description="Assets ranked by composite unreliability score"
          actions={
            <MetricTooltip
              label="Bad Actor Score"
              what="Composite score (0-1) combining normalized failure count, downtime hours, and availability gap."
              why="Identifies which assets have the worst combination of frequent failures, long downtime, and low availability."
              basis="Score = weighted sum of normalized metrics. Higher score = worse reliability performance. Captures multiple dimensions of unreliability."
              interpret="Score > 0.7: critical — immediate attention needed. 0.4-0.7: monitor closely. < 0.4: acceptable. Click to investigate root causes."
            />
          }
        >
          <Table>
            <thead>
              <tr>
                <Th>Rank</Th>
                <Th>Asset</Th>
                <Th>Failures</Th>
                <Th>Downtime (h)</Th>
                <Th>Availability</Th>
                <Th>Score</Th>
              </tr>
            </thead>
            <tbody>
              {badActors.map((ba, idx) => (
                <tr key={ba.asset_id} className="odd:bg-ink-900 cursor-pointer hover:bg-ink-800/50" onClick={() => navigate(`/analytics/asset/${ba.asset_id}`)}>
                  <Td>{idx + 1}</Td>
                  <Td className="text-accent-400 font-medium">{ba.asset_name}</Td>
                  <Td>{ba.failure_count}</Td>
                  <Td>{ba.total_downtime_hours.toFixed(1)}</Td>
                  <Td>
                    <span className={`font-medium ${ba.availability >= 0.95 ? "text-emerald-400" : ba.availability >= 0.85 ? "text-amber-400" : "text-red-400"}`}>
                      {(ba.availability * 100).toFixed(1)}%
                    </span>
                  </Td>
                  <Td>
                    <span className={`font-semibold ${ba.composite_score >= 0.7 ? "text-red-400" : ba.composite_score >= 0.4 ? "text-amber-400" : "text-emerald-400"}`}>
                      {ba.composite_score.toFixed(3)}
                    </span>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      )}

      {/* ─── Spare Parts Forecast ─── */}
      {spareDemand && spareDemand.forecasts.length > 0 && (
        <Card
          title="Spare Parts Demand Forecast"
          description={`Projected demand over ${(spareDemand.horizon_hours / 720).toFixed(0)} months`}
          actions={
            <MetricTooltip
              label="Spare Demand"
              what="Predicted number of spare parts needed per failure mode over the forecast horizon, with 90% confidence intervals."
              why="Enables proactive inventory management. Stockouts cause extended downtime; overstocking ties up capital."
              basis="Uses Poisson distribution based on historical failure rates. 90% CI (5th-95th percentile) covers most realistic demand scenarios."
              interpret="Stock to the upper bound for critical parts. Expected value is the planning baseline. Sum gives total fleet demand."
            />
          }
        >
          <Table>
            <thead>
              <tr>
                <Th>Part</Th>
                <Th>Expected Failures</Th>
                <Th>Lower (5%)</Th>
                <Th>Upper (95%)</Th>
              </tr>
            </thead>
            <tbody>
              {spareDemand.forecasts.map((f) => (
                <tr key={f.part_name} className="odd:bg-ink-900">
                  <Td>{f.part_name}</Td>
                  <Td className="font-medium text-white">{f.expected_failures.toFixed(1)}</Td>
                  <Td>{f.lower_bound}</Td>
                  <Td>{f.upper_bound}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
          <div className="mt-3 text-sm text-slate-400">
            Total expected replacements: <span className="text-white font-medium">{spareDemand.total_expected_failures.toFixed(1)}</span>
          </div>
        </Card>
      )}
    </div>
  );
}
