import { useEffect, useState } from "react";

type ChickenSwitchModalProps = {
  open: boolean;
  title: string;
  description: string;
  itemName?: string;
  switchLabel: string;
  confirmLabel: string;
  confirmingLabel?: string;
  hint?: string;
  confirming: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export default function ChickenSwitchModal({
  open,
  title,
  description,
  itemName,
  switchLabel,
  confirmLabel,
  confirmingLabel = "Deleting...",
  hint = "This action cannot be undone.",
  confirming,
  onCancel,
  onConfirm,
}: ChickenSwitchModalProps) {
  const [armed, setArmed] = useState(false);

  useEffect(() => {
    if (!open) {
      setArmed(false);
    }
  }, [open]);

  if (!open) {
    return null;
  }

  return (
    <div className="modal-backdrop chicken-switch-backdrop" role="presentation" onClick={onCancel}>
      <div
        className="modal-card chicken-switch-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="chicken-switch-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="chicken-switch-title">{title}</h3>
        </header>

        <div className="modal-card-body">
          <p>{description}</p>
          {itemName ? <p className="confirm-reason confirm-reason-negative">{itemName}</p> : null}
          <label className="chicken-switch-control">
            <input
              type="checkbox"
              checked={armed}
              disabled={confirming}
              onChange={(event) => setArmed(event.target.checked)}
            />
            <span>{switchLabel}</span>
          </label>
          {hint ? <p className="field-hint">{hint}</p> : null}
          <div className="modal-actions">
            <button type="button" className="secondary-button modal-secondary" disabled={confirming} onClick={onCancel}>
              Cancel
            </button>
            <button
              type="button"
              className="danger-button"
              disabled={!armed || confirming}
              onClick={onConfirm}
            >
              {confirming ? confirmingLabel : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
