import AiSummaryIcon from "./AiSummaryIcon";
import IconTooltip from "./IconTooltip";
import ViewIcon from "./ViewIcon";
import type { CommunicationRecord } from "./communicationAi";
import { COMMUNICATION_STATUS_DRAFT, COMMUNICATION_TYPE_INBOUND_EMAIL } from "./formOptions";
import { formatTimestamp } from "./utils";

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
    </svg>
  );
}

type CommunicationRecordsTableProps = {
  records: CommunicationRecord[];
  emptyMessage: string;
  disabled: boolean;
  deletingEmailId?: number | null;
  onView: (record: CommunicationRecord) => void;
  onDeleteEmail?: (record: CommunicationRecord) => void;
  onOpenAiSummary: (record: CommunicationRecord) => void;
};

export default function CommunicationRecordsTable({
  records,
  emptyMessage,
  deletingEmailId = null,
  onView,
  onDeleteEmail,
  onOpenAiSummary,
}: CommunicationRecordsTableProps) {
  if (records.length === 0) {
    return <p className="meta communication-records-empty">{emptyMessage}</p>;
  }

  return (
    <div className="communication-records-table-wrap">
      <table className="communication-records-table">
        <thead>
          <tr>
            <th scope="col">File name</th>
            <th scope="col">Date / Time</th>
            <th scope="col">Uploaded By</th>
            <th scope="col">AI Status</th>
            <th scope="col" className="communication-records-actions-col">
              Actions
            </th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => {
            const canDeleteEmail =
              record.kind === "email" &&
              (record.communication?.status === COMMUNICATION_STATUS_DRAFT ||
                record.communication?.communication_type === COMMUNICATION_TYPE_INBOUND_EMAIL) &&
              onDeleteEmail;

            return (
              <tr key={`${record.kind}-${record.id}`}>
                <td>
                  <button
                    type="button"
                    className="link-button communication-records-subject"
                    title={record.subject}
                    onClick={() => onView(record)}
                  >
                    <span className="communication-records-subject-text">{record.subject}</span>
                  </button>
                </td>
                <td className="communication-records-meta">{formatTimestamp(record.dateTime)}</td>
                <td className="communication-records-meta">{record.uploadedBy}</td>
                <td>
                  {record.aiNoteId ? (
                    <span className="communication-ai-status communication-ai-status--analyzed">✨ Analyzed</span>
                  ) : (
                    <span className="communication-ai-status communication-ai-status--pending">Pending</span>
                  )}
                </td>
                <td className="communication-records-actions-col">
                  <div className="item-icon-actions communication-records-actions">
                    <IconTooltip label={record.aiNoteId ? "AI Summary" : "No AI summary yet"}>
                      <button
                        type="button"
                        className="icon-button icon-button-ai"
                        disabled={!record.aiNoteId}
                        aria-label={`AI Summary for ${record.subject}`}
                        onClick={() => onOpenAiSummary(record)}
                      >
                        <AiSummaryIcon />
                      </button>
                    </IconTooltip>
                    <IconTooltip label={`View ${record.subject}`}>
                      <button
                        type="button"
                        className="icon-button"
                        aria-label={`View ${record.subject}`}
                        onClick={() => onView(record)}
                      >
                        <ViewIcon />
                      </button>
                    </IconTooltip>
                    {canDeleteEmail ? (
                      <IconTooltip label="Delete draft">
                        <button
                          type="button"
                          className="icon-button icon-button-danger"
                          disabled={deletingEmailId === record.id}
                          aria-label={`Delete ${record.subject}`}
                          onClick={() => onDeleteEmail(record)}
                        >
                          <TrashIcon />
                        </button>
                      </IconTooltip>
                    ) : null}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
