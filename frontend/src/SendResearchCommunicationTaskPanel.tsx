import { useEffect, useMemo, useState } from "react";
import { fetchCommunication, sendResearchCommunicationViaSailsPipeline } from "./api";
import { COMMUNICATION_STATUS_SENT, COMMUNICATION_TYPE_RESEARCH_PROPOSAL } from "./formOptions";
import type { RequestCommunication, RequestCommunicationSummary } from "./types";
import ResearchCommunicationBodyPreview from "./ResearchCommunicationBodyPreview";
import { copyCommunicationBodyToClipboard } from "./utils";
import { communicationStatusClass } from "./workflowForm";

type SendResearchCommunicationTaskPanelProps = {
  requestId: number;
  communications: RequestCommunicationSummary[];
  disabled: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
};

export default function SendResearchCommunicationTaskPanel({
  requestId,
  communications,
  disabled,
  onChanged,
  onError,
}: SendResearchCommunicationTaskPanelProps) {
  const proposalCommunications = useMemo(
    () =>
      communications.filter(
        (communication) => communication.communication_type === COMMUNICATION_TYPE_RESEARCH_PROPOSAL,
      ),
    [communications],
  );

  const [selectedCommunicationId, setSelectedCommunicationId] = useState<number | "">("");
  const [loadedCommunication, setLoadedCommunication] = useState<RequestCommunication | null>(null);
  const [loadingCommunication, setLoadingCommunication] = useState(false);
  const [sending, setSending] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  useEffect(() => {
    if (proposalCommunications.length === 0) {
      setSelectedCommunicationId("");
      setLoadedCommunication(null);
      return;
    }

    setSelectedCommunicationId((current) => {
      if (typeof current === "number" && proposalCommunications.some((entry) => entry.id === current)) {
        return current;
      }
      return proposalCommunications[0].id;
    });
  }, [proposalCommunications]);

  useEffect(() => {
    if (typeof selectedCommunicationId !== "number") {
      setLoadedCommunication(null);
      return;
    }

    let cancelled = false;
    setLoadingCommunication(true);
    setStatusMessage(null);
    onError("");

    fetchCommunication(requestId, selectedCommunicationId)
      .then((communication) => {
        if (!cancelled) {
          setLoadedCommunication(communication);
        }
      })
      .catch((loadError) => {
        if (!cancelled) {
          setLoadedCommunication(null);
          onError(loadError instanceof Error ? loadError.message : "Unable to load communication.");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingCommunication(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [requestId, selectedCommunicationId]);

  const selectedSummary =
    typeof selectedCommunicationId === "number"
      ? proposalCommunications.find((communication) => communication.id === selectedCommunicationId) ?? null
      : null;

  async function handleCopyBody() {
    if (!loadedCommunication) {
      return;
    }

    try {
      await copyCommunicationBodyToClipboard(loadedCommunication.body);
      setStatusMessage("Message body copied to clipboard.");
    } catch {
      onError("Unable to copy message body.");
    }
  }

  async function handleSendViaSailsPipeline() {
    if (!loadedCommunication || loadedCommunication.status === COMMUNICATION_STATUS_SENT) {
      return;
    }

    setSending(true);
    onError("");
    setStatusMessage(null);
    try {
      const result = await sendResearchCommunicationViaSailsPipeline(requestId, loadedCommunication.id);
      setLoadedCommunication(result.communication);
      setStatusMessage("Email sent via SailsPipeline. Check Mailpit to confirm delivery.");
      await onChanged();
    } catch (sendError) {
      onError(sendError instanceof Error ? sendError.message : "Unable to send communication via SailsPipeline.");
    } finally {
      setSending(false);
    }
  }

  if (proposalCommunications.length === 0) {
    return (
      <div className="send-research-communication-task-panel">
        <p className="status error">
          No cruise proposal communications were found. Complete the Research workflow draft step first.
        </p>
      </div>
    );
  }

  return (
    <div className="send-research-communication-task-panel">
      <label>
        Cruise proposal communication
        <select
          value={selectedCommunicationId}
          disabled={disabled || loadingCommunication || sending}
          onChange={(event) => {
            const nextValue = event.target.value;
            setSelectedCommunicationId(nextValue ? Number(nextValue) : "");
          }}
        >
          {proposalCommunications.map((communication) => (
            <option key={communication.id} value={communication.id}>
              {communication.subject} ({communication.status})
            </option>
          ))}
        </select>
      </label>

      {selectedSummary ? (
        <p className="meta">
          Status:{" "}
          <span className={`communication-status ${communicationStatusClass(selectedSummary.status)}`}>
            {selectedSummary.status}
          </span>
        </p>
      ) : null}

      {loadingCommunication ? <p className="meta">Loading communication...</p> : null}

      {loadedCommunication ? (
        <div className="send-research-communication-preview">
          <div className="send-research-communication-field">
            <label htmlFor="send-research-subject">Subject</label>
            <input id="send-research-subject" type="text" readOnly value={loadedCommunication.subject} />
          </div>

          <div className="send-research-communication-field">
            <label htmlFor="send-research-body">Message preview</label>
            <ResearchCommunicationBodyPreview body={loadedCommunication.body} id="send-research-body" />
          </div>

          {!disabled && loadedCommunication.status !== COMMUNICATION_STATUS_SENT ? (
            <div className="send-research-communication-action-row">
              <button
                type="button"
                className="modal-secondary"
                disabled={sending}
                onClick={() => void handleCopyBody()}
              >
                Copy formatted body
              </button>
              <button
                type="button"
                className="modal-primary"
                disabled={sending}
                onClick={() => void handleSendViaSailsPipeline()}
              >
                {sending ? "Sending..." : "Send via SailsPipeline"}
              </button>
            </div>
          ) : null}

          {statusMessage ? <p className="status success workflow-task-upload-success">{statusMessage}</p> : null}
        </div>
      ) : null}
    </div>
  );
}
