import { formatCruiseLines } from "./CruiseLineMultiSelect";
import { PRIMARY_CLOSE_REASON } from "./formOptions";
import { useEffect, useState } from "react";
import { fetchOpenRequests } from "./api";
import type { DashboardData, DashboardOpenRequest } from "./types";
import { formatDestinationSummary, formatDate, formatTimestamp } from "./utils";
import ViewIcon from "./ViewIcon";
import IconTooltip from "./IconTooltip";

const OPEN_REQUESTS_PAGE_SIZE = 25;

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
  const [openRequests, setOpenRequests] = useState<DashboardOpenRequest[]>([]);
  const [openRequestsLoading, setOpenRequestsLoading] = useState(true);
  const [openRequestsError, setOpenRequestsError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  async function loadOpenRequests(activeSearch: string, activePage: number) {
    setOpenRequestsLoading(true);
    setOpenRequestsError("");
    try {
      const response = await fetchOpenRequests({
        q: activeSearch,
        page: activePage,
        pageSize: OPEN_REQUESTS_PAGE_SIZE,
      });
      setOpenRequests(response.items);
      setTotal(response.total);
      setTotalPages(response.total_pages);
      if (response.total_pages > 0 && activePage > response.total_pages) {
        setPage(response.total_pages);
      }
    } catch (loadError) {
      setOpenRequestsError(loadError instanceof Error ? loadError.message : "Unable to load open requests.");
    } finally {
      setOpenRequestsLoading(false);
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearchQuery(searchInput.trim());
      setPage(1);
    }, 300);

    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    void loadOpenRequests(searchQuery, page);
  }, [searchQuery, page, dashboard.open_count]);

  const pageStart = total === 0 ? 0 : (page - 1) * OPEN_REQUESTS_PAGE_SIZE + 1;
  const pageEnd = total === 0 ? 0 : Math.min(page * OPEN_REQUESTS_PAGE_SIZE, total);
  const emptyMessage = searchQuery.trim()
    ? "No open requests match your search."
    : "No open requests yet. Create the first one.";

  return (
    <section className="dashboard">
      <div className="stats-grid">
        <article className="stat-card stat-card-warning">
          <header className="stat-card-header">
            <span className="stat-label">Stale requests</span>
          </header>
          <div className="stat-card-body">
            <strong className="stat-value">{dashboard.stale_count}</strong>
            <div className="stat-card-meta">
              <span className="stat-hint">No request activity in 3+ days</span>
            </div>
          </div>
        </article>
        <article
          className="stat-card stat-card-closed stat-card-clickable"
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
          <header className="stat-card-header">
            <span className="stat-label">Closed requests</span>
          </header>
          <div className="stat-card-body">
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
          </div>
        </article>
      </div>

      <section className="card open-requests-table-card">
        <header className="open-requests-table-card-header">
          <div className="open-requests-table-card-header-main">
            <h3>Open Requests</h3>
            <span className="open-requests-table-card-count" aria-label={`${dashboard.open_count} open requests`}>
              {dashboard.open_count}
            </span>
          </div>
          <button type="button" onClick={onNewRequest}>
            New Request
          </button>
        </header>
        <div className="open-requests-table-card-body">
          <div className="open-requests-table-toolbar">
            <label className="open-requests-search">
              Search open requests
              <input
                type="search"
                value={searchInput}
                placeholder="Client, trip, next task, cruise line, or agent"
                onChange={(event) => setSearchInput(event.target.value)}
              />
            </label>
          </div>

          {openRequestsLoading ? (
            <p>Loading open requests...</p>
          ) : openRequests.length === 0 ? (
            <p>{emptyMessage}</p>
          ) : (
            <>
              <div className="open-requests-table-wrap">
                <table className="open-requests-table">
                  <thead>
                    <tr>
                      <th scope="col">Client</th>
                      <th scope="col">Trip</th>
                      <th scope="col">Next task</th>
                      <th scope="col">Last worked</th>
                      <th scope="col">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {openRequests.map((request) => (
                      <tr key={request.id} className={request.is_stale ? "open-requests-row-stale" : undefined}>
                        <td>
                          <strong>
                            {request.first_name} {request.last_name}
                          </strong>
                          <div className="meta">{formatDestinationSummary(request)}</div>
                        </td>
                        <td>
                          <div className="meta">
                            {formatCruiseLines(request.cruise_lines)} · {formatDate(request.departure_date)} to{" "}
                            {formatDate(request.return_date)}
                          </div>
                        </td>
                        <td>
                          {request.next_open_task ? (
                            <>
                              <div className="open-requests-next-task-title">{request.next_open_task.title}</div>
                              <div className="meta">{request.next_open_task.workflow_name} workflow</div>
                            </>
                          ) : (
                            <div className="meta">No open workflow task</div>
                          )}
                        </td>
                        <td>
                          <div className="open-requests-last-worked">
                            <span className="meta">
                              {request.last_worked_by.username} · {formatTimestamp(request.last_worked_at)}
                            </span>
                            {request.is_stale ? <span className="stale-badge">Stale</span> : null}
                          </div>
                        </td>
                        <td className="dashboard-table-actions-cell">
                          <IconTooltip label={`View request for ${request.first_name} ${request.last_name}`}>
                            <button
                              type="button"
                              className="icon-button"
                              aria-label={`View request for ${request.first_name} ${request.last_name}`}
                              onClick={() => onOpenRequest(request.id)}
                            >
                              <ViewIcon />
                            </button>
                          </IconTooltip>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="table-pagination">
                <p className="table-pagination-summary">
                  {searchQuery.trim()
                    ? `Showing ${pageStart}-${pageEnd} of ${total} matching open requests`
                    : `Showing ${pageStart}-${pageEnd} of ${total} open requests`}
                </p>
                <div className="table-pagination-controls">
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={page <= 1 || openRequestsLoading}
                    onClick={() => setPage((currentPage) => Math.max(1, currentPage - 1))}
                  >
                    Previous
                  </button>
                  <span className="table-pagination-status">
                    Page {totalPages === 0 ? 0 : page} of {totalPages}
                  </span>
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={page >= totalPages || totalPages === 0 || openRequestsLoading}
                    onClick={() => setPage((currentPage) => currentPage + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </section>

      {openRequestsError ? <p className="status error">{openRequestsError}</p> : null}
    </section>
  );
}
