import { FormEvent, useEffect, useState } from "react";
import { QUOTED_INSURANCE_STATUSES } from "./formOptions";
import { emptyQuotedInsuranceForm, quotedInsuranceStatusOptionClass, quotedInsuranceToForm } from "./quotedInsuranceForm";
import StatusPicker from "./StatusPicker";
import QuoteMailedToggle from "./QuoteMailedToggle";
import type { QuotedInsurance, QuotedInsuranceInput } from "./types";
import "./insurance-portal.css";

type QuotedInsuranceModalProps = {
  open: boolean;
  quote: QuotedInsurance | null;
  saving: boolean;
  disabled: boolean;
  onCancel: () => void;
  onSave: (payload: QuotedInsuranceInput) => Promise<void>;
};

export default function QuotedInsuranceModal({
  open,
  quote,
  saving,
  disabled,
  onCancel,
  onSave,
}: QuotedInsuranceModalProps) {
  const [form, setForm] = useState<QuotedInsuranceInput>(emptyQuotedInsuranceForm);

  useEffect(() => {
    if (!open) {
      setForm(emptyQuotedInsuranceForm);
      return;
    }
    setForm(quote ? quotedInsuranceToForm(quote) : emptyQuotedInsuranceForm);
  }, [open, quote]);

  if (!open) {
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (disabled) {
      return;
    }
    await onSave(form);
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onCancel}>
      <div
        className="modal-card modal-card-wide"
        role="dialog"
        aria-modal="true"
        aria-labelledby="quoted-insurance-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="quoted-insurance-title">
            {quote ? "Edit quoted insurance" : "Quoted insurance"}
          </h3>
        </header>

        <form className="modal-form-layout" onSubmit={handleSubmit}>
          <div className="modal-scroll-body quoted-insurance-form">
            <div className="modal-section-panel">
          <label>
            Carrier
            <input
              required
              disabled={disabled || saving}
              value={form.carrier}
              onChange={(event) => setForm({ ...form, carrier: event.target.value })}
            />
          </label>

          <label>
            Name of plan
            <input
              required
              disabled={disabled || saving}
              value={form.plan_name}
              onChange={(event) => setForm({ ...form, plan_name: event.target.value })}
            />
          </label>

          <div className="field-row">
            <label>
              Premium cost
              <input
                required
                disabled={disabled || saving}
                type="number"
                min={0}
                step="0.01"
                value={form.premium_cost}
                onChange={(event) =>
                  setForm({ ...form, premium_cost: Number(event.target.value) })
                }
              />
            </label>
            <label>
              Cancellation coverage amount
              <input
                required
                disabled={disabled || saving}
                type="number"
                min={0}
                step="0.01"
                value={form.cancellation_coverage}
                onChange={(event) =>
                  setForm({ ...form, cancellation_coverage: Number(event.target.value) })
                }
              />
            </label>
          </div>

          <div className="field-row">
            <label>
              Medical coverage
              <input
                required
                disabled={disabled || saving}
                type="number"
                min={0}
                step="0.01"
                value={form.medical_coverage}
                onChange={(event) =>
                  setForm({ ...form, medical_coverage: Number(event.target.value) })
                }
              />
            </label>
            <label>
              Medical evac coverage
              <input
                required
                disabled={disabled || saving}
                type="number"
                min={0}
                step="0.01"
                value={form.medical_evac_coverage}
                onChange={(event) =>
                  setForm({ ...form, medical_evac_coverage: Number(event.target.value) })
                }
              />
            </label>
          </div>

          {quote ? (
            <StatusPicker
              label="Status"
              value={form.status ?? quote.status}
              options={QUOTED_INSURANCE_STATUSES}
              onChange={(status) => setForm({ ...form, status })}
              disabled={disabled || saving}
              getOptionClassName={quotedInsuranceStatusOptionClass}
            />
          ) : null}

          <QuoteMailedToggle
            value={form.quote_mailed ?? quote?.quote_mailed ?? false}
            disabled={disabled || saving}
            onChange={(quote_mailed) => setForm({ ...form, quote_mailed })}
          />
            </div>
          </div>

          <div className="modal-actions modal-actions-footer">
            <button type="button" className="modal-secondary" disabled={saving} onClick={onCancel}>
              Cancel
            </button>
            {!disabled ? (
              <button type="submit" className="modal-primary" disabled={saving}>
                {saving ? "Saving..." : quote ? "Save insurance quote" : "Add insurance quote"}
              </button>
            ) : null}
          </div>
        </form>
      </div>
    </div>
  );
}
