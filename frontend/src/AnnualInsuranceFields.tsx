import type { RequestPassengerInput } from "./types";
import { formatDate } from "./utils";

type AnnualInsuranceDraft = Pick<
  RequestPassengerInput,
  "has_annual_insurance" | "annual_insurance_expires_at" | "annual_insurance_policy_number"
>;

type AnnualInsuranceFieldsProps = {
  value: AnnualInsuranceDraft;
  onChange: (value: AnnualInsuranceDraft) => void;
  disabled?: boolean;
  readOnly?: boolean;
};

export function formatAnnualInsuranceSummary(client: AnnualInsuranceDraft): string {
  if (!client.has_annual_insurance) {
    return "No annual policy on file";
  }
  const parts = [
    client.annual_insurance_policy_number?.trim(),
    client.annual_insurance_expires_at ? `expires ${formatDate(client.annual_insurance_expires_at)}` : null,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : "Annual policy on file (details incomplete)";
}

export default function AnnualInsuranceFields({
  value,
  onChange,
  disabled = false,
  readOnly = false,
}: AnnualInsuranceFieldsProps) {
  if (readOnly) {
    return (
      <dl className="annual-insurance-readonly">
        <div>
          <dt>Annual travel insurance</dt>
          <dd>{value.has_annual_insurance ? "Yes" : "No"}</dd>
        </div>
        {value.has_annual_insurance ? (
          <>
            <div>
              <dt>Policy number</dt>
              <dd>{value.annual_insurance_policy_number?.trim() || "—"}</dd>
            </div>
            <div>
              <dt>Expiration date</dt>
              <dd>
                {value.annual_insurance_expires_at ? formatDate(value.annual_insurance_expires_at) : "—"}
              </dd>
            </div>
          </>
        ) : null}
      </dl>
    );
  }

  return (
    <div className="annual-insurance-fields">
      <span className="field-label">Annual travel insurance</span>
      <p className="field-hint">
        Enable when this client maintains their own annual travel insurance policy across trips.
      </p>
      <label className="travel-insurance-mailed-checkbox annual-insurance-toggle">
        <input
          type="checkbox"
          checked={Boolean(value.has_annual_insurance)}
          disabled={disabled}
          onChange={(event) => onChange({ ...value, has_annual_insurance: event.target.checked })}
        />
        <span>Client has annual travel insurance</span>
      </label>
      <div className="field-row">
        <label>
          Policy number
          <input
            type="text"
            disabled={disabled || !value.has_annual_insurance}
            value={value.annual_insurance_policy_number ?? ""}
            onChange={(event) =>
              onChange({ ...value, annual_insurance_policy_number: event.target.value })
            }
          />
        </label>
        <label>
          Expiration date
          <input
            type="date"
            disabled={disabled || !value.has_annual_insurance}
            value={value.annual_insurance_expires_at ?? ""}
            onChange={(event) => onChange({ ...value, annual_insurance_expires_at: event.target.value })}
          />
        </label>
      </div>
    </div>
  );
}
