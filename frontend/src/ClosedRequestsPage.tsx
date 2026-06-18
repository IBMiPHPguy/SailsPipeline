import { formatCruiseLines } from "./CruiseLineMultiSelect";
import { useEffect, useState } from "react";
import { fetchClosedRequests, reopenRequest } from "./api";
import { canReopenClosedRequest, closeReasonClassName } from "./closeReasonUtils";
import type { TravelRequest } from "./types";
import { formatDestinationSummary, formatDate, formatTimestamp } from "./utils";

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

  async function loadClosedRequests() {
    setLoading(true);
    setError("");
    try {
      setRequests(await fetchClosedRequests());
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load closed requests.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadClosedRequests();
  }, []);

  async function handleReopen(request: TravelRequest) {
    if (!canReopenClosedRequest(request)) {
      return;
    }

    setReopeningId(request.id);
    setError("");
    try {
      await reopenRequest(request.id);
      await loadClosedRequests();
      onReopened();
    } catch (reopenError) {
      setError(reopenError instanceof Error ? reopenError.message : "Unable to reopen request.");
    } finally {
      setReopeningId(null);
    }
  }

  return (
    <section className="closed-requests-page">
      <div className="dashboard-header">
        <div>
          <h2>Closed Requests</h2>
          <p>
            {closedCount} closed request{closedCount === 1 ? "" : "s"}. Purchased trips stay closed; other requests
            can be reopened.
          </p>
        </div>
      </div>

      {loading ? (
        <section className="card">
          <p>Loading closed requests...</p>
        </section>
      ) : requests.length === 0 ? (
        <section className="card">
          <p>No closed requests yet.</p>
        </section>
      ) : (
        <section className="card closed-requests-table-card">
          <div className="closed-requests-table-wrap">
            <table className="closed-requests-table">
              <thead>
                <tr>
                  <th scope="col">Client</th>
                  <th scope="col">Trip</th>
                  <th scope="col">Close reason</th>
                  <th scope="col">Closed</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((request) => {
                  const canReopen = canReopenClosedRequest(request);
                  return (
                    <tr key={request.id}>
                      <td>
                        <strong>
                          {request.first_name} {request.last_name}
                        </strong>
                        <div className="meta">{request.email}</div>
                      </td>
                      <td>
                        <div>{formatDestinationSummary(request)}</div>
                        <div className="meta">
                          {formatCruiseLines(request.cruise_lines)} · {formatDate(request.departure_date)} to {formatDate(request.return_date)}
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
                      <td>
                        <div className="closed-requests-actions">
                          <button type="button" className="modal-secondary" onClick={() => onOpenRequest(request.id)}>
                            View
                          </button>
                          {canReopen ? (
                            <button
                              type="button"
                              disabled={reopeningId === request.id}
                              onClick={() => void handleReopen(request)}
                            >
                              {reopeningId === request.id ? "Reopening..." : "Reopen"}
                            </button>
                          ) : (
                            <span className="meta closed-requests-no-reopen">Cannot reopen</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {error ? <p className="status error">{error}</p> : null}
    </section>
  );
}
