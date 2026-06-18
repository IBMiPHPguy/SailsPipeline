import { useEffect, useState } from "react";
import CloseReasonPicker from "./CloseReasonPicker";
import { PRIMARY_CLOSE_REASON } from "./formOptions";
import RequestSummary from "./RequestSummary";
import type { TravelRequest } from "./types";

type CloseRequestModalMode = "close" | "complete_enter_trip_crm";

type CloseRequestModalProps = {
  open: boolean;
  request: TravelRequest;
  closing: boolean;
  mode?: CloseRequestModalMode;
  onCancel: () => void;
  onConfirm: (closeReason: string) => void;
};

export default function CloseRequestModal({
  open,
  request,
  closing,
  mode = "close",
  onCancel,
  onConfirm,
}: CloseRequestModalProps) {
  const [step, setStep] = useState<"select" | "confirm">("select");
  const [closeReason, setCloseReason] = useState("");

  useEffect(() => {
    if (!open) {
      setStep("select");
      setCloseReason("");
    }
  }, [open]);

  if (!open) {
    return null;
  }

  const isCompleteWorkflow = mode === "complete_enter_trip_crm";
  const selectTitle = isCompleteWorkflow ? "Complete Enter Trip in CRM" : "Close request";
  const confirmTitle = isCompleteWorkflow ? "Confirm completion" : "Confirm close";
  const selectIntro = isCompleteWorkflow
    ? "Select a close reason for this request before completing the workflow."
    : "Select a close reason for this request.";
  const confirmIntro = isCompleteWorkflow
    ? "Complete the workflow and close this request with reason:"
    : "Close this request with reason:";
  const confirmHint = isCompleteWorkflow
    ? "The request will be closed and the workflow marked complete."
    : "This action cannot be undone from the request form.";
  const confirmButtonLabel = isCompleteWorkflow ? "Complete workflow" : "Confirm close";

  function handleContinue() {
    if (!closeReason) {
      return;
    }
    setStep("confirm");
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onCancel}>
      <div
        className="modal-card close-request-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="close-request-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="close-request-title">{step === "select" ? selectTitle : confirmTitle}</h3>
        </header>

        <div className="modal-card-body">
          <RequestSummary request={request} />

          {step === "select" ? (
            <>
              <p>{selectIntro}</p>
              <CloseReasonPicker value={closeReason} onChange={setCloseReason} />
              <div className="modal-actions">
                <button type="button" className="secondary-button modal-secondary" onClick={onCancel}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="danger-button"
                  disabled={!closeReason}
                  onClick={handleContinue}
                >
                  Continue
                </button>
              </div>
            </>
          ) : (
            <>
              <p>{confirmIntro}</p>
              <p
                className={
                  closeReason === PRIMARY_CLOSE_REASON
                    ? "confirm-reason confirm-reason-success"
                    : "confirm-reason confirm-reason-negative"
                }
              >
                {closeReason}
              </p>
              <p className="field-hint">{confirmHint}</p>
              <div className="modal-actions">
                <button
                  type="button"
                  className="secondary-button modal-secondary"
                  disabled={closing}
                  onClick={() => setStep("select")}
                >
                  Back
                </button>
                <button
                  type="button"
                  className={isCompleteWorkflow ? undefined : "danger-button"}
                  disabled={closing}
                  onClick={() => onConfirm(closeReason)}
                >
                  {closing ? (isCompleteWorkflow ? "Completing..." : "Closing...") : confirmButtonLabel}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
