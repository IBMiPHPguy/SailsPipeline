import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { askSalesCopilot, fetchSalesAnalytics, fetchSalesAnalyticsKeyMetrics } from "./api";
import { formatMoney } from "./cabinPricing";
import {
  buildChartYAxis,
  buildYearMonthKey,
  formatAxisMoney,
  monthShortLabel,
} from "./salesChartAxis";
import {
  groupRejectionReasonsBySegment,
  SALES_REJECTION_SEGMENTS,
  type SalesRejectionSegment,
} from "./salesAnalyticsRejection";
import type {
  SalesAnalyticsData,
  SalesAnalyticsMonthCommission,
  SalesAnalyticsRejectionReason,
  SalesAnalyticsYearSummary,
} from "./types";
import { useAgencyAiStatus } from "./useAgencyAiStatus";

const COPILOT_QUICK_PROMPTS = [
  "Find our high-value premium leads",
  "Summarize our pipeline bottlenecks",
  "Show top reasons for rejected quotes",
] as const;

type SalesAnalyticsProps = {
  onError: (message: string) => void;
};

function formatWinRate(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return Number.isInteger(value) ? `${value}%` : `${value.toFixed(1)}%`;
}

function useCurrentCalendarYear(): number {
  return new Date().getFullYear();
}

function SalesAnalyticsYearKpis({
  currentYearSummary,
  priorYears,
  onError,
}: {
  currentYearSummary: SalesAnalyticsYearSummary;
  priorYears: number[];
  onError: (message: string) => void;
}) {
  const currentYear = useCurrentCalendarYear();
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [summary, setSummary] = useState(currentYearSummary);
  const [loadingPriorYear, setLoadingPriorYear] = useState(false);
  const summaryCacheRef = useRef<Map<number, SalesAnalyticsYearSummary>>(
    new Map([[currentYearSummary.year, currentYearSummary]]),
  );
  const showPriorYearFilter = priorYears.length > 0;
  const viewingPriorYear = selectedYear !== null;

  useEffect(() => {
    summaryCacheRef.current.set(currentYearSummary.year, currentYearSummary);
    if (!viewingPriorYear) {
      setSummary(currentYearSummary);
    }
  }, [currentYearSummary, viewingPriorYear]);

  async function handlePriorYearChange(nextYear: string) {
    if (!nextYear) {
      setSelectedYear(null);
      setSummary(currentYearSummary);
      return;
    }

    const year = Number(nextYear);
    setSelectedYear(year);

    const cached = summaryCacheRef.current.get(year);
    if (cached) {
      setSummary(cached);
      return;
    }

    setLoadingPriorYear(true);
    try {
      const fetched = await fetchSalesAnalyticsKeyMetrics(year);
      summaryCacheRef.current.set(year, fetched);
      setSummary(fetched);
    } catch (loadError) {
      onError(loadError instanceof Error ? loadError.message : `Unable to load ${year} key metrics.`);
      setSelectedYear(null);
      setSummary(currentYearSummary);
    } finally {
      setLoadingPriorYear(false);
    }
  }

  const metrics = [
    {
      id: "booked",
      label: "Overall sales booked",
      value: formatMoney(summary.total_sales_booked),
      tone: "positive" as const,
    },
    {
      id: "lost",
      label: "Overall lost sales",
      value: formatMoney(summary.total_sales_lost),
      tone: "negative" as const,
    },
    {
      id: "commission-rate",
      label: "Average commission rate",
      value: formatWinRate(summary.average_commission_rate_percent),
      tone: "neutral" as const,
    },
    {
      id: "win-rate",
      label: "Overall win rate",
      value: formatWinRate(summary.win_rate_percent),
      tone: "neutral" as const,
    },
  ];

  return (
    <div className="sales-analytics-year-kpis">
      <div className="sales-analytics-year-kpis-toolbar">
        <p className="sales-analytics-year-kpis-heading">Key metrics · {summary.year}</p>
        {showPriorYearFilter ? (
          <label className="sales-analytics-year-kpis-filter">
            Prior year
            <select
              value={selectedYear ?? ""}
              disabled={loadingPriorYear}
              onChange={(event) => {
                void handlePriorYearChange(event.target.value);
              }}
            >
              <option value="">Current year ({currentYear})</option>
              {[...priorYears].reverse().map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </label>
        ) : null}
      </div>
      {loadingPriorYear ? (
        <p className="meta sales-analytics-year-kpis-loading" aria-live="polite">
          Loading {selectedYear} key metrics...
        </p>
      ) : null}
      <dl
        className={`sales-analytics-year-kpi-grid${loadingPriorYear ? " sales-analytics-year-kpi-grid--loading" : ""}`}
        aria-busy={loadingPriorYear}
      >
        {metrics.map((metric) => (
          <div className={`sales-analytics-year-kpi sales-analytics-year-kpi--${metric.tone}`} key={metric.id}>
            <dt>{metric.label}</dt>
            <dd>{loadingPriorYear ? "…" : metric.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function CommissionTimelineChart({ data }: { data: SalesAnalyticsData }) {
  const currentYear = new Date().getFullYear();
  const availableYears = data.available_years.length > 0 ? data.available_years : [currentYear, currentYear + 1];
  const defaultYear = availableYears.includes(currentYear) ? currentYear : availableYears[availableYears.length - 1];
  const [selectedYear, setSelectedYear] = useState(defaultYear);

  useEffect(() => {
    if (!availableYears.includes(selectedYear)) {
      setSelectedYear(defaultYear);
    }
  }, [availableYears, defaultYear, selectedYear]);

  const timelineByKey = useMemo(() => {
    const map = new Map<string, SalesAnalyticsMonthCommission>();
    for (const month of data.commission_timeline) {
      map.set(month.month_key, month);
    }
    return map;
  }, [data.commission_timeline]);

  const monthsInYear = useMemo(() => {
    return Array.from({ length: 12 }, (_, index) => {
      const month = index + 1;
      const monthKey = buildYearMonthKey(selectedYear, month);
      const existing = timelineByKey.get(monthKey);
      if (existing) {
        return existing;
      }
      return {
        month_key: monthKey,
        label: monthShortLabel(month),
        total_commission: 0,
        booking_count: 0,
      };
    });
  }, [selectedYear, timelineByKey]);

  const yearTotal = useMemo(
    () => monthsInYear.reduce((sum, month) => sum + month.total_commission, 0),
    [monthsInYear],
  );

  const maxCommission = useMemo(
    () => Math.max(...monthsInYear.map((month) => month.total_commission), 0),
    [monthsInYear],
  );

  const yAxis = useMemo(() => buildChartYAxis(maxCommission), [maxCommission]);

  return (
    <section className="sales-analytics-card sales-analytics-card-wide">
      <header className="sales-analytics-card-header sales-analytics-card-header-chart">
        <div>
          <h3>Pipeline revenue &amp; cash-flow timeline</h3>
          <p className="sales-analytics-card-subtitle">
            Accepted booking commission by sailing month · hover bars for amounts
          </p>
        </div>
        <div className="sales-analytics-chart-controls">
          <div className="sales-analytics-kpi sales-analytics-kpi-chart">
            <span className="sales-analytics-kpi-label">{selectedYear} total</span>
            <strong>{formatMoney(yearTotal)}</strong>
          </div>
          <span className="sales-analytics-chart-controls-divider" aria-hidden="true" />
          <label className="sales-commission-year-filter">
            Year
            <select
              value={selectedYear}
              onChange={(event) => setSelectedYear(Number(event.target.value))}
            >
              {availableYears.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>
      <div className="sales-analytics-card-body">
        {yearTotal === 0 ? (
          <p className="meta sales-analytics-empty sales-analytics-empty-inline">
            No accepted booking commission scheduled for {selectedYear} yet.
          </p>
        ) : null}
        <div className="sales-commission-chart-panel" role="img" aria-label={`Commission forecast for ${selectedYear}`}>
          <div className="sales-commission-y-axis" aria-hidden="true">
            {yAxis.ticks.map((tick) => {
              const ratio = yAxis.max > 0 ? tick / yAxis.max : 0;
              return (
                <span
                  className="sales-commission-y-axis-label"
                  key={tick}
                  style={{ top: `${100 - ratio * 100}%` }}
                >
                  {formatAxisMoney(tick)}
                </span>
              );
            })}
          </div>
          <div className="sales-commission-plot-wrap">
            <div className="sales-commission-plot">
              <div className="sales-commission-grid" aria-hidden="true">
                {yAxis.ticks.map((tick) => (
                  <div
                    key={tick}
                    className="sales-commission-grid-line"
                    style={{ bottom: `${(tick / yAxis.max) * 100}%` }}
                  />
                ))}
              </div>
              <div className="sales-commission-chart">
                {monthsInYear.map((month) => {
                  const heightPercent =
                    month.total_commission > 0
                      ? Math.max(2, (month.total_commission / yAxis.max) * 100)
                      : 0;
                  const tooltip = formatMoney(month.total_commission);

                  return (
                    <div className="sales-commission-chart-bar-wrap" key={month.month_key}>
                      {month.total_commission > 0 ? (
                        <div
                          className="sales-commission-bar-hit"
                          tabIndex={0}
                          aria-label={tooltip}
                        >
                          <div
                            className="sales-commission-chart-bar"
                            style={{ height: `${heightPercent}%` }}
                          >
                            <span className="sales-commission-bar-tooltip" role="tooltip">
                              {tooltip}
                            </span>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="sales-commission-x-axis">
              {monthsInYear.map((month) => (
                <div className="sales-commission-x-axis-column" key={`${month.month_key}-axis`}>
                  <span className="sales-commission-chart-label">
                    {monthShortLabel(Number(month.month_key.slice(5, 7)))}
                  </span>
                  {month.booking_count > 0 ? (
                    <span className="sales-commission-chart-meta meta">
                      {month.booking_count} booking{month.booking_count === 1 ? "" : "s"}
                    </span>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function FunnelTracker({ data }: { data: SalesAnalyticsData }) {
  const maxCount = useMemo(
    () => Math.max(...data.funnel_stages.map((stage) => stage.count), 1),
    [data.funnel_stages],
  );

  return (
    <section className="sales-analytics-card">
      <header className="sales-analytics-card-header">
        <div>
          <h3>Close ratio &amp; funnel leaks</h3>
          <p className="sales-analytics-card-subtitle">Open leads through accepted and rejected outcomes</p>
        </div>
      </header>
      <div className="sales-analytics-card-body">
        <div className="sales-funnel">
          {data.funnel_stages.map((stage) => {
            const widthPercent = Math.max(22, (stage.count / maxCount) * 100);
            return (
              <div className="sales-funnel-row" key={stage.label}>
                <div className="sales-funnel-row-label">
                  <span className="sales-funnel-label">{stage.label}</span>
                  <span className="sales-funnel-count">{stage.count}</span>
                </div>
                <div className="sales-funnel-track">
                  <div className="sales-funnel-fill" style={{ width: `${widthPercent}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function RejectionReasonSegmentList({
  items,
  segment,
  maxCount,
}: {
  items: SalesAnalyticsRejectionReason[];
  segment: SalesRejectionSegment;
  maxCount: number;
}) {
  if (items.length === 0) {
    return <p className="meta sales-analytics-empty sales-analytics-empty-inline">No quote rejections recorded yet.</p>;
  }

  return (
    <ul className="sales-rejection-list">
      {items.map((item) => (
        <li className="sales-rejection-item" key={`${segment}-${item.reason}`}>
          <div className="sales-rejection-row">
            <span className="sales-rejection-reason">{item.reason}</span>
            <span className="sales-rejection-count">{item.count}</span>
          </div>
          <div className="sales-rejection-bar-track">
            <div
              className={`sales-rejection-bar-fill sales-rejection-bar-fill--${segment}`}
              style={{ width: `${(item.count / maxCount) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

function RejectionReasonsChart({ reasons }: { reasons: SalesAnalyticsData["rejection_reasons"] }) {
  const groupedReasons = useMemo(() => groupRejectionReasonsBySegment(reasons), [reasons]);
  const maxCount = useMemo(() => Math.max(...reasons.map((item) => item.count), 1), [reasons]);
  const hasAnyReasons = reasons.length > 0;

  return (
    <section className="sales-analytics-card">
      <header className="sales-analytics-card-header">
        <div>
          <h3>Rejection &amp; loss drivers</h3>
          <p className="sales-analytics-card-subtitle">
            Proposed cruise rejection reasons on active leads vs closed leads without a booking
          </p>
        </div>
      </header>
      <div className="sales-analytics-card-body sales-rejection-drivers">
        {!hasAnyReasons ? (
          <p className="meta sales-analytics-empty">No rejection or loss reasons recorded yet.</p>
        ) : (
          SALES_REJECTION_SEGMENTS.map((segment) => {
            const items = groupedReasons.get(segment.id) ?? [];
            return (
              <section
                className={`sales-rejection-segment sales-rejection-segment--${segment.id}`}
                key={segment.id}
                aria-label={segment.title}
              >
                <header className="sales-rejection-segment-header">
                  <span className={`sales-rejection-segment-badge sales-rejection-segment-badge--${segment.id}`}>
                    {segment.badgeLabel}
                  </span>
                  <div>
                    <h4 className="sales-rejection-segment-title">{segment.title}</h4>
                  </div>
                </header>
                <RejectionReasonSegmentList items={items} segment={segment.id} maxCount={maxCount} />
              </section>
            );
          })
        )}
      </div>
    </section>
  );
}

function CruiseLineShareChart({ shares }: { shares: SalesAnalyticsData["cruise_line_shares"] }) {
  const palette = ["#1864ab", "#0b7285", "#5c7cfa", "#1098ad", "#364fc7", "#4263eb", "#1864ab", "#0ca678"];

  return (
    <section className="sales-analytics-card sales-analytics-card-wide">
      <header className="sales-analytics-card-header">
        <div>
          <h3>Cruise line brand share</h3>
          <p className="sales-analytics-card-subtitle">
            Deposited booking volume, commission, and mix by supplier partner
          </p>
        </div>
      </header>
      <div className="sales-analytics-card-body">
        {shares.length === 0 ? (
          <p className="meta sales-analytics-empty">No deposited bookings to analyze yet.</p>
        ) : (
          <ul className="sales-cruise-line-list">
            {shares.map((share, index) => (
              <li className="sales-cruise-line-item" key={share.cruise_line}>
                <div className="sales-cruise-line-item-header">
                  <div className="sales-cruise-line-title-block">
                    <span className="sales-cruise-line-name">{share.cruise_line}</span>
                    <dl className="sales-cruise-line-metrics">
                      <div className="sales-cruise-line-metric">
                        <dt>Total volume</dt>
                        <dd>{formatMoney(share.total_booking_amount)}</dd>
                      </div>
                      <div className="sales-cruise-line-metric">
                        <dt>Total commission booked</dt>
                        <dd>{formatMoney(share.total_commission)}</dd>
                      </div>
                      <div className="sales-cruise-line-metric">
                        <dt>Median price per room booked</dt>
                        <dd>{formatMoney(share.median_booking_amount)}</dd>
                      </div>
                      <div className="sales-cruise-line-metric">
                        <dt>Comm. rate</dt>
                        <dd>{share.commission_rate_percent.toFixed(1)}%</dd>
                      </div>
                    </dl>
                  </div>
                  <span className="sales-cruise-line-meta">
                    {share.booking_count} booking{share.booking_count === 1 ? "" : "s"} · {share.share_percent}%
                  </span>
                </div>
                <div className="sales-cruise-line-bar-track">
                  <div
                    className="sales-cruise-line-bar-fill"
                    style={{
                      width: `${share.share_percent}%`,
                      background: palette[index % palette.length],
                    }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function FirstMateCopilot() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const { aiUnavailableMessage } = useAgencyAiStatus();
  const aiBlocked = Boolean(aiUnavailableMessage);

  async function submitQuestion(prompt: string) {
    const trimmed = prompt.trim();
    if (!trimmed || aiBlocked) {
      return;
    }
    setAsking(true);
    setError("");
    try {
      const response = await askSalesCopilot(trimmed);
      setAnswer(response);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to get a copilot answer.");
    } finally {
      setAsking(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await submitQuestion(question);
  }

  return (
    <section className="sales-analytics-card sales-analytics-copilot sales-analytics-copilot-top">
      <header className="sales-analytics-copilot-header sales-analytics-copilot-header-top">
        <div className="sales-analytics-copilot-intro">
          <h3>✨ First Mate AI Copilot</h3>
          <p className="sales-analytics-card-subtitle">
            Ask natural-language questions about your pipeline portfolio.
          </p>
        </div>
        <form className="sales-analytics-copilot-form" onSubmit={handleSubmit}>
          <label className="sales-analytics-copilot-label">
            <span className="sr-only">Your question</span>
            <input
              type="text"
              value={question}
              placeholder="e.g. Where is commission peaking next quarter?"
              disabled={asking || aiBlocked}
              onChange={(event) => setQuestion(event.target.value)}
            />
          </label>
          <button
            type="submit"
            className="modal-primary sales-analytics-copilot-submit"
            disabled={asking || aiBlocked || !question.trim()}
          >
            {asking ? "Thinking..." : "Ask First Mate"}
          </button>
        </form>
      </header>
      <div className="sales-analytics-copilot-body">
        {aiUnavailableMessage ? (
          <p className="status warning sales-analytics-copilot-status">{aiUnavailableMessage}</p>
        ) : null}
        <div className="sales-analytics-copilot-prompts">
          {COPILOT_QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              className="sales-analytics-prompt-pill"
              disabled={asking || aiBlocked}
              onClick={() => {
                setQuestion(prompt);
                void submitQuestion(prompt);
              }}
            >
              {prompt}
            </button>
          ))}
        </div>
        {error ? <p className="status error sales-analytics-copilot-status">{error}</p> : null}
        {answer ? (
          <div className="sales-analytics-copilot-answer modal-section-panel">
            <p className="sales-analytics-copilot-answer-label">First Mate</p>
            <p>{answer}</p>
          </div>
        ) : (
          <p className="meta sales-analytics-copilot-hint">
            Use a quick prompt or type your own question to explore leads, bottlenecks, and revenue timing.
          </p>
        )}
      </div>
    </section>
  );
}

function SalesAnalyticsPageHeader({
  currentYearSummary,
  priorYears,
  onError,
}: {
  currentYearSummary?: SalesAnalyticsYearSummary;
  priorYears?: number[];
  onError?: (message: string) => void;
}) {
  return (
    <section className="request-summary-card request-summary-card-compact sales-analytics-summary-card">
      <div className="request-summary-compact-row">
        <div className="request-summary-compact-title">
          <h2>Sales Analytics</h2>
        </div>
      </div>
      <div className="request-summary-compact-meta">
        <span>Portfolio forecasting, conversion health, and supplier mix for your active pipeline</span>
      </div>
      {currentYearSummary && onError ? (
        <SalesAnalyticsYearKpis
          currentYearSummary={currentYearSummary}
          priorYears={priorYears ?? []}
          onError={onError}
        />
      ) : null}
    </section>
  );
}

export default function SalesAnalytics({ onError }: SalesAnalyticsProps) {
  const [data, setData] = useState<SalesAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchSalesAnalytics()
      .then((analytics) => {
        if (!cancelled) {
          setData(analytics);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          onError(loadError instanceof Error ? loadError.message : "Unable to load sales analytics.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [onError]);

  if (loading) {
    return (
      <div className="workspace workspace-tabbed sales-analytics-page">
        <SalesAnalyticsPageHeader />
        <section className="section-card sales-analytics-board">
          <div className="section-card-body sales-analytics-board-body">
            <p className="meta">Loading sales analytics...</p>
          </div>
        </section>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="workspace workspace-tabbed sales-analytics-page">
        <SalesAnalyticsPageHeader />
        <section className="section-card sales-analytics-board">
          <div className="section-card-body sales-analytics-board-body">
            <p className="meta">Unable to load sales analytics.</p>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="workspace workspace-tabbed sales-analytics-page">
      <SalesAnalyticsPageHeader
        currentYearSummary={data.current_year_summary}
        priorYears={data.key_metrics_prior_years}
        onError={onError}
      />

      <section className="section-card sales-analytics-board">
        <div className="section-card-body sales-analytics-board-body">
          <FirstMateCopilot />
          <CommissionTimelineChart data={data} />
          <div className="sales-analytics-split">
            <FunnelTracker data={data} />
            <RejectionReasonsChart reasons={data.rejection_reasons} />
          </div>
          <CruiseLineShareChart shares={data.cruise_line_shares} />
        </div>
      </section>
    </div>
  );
}
