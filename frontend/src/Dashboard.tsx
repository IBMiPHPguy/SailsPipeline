import { PRIMARY_CLOSE_REASON } from "./formOptions";
import type { DashboardData } from "./types";
import RequestSummary from "./RequestSummary";

function formatSuccessfulSalesCloseRate(rate: number | null): string {
  if (rate === null) {
    return "—";
  }

  return Number.isInteger(rate) ? `${rate}%` : `${rate.toFixed(1)}%`;
}

type DashboardProps = {
  dashboard: DashboardData;
  onNewRequest: () => void;
  onOpenRequest: (requestId: number) => void;
  onOpenClosedRequests: () => void;
};

export default function Dashboard({
  dashboard,
  onNewRequest,
  onOpenRequest,
  onOpenClosedRequests,
}: DashboardProps) {
  return (
    <section className="dashboard">
      <div className="dashboard-header">
        <div>
          <h2>Dashboard</h2>
          <p>Review open cruise travel requests and start new intake.</p>
        </div>
        <button type="button" onClick={onNewRequest}>
          New Request
        </button>
      </div>

      <div className="stats-grid">
        <article className="stat-card">
          <span className="stat-label">Open requests</span>
          <strong className="stat-value">{dashboard.open_count}</strong>
          <div className="stat-card-meta" />
        </article>
        <article className="stat-card stat-card-warning">
          <span className="stat-label">Stale requests</span>
          <strong className="stat-value">{dashboard.stale_count}</strong>
          <div className="stat-card-meta">
            <span className="stat-hint">No request activity in 3+ days</span>
          </div>
        </article>
        <article
          className="stat-card stat-card-clickable"
          role="button"
          tabIndex={0}
          onClick={onOpenClosedRequests}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              onOpenClosedRequests();
            }
          }}
        >
          <span className="stat-label">Closed requests</span>
          <strong className="stat-value">{dashboard.closed_count}</strong>
          <div className="stat-card-meta">
            <div className="stat-subcounts">
              <span>
                {PRIMARY_CLOSE_REASON}: {dashboard.purchased_closed_count}
              </span>
              <span>Other close reasons: {dashboard.other_closed_count}</span>
            </div>
            <span className="stat-success-rate">
              Successful Sales Close Rate: {formatSuccessfulSalesCloseRate(dashboard.successful_sales_close_rate)}
            </span>
            <span className="stat-hint stat-hint-neutral">View closed requests and reopen if needed</span>
          </div>
        </article>
      </div>

      <section className="card">
        <h3>Open Requests</h3>
        {dashboard.open_requests.length === 0 ? (
          <p>No open requests yet. Create the first one.</p>
        ) : (
          <div className="requests">
            {dashboard.open_requests.map((request) => (
              <button
                type="button"
                key={request.id}
                className={`request-item request-button ${request.is_stale ? "stale" : ""}`}
                onClick={() => onOpenRequest(request.id)}
              >
                <RequestSummary
                  request={request}
                  nextOpenTask={request.next_open_task}
                  lastWorkedAt={request.last_worked_at}
                  lastWorkedBy={request.last_worked_by}
                  isStale={request.is_stale}
                />
              </button>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
