import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, useCallback, Suspense, lazy, useEffect } from "react";
import { listAssets, getAssetAnalytics, downloadAssetReport, getExtendedAssetAnalytics, getBadActors } from "../api/endpoints";
import { Card } from "../components/Card";
import { Stat } from "../components/Stat";
import { Table, Th, Td } from "../components/Table";
import { Button } from "../components/Button";
import { format } from "date-fns";
import { Spinner } from "../components/Spinner";
import { Alert } from "../components/Alert";

const ParetoChart = lazy(() => import("../components/charts/ParetoChart"));
const Sparkline = lazy(() => import("../components/charts/Sparkline"));
const ReliabilityCurves = lazy(() => import("../components/charts/ReliabilityCurves"));

export default function Analytics() {
  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 500 }) });
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  // Auto-select first asset if available
  useEffect(() => {
    if (!selectedAssetId && assets && assets.length > 0) {
      setSelectedAssetId(assets[0].id);
    }
  }, [assets, selectedAssetId]);

  // Fetch analytics for the selected asset
  const {
    data: analytics,
    isLoading: analyticsLoading,
    isError: analyticsError,
    error: analyticsErrorObj,
  } = useQuery({
    queryKey: ["analytics", selectedAssetId],
    queryFn: () => (selectedAssetId ? getAssetAnalytics(selectedAssetId) : Promise.resolve(null)),
    enabled: selectedAssetId !== null,
  });

  // Extended analytics (manufacturing + business + extended reliability)
  const { data: extended, isLoading: extendedLoading } = useQuery({
    queryKey: ["analytics-extended", selectedAssetId],
    queryFn: () => (selectedAssetId ? getExtendedAssetAnalytics(selectedAssetId) : Promise.resolve(null)),
    enabled: selectedAssetId !== null,
  });

  // Fleet bad actors
  const { data: badActors } = useQuery({
    queryKey: ["bad-actors"],
    queryFn: () => getBadActors({ top_n: 10 }),
  });

  // MTBF trend from intervals
  const mtbfTrend = useMemo(() => {
    if (!analytics?.intervals_hours || analytics.intervals_hours.length < 2) {
      return { labels: [] as string[], values: [] as number[] };
    }
    const intervals = analytics.intervals_hours.filter((_, i) => !analytics.censored_flags[i]);
    if (intervals.length < 2) return { labels: [] as string[], values: [] as number[] };
    
    return {
      labels: intervals.map((_, i) => `#${i + 1}`),
      values: intervals.map((v) => Number(v.toFixed(2))),
    };
  }, [analytics]);

  // Pareto chart data
  const paretoChart = useMemo(() => {
    if (!analytics?.failure_modes || analytics.failure_modes.length === 0) return null;
    return {
      labels: analytics.failure_modes.map((fm) => fm.name),
      values: analytics.failure_modes.map((fm) => fm.count),
    };
  }, [analytics]);

  // PDF download handler
  const handleDownloadReport = useCallback(async () => {
    if (!selectedAssetId) return;
    setIsDownloading(true);
    try {
      const blob = await downloadAssetReport(selectedAssetId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `asset_${selectedAssetId}_reliability_report.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download report:", err);
    } finally {
      setIsDownloading(false);
    }
  }, [selectedAssetId]);

  return (
    <div className="space-y-6">
      {/* Asset selector and actions */}
      <div className="flex flex-wrap gap-4 items-end justify-between">
        <div>
          <label className="text-sm text-slate-200 block mb-1">Select Asset</label>
          <select
            className="w-64 rounded-md border border-slate-700 bg-ink-900 px-3 py-2 text-sm"
            value={selectedAssetId ?? ""}
            onChange={(e) => setSelectedAssetId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="" disabled>
              Choose an asset...
            </option>
            {(assets ?? []).map((asset) => (
              <option key={asset.id} value={asset.id}>
                #{asset.id} — {asset.name}
              </option>
            ))}
          </select>
        </div>
        <Button
          variant="primary"
          onClick={handleDownloadReport}
          disabled={!selectedAssetId || isDownloading || analyticsLoading}
        >
          {isDownloading ? (
            <>
              <Spinner />
              <span className="ml-2">Generating...</span>
            </>
          ) : (
            "Download PDF Report"
          )}
        </Button>
      </div>

      {/* Loading / Error states */}
      {analyticsLoading && (
        <div className="flex items-center justify-center py-12">
          <Spinner />
          <span className="ml-3 text-slate-400">Loading analytics...</span>
        </div>
      )}

      {analyticsError && (
        <Alert tone="danger">
          Failed to load analytics: {analyticsErrorObj instanceof Error ? analyticsErrorObj.message : "Unknown error"}
        </Alert>
      )}

      {/* Analytics content */}
      {analytics && !analyticsLoading && (
        <>
          {/* KPIs */}
          <div className="grid gap-4 grid-cols-1 md:grid-cols-5">
            <Stat
              label="Failures"
              value={analytics.kpis.failure_count.toString()}
              hint="Total failure events"
            />
            <Stat
              label="Exposure (h)"
              value={analytics.kpis.total_exposure_hours.toFixed(1)}
              hint="Total logged hours"
            />
            <Stat
              label="MTBF (h)"
              value={analytics.kpis.mtbf_hours.toFixed(2)}
              hint="Mean time between failures"
            />
            <Stat
              label="MTTR (h)"
              value={analytics.kpis.mttr_hours.toFixed(2)}
              hint="Mean time to repair"
            />
            <Stat
              label="Availability"
              value={`${(analytics.kpis.availability * 100).toFixed(1)}%`}
              hint="MTBF / (MTBF + MTTR)"
            />
          </div>

          {/* Weibull Analysis */}
          <Card
            title="Weibull Analysis"
            description="2-parameter Weibull distribution fitted with MLE and bootstrap confidence intervals"
            actions={
              analytics.weibull ? (
                <span className="text-xs text-green-400">Fit successful</span>
              ) : (
                <span className="text-xs text-yellow-400">Insufficient data</span>
              )
            }
          >
            {analytics.weibull ? (
              <div className="space-y-6">
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <div className="bg-ink-900/50 rounded-lg p-4">
                    <div className="text-sm text-slate-400 mb-1">Shape (β)</div>
                    <div className="text-2xl font-semibold text-white">
                      {analytics.weibull.shape.toFixed(3)}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      95% CI: [{analytics.weibull.shape_ci[0].toFixed(3)}, {analytics.weibull.shape_ci[1].toFixed(3)}]
                    </div>
                  </div>
                  <div className="bg-ink-900/50 rounded-lg p-4">
                    <div className="text-sm text-slate-400 mb-1">Scale (η)</div>
                    <div className="text-2xl font-semibold text-white">
                      {analytics.weibull.scale.toFixed(2)} h
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      95% CI: [{analytics.weibull.scale_ci[0].toFixed(2)}, {analytics.weibull.scale_ci[1].toFixed(2)}]
                    </div>
                  </div>
                  <div className="bg-ink-900/50 rounded-lg p-4">
                    <div className="text-sm text-slate-400 mb-1">Failure Pattern</div>
                    <div className="text-lg font-medium text-white">
                      {analytics.weibull.shape < 1
                        ? "Infant mortality"
                        : analytics.weibull.shape === 1
                        ? "Random failures"
                        : "Wear-out"}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      β {"<"} 1: early life, β = 1: random, β {">"} 1: wear-out
                    </div>
                  </div>
                  <div className="bg-ink-900/50 rounded-lg p-4">
                    <div className="text-sm text-slate-400 mb-1">B10 Life</div>
                    <div className="text-2xl font-semibold text-white">
                      {(analytics.weibull.scale * Math.pow(-Math.log(0.9), 1 / analytics.weibull.shape)).toFixed(1)} h
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      Time at which 10% will have failed
                    </div>
                  </div>
                </div>

                {/* Reliability Curves */}
                {analytics.curves && analytics.curves.times.length > 0 && (
                  <Suspense fallback={<Spinner />}>
                    <ReliabilityCurves
                      times={analytics.curves.times}
                      reliability={analytics.curves.reliability}
                      hazard={analytics.curves.hazard}
                    />
                  </Suspense>
                )}
              </div>
            ) : (
              <div className="text-slate-400 py-8 text-center">
                <p className="mb-2">Weibull analysis requires at least one complete failure interval.</p>
                <p className="text-sm">Log more failure events with exposure data to enable analysis.</p>
              </div>
            )}
          </Card>

          {/* Failure Mode Pareto */}
          <Card
            title="Failure Mode Pareto"
            description="Breakdown of failure modes from event details"
          >
            {analytics.failure_modes.length > 0 ? (
              <div className="grid gap-4 md:grid-cols-2">
                <Table>
                  <thead>
                    <tr>
                      <Th>Failure Mode</Th>
                      <Th>Category</Th>
                      <Th>Count</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {analytics.failure_modes.map((fm) => (
                      <tr key={fm.name} className="odd:bg-ink-900">
                        <Td>{fm.name}</Td>
                        <Td className="text-slate-400">{fm.category ?? "—"}</Td>
                        <Td>{fm.count}</Td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
                <Suspense fallback={<Spinner />}>
                  {paretoChart && <ParetoChart labels={paretoChart.labels} values={paretoChart.values} />}
                </Suspense>
              </div>
            ) : (
              <p className="text-sm text-slate-400">No failure mode data recorded yet.</p>
            )}
          </Card>

          {/* MTBF Trend */}
          <Card
            title="Time Between Failures"
            description="Distribution of intervals between consecutive failures (hours)"
          >
            {mtbfTrend.values.length > 0 ? (
              <Suspense fallback={<Spinner />}>
                <Sparkline labels={mtbfTrend.labels} values={mtbfTrend.values} />
              </Suspense>
            ) : (
              <p className="text-sm text-slate-400">At least two failure events required to show trend.</p>
            )}
          </Card>

          {/* Event Timeline */}
          <Card
            title="Recent Events"
            description={`Last ${analytics.recent_events.length} events for this asset`}
          >
            {analytics.recent_events.length > 0 ? (
              <Table>
                <thead>
                  <tr>
                    <Th>Timestamp</Th>
                    <Th>Type</Th>
                    <Th>Downtime (min)</Th>
                    <Th>Description</Th>
                  </tr>
                </thead>
                <tbody>
                  {analytics.recent_events.map((evt) => (
                    <tr key={evt.id} className="odd:bg-ink-900">
                      <Td>{format(new Date(evt.timestamp), "yyyy-MM-dd HH:mm")}</Td>
                      <Td>
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            evt.event_type === "failure"
                              ? "bg-red-900/50 text-red-400"
                              : evt.event_type === "maintenance"
                              ? "bg-green-900/50 text-green-400"
                              : "bg-blue-900/50 text-blue-400"
                          }`}
                        >
                          {evt.event_type}
                        </span>
                      </Td>
                      <Td>{evt.downtime_minutes.toFixed(0)}</Td>
                      <Td className="text-slate-300">{evt.description ?? "—"}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            ) : (
              <p className="text-sm text-slate-400">No events recorded for this asset.</p>
            )}
          </Card>

          {/* ============================================================= */}
          {/* Extended Analytics — Manufacturing, Business, Extended Rel.    */}
          {/* ============================================================= */}
          {extendedLoading && (
            <div className="flex items-center gap-2 text-slate-400 text-sm py-4">
              <Spinner /> Loading extended analytics...
            </div>
          )}

          {extended && !extendedLoading && (
            <>
              {/* ---- Asset Health Index ---- */}
              {extended.health_index && (
                <Card title="Asset Health Index" description="Composite 0-100 score from reliability, OEE, downtime quality, and repair trends">
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="flex flex-col items-center justify-center bg-ink-900/50 rounded-lg p-6">
                      <div className={`text-5xl font-bold ${
                        extended.health_index.grade === "A" ? "text-emerald-400" :
                        extended.health_index.grade === "B" ? "text-green-400" :
                        extended.health_index.grade === "C" ? "text-amber-400" :
                        extended.health_index.grade === "D" ? "text-orange-400" : "text-red-400"
                      }`}>
                        {extended.health_index.score.toFixed(0)}
                      </div>
                      <div className={`text-3xl font-semibold mt-1 ${
                        extended.health_index.grade === "A" ? "text-emerald-400" :
                        extended.health_index.grade === "B" ? "text-green-400" :
                        extended.health_index.grade === "C" ? "text-amber-400" :
                        extended.health_index.grade === "D" ? "text-orange-400" : "text-red-400"
                      }`}>
                        Grade {extended.health_index.grade}
                      </div>
                    </div>
                    <div className="md:col-span-2 grid grid-cols-2 lg:grid-cols-3 gap-3">
                      {Object.entries(extended.health_index.components).map(([key, val]) => (
                        <div key={key} className="bg-ink-900/50 rounded-lg p-3">
                          <div className="text-xs text-slate-400 capitalize">{key.replace(/_/g, " ")}</div>
                          <div className="flex items-center gap-2 mt-1">
                            <div className="flex-1 h-2 bg-slate-700 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full ${
                                  val >= 80 ? "bg-emerald-500" : val >= 60 ? "bg-amber-500" : "bg-red-500"
                                }`}
                                style={{ width: `${Math.min(val, 100)}%` }}
                              />
                            </div>
                            <span className="text-sm font-medium text-white w-10 text-right">{val.toFixed(0)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </Card>
              )}

              {/* ---- Extended Reliability Metrics ---- */}
              <Card title="Extended Reliability" description="B-life, failure rate, MTTF, and repair trend analysis">
                <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
                  {extended.b10_life && (
                    <div className="bg-ink-900/50 rounded-lg p-4">
                      <div className="text-sm text-slate-400 mb-1">B10 Life</div>
                      <div className="text-2xl font-semibold text-white">{extended.b10_life.life_hours.toFixed(1)} h</div>
                      <div className="text-xs text-slate-500 mt-1">10% of population fails by this time</div>
                    </div>
                  )}
                  {extended.mttf_hours != null && (
                    <div className="bg-ink-900/50 rounded-lg p-4">
                      <div className="text-sm text-slate-400 mb-1">MTTF</div>
                      <div className="text-2xl font-semibold text-white">{extended.mttf_hours.toFixed(1)} h</div>
                      <div className="text-xs text-slate-500 mt-1">Mean time to failure (Weibull)</div>
                    </div>
                  )}
                  {extended.failure_rate && (
                    <div className="bg-ink-900/50 rounded-lg p-4">
                      <div className="text-sm text-slate-400 mb-1">Failure Rate (λ)</div>
                      <div className="text-2xl font-semibold text-white">{(extended.failure_rate.average_rate * 1000).toFixed(2)}</div>
                      <div className="text-xs text-slate-500 mt-1">per 1,000 hours (avg)</div>
                    </div>
                  )}
                  {extended.repair_effectiveness && (
                    <div className="bg-ink-900/50 rounded-lg p-4">
                      <div className="text-sm text-slate-400 mb-1">Repair Trend</div>
                      <div className={`text-2xl font-semibold ${extended.repair_effectiveness.improving ? "text-emerald-400" : "text-red-400"}`}>
                        {extended.repair_effectiveness.trend_ratio.toFixed(2)}×
                      </div>
                      <div className="text-xs text-slate-500 mt-1">
                        {extended.repair_effectiveness.improving ? "Improving — repairs are effective" : "Degrading — investigate root cause"}
                      </div>
                    </div>
                  )}
                </div>
              </Card>

              {/* ---- RPN / FMEA ---- */}
              {extended.rpn && extended.rpn.entries.length > 0 && (
                <Card title="Risk Priority Number (RPN)" description="FMEA-style ranking: Severity × Occurrence × Detection">
                  <Table>
                    <thead>
                      <tr>
                        <Th>Failure Mode</Th>
                        <Th>Severity</Th>
                        <Th>Occurrence</Th>
                        <Th>Detection</Th>
                        <Th>RPN</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {extended.rpn.entries.map((e) => (
                        <tr key={e.failure_mode} className="odd:bg-ink-900">
                          <Td>{e.failure_mode}</Td>
                          <Td>{e.severity}</Td>
                          <Td>{e.occurrence}</Td>
                          <Td>{e.detection}</Td>
                          <Td>
                            <span className={`font-semibold ${e.rpn >= 200 ? "text-red-400" : e.rpn >= 100 ? "text-amber-400" : "text-emerald-400"}`}>
                              {e.rpn}
                            </span>
                          </Td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                </Card>
              )}

              {/* ---- Manufacturing / OEE ---- */}
              {extended.manufacturing && (
                <Card title="Manufacturing Performance" description="OEE framework — Availability × Performance × Quality">
                  <div className="space-y-6">
                    {/* OEE gauge row */}
                    <div className="grid gap-4 grid-cols-1 md:grid-cols-4">
                      <div className="bg-ink-900/50 rounded-lg p-4 text-center">
                        <div className="text-sm text-slate-400 mb-1">OEE</div>
                        <div className={`text-3xl font-bold ${
                          extended.manufacturing.oee.oee >= 0.85 ? "text-emerald-400" :
                          extended.manufacturing.oee.oee >= 0.65 ? "text-amber-400" : "text-red-400"
                        }`}>
                          {(extended.manufacturing.oee.oee * 100).toFixed(1)}%
                        </div>
                        <div className="text-xs text-slate-500 mt-1">
                          {extended.manufacturing.oee.oee >= 0.85 ? "World-class" :
                           extended.manufacturing.oee.oee >= 0.65 ? "Typical" : "Below average"}
                        </div>
                      </div>
                      <div className="bg-ink-900/50 rounded-lg p-4 text-center">
                        <div className="text-sm text-slate-400 mb-1">Availability</div>
                        <div className="text-2xl font-semibold text-white">{(extended.manufacturing.oee.availability * 100).toFixed(1)}%</div>
                      </div>
                      <div className="bg-ink-900/50 rounded-lg p-4 text-center">
                        <div className="text-sm text-slate-400 mb-1">Performance</div>
                        <div className="text-2xl font-semibold text-white">{(extended.manufacturing.oee.performance * 100).toFixed(1)}%</div>
                      </div>
                      <div className="bg-ink-900/50 rounded-lg p-4 text-center">
                        <div className="text-sm text-slate-400 mb-1">Quality</div>
                        <div className="text-2xl font-semibold text-white">{(extended.manufacturing.oee.quality * 100).toFixed(1)}%</div>
                      </div>
                    </div>

                    {/* Downtime split */}
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <h3 className="text-sm font-medium text-slate-300 mb-3">Downtime Breakdown</h3>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-slate-400">Planned</span>
                            <span className="text-white font-medium">{extended.manufacturing.downtime_split.planned_downtime_hours.toFixed(1)} h ({extended.manufacturing.downtime_split.planned_count} events)</span>
                          </div>
                          <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-green-500 rounded-full"
                              style={{ width: `${extended.manufacturing.downtime_split.total_downtime_hours > 0 ? ((1 - extended.manufacturing.downtime_split.unplanned_ratio) * 100) : 0}%` }}
                            />
                          </div>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-slate-400">Unplanned</span>
                            <span className="text-white font-medium">{extended.manufacturing.downtime_split.unplanned_downtime_hours.toFixed(1)} h ({extended.manufacturing.downtime_split.unplanned_count} events)</span>
                          </div>
                          <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-red-500 rounded-full"
                              style={{ width: `${extended.manufacturing.downtime_split.unplanned_ratio * 100}%` }}
                            />
                          </div>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-ink-900/50 rounded-lg p-3">
                          <div className="text-xs text-slate-400">MTBM</div>
                          <div className="text-xl font-semibold text-white mt-1">{extended.manufacturing.mtbm.mtbm_hours.toFixed(1)} h</div>
                          <div className="text-xs text-slate-500">Mean time between maintenance</div>
                        </div>
                        <div className="bg-ink-900/50 rounded-lg p-3">
                          <div className="text-xs text-slate-400">Throughput</div>
                          <div className="text-xl font-semibold text-white mt-1">{extended.manufacturing.performance.actual_throughput.toFixed(1)}</div>
                          <div className="text-xs text-slate-500">cycles/hour (design: {extended.manufacturing.performance.design_throughput.toFixed(1)})</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              )}

              {/* ---- Business Impact ---- */}
              <Card title="Business Impact" description="Cost of unreliability and PM optimization">
                <div className="grid gap-4 md:grid-cols-2">
                  {/* COUR */}
                  {extended.cour && (
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium text-slate-300">Cost of Unreliability</h3>
                      <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4">
                        <div className="text-3xl font-bold text-red-400">
                          ${extended.cour.total_cost.toLocaleString()}
                        </div>
                        <div className="text-xs text-slate-400 mt-1">Estimated total cost</div>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="bg-ink-900/50 rounded p-2">
                          <div className="text-xs text-slate-400">Lost Production</div>
                          <div className="text-white font-medium">${extended.cour.lost_production_cost.toLocaleString()}</div>
                        </div>
                        <div className="bg-ink-900/50 rounded p-2">
                          <div className="text-xs text-slate-400">Repair Cost</div>
                          <div className="text-white font-medium">${extended.cour.repair_cost.toLocaleString()}</div>
                        </div>
                        <div className="bg-ink-900/50 rounded p-2">
                          <div className="text-xs text-slate-400">Cost per Failure</div>
                          <div className="text-white font-medium">${extended.cour.cost_per_failure.toLocaleString()}</div>
                        </div>
                        <div className="bg-ink-900/50 rounded p-2">
                          <div className="text-xs text-slate-400">Unplanned DT</div>
                          <div className="text-white font-medium">{extended.cour.unplanned_downtime_hours.toFixed(1)} h</div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* PM Optimization */}
                  {extended.pm_optimization && (
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium text-slate-300">PM Optimization</h3>
                      <div className={`rounded-lg border p-4 ${
                        extended.pm_optimization.assessment === "appropriate" ? "bg-emerald-900/20 border-emerald-500/30" :
                        extended.pm_optimization.assessment === "pm_not_recommended" ? "bg-blue-900/20 border-blue-500/30" :
                        extended.pm_optimization.assessment === "over_maintaining" ? "bg-amber-900/20 border-amber-500/30" :
                        "bg-red-900/20 border-red-500/30"
                      }`}>
                        <div className="text-lg font-semibold text-white capitalize">
                          {extended.pm_optimization.failure_pattern.replace(/_/g, " ")}
                        </div>
                        <div className="text-sm text-slate-300 mt-1">
                          {extended.pm_optimization.assessment === "pm_not_recommended"
                            ? "Preventive maintenance may not reduce failures. Consider condition-based monitoring."
                            : extended.pm_optimization.assessment === "appropriate"
                            ? "Current PM interval is well-matched to failure behavior."
                            : extended.pm_optimization.assessment === "over_maintaining"
                            ? "PM is more frequent than necessary. Consider extending intervals."
                            : extended.pm_optimization.assessment === "under_maintaining"
                            ? "PM is too infrequent. Risk of unplanned failures. Decrease interval."
                            : "Insufficient PM scheduling data for comparison."}
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="bg-ink-900/50 rounded p-2">
                          <div className="text-xs text-slate-400">Weibull β</div>
                          <div className="text-white font-medium">{extended.pm_optimization.weibull_shape.toFixed(3)}</div>
                        </div>
                        <div className="bg-ink-900/50 rounded p-2">
                          <div className="text-xs text-slate-400">Recommended PM</div>
                          <div className="text-white font-medium">{extended.pm_optimization.recommended_pm_hours.toFixed(0)} h</div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </Card>
            </>
          )}

          {/* ---- Fleet Bad Actors ---- */}
          {badActors && badActors.length > 0 && (
            <Card title="Fleet Bad Actors" description="Top worst-performing assets by composite score (failures, downtime, availability)">
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
                    <tr key={ba.asset_id} className="odd:bg-ink-900">
                      <Td>{idx + 1}</Td>
                      <Td>
                        <button
                          className="text-accent-400 hover:underline"
                          onClick={() => setSelectedAssetId(ba.asset_id)}
                        >
                          {ba.asset_name}
                        </button>
                      </Td>
                      <Td>{ba.failure_count}</Td>
                      <Td>{ba.total_downtime_hours.toFixed(1)}</Td>
                      <Td>{(ba.availability * 100).toFixed(1)}%</Td>
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
        </>
      )}

      {/* No asset selected state */}
      {!selectedAssetId && !analyticsLoading && (
        <div className="text-center py-12 text-slate-400">
          <p className="text-lg mb-2">Select an asset to view reliability analytics</p>
          <p className="text-sm">
            Analytics include Weibull analysis, reliability curves, failure mode breakdown, and PDF reports.
          </p>
        </div>
      )}
    </div>
  );
}
