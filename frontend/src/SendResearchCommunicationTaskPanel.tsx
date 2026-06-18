import { useEffect, useMemo, useState } from "react";
import { fetchCommunication, updateCommunication } from "./api";
import {
  COMMUNICATION_STATUS_SENT,
  COMMUNICATION_TYPE_RESEARCH_PROPOSAL,
} from "./formOptions";
import type { RequestCommunication, RequestCommunicationSummary } from "./types";
import ResearchCommunicationBodyPreview from "./ResearchCommunicationBodyPreview";
import { copyCommunicationBodyToClipboard, copyTextToClipboard } from "./utils";
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
  const [markingSent, setMarkingSent] = useState(false);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);

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
    setCopyMessage(null);
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
      setCopyMessage("Message body copied to clipboard.");
    } catch {
      onError("Unable to copy message body.");
    }
  }

  async function handleCopy(label: string, value: string) {
    try {
      await copyTextToClipboard(value);
      setCopyMessage(`${label} copied to clipboard.`);
    } catch {
      onError(`Unable to copy ${label.toLowerCase()}.`);
    }
  }

  async function handleMarkSent() {
    if (!loadedCommunication || loadedCommunication.status === COMMUNICATION_STATUS_SENT) {
      return;
    }

    setMarkingSent(true);
    onError("");
    try {
      await updateCommunication(requestId, loadedCommunication.id, {
        communication_type: loadedCommunication.communication_type,
        subject: loadedCommunication.subject,
        body: loadedCommunication.body,
        request_workflow_id: loadedCommunication.request_workflow_id,
        status: COMMUNICATION_STATUS_SENT,
      });
      setLoadedCommunication({ ...loadedCommunication, status: COMMUNICATION_STATUS_SENT });
      await onChanged();
    } catch (updateError) {
      onError(updateError instanceof Error ? updateError.message : "Unable to mark communication as sent.");
    } finally {
      setMarkingSent(false);
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
          disabled={disabled || loadingCommunication}
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
            <div className="send-research-communication-copy-row">
              <input id="send-research-subject" type="text" readOnly value={loadedCommunication.subject} />
              <button
                type="button"
                className="modal-secondary"
                disabled={disabled}
                onClick={() => void handleCopy("Subject", loadedCommunication.subject)}
              >
                Copy subject
              </button>
            </div>
          </div>

          <div className="send-research-communication-field">
            <label htmlFor="send-research-body">Message preview</label>
            <div className="send-research-communication-copy-row send-research-communication-copy-row--stacked">
              <ResearchCommunicationBodyPreview body={loadedCommunication.body} id="send-research-body" />
              <button
                type="button"
                className="modal-secondary"
                disabled={disabled}
                onClick={() => void handleCopyBody()}
              >
                Copy formatted body
              </button>
            </div>
          </div>

          {copyMessage ? <p className="status success workflow-task-upload-success">{copyMessage}</p> : null}

          {!disabled && loadedCommunication.status !== COMMUNICATION_STATUS_SENT ? (
            <button type="button" disabled={markingSent} onClick={() => void handleMarkSent()}>
              {markingSent ? "Updating..." : "Mark communication as sent"}
            </button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
