import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, useCallback, Suspense, lazy, useEffect } from "react";
import { listAssets, getAssetAnalytics, downloadAssetReport } from "../api/endpoints";
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
