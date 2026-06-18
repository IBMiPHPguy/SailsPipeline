import { formatCruiseLines } from "./CruiseLineMultiSelect";
import type { DashboardNextOpenTask, TravelRequest, UserAudit } from "./types";
import { formatDestinationSummary, formatDate, formatTimestamp } from "./utils";

type RequestSummaryProps = {
  request: TravelRequest;
  nextOpenTask?: DashboardNextOpenTask | null;
  lastWorkedAt?: string;
  lastWorkedBy?: UserAudit;
  isStale?: boolean;
};

export default function RequestSummary({
  request,
  nextOpenTask,
  lastWorkedAt,
  lastWorkedBy,
  isStale,
}: RequestSummaryProps) {
  return (
    <div className="request-summary">
      <strong>
        {request.first_name} {request.last_name} · {formatDestinationSummary(request)}
      </strong>
      <div className="meta">
        {formatCruiseLines(request.cruise_lines)} · {formatDate(request.departure_date)} to {formatDate(request.return_date)}
      </div>
      {nextOpenTask !== undefined ? (
        nextOpenTask ? (
          <div className="request-summary-next-task">
            <span className="request-summary-next-task-label">Next task</span>
            <span className="request-summary-next-task-title">{nextOpenTask.title}</span>
            <span className="request-summary-next-task-workflow">{nextOpenTask.workflow_name} workflow</span>
          </div>
        ) : (
          <div className="request-summary-next-task request-summary-next-task-empty">
            <span className="request-summary-next-task-label">Next task</span>
            <span className="request-summary-next-task-title">No open workflow task</span>
          </div>
        )
      ) : null}
      {lastWorkedAt && lastWorkedBy ? (
        <div className="request-summary-footer">
          <span className="meta">
            Last worked by {lastWorkedBy.username} · {formatTimestamp(lastWorkedAt)}
          </span>
          {isStale ? <span className="stale-badge">Stale</span> : null}
        </div>
      ) : null}
    </div>
  );
}