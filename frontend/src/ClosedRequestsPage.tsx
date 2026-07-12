import { formatCruiseLines } from "./CruiseLineMultiSelect";
import { PRIMARY_CLOSE_REASON } from "./formOptions";
import { useEffect, useState } from "react";
import { fetchClosedRequests, reopenRequest } from "./api";
import { canReopenClosedRequest, closeReasonClassName } from "./closeReasonUtils";
import IconTooltip from "./IconTooltip";
import ReportPagination from "./ReportPagination";
import { DEFAULT_PAGE_SIZE, type PageSizeOption } from "./pagination";
import type { TravelRequest } from "./types";
import { formatDestinationSummary, formatDate, formatTimestamp } from "./utils";
import ReopenIcon from "./ReopenIcon";
import ViewIcon from "./ViewIcon";

const CLOSED_REQUESTS_HEADER_TOOLTIP = `${PRIMARY_CLOSE_REASON} trips stay closed; other requests can be reopened from the table.`;

type ClosedRequestsPageProps = {
  closedCount: number;
  onOpenRequest: (requestId: number) => void;
  onReopened: () => void;
};

export default function ClosedRequestsPage({
  closedCount,
  onOpenRequest,
  onReopened,
}: ClosedRequestsPageProps) {
  const [requests, setRequests] = useState<TravelRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reopeningId, setReopeningId] = useState<number | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<PageSizeOption>(DEFAULT_PAGE_SIZE);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  async function loadClosedRequests(activeSearch: string, activePage: number, activePageSize: number) {
    setLoading(true);
    setError("");
    try {
      const response = await fetchClosedRequests({
        q: activeSearch,
        page: activePage,
        pageSize: activePageSize,
      });
      setRequests(response.items);
      setTotal(response.total);
      setTotalPages(response.total_pages);
      if (response.total_pages > 0 && activePage > response.total_pages) {
        setPage(response.total_pages);
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load closed requests.");
    } finally {
      setLoading(false);
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
    void loadClosedRequests(searchQuery, page, pageSize);
  }, [searchQuery, page, pageSize]);

  async function handleReopen(request: TravelRequest) {
    if (!canReopenClosedRequest(request)) {
      return;
    }

    setReopeningId(request.id);
    setError("");
    try {
      await reopenRequest(request.id);
      await loadClosedRequests(searchQuery, page, pageSize);
      onReopened();
    } catch (reopenError) {
      setError(reopenError instanceof Error ? reopenError.message : "Unable to reopen request.");
    } finally {
      setReopeningId(null);
    }
  }

  const emptyMessage = searchQuery.trim()
    ? "No closed requests match your search."
    : "No closed requests yet.";

  return (
    <section className="closed-requests-page">
      <section className="card open-requests-table-card closed-requests-table-card">
        <header className="open-requests-table-card-header closed-requests-table-card-header">
          <IconTooltip label={CLOSED_REQUESTS_HEADER_TOOLTIP} placement="below" wide align="start">
            <h3 tabIndex={0}>Closed Requests</h3>
          </IconTooltip>
          <span
            className="open-requests-table-card-count closed-requests-table-card-count"
            aria-label={`${closedCount} closed requests`}
          >
            {closedCount}
          </span>
        </header>
        <div className="open-requests-table-card-body">
          <div className="closed-requests-table-toolbar">
            <label className="closed-requests-search">
              Search closed requests
              <input
                type="search"
                value={searchInput}
                placeholder="Client, trip, close reason, cruise line, or agent"
                onChange={(event) => setSearchInput(event.target.value)}
              />
            </label>
          </div>

          {loading ? (
            <p>Loading closed requests...</p>
          ) : requests.length === 0 ? (
            <p>{emptyMessage}</p>
          ) : (
            <>
              <div className="open-requests-table-wrap">
                <table className="open-requests-table">
                  <thead>
                    <tr>
                      <th scope="col">Client</th>
                      <th scope="col">Trip</th>
                      <th scope="col">Close reason</th>
                      <th scope="col">Closed</th>
                      <th scope="col">
                        <span className="sr-only">Actions</span>
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {requests.map((request) => {
                      const canReopen = canReopenClosedRequest(request);
                      const isReopening = reopeningId === request.id;
                      const clientName = `${request.first_name} ${request.last_name}`;

                      return (
                        <tr key={request.id}>
                          <td>
                            <strong>{clientName}</strong>
                            <div className="meta">{request.email}</div>
                          </td>
                          <td>
                            <div>{formatDestinationSummary(request)}</div>
                            <div className="meta">
                              {formatCruiseLines(request.cruise_lines)} · {formatDate(request.departure_date)} to{" "}
                              {formatDate(request.return_date)}
                            </div>
                          </td>
                          <td>
                            {request.close_reason ? (
                              <span className={closeReasonClassName(request.close_reason)}>{request.close_reason}</span>
                            ) : (
                              <span className="meta">—</span>
                            )}
                          </td>
                          <td className="meta">
                            {request.updated_by.username} · {formatTimestamp(request.updated_at)}
                          </td>
                          <td className="dashboard-table-actions-cell">
                            <div className="dashboard-table-actions">
                              <IconTooltip label={`View request for ${clientName}`}>
                                <button
                                  type="button"
                                  className="icon-button"
                                  aria-label={`View request for ${clientName}`}
                                  onClick={() => onOpenRequest(request.id)}
                                >
                                  <ViewIcon />
                                </button>
                              </IconTooltip>
                              <IconTooltip
                                label={
                                  canReopen
                                    ? isReopening
                                      ? "Reopening request..."
                                      : "Reopen request"
                                    : `${PRIMARY_CLOSE_REASON} trips cannot be reopened`
                                }
                              >
                                <button
                                  type="button"
                                  className="icon-button icon-button-reopen"
                                  aria-label={
                                    canReopen
                                      ? `Reopen request for ${clientName}`
                                      : `Cannot reopen request for ${clientName}`
                                  }
                                  disabled={!canReopen || isReopening}
                                  onClick={() => void handleReopen(request)}
                                >
                                  <ReopenIcon />
                                </button>
                              </IconTooltip>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <ReportPagination
                page={page}
                total={total}
                totalPages={totalPages}
                pageSize={pageSize}
                loading={loading}
                summaryLabel={searchQuery.trim() ? "matching closed requests" : "closed requests"}
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

      {error ? <p className="status error">{error}</p> : null}
    </section>
  );
}
