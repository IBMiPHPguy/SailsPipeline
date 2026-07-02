import { useCallback, useEffect, useState } from "react";
import { fetchTermsStatusForRequest, sendMasterTermsEmail } from "./termsApi";
import type { TermsRequestStatusResponse } from "./termsApi";
import { formatDate } from "./utils";
import "./terms-portal.css";

type MasterTermsTaskPanelProps = {
  requestId: number;
  disabled: boolean;
  isDone: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
};

function formatAcceptedAt(value: string | null | undefined): string {
  if (!value) {
    return "on file";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return formatDate(parsed.toISOString().slice(0, 10));
}

export default function MasterTermsTaskPanel({
  requestId,
  disabled,
  isDone,
  onChanged,
  onError,
}: MasterTermsTaskPanelProps) {
  const readOnly = disabled || isDone;
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<TermsRequestStatusResponse | null>(null);
  const [sending, setSending] = useState(false);
  const [sendSuccess, setSendSuccess] = useState("");

  const refreshStatus = useCallback(async () => {
    setLoading(true);
    onError("");
    try {
      const nextStatus = await fetchTermsStatusForRequest(requestId);
      setStatus(nextStatus);
      if (nextStatus.task_auto_completed) {
        await onChanged();
      }
      return nextStatus;
    } catch (loadError) {
      onError(loadError instanceof Error ? loadError.message : "Unable to load Master Terms status.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [onChanged, onError, requestId]);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  async function handleSendEmail() {
    if (readOnly || sending) {
      return;
    }

    setSending(true);
    setSendSuccess("");
    onError("");
    try {
      const result = await sendMasterTermsEmail(requestId);
      setSendSuccess(result.message);
      await refreshStatus();
    } catch (sendError) {
      onError(sendError instanceof Error ? sendError.message : "Unable to send Master Terms review email.");
    } finally {
      setSending(false);
    }
  }

  const onFile = Boolean(status?.on_file || isDone);

  return (
    <section className="master-terms-task-card">
      <header className="master-terms-task-header">
        <h3>Master Terms &amp; Conditions</h3>
      </header>
      <div className="master-terms-task-body">
        {loading ? <p className="muted">Checking client Master T&amp;C status…</p> : null}

        {!loading && onFile ? (
          <>
            <p className="master-terms-on-file">
              Master T&amp;C on File (Accepted {formatAcceptedAt(status?.accepted_at)})
            </p>
            <p className="muted workflow-task-guidance">
              {isDone
                ? "This step is complete. The client's Master Terms acceptance is on file for all future bookings."
                : "Client acceptance recorded. This task will update to Done automatically."}
            </p>
          </>
        ) : null}

        {!loading && status && !onFile ? (
          <>
            <p className="workflow-task-guidance">
              No Master Terms &amp; Conditions are on file for this client. Send a secure review email with a 48-hour
              clickwrap link.
            </p>
            {!readOnly ? (
              <button type="button" onClick={() => void handleSendEmail()} disabled={sending}>
                {sending ? "Sending…" : "Send Master T&C Review Email"}
              </button>
            ) : null}
            {sendSuccess ? <p className="master-terms-send-success">{sendSuccess}</p> : null}
            {sendSuccess ? (
              <p className="muted workflow-task-guidance" style={{ marginTop: "0.75rem" }}>
                Waiting for the client to accept via the secure portal. This task will mark Done automatically when they
                submit acceptance — no need to refresh manually.
              </p>
            ) : null}
          </>
        ) : null}
      </div>
    </section>
  );
}
