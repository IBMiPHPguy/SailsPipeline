import { REQUEST_DASHBOARD_PAGE_TITLE } from "./branding";
import { formatCruiseLines } from "./CruiseLineMultiSelect";
import { PRIMARY_CLOSE_REASON } from "./formOptions";
import { useEffect, useRef, useState } from "react";
import { fetchOpenRequests } from "./api";
import { formatMoney } from "./cabinPricing";
import { getNextTaskBadgeClass } from "./nextTaskBadge";
import OpenRequestQuickActions from "./OpenRequestQuickActions";
import ReportPagination from "./ReportPagination";
import { DEFAULT_PAGE_SIZE, type PageSizeOption } from "./pagination";
import type { DashboardData, DashboardOpenRequest } from "./types";
import { formatDestinationSummary, formatDate, formatTimestamp } from "./utils";

function formatSuccessfulSalesCloseRate(rate: number | null): string {
  if (rate === null) {
    return "—";
  }

  return Number.isInteger(rate) ? `${rate}%` : `${rate.toFixed(1)}%`;
}

function formatPipelineValueSubtitle(value: number): string {
  if (value <= 0) {
    return "No quoted value yet";
  }
  return `${formatMoney(value)} in active quotes`;
}

type DashboardProps = {
  dashboard: DashboardData;
  onNewRequest: () => void;
  onOpenRequest: (requestId: number) => void;
  onOpenClosedRequests: () => void;
  onDashboardRefresh: () => void;
};

export default function Dashboard({
  dashboard,
  onNewRequest,
  onOpenRequest,
  onOpenClosedRequests,
  onDashboardRefresh,
}: DashboardProps) {
  const [openRequests, setOpenRequests] = useState<DashboardOpenRequest[]>([]);
  const [openRequestsLoading, setOpenRequestsLoading] = useState(true);
  const [openRequestsError, setOpenRequestsError] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<PageSizeOption>(DEFAULT_PAGE_SIZE);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [listVersion, setListVersion] = useState(0);
  const loadRequestRef = useRef(0);

  async function loadOpenRequests(activeSearch: string, activePage: number, activePageSize: number) {
    const requestId = loadRequestRef.current + 1;
    loadRequestRef.current = requestId;
    setOpenRequestsLoading(true);
    setOpenRequestsError("");
    try {
      const response = await fetchOpenRequests({
        q: activeSearch,
        page: activePage,
        pageSize: activePageSize,
      });
      if (requestId !== loadRequestRef.current) {
        return;
      }
      setOpenRequests(response.items ?? []);
      setTotal(response.total);
      setTotalPages(response.total_pages);
      if (response.total_pages > 0 && activePage > response.total_pages) {
        setPage(response.total_pages);
      }
    } catch (loadError) {
      if (requestId !== loadRequestRef.current) {
        return;
      }
      setOpenRequestsError(loadError instanceof Error ? loadError.message : "Unable to load open requests.");
    } finally {
      if (requestId === loadRequestRef.current) {
        setOpenRequestsLoading(false);
      }
    }
  }

  function handleRequestStatusChanged() {
    setListVersion((current) => current + 1);
    onDashboardRefresh();
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearchQuery(searchInput.trim());
      setPage(1);
    }, 300);

    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    void loadOpenRequests(searchQuery, page, pageSize);
  }, [searchQuery, page, pageSize, dashboard.open_count, listVersion]);

  const emptyMessage = searchQuery.trim()
    ? "No open requests match your search."
    : "No open requests yet. Create the first one.";

  return (
    <section className="dashboard">
      <section className="request-summary-card request-summary-card-compact dashboard-summary-card">
        <div className="request-summary-compact-row">
          <div className="request-summary-compact-title">
            <h2>{REQUEST_DASHBOARD_PAGE_TITLE}</h2>
          </div>
        </div>
        <div className="request-summary-compact-meta">
          <span>
            {dashboard.open_count} open requests · {formatPipelineValueSubtitle(dashboard.total_pipeline_value)}
          </span>
        </div>

        <div className="stats-grid dashboard-stats-grid">
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
      </section>

      <section className="card open-requests-table-card dashboard-open-requests-card">
        <header className="open-requests-table-card-header">
          <div className="open-requests-table-card-header-main">
            <div className="open-requests-table-card-title-group">
              <h3>Open Requests</h3>
              <span className="open-requests-table-card-count" aria-label={`${dashboard.open_count} open requests`}>
                {dashboard.open_count}
              </span>
            </div>
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
                        <td className="open-requests-next-task-cell">
                          {request.next_open_task ? (
                            <>
                              <div className="open-requests-next-task-badge-wrap">
                                <span
                                  className={`next-task-badge ${getNextTaskBadgeClass(request.next_open_task.task_key)}`}
                                >
                                  {request.next_open_task.title}
                                </span>
                              </div>
                              <div className="meta open-requests-next-task-workflow">
                                {request.next_open_task.workflow_name} workflow
                              </div>
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
                          <OpenRequestQuickActions
                            request={request}
                            onView={() => onOpenRequest(request.id)}
                            onStatusChanged={handleRequestStatusChanged}
                            onError={setOpenRequestsError}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <ReportPagination
                page={page}
                total={total}
                totalPages={totalPages}
                pageSize={pageSize}
                loading={openRequestsLoading}
                summaryLabel={searchQuery.trim() ? "matching open requests" : "open requests"}
                onPageChange={setPage}
                onPageSizeChange={(size) => {
                  setPageSize(size);
                  setPage(1);
                }}
              />
            </>
          )}
        </div>
      </section>

      {openRequestsError ? <p className="status error">{openRequestsError}</p> : null}
    </section>
  );
}
