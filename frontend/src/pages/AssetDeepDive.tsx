import { useQuery } from "@tanstack/react-query";
import { useMemo, useState, useCallback, Suspense, lazy } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { listAssets, getAssetAnalytics, downloadAssetReport, getExtendedAssetAnalytics } from "../api/endpoints";
import { Card } from "../components/Card";
import { Table, Th, Td } from "../components/Table";
import { Button } from "../components/Button";
import { format } from "date-fns";
import { Spinner } from "../components/Spinner";
import { Alert } from "../components/Alert";
import { MetricTooltip, StatWithTooltip } from "../components/MetricTooltip";

const ParetoChart = lazy(() => import("../components/charts/ParetoChart"));
const Sparkline = lazy(() => import("../components/charts/Sparkline"));
const ReliabilityCurves = lazy(() => import("../components/charts/ReliabilityCurves"));

export default function AssetDeepDive() {
  const { assetId } = useParams<{ assetId: string }>();
  const navigate = useNavigate();
  const selectedAssetId = assetId ? Number(assetId) : null;
  const [isDownloading, setIsDownloading] = useState(false);

  const { data: assets } = useQuery({ queryKey: ["assets"], queryFn: () => listAssets({ limit: 500 }) });

  const selectedAsset = useMemo(() => {
    if (!assets || !selectedAssetId) return null;
    return assets.find((a) => a.id === selectedAssetId) ?? null;
  }, [assets, selectedAssetId]);

  const { data: analytics, isLoading: analyticsLoading, isError: analyticsError, error: analyticsErrorObj } = useQuery({
    queryKey: ["analytics", selectedAssetId],
    queryFn: () => (selectedAssetId ? getAssetAnalytics(selectedAssetId) : Promise.resolve(null)),
    enabled: selectedAssetId !== null,
  });

  const { data: extended, isLoading: extendedLoading } = useQuery({
    queryKey: ["analytics-extended", selectedAssetId],
    queryFn: () => (selectedAssetId ? getExtendedAssetAnalytics(selectedAssetId) : Promise.resolve(null)),
    enabled: selectedAssetId !== null,
  });

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

  const paretoChart = useMemo(() => {
    if (!analytics?.failure_modes || analytics.failure_modes.length === 0) return null;
    return {
      labels: analytics.failure_modes.map((fm) => fm.name),
      values: analytics.failure_modes.map((fm) => fm.count),
    };
  }, [analytics]);

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

  if (!selectedAssetId) {
    return (
      <div className="text-center py-20 text-slate-400">
        <p className="text-lg mb-2">No asset selected</p>
        <Button onClick={() => navigate("/analytics")}>← Back to All Assets</Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ─── Asset Identity Header ─── */}
      <div className="rounded-xl border border-accent-500/20 bg-gradient-to-r from-accent-900/10 to-ink-900/60 p-5">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate("/analytics")} className="text-slate-400 hover:text-white transition text-sm">
              ← All Assets
            </button>
            <div className="h-8 border-l border-slate-700" />
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-display text-white">
                  {selectedAsset?.name ?? `Asset #${selectedAssetId}`}
                </h1>
                {extended?.health_index && (
                  <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                    extended.health_index.grade === "A" ? "bg-emerald-900/50 text-emerald-400 border border-emerald-500/30" :
                    extended.health_index.grade === "B" ? "bg-green-900/50 text-green-400 border border-green-500/30" :
                    extended.health_index.grade === "C" ? "bg-amber-900/50 text-amber-400 border border-amber-500/30" :
                    extended.health_index.grade === "D" ? "bg-orange-900/50 text-orange-400 border border-orange-500/30" :
                    "bg-red-900/50 text-red-400 border border-red-500/30"
                  }`}>
                    Grade {extended.health_index.grade} · {extended.health_index.score.toFixed(0)}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-4 text-sm text-slate-400 mt-1">
                {selectedAsset?.type && <span>Type: {selectedAsset.type}</span>}
                {selectedAsset?.serial && <span>Serial: {selectedAsset.serial}</span>}
                {selectedAsset?.in_service_date && <span>In service: {selectedAsset.in_service_date}</span>}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Asset selector for quick navigation */}
            <select
              className="rounded-md border border-slate-700 bg-ink-900 px-3 py-2 text-sm"
              value={selectedAssetId}
              onChange={(e) => navigate(`/analytics/asset/${e.target.value}`)}
            >
              {(assets ?? []).map((asset) => (
                <option key={asset.id} value={asset.id}>
                  #{asset.id} — {asset.name}
                </option>
              ))}
            </select>
            <Button
              variant="primary"
              onClick={handleDownloadReport}
              disabled={isDownloading || analyticsLoading}
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
        </div>
      </div>

      {/* Loading / Error */}
      {analyticsLoading && (
        <div className="flex items-center justify-center py-12">
          <Spinner />
          <span className="ml-3 text-slate-400">Loading asset analytics...</span>
        </div>
      )}

      {analyticsError && (
        <Alert tone="danger">
          Failed to load analytics: {analyticsErrorObj instanceof Error ? analyticsErrorObj.message : "Unknown error"}
        </Alert>
      )}

      {analytics && !analyticsLoading && (
        <>
          {/* ─── Core KPIs ─── */}
          <div className="grid gap-4 grid-cols-1 md:grid-cols-5">
            <StatWithTooltip
              label="Failures"
              value={analytics.kpis.failure_count.toString()}
              valueClass={analytics.kpis.failure_count > 5 ? "text-red-400" : undefined}
              tooltip={{
                what: "Total number of failure events recorded for this specific asset.",
                why: "Each failure is a data point for Weibull analysis, drives MTBF calculation, and represents a maintenance event with associated cost and downtime.",
                basis: "Failure count is the foundation of all reliability statistics. The Weibull MLE estimator uses individual failure times to fit the shape (β) and scale (η) parameters.",
                interpret: "Compare against peer assets of the same type. High failure count may indicate design, operational, or maintenance issues specific to this unit.",
              }}
            />
            <StatWithTooltip
              label="Exposure (h)"
              value={analytics.kpis.total_exposure_hours.toFixed(1)}
              tooltip={{
                what: "Total logged operating hours for this asset.",
                why: "The denominator for failure rate calculation. Without accurate exposure, reliability metrics are unreliable.",
                basis: "Operating time (T) determines where the asset sits on its reliability curve R(t). Accurate tracking enables Weibull analysis and remaining useful life estimation.",
                interpret: "Verify this matches expected utilization. If significantly lower than calendar time × utilization rate, exposure logging may be incomplete.",
              }}
            />
            <StatWithTooltip
              label="MTBF (h)"
              value={analytics.kpis.mtbf_hours.toFixed(1)}
              tooltip={{
                what: "Mean Time Between Failures — average hours between consecutive failures for this asset.",
                why: "Primary measure of this asset's reliability. Directly determines expected failure frequency and maintenance planning intervals.",
                basis: "MTBF = Total Operating Hours / Failure Count. For Weibull-distributed times, MTBF = η · Γ(1 + 1/β). Lower MTBF = more frequent failures.",
                interpret: "Compare against design MTBF and peer assets. Decreasing MTBF over time indicates degradation. MTBF alone doesn't describe the failure pattern — use Weibull β for that.",
              }}
            />
            <StatWithTooltip
              label="MTTR (h)"
              value={analytics.kpis.mttr_hours.toFixed(2)}
              tooltip={{
                what: "Mean Time To Repair — average hours of downtime per failure event.",
                why: "MTTR directly impacts availability and production loss. Lower MTTR = faster recovery from failures.",
                basis: "MTTR = Total Downtime Hours / Number of Repairs. Combined with MTBF, determines inherent availability: A = MTBF / (MTBF + MTTR).",
                interpret: "High MTTR may indicate: complex failure modes, inadequate spare parts, insufficient technician training, or poor maintenance procedures. Address the root cause of slow repairs.",
              }}
            />
            <StatWithTooltip
              label="Availability"
              value={`${(analytics.kpis.availability * 100).toFixed(1)}%`}
              valueClass={analytics.kpis.availability >= 0.95 ? "text-emerald-400" : analytics.kpis.availability >= 0.85 ? "text-amber-400" : "text-red-400"}
              tooltip={{
                what: "Inherent availability — the fraction of time this asset is operational (not under repair).",
                why: "Availability is the most business-relevant reliability metric. It directly determines production capacity and revenue potential.",
                basis: "A = MTBF / (MTBF + MTTR). This is inherent availability, excluding logistics and admin delays. World-class is >95% for most industrial assets.",
                interpret: "Below 90%: critical — investigate both MTBF (failure frequency) and MTTR (repair speed). Improve MTBF through root cause elimination, MTTR through better procedures/parts.",
              }}
            />
          </div>

          {/* ─── Weibull Analysis ─── */}
          <Card
            title="Weibull Analysis"
            description="2-parameter Weibull distribution fitted via MLE with bootstrap confidence intervals"
            actions={
              <div className="flex items-center gap-2">
                <MetricTooltip
                  label="Weibull Analysis"
                  what="Statistical model fitting failure times to a Weibull distribution, yielding shape (β) and scale (η) parameters."
                  why="The Weibull distribution is the most versatile model in reliability engineering. It identifies the failure pattern and enables remaining life prediction."
                  basis="The Weibull PDF is f(t) = (β/η)(t/η)^(β-1)·e^(-(t/η)^β). MLE (Maximum Likelihood Estimation) finds β and η that best explain observed failures. Bootstrap generates confidence intervals."
                  interpret="β < 1: infant mortality (decreasing failure rate). β = 1: random failures (constant rate, exponential). β > 1: wear-out (increasing failure rate). η is the characteristic life — 63.2% of units fail by η hours."
                />
                {analytics.weibull ? (
                  <span className="text-xs text-green-400">Fit successful</span>
                ) : (
                  <span className="text-xs text-yellow-400">Insufficient data</span>
                )}
              </div>
            }
          >
            {analytics.weibull ? (
              <div className="space-y-6">
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <div className="bg-ink-900/50 rounded-lg p-4">
                    <div className="flex items-center gap-1.5">
                      <div className="text-sm text-slate-400 mb-1">Shape (β)</div>
                      <MetricTooltip
                        label="Shape Parameter (β)"
                        what="Weibull shape parameter — determines the type of failure behavior."
                        why="β is the most important single number in reliability analysis. It tells you WHAT TYPE of failures are occurring."
                        basis="β < 1: decreasing hazard (infant mortality, burn-in). β = 1: constant hazard (random, exponential). β > 1: increasing hazard (wear-out, aging). β ≈ 3.5: approximates normal distribution."
                        interpret="β < 1 → improve manufacturing/installation quality. β ≈ 1 → failures are random, time-based PM won't help. β > 1 → PM is effective, schedule before characteristic life η."
                      />
                    </div>
                    <div className="text-2xl font-semibold text-white">{analytics.weibull.shape.toFixed(3)}</div>
                    <div className="text-xs text-slate-500 mt-1">
                      95% CI: [{analytics.weibull.shape_ci[0].toFixed(3)}, {analytics.weibull.shape_ci[1].toFixed(3)}]
                    </div>
                  </div>
                  <div className="bg-ink-900/50 rounded-lg p-4">
                    <div className="flex items-center gap-1.5">
                      <div className="text-sm text-slate-400 mb-1">Scale (η)</div>
                      <MetricTooltip
                        label="Scale Parameter (η)"
                        what="Weibull scale parameter (characteristic life) — the time at which 63.2% of units will have failed."
                        why="η is your reliability planning anchor. It tells you WHEN to expect most failures to occur."
                        basis="η is the characteristic life: R(η) = e^(-1) ≈ 0.368. At time η, 63.2% of the population has failed. Scale directly sizes the time axis of the failure distribution."
                        interpret="Schedule preventive maintenance at a fraction of η (typically 50-80% depending on consequences of failure). η with β together define the entire failure time distribution."
                      />
                    </div>
                    <div className="text-2xl font-semibold text-white">{analytics.weibull.scale.toFixed(2)} h</div>
                    <div className="text-xs text-slate-500 mt-1">
                      95% CI: [{analytics.weibull.scale_ci[0].toFixed(2)}, {analytics.weibull.scale_ci[1].toFixed(2)}]
                    </div>
                  </div>
                  <div className="bg-ink-900/50 rounded-lg p-4">
                    <div className="flex items-center gap-1.5">
                      <div className="text-sm text-slate-400 mb-1">Failure Pattern</div>
                      <MetricTooltip
                        label="Failure Pattern"
                        what="Classification of the failure behavior based on Weibull β — determines which region of the bathtub curve this asset operates in."
                        why="The failure pattern dictates the appropriate maintenance strategy. The wrong strategy wastes money or increases failure risk."
                        basis="Maps directly to bathtub curve: infant mortality (decreasing hazard, β<1), useful life (constant hazard, β≈1), wear-out (increasing hazard, β>1)."
                        interpret="Infant mortality → improve commissioning, burn-in testing. Random → condition-based monitoring, not time-based PM. Wear-out → schedule PM at optimal interval before η."
                      />
                    </div>
                    <div className="text-lg font-medium text-white">
                      {analytics.weibull.shape < 1 ? "Infant mortality" : analytics.weibull.shape === 1 ? "Random failures" : "Wear-out"}
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      β {"<"} 1: early life, β = 1: random, β {">"} 1: wear-out
                    </div>
                  </div>
                  <div className="bg-ink-900/50 rounded-lg p-4">
                    <div className="flex items-center gap-1.5">
                      <div className="text-sm text-slate-400 mb-1">B10 Life</div>
                      <MetricTooltip
                        label="B10 Life"
                        what="The operating time at which 10% of the population is expected to have failed (90% reliability point)."
                        why="B10 life is a conservative planning metric used for warranty periods, PM scheduling, and spare parts timing."
                        basis="B10 = η · (-ln(0.9))^(1/β). At B10 hours, reliability R(t) = 0.90. Used extensively in bearing life calculations (L10) and industrial PM planning."
                        interpret="Schedule PM near or before B10 for critical assets. B10 is more conservative than MTBF for planning. For non-critical assets, B20 or MTBF may be appropriate."
                      />
                    </div>
                    <div className="text-2xl font-semibold text-white">
                      {(analytics.weibull.scale * Math.pow(-Math.log(0.9), 1 / analytics.weibull.shape)).toFixed(1)} h
                    </div>
                    <div className="text-xs text-slate-500 mt-1">Time at which 10% will have failed</div>
                  </div>
                </div>

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

          {/* ─── Failure Mode Pareto ─── */}
          <Card
            title="Failure Mode Pareto"
            description="Breakdown of failure modes from event details"
            actions={
              <MetricTooltip
                label="Failure Mode Pareto"
                what="Ranking of failure modes by occurrence count for this specific asset."
                why="Identifies the dominant failure modes — focus root cause analysis and corrective actions on the top items for maximum reliability improvement."
                basis="Pareto (80/20) principle: a small number of failure modes typically cause the majority of failures. Addressing top modes yields disproportionate improvement."
                interpret="Eliminate failure modes from the top down. Each mode removed proportionally increases MTBF. Link to root cause analysis for sustainable correction."
              />
            }
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

          {/* ─── MTBF Trend ─── */}
          <Card
            title="Time Between Failures"
            description="Distribution of intervals between consecutive failures (hours)"
            actions={
              <MetricTooltip
                label="TBF Intervals"
                what="Chart of individual time intervals between consecutive failures — each point is one inter-failure interval."
                why="Visualizes whether failure intervals are stable, improving, or deteriorating over time."
                basis="If intervals are increasing, repairs are effective (reliability growth). Decreasing intervals suggest degradation. The Weibull model assumes all intervals come from the same distribution."
                interpret="Upward trend = reliability improvement. Downward trend = degradation, investigate root cause. High variance = inconsistent failure behavior, consider mixed-mode analysis."
              />
            }
          >
            {mtbfTrend.values.length > 0 ? (
              <Suspense fallback={<Spinner />}>
                <Sparkline labels={mtbfTrend.labels} values={mtbfTrend.values} />
              </Suspense>
            ) : (
              <p className="text-sm text-slate-400">At least two failure events required to show trend.</p>
            )}
          </Card>

          {/* ─── Event Timeline ─── */}
          <Card
            title="Event Timeline"
            description={`Last ${analytics.recent_events.length} events for this asset`}
            actions={
              <MetricTooltip
                label="Event Timeline"
                what="Chronological list of all events (failures, maintenance, inspections) for this asset."
                why="Event history reveals patterns: recurring failures, maintenance effectiveness, and seasonal trends."
                basis="Event-level data is the raw input for all reliability calculations. Each failure event contributes a data point to Weibull analysis and MTBF."
                interpret="Look for: failure clustering (many failures close together), maintenance followed by failure (maintenance-induced), or long failure-free periods (effective PM)."
              />
            }
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
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          evt.event_type === "failure" ? "bg-red-900/50 text-red-400" :
                          evt.event_type === "maintenance" ? "bg-green-900/50 text-green-400" :
                          "bg-blue-900/50 text-blue-400"
                        }`}>
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

          {/* ═══════════════════════════════════════════════════════ */}
          {/* Extended Analytics */}
          {/* ═══════════════════════════════════════════════════════ */}
          {extendedLoading && (
            <div className="flex items-center gap-2 text-slate-400 text-sm py-4">
              <Spinner /> Loading extended analytics...
            </div>
          )}

          {extended && !extendedLoading && (
            <>
              {/* Asset Health Index */}
              {extended.health_index && (
                <Card
                  title="Asset Health Index"
                  description="Composite 0-100 score from reliability, OEE, downtime quality, and repair trends"
                  actions={
                    <MetricTooltip
                      label="Health Index"
                      what="Weighted composite score (0-100) assessing overall asset health across multiple dimensions."
                      why="Combines reliability, availability, OEE, and repair trends into a single actionable number for prioritization."
                      basis="Components are normalized to 0-100 and weighted: availability (30%), failure rate trend (25%), OEE (20%), repair effectiveness (15%), downtime quality (10%). Weights reflect reliability engineering priorities."
                      interpret="Score > 80: asset is healthy. 60-80: monitor, plan improvements. < 60: immediate investigation needed. Check individual components to identify which dimension is dragging the score down."
                    />
                  }
                >
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
                                className={`h-full rounded-full ${val >= 80 ? "bg-emerald-500" : val >= 60 ? "bg-amber-500" : "bg-red-500"}`}
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

              {/* Extended Reliability Metrics */}
              <Card
                title="Extended Reliability"
                description="B-life, failure rate, MTTF, and repair trend analysis"
                actions={
                  <MetricTooltip
                    label="Extended Reliability"
                    what="Advanced reliability metrics beyond basic MTBF: B10 life, instantaneous failure rate, MTTF, and repair effectiveness trend."
                    why="These metrics provide deeper insight into failure behavior, remaining useful life, and whether maintenance is improving or degrading reliability."
                    basis="B10 life from Weibull CDF inversion. Failure rate λ(t) from Weibull hazard function. MTTF from Weibull expected value. Repair trend from sequential comparison of inter-failure intervals."
                    interpret="Improving repair trend (ratio > 1) means repairs are effective. Degrading trend (ratio < 1) means the asset is getting worse despite repairs — escalate to engineering."
                  />
                }
              >
                <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-4">
                  {extended.b10_life && (
                    <div className="bg-ink-900/50 rounded-lg p-4">
                      <div className="flex items-center gap-1.5">
                        <div className="text-sm text-slate-400 mb-1">B10 Life</div>
                        <MetricTooltip
                          label="B10 Life"
                          what="Operating time by which 10% of units are expected to fail."
                          why="Conservative planning metric for PM scheduling and warranty periods."
                          basis="B10 = η · (-ln(0.9))^(1/β) from the Weibull survival function inversion."
                          interpret="Schedule PM before B10 for critical assets. Use B10 as warranty limit."
                        />
                      </div>
                      <div className="text-2xl font-semibold text-white">{extended.b10_life.life_hours.toFixed(1)} h</div>
                    </div>
                  )}
                  {extended.mttf_hours != null && (
                    <div className="bg-ink-900/50 rounded-lg p-4">
                      <div className="flex items-center gap-1.5">
                        <div className="text-sm text-slate-400 mb-1">MTTF</div>
                        <MetricTooltip
                          label="MTTF"
                          what="Mean Time To Failure — expected value of the Weibull failure time distribution."
                          why="MTTF is the Weibull-based equivalent of MTBF. More statistically rigorous than simple averaging."
                          basis="MTTF = η · Γ(1 + 1/β) where Γ is the gamma function. For β = 1, MTTF = η = MTBF."
                          interpret="MTTF > MTBF typically with β > 1 (wear-out). Use for lifetime planning and replacement scheduling."
                        />
                      </div>
                      <div className="text-2xl font-semibold text-white">{extended.mttf_hours.toFixed(1)} h</div>
                    </div>
                  )}
                  {extended.failure_rate && (
                    <div className="bg-ink-900/50 rounded-lg p-4">
                      <div className="flex items-center gap-1.5">
                        <div className="text-sm text-slate-400 mb-1">Failure Rate (λ)</div>
                        <MetricTooltip
                          label="Failure Rate"
                          what="Average failure rate expressed as failures per 1,000 operating hours."
                          why="Failure rate is the reciprocal of MTBF and drives maintenance staffing, spare parts demand, and risk calculations."
                          basis="λ = failures / total operating hours. For Weibull, instantaneous rate varies with time: h(t) = (β/η)(t/η)^(β-1)."
                          interpret="Lower is better. Compare against industry benchmarks. Use for Poisson-based spare parts forecasting."
                        />
                      </div>
                      <div className="text-2xl font-semibold text-white">{(extended.failure_rate.average_rate * 1000).toFixed(2)}</div>
                      <div className="text-xs text-slate-500 mt-1">per 1,000 hours (avg)</div>
                    </div>
                  )}
                  {extended.repair_effectiveness && (
                    <div className="bg-ink-900/50 rounded-lg p-4">
                      <div className="flex items-center gap-1.5">
                        <div className="text-sm text-slate-400 mb-1">Repair Trend</div>
                        <MetricTooltip
                          label="Repair Effectiveness"
                          what="Ratio comparing recent inter-failure intervals to earlier ones. Values > 1 mean intervals are growing (improving)."
                          why="Reveals whether repairs are restoring the asset to better-than-before condition or if it's degrading despite maintenance."
                          basis="Compares average of later half intervals vs earlier half. Based on Crow-AMSAA reliability growth modeling concepts."
                          interpret="Ratio > 1: improving (good repairs). Ratio < 1: degrading (investigate maintenance quality). Ratio ≈ 1: stable (no change)."
                        />
                      </div>
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

              {/* RPN / FMEA */}
              {extended.rpn && extended.rpn.entries.length > 0 && (
                <Card
                  title="Risk Priority Number (RPN)"
                  description="FMEA-style ranking: Severity × Occurrence × Detection"
                  actions={
                    <MetricTooltip
                      label="RPN Analysis"
                      what="Failure Mode and Effects Analysis (FMEA) scoring. Each failure mode gets a Risk Priority Number = Severity × Occurrence × Detection."
                      why="RPN prioritizes which failure modes pose the greatest risk considering not just frequency but also severity of consequences and ability to detect before failure."
                      basis="FMEA is an industry-standard risk assessment tool (SAE J1739, AIAG). Severity (1-10): impact of failure. Occurrence (1-10): frequency. Detection (1-10): ability to detect before failure (10 = undetectable)."
                      interpret="RPN > 200: high risk, immediate action required. 100-200: moderate risk, plan improvements. < 100: acceptable risk. Reduce RPN by improving any of the three factors."
                    />
                  }
                >
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

              {/* Manufacturing / OEE */}
              {extended.manufacturing && (
                <Card
                  title="Manufacturing Performance"
                  description="OEE framework — Availability × Performance × Quality"
                  actions={
                    <MetricTooltip
                      label="OEE"
                      what="Overall Equipment Effectiveness — the gold-standard manufacturing metric combining Availability, Performance, and Quality."
                      why="OEE reveals hidden capacity losses. A 100% OEE means perfect production: no downtime, no speed loss, no defects."
                      basis="OEE = Availability × Performance × Quality. World-class OEE is 85%+. Each component identifies a different type of loss: downtime losses, speed losses, quality losses."
                      interpret="OEE < 65%: significant improvement opportunity. Identify which factor (A, P, or Q) is lowest for targeted improvement. Small improvements in each factor compound multiplicatively."
                    />
                  }
                >
                  <div className="space-y-6">
                    <div className="grid gap-4 grid-cols-1 md:grid-cols-4">
                      <div className="bg-ink-900/50 rounded-lg p-4 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <div className="text-sm text-slate-400 mb-1">OEE</div>
                          <MetricTooltip
                            label="OEE Score"
                            what="Overall Equipment Effectiveness = Availability × Performance × Quality."
                            why="Single number summarizing total equipment effectiveness. Captures all major loss categories."
                            basis="OEE is the product of three ratios, each between 0-1. Benchmarks: <65% typical, 65-85% good, >85% world-class (Seiichi Nakajima, TPM framework)."
                            interpret="Improve the lowest component first for biggest OEE gain. Track weekly/monthly trend."
                          />
                        </div>
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

                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <div className="flex items-center gap-1.5 mb-3">
                          <h3 className="text-sm font-medium text-slate-300">Downtime Breakdown</h3>
                          <MetricTooltip
                            label="Downtime Split"
                            what="Breakdown of total downtime into planned (scheduled maintenance) vs unplanned (failures, breakdowns)."
                            why="A high unplanned ratio indicates reactive maintenance. Shifting toward planned downtime reduces production disruption and emergency costs."
                            basis="Best practice target: <10% unplanned as share of total downtime. Proactive organizations achieve <5%. Unplanned downtime costs 3-5× more than planned downtime."
                            interpret="Unplanned ratio > 50%: highly reactive — implement PM program. 20-50%: transitioning. < 20%: proactive maintenance culture."
                          />
                        </div>
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-slate-400">Planned</span>
                            <span className="text-white font-medium">{extended.manufacturing.downtime_split.planned_downtime_hours.toFixed(1)} h ({extended.manufacturing.downtime_split.planned_count} events)</span>
                          </div>
                          <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                            <div className="h-full bg-green-500 rounded-full"
                              style={{ width: `${extended.manufacturing.downtime_split.total_downtime_hours > 0 ? ((1 - extended.manufacturing.downtime_split.unplanned_ratio) * 100) : 0}%` }}
                            />
                          </div>
                          <div className="flex items-center justify-between text-sm">
                            <span className="text-slate-400">Unplanned</span>
                            <span className="text-white font-medium">{extended.manufacturing.downtime_split.unplanned_downtime_hours.toFixed(1)} h ({extended.manufacturing.downtime_split.unplanned_count} events)</span>
                          </div>
                          <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
                            <div className="h-full bg-red-500 rounded-full"
                              style={{ width: `${extended.manufacturing.downtime_split.unplanned_ratio * 100}%` }}
                            />
                          </div>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-ink-900/50 rounded-lg p-3">
                          <div className="flex items-center gap-1">
                            <div className="text-xs text-slate-400">MTBM</div>
                            <MetricTooltip
                              label="MTBM"
                              what="Mean Time Between Maintenance — average hours between any maintenance event (planned or unplanned)."
                              why="MTBM reflects total maintenance burden. Lower MTBM = more frequent maintenance disruptions."
                              basis="MTBM = Operating Hours / Total Maintenance Events. Differs from MTBF which only counts failures."
                              interpret="MTBM << MTBF suggests excessive planned maintenance. MTBM ≈ MTBF means most maintenance is reactive."
                            />
                          </div>
                          <div className="text-xl font-semibold text-white mt-1">{extended.manufacturing.mtbm.mtbm_hours.toFixed(1)} h</div>
                        </div>
                        <div className="bg-ink-900/50 rounded-lg p-3">
                          <div className="flex items-center gap-1">
                            <div className="text-xs text-slate-400">Throughput</div>
                            <MetricTooltip
                              label="Throughput"
                              what="Actual production throughput in cycles per hour compared to design capacity."
                              why="Gap between actual and design throughput represents speed losses — one of the three OEE loss categories."
                              basis="Performance Rate = Actual Throughput / Design Throughput. Speed losses include minor stoppages, reduced speed, and idling."
                              interpret="Actual << Design: investigate speed limiters (tooling, material, operator). Gradual decline may indicate wear or calibration drift."
                            />
                          </div>
                          <div className="text-xl font-semibold text-white mt-1">{extended.manufacturing.performance.actual_throughput.toFixed(1)}</div>
                          <div className="text-xs text-slate-500">cycles/h (design: {extended.manufacturing.performance.design_throughput.toFixed(1)})</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </Card>
              )}

              {/* Business Impact */}
              <Card
                title="Business Impact"
                description="Cost of unreliability and PM optimization"
                actions={
                  <MetricTooltip
                    label="Business Impact"
                    what="Financial analysis of unreliability costs and preventive maintenance optimization for this asset."
                    why="Translates reliability problems into business language (dollars). Essential for justifying reliability improvement investments."
                    basis="COUR (Cost of Unreliability) = Lost Production Cost + Repair Cost. Lost production = unplanned downtime hours × hourly production value. PM optimization uses Weibull β to determine if time-based PM is appropriate."
                    interpret="High COUR justifies reliability improvement investment. PM optimization tells you whether to do PM, how often, and if current intervals are appropriate."
                  />
                }
              >
                <div className="grid gap-4 md:grid-cols-2">
                  {extended.cour && (
                    <div className="space-y-3">
                      <h3 className="text-sm font-medium text-slate-300">Cost of Unreliability</h3>
                      <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4">
                        <div className="text-3xl font-bold text-red-400">${extended.cour.total_cost.toLocaleString()}</div>
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

                  {extended.pm_optimization && (
                    <div className="space-y-3">
                      <div className="flex items-center gap-1.5">
                        <h3 className="text-sm font-medium text-slate-300">PM Optimization</h3>
                        <MetricTooltip
                          label="PM Optimization"
                          what="Analysis of whether preventive maintenance is appropriate and optimally scheduled based on the Weibull failure pattern."
                          why="Doing PM on random-failure assets wastes money. Doing too little PM on wear-out assets increases failures. Optimization finds the sweet spot."
                          basis="PM is only effective when β > 1 (wear-out failures). Optimal PM interval ≈ η × (cost ratio adjustment). Over-maintaining: PM interval << optimal. Under-maintaining: PM interval >> optimal."
                          interpret="'PM not recommended' (β<1): switch to condition-based monitoring. 'Appropriate': current schedule is good. 'Under-maintaining': decrease PM interval to reduce failures."
                        />
                      </div>
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
        </>
      )}
    </div>
  );
}
