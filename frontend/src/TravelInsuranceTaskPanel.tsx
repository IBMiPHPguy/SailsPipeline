import { useCallback, useEffect, useMemo, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
import { updateQuotedInsurance, updateTask } from "./api";
import CheckIcon from "./CheckIcon";
import ClientModal from "./ClientModal";
import IconTooltip from "./IconTooltip";
import RejectIcon from "./RejectIcon";
import {
  QUOTED_INSURANCE_STATUS_ACCEPTED,
  QUOTED_INSURANCE_STATUS_DECLINED,
  QUOTED_INSURANCE_STATUS_PROPOSED,
  TASK_STATUS_DONE,
} from "./formOptions";
import {
  clearExpiredAnnualInsurance,
  fetchInsuranceStatusForRequest,
  sendInsuranceWaiverEmail,
  updateAnnualInsurance,
  type AnnualInsuranceUpdate,
  type InsuranceRequestStatusResponse,
} from "./insuranceApi";
import { formatMoney, quotedInsuranceStatusClass, quotedInsuranceToForm } from "./quotedInsuranceForm";
import { QuoteMailedBadge } from "./QuoteMailedToggle";
import type { QuotedInsurance, RequestPassenger, RequestTask } from "./types";
import { formatDate, formatTimestamp, formatWaiverTimeRemaining } from "./utils";
import "./insurance-portal.css";

type TravelInsuranceTaskPanelProps = {
  requestId: number;
  passengers: RequestPassenger[];
  quotes: QuotedInsurance[];
  task: RequestTask;
  taskId: string;
  disabled: boolean;
  isDone: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  onSaved: () => void;
  onNavigateToQuotedInsurance?: () => void;
  setPanelFooterAction: Dispatch<SetStateAction<ReactNode>>;
};

type AnnualDraft = {
  has_annual_insurance: boolean;
  annual_insurance_expires_at: string;
  annual_insurance_policy_number: string;
};

function primaryPassenger(passengers: RequestPassenger[]): RequestPassenger | null {
  if (!passengers.length) {
    return null;
  }
  return passengers.find((passenger) => passenger.is_primary) ?? passengers[0];
}

function toAnnualDraftFromStatus(status: InsuranceRequestStatusResponse): AnnualDraft {
  return {
    has_annual_insurance: status.has_annual_insurance,
    annual_insurance_expires_at: status.annual_insurance_expires_at ?? "",
    annual_insurance_policy_number: status.annual_insurance_policy_number ?? "",
  };
}

function readAnnualCheckConfirmed(result: Record<string, unknown> | null | undefined): boolean {
  return result?.annual_insurance_check_confirmed === true;
}

function annualDraftMatchesStatus(
  draft: AnnualDraft,
  status: InsuranceRequestStatusResponse | null,
): boolean {
  if (!status) {
    return false;
  }
  return (
    draft.annual_insurance_policy_number.trim() === (status.annual_insurance_policy_number ?? "").trim() &&
    draft.annual_insurance_expires_at.trim() === (status.annual_insurance_expires_at ?? "").trim()
  );
}

function isExpirationDateInFuture(dateStr: string): boolean {
  const trimmed = dateStr.trim();
  if (!trimmed) {
    return false;
  }
  const expiration = new Date(`${trimmed}T12:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  expiration.setHours(0, 0, 0, 0);
  return expiration > today;
}

export default function TravelInsuranceTaskPanel({
  requestId,
  passengers,
  quotes,
  task,
  taskId,
  disabled,
  isDone,
  onChanged,
  onError,
  onSaved,
  onNavigateToQuotedInsurance,
  setPanelFooterAction,
}: TravelInsuranceTaskPanelProps) {
  const readOnly = disabled || isDone;
  const primary = useMemo(() => primaryPassenger(passengers), [passengers]);

  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<InsuranceRequestStatusResponse | null>(null);
  const [annualDraft, setAnnualDraft] = useState<AnnualDraft>({
    has_annual_insurance: false,
    annual_insurance_expires_at: "",
    annual_insurance_policy_number: "",
  });
  const [saving, setSaving] = useState(false);
  const [clearingAnnual, setClearingAnnual] = useState(false);
  const [sendingWaiver, setSendingWaiver] = useState(false);
  const [waiverSentMessage, setWaiverSentMessage] = useState("");
  const [updatingQuoteId, setUpdatingQuoteId] = useState<number | null>(null);
  const [waiverClockMs, setWaiverClockMs] = useState(() => Date.now());
  const [annualCheckConfirmed, setAnnualCheckConfirmed] = useState(() =>
    readAnnualCheckConfirmed(task.result),
  );
  const [confirmingAnnualCheck, setConfirmingAnnualCheck] = useState(false);
  const [annualInsuranceModalOpen, setAnnualInsuranceModalOpen] = useState(false);

  const registryClientId =
    status?.client_registry_passenger_id ?? primary?.passenger_id ?? null;

  useEffect(() => {
    setAnnualCheckConfirmed(readAnnualCheckConfirmed(task.result));
  }, [task.id, task.result]);

  const refreshStatus = useCallback(async () => {
    setLoading(true);
    onError("");
    try {
      const nextStatus = await fetchInsuranceStatusForRequest(requestId);
      setStatus(nextStatus);
      return nextStatus;
    } catch (loadError) {
      onError(loadError instanceof Error ? loadError.message : "Unable to load insurance status.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [onError, requestId]);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  const waiverPending = status?.waiver_request_status === "pending";
  const waiverExpiredUnanswered = status?.waiver_request_status === "expired" && !status?.waiver_signed;
  const waiverTimeRemaining =
    waiverPending && status?.waiver_expires_at
      ? formatWaiverTimeRemaining(status.waiver_expires_at, new Date(waiverClockMs))
      : null;

  useEffect(() => {
    if (!waiverPending || !status?.waiver_expires_at) {
      return;
    }

    const intervalId = window.setInterval(() => {
      setWaiverClockMs(Date.now());
    }, 60000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [status?.waiver_expires_at, waiverPending]);

  useEffect(() => {
    if (waiverPending && waiverTimeRemaining === "expired") {
      void refreshStatus();
    }
  }, [refreshStatus, waiverPending, waiverTimeRemaining]);

  const statusReady = !loading && status !== null;
  const clientHasAnnualInsurance = Boolean(status?.has_annual_insurance);
  const annualIsValid = Boolean(status?.annual_insurance_is_valid);
  const annualIsExpired = Boolean(status?.annual_insurance_is_expired);
  const annualDraftDirty = statusReady && clientHasAnnualInsurance && !annualDraftMatchesStatus(annualDraft, status);
  const clientName =
    status?.client_name?.trim() ||
    (primary ? `${primary.first_name} ${primary.last_name}`.trim() : "This client");
  const showAnnualCheckGate =
    statusReady && !clientHasAnnualInsurance && !annualCheckConfirmed && !readOnly;
  const showPerTripTrack =
    statusReady && !clientHasAnnualInsurance && (annualCheckConfirmed || readOnly);
  const noQuotesYet = quotes.length === 0;
  const hasProposedQuotes = quotes.some((quote) => quote.status === QUOTED_INSURANCE_STATUS_PROPOSED);
  const hasAcceptedQuote = quotes.some((quote) => quote.status === QUOTED_INSURANCE_STATUS_ACCEPTED);

  const showAnnualFieldsReadOnly =
    clientHasAnnualInsurance && (readOnly || annualIsValid);
  const showAnnualUpdateActions =
    !readOnly && clientHasAnnualInsurance && !annualIsValid;
  const showAnnualCompleteButton =
    !readOnly && clientHasAnnualInsurance && annualIsValid && !annualDraftDirty;
  const showPerTripPreferenceStep =
    showPerTripTrack && noQuotesYet && !status?.waiver_signed && !waiverPending;
  const showPerTripAllDeclinedStep =
    showPerTripTrack &&
    !noQuotesYet &&
    Boolean(status?.all_quotes_declined) &&
    !status?.waiver_signed;
  const showSendWaiverButton =
    !readOnly && !status?.waiver_signed && !waiverPending && (showPerTripPreferenceStep || showPerTripAllDeclinedStep);
  const allQuotesDeclined =
    showPerTripTrack && !noQuotesYet && Boolean(status?.all_quotes_declined);
  const showWaiverStatusBanner =
    showPerTripTrack &&
    Boolean(status?.waiver_sent_at) &&
    (waiverPending || waiverExpiredUnanswered);
  const showPerTripCompleteButton =
    showPerTripTrack &&
    !showPerTripPreferenceStep &&
    !showPerTripAllDeclinedStep &&
    !hasProposedQuotes &&
    (hasAcceptedQuote || Boolean(status?.waiver_signed));

  const showTaskCompleteButton =
    !readOnly && statusReady && (showAnnualCompleteButton || showPerTripCompleteButton);
  const showPanelFooter =
    !readOnly &&
    statusReady &&
    (showAnnualCheckGate ||
      (clientHasAnnualInsurance && showAnnualUpdateActions) ||
      (showPerTripTrack && (showPerTripPreferenceStep || showPerTripAllDeclinedStep)));

  const canCompleteTask =
    Boolean(status?.can_complete_task) &&
    (!clientHasAnnualInsurance || (annualIsValid && !annualDraftDirty));

  const showComplianceLock =
    statusReady &&
    !showAnnualCheckGate &&
    !annualIsExpired &&
    !showWaiverStatusBanner &&
    status &&
    !canCompleteTask &&
    Boolean(status.completion_blocked_reason);

  async function handleConfirmAnnualCheck() {
    if (readOnly || confirmingAnnualCheck || clientHasAnnualInsurance) {
      return;
    }

    setConfirmingAnnualCheck(true);
    onError("");
    try {
      await updateTask(requestId, taskId, {
        result: {
          ...(task.result ?? {}),
          annual_insurance_check_confirmed: true,
          annual_insurance_check_result: "no_annual_on_file",
          annual_insurance_check_confirmed_at: new Date().toISOString(),
        },
      });
      setAnnualCheckConfirmed(true);
      await onChanged();
    } catch (confirmError) {
      onError(
        confirmError instanceof Error ? confirmError.message : "Unable to record annual insurance check.",
      );
    } finally {
      setConfirmingAnnualCheck(false);
    }
  }

  useEffect(() => {
    if (!status) {
      return;
    }
    setAnnualDraft(toAnnualDraftFromStatus(status));
  }, [status]);

  async function handleAnnualInsuranceSaved() {
    setAnnualInsuranceModalOpen(false);
    onError("");
    await refreshStatus();
    await onChanged();
  }

  async function handleUpdateAnnual() {
    if (readOnly || saving || !primary) {
      return;
    }

    const policyNumber = annualDraft.annual_insurance_policy_number.trim();
    const expiration = annualDraft.annual_insurance_expires_at.trim();
    if (!policyNumber || !expiration) {
      onError("Enter the policy number and expiration date.");
      return;
    }
    if (!isExpirationDateInFuture(expiration)) {
      onError(
        "The expiration date must be in the future. Enter a valid policy expiration or remove annual insurance to use per-trip coverage.",
      );
      return;
    }

    setSaving(true);
    onError("");
    try {
      const payload: AnnualInsuranceUpdate = {
        annual_insurance_expires_at: expiration,
        annual_insurance_policy_number: policyNumber,
      };
      const nextStatus = await updateAnnualInsurance(requestId, payload);
      setStatus(nextStatus);
      setAnnualDraft(toAnnualDraftFromStatus(nextStatus));
      await onChanged();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to update annual insurance.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRemoveAnnualInsurance() {
    if (readOnly || clearingAnnual || saving) {
      return;
    }

    setClearingAnnual(true);
    onError("");
    try {
      const nextStatus = await clearExpiredAnnualInsurance(requestId);
      setStatus(nextStatus);
      await updateTask(requestId, taskId, {
        result: {
          ...(task.result ?? {}),
          annual_insurance_check_confirmed: true,
          annual_insurance_check_result: "expired_annual_cleared",
          annual_insurance_check_confirmed_at: new Date().toISOString(),
        },
      });
      setAnnualCheckConfirmed(true);
      await onChanged();
    } catch (clearError) {
      onError(
        clearError instanceof Error ? clearError.message : "Unable to clear expired annual insurance.",
      );
    } finally {
      setClearingAnnual(false);
    }
  }

  async function handleQuoteStatusChange(quote: QuotedInsurance, nextStatus: string) {
    if (readOnly || updatingQuoteId !== null) {
      return;
    }

    setUpdatingQuoteId(quote.id);
    onError("");
    try {
      await updateQuotedInsurance(requestId, quote.id, {
        ...quotedInsuranceToForm(quote),
        status: nextStatus,
      });
      await onChanged();
      await refreshStatus();
    } catch (updateError) {
      onError(updateError instanceof Error ? updateError.message : "Unable to update insurance quote.");
    } finally {
      setUpdatingQuoteId(null);
    }
  }

  function handleAcceptQuote(quote: QuotedInsurance) {
    void handleQuoteStatusChange(quote, QUOTED_INSURANCE_STATUS_ACCEPTED);
  }

  function handleRejectQuote(quote: QuotedInsurance) {
    void handleQuoteStatusChange(quote, QUOTED_INSURANCE_STATUS_DECLINED);
  }

  function handleNavigateToQuotedInsurance() {
    onNavigateToQuotedInsurance?.();
    onSaved();
  }

  async function handleSendWaiver() {
    if (readOnly || sendingWaiver) {
      return;
    }

    setSendingWaiver(true);
    setWaiverSentMessage("");
    onError("");
    try {
      const result = await sendInsuranceWaiverEmail(requestId);
      setWaiverSentMessage(result.message);
      await refreshStatus();
    } catch (sendError) {
      onError(sendError instanceof Error ? sendError.message : "Unable to send insurance waiver email.");
    } finally {
      setSendingWaiver(false);
    }
  }

  const footerBusy =
    saving || clearingAnnual || confirmingAnnualCheck || sendingWaiver || updatingQuoteId !== null;

  async function handleCompleteTask() {
    if (readOnly || saving || clearingAnnual || !canCompleteTask) {
      return;
    }

    setSaving(true);
    onError("");
    try {
      await updateTask(requestId, taskId, { status: TASK_STATUS_DONE, is_completed: true });
      await onChanged();
      onSaved();
    } catch (completeError) {
      onError(completeError instanceof Error ? completeError.message : "Unable to complete insurance task.");
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    if (!showTaskCompleteButton) {
      setPanelFooterAction(null);
      return;
    }

    setPanelFooterAction(
      <button
        type="button"
        className="modal-primary"
        disabled={footerBusy || !canCompleteTask}
        onClick={() => void handleCompleteTask()}
      >
        {saving ? "Completing…" : "Complete task"}
      </button>,
    );

    return () => {
      setPanelFooterAction(null);
    };
  }, [
    canCompleteTask,
    footerBusy,
    saving,
    setPanelFooterAction,
    showTaskCompleteButton,
  ]);

  function handleClientWantsOptions() {
    handleNavigateToQuotedInsurance();
  }

  function handleClientDeclinesOptions() {
    void handleSendWaiver();
  }

  if (!primary) {
    return (
      <div className="workflow-task-guidance">
        <p>Add a primary passenger before validating travel insurance.</p>
      </div>
    );
  }

  return (
    <>
      <section className="travel-insurance-task-card">
        <header className="travel-insurance-task-header">
          <h3>Travel insurance validation</h3>
        </header>
        <div className="travel-insurance-task-body">
          {loading ? <p className="muted">Loading insurance verification status…</p> : null}

          {statusReady && clientHasAnnualInsurance ? (
            <>
              <p className="travel-insurance-track-label">Track 1 · Annual insurance</p>
              {annualIsValid && !annualDraftDirty ? (
                <p className="workflow-task-guidance">
                  This client has valid annual travel insurance on file
                  {status?.annual_insurance_expires_at
                    ? ` through ${formatDate(status.annual_insurance_expires_at)}`
                    : ""}
                  . You can complete this task.
                </p>
              ) : annualIsExpired ? (
                <p className="travel-insurance-compliance-lock">
                  Annual insurance expired
                  {status?.annual_insurance_expires_at
                    ? ` on ${formatDate(status.annual_insurance_expires_at)}`
                    : ""}
                  . Update the policy details or remove annual coverage to continue with per-trip insurance.
                </p>
              ) : (
                <p className="workflow-task-guidance">
                  This client has annual travel insurance on file. Confirm policy details before completing this
                  task.
                </p>
              )}
              {showAnnualFieldsReadOnly ? (
                <dl className="annual-insurance-readonly travel-insurance-annual-readonly">
                  <div>
                    <dt>Policy number</dt>
                    <dd>{status?.annual_insurance_policy_number?.trim() || "—"}</dd>
                  </div>
                  <div>
                    <dt>Expiration date</dt>
                    <dd>
                      {status?.annual_insurance_expires_at
                        ? formatDate(status.annual_insurance_expires_at)
                        : "—"}
                    </dd>
                  </div>
                </dl>
              ) : (
                <div className="field-row">
                  <label>
                    Policy number
                    <input
                      type="text"
                      disabled={readOnly || saving || clearingAnnual}
                      value={annualDraft.annual_insurance_policy_number}
                      onChange={(event) =>
                        setAnnualDraft((draft) => ({
                          ...draft,
                          annual_insurance_policy_number: event.target.value,
                        }))
                      }
                    />
                  </label>
                  <label>
                    Expiration date
                    <input
                      type="date"
                      disabled={readOnly || saving || clearingAnnual}
                      value={annualDraft.annual_insurance_expires_at}
                      onChange={(event) =>
                        setAnnualDraft((draft) => ({
                          ...draft,
                          annual_insurance_expires_at: event.target.value,
                        }))
                      }
                    />
                  </label>
                </div>
              )}
            </>
          ) : null}

          {showAnnualCheckGate ? (
            <>
              <p className="travel-insurance-track-label">Step 1 · Verify annual insurance status</p>
              <section className="travel-insurance-check-card">
                <p className="workflow-task-guidance">
                  Before reviewing per-trip insurance options, confirm whether{" "}
                  <strong>{clientName}</strong> maintains annual travel insurance on their client profile.
                </p>
                <dl className="travel-insurance-check-results">
                  <div>
                    <dt>Client profile check</dt>
                    <dd>
                      <span className="travel-insurance-check-badge travel-insurance-check-badge--none">
                        No annual insurance on file
                      </span>
                    </dd>
                  </div>
                  <div>
                    <dt>Policy number</dt>
                    <dd>—</dd>
                  </div>
                  <div>
                    <dt>Expiration date</dt>
                    <dd>—</dd>
                  </div>
                </dl>
                <p className="field-hint">
                  If this client maintains their own annual policy, use <strong>Add annual insurance</strong> to
                  update their client profile without leaving this task.
                </p>
              </section>
            </>
          ) : null}

          {showPerTripTrack ? (
            <>
              {!allQuotesDeclined ? (
                <p className="travel-insurance-track-label">Track 2 · Per-trip insurance</p>
              ) : null}
              <p className="workflow-task-guidance muted travel-insurance-per-trip-intro">
                No annual travel insurance is on file for this client. Use per-trip quotes below, or enable an
                annual travel insurance policy on the Clients page if they maintain their own coverage.
              </p>

              {noQuotesYet ? (
                <>
                  {!waiverPending && !waiverExpiredUnanswered ? (
                    <p className="workflow-task-guidance">
                      No insurance quotes are stored for this request yet. Does the client want you to prepare insurance
                      options?
                    </p>
                  ) : null}
                </>
              ) : (
                <>
                  {!allQuotesDeclined ? (
                    <p className="workflow-task-guidance travel-insurance-per-trip-review">
                      Review proposed trip insurance quotes. Accept the option the client chose, or reject quotes they
                      declined.
                    </p>
                  ) : null}
                  <div className="travel-insurance-quote-list">
                  {quotes.map((quote) => {
                    const isProposed = quote.status === QUOTED_INSURANCE_STATUS_PROPOSED;
                    const quoteUpdating = updatingQuoteId === quote.id;

                    return (
                      <article className="travel-insurance-quote-row" key={quote.id}>
                        <div className="travel-insurance-quote-row-header">
                          <div className="travel-insurance-quote-row-main">
                            <strong>
                              {quote.carrier} · {quote.plan_name}
                            </strong>
                            <div className="meta">Premium {formatMoney(quote.premium_cost)}</div>
                            <div className="meta">
                              Cancellation {formatMoney(quote.cancellation_coverage)} · Medical{" "}
                              {formatMoney(quote.medical_coverage)} · Evac {formatMoney(quote.medical_evac_coverage)}
                            </div>
                            {quote.declined_at ? (
                              <div className="meta">Declined {formatDate(quote.declined_at)}</div>
                            ) : null}
                          </div>
                          <div className="travel-insurance-quote-row-badges">
                            <div className="travel-insurance-quote-row-status-pills">
                              <span className={`quote-status ${quotedInsuranceStatusClass(quote.status)}`}>
                                {quote.status}
                              </span>
                              {quote.quote_mailed ? <QuoteMailedBadge /> : null}
                            </div>
                            {!readOnly && isProposed ? (
                              <div className="proposed-cruise-quote-quick-actions travel-insurance-quote-quick-actions">
                                <IconTooltip label="Accept insurance quote" placement="below" align="end">
                                  <button
                                    type="button"
                                    className="icon-button icon-button-success proposed-cruise-quote-accept"
                                    aria-label="Accept insurance quote"
                                    disabled={quoteUpdating}
                                    onClick={() => handleAcceptQuote(quote)}
                                  >
                                    <CheckIcon />
                                  </button>
                                </IconTooltip>
                                <IconTooltip label="Reject insurance quote" placement="below" align="end">
                                  <button
                                    type="button"
                                    className="icon-button icon-button-danger proposed-cruise-quote-reject"
                                    aria-label="Reject insurance quote"
                                    disabled={quoteUpdating}
                                    onClick={() => handleRejectQuote(quote)}
                                  >
                                    <RejectIcon />
                                  </button>
                                </IconTooltip>
                              </div>
                            ) : null}
                          </div>
                        </div>
                      </article>
                    );
                  })}
                  </div>

                  {status?.waiver_signed ? (
                    <p className="travel-insurance-waiver-sent">
                      Waiver signed
                      {status.waiver_signed_at ? ` · ${formatDate(status.waiver_signed_at)}` : ""}
                    </p>
                  ) : null}
                </>
              )}

              {(waiverPending && status?.waiver_sent_at) ||
              (waiverExpiredUnanswered && status?.waiver_sent_at) ||
              waiverSentMessage ? (
                <div className="travel-insurance-waiver-status-bottom">
                  {waiverPending && status?.waiver_sent_at ? (
                    <p className="travel-insurance-waiver-pending">
                      Waiver email sent {formatTimestamp(status.waiver_sent_at)}. The client has{" "}
                      <strong>{waiverTimeRemaining}</strong> left to respond before the secure link expires.
                    </p>
                  ) : null}

                  {waiverExpiredUnanswered && status?.waiver_sent_at ? (
                    <p className="travel-insurance-waiver-expired">
                      The client did not respond to the waiver email sent {formatTimestamp(status.waiver_sent_at)}
                      {status.waiver_expires_at
                        ? ` before it expired on ${formatTimestamp(status.waiver_expires_at)}`
                        : ""}
                      . Call the client to follow up, then resend the waiver if they still decline coverage.
                    </p>
                  ) : null}

                  {waiverSentMessage ? <p className="travel-insurance-waiver-sent">{waiverSentMessage}</p> : null}
                </div>
              ) : null}
            </>
          ) : null}

          {statusReady && !showAnnualCheckGate && !showPerTripTrack && !clientHasAnnualInsurance ? (
            <p className="muted">Unable to determine annual insurance status for this client.</p>
          ) : null}

          {showComplianceLock ? (
            <p className="travel-insurance-compliance-lock">{status?.completion_blocked_reason}</p>
          ) : null}
        </div>

        {showPanelFooter ? (
          <footer
            className={`travel-insurance-task-footer modal-actions modal-actions-footer${
              showAnnualUpdateActions || showPerTripPreferenceStep || showPerTripAllDeclinedStep
                ? " travel-insurance-task-footer--annual-actions"
                : ""
            }`}
          >
            {showAnnualCheckGate ? (
              <>
                <button
                  type="button"
                  className="modal-secondary"
                  disabled={!registryClientId || footerBusy}
                  onClick={() => setAnnualInsuranceModalOpen(true)}
                >
                  Add annual insurance
                </button>
                <button
                  type="button"
                  disabled={footerBusy}
                  onClick={() => void handleConfirmAnnualCheck()}
                >
                  {confirmingAnnualCheck ? "Confirming…" : "Confirmed — proceed with per-trip insurance"}
                </button>
              </>
            ) : null}

            {clientHasAnnualInsurance ? (
              <>
                {showAnnualUpdateActions ? (
                  <>
                    <button type="button" disabled={footerBusy} onClick={() => void handleUpdateAnnual()}>
                      {saving ? "Updating…" : "Update Annual Insurance"}
                    </button>
                    {annualIsExpired ? (
                      <button
                        type="button"
                        className="modal-secondary"
                        disabled={footerBusy}
                        onClick={() => void handleRemoveAnnualInsurance()}
                      >
                        {clearingAnnual ? "Removing…" : "Remove Annual Insurance"}
                      </button>
                    ) : null}
                  </>
                ) : null}
              </>
            ) : null}

            {showPerTripTrack ? (
              <>
                {showPerTripPreferenceStep ? (
                  <>
                    <button type="button" className="modal-secondary" disabled={footerBusy} onClick={handleClientDeclinesOptions}>
                      No — send waiver email
                    </button>
                    <button type="button" disabled={footerBusy} onClick={handleClientWantsOptions}>
                      Yes — client wants options
                    </button>
                  </>
                ) : null}
                {showPerTripAllDeclinedStep ? (
                  <>
                    {showSendWaiverButton ? (
                      <button type="button" className="modal-secondary" disabled={footerBusy} onClick={() => void handleSendWaiver()}>
                        {sendingWaiver ? "Sending…" : "Send insurance waiver email"}
                      </button>
                    ) : null}
                    <button type="button" disabled={footerBusy} onClick={handleNavigateToQuotedInsurance}>
                      Get more insurance quotes
                    </button>
                  </>
                ) : null}
              </>
            ) : null}
          </footer>
        ) : null}
      </section>

      {annualInsuranceModalOpen && registryClientId ? (
        <ClientModal
          open={annualInsuranceModalOpen}
          clientId={registryClientId}
          mode="edit"
          annualInsuranceQuickEdit
          stacked
          onClose={() => setAnnualInsuranceModalOpen(false)}
          onModeChange={() => undefined}
          onSaved={() => void handleAnnualInsuranceSaved()}
          onDeactivated={() => undefined}
        />
      ) : null}
    </>
  );
}
