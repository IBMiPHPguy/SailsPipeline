import { QUALIFIERS } from "./formOptions";
import { qualifierBadgeClass } from "./qualifierDisplay";
import type { RequestPassengerInput } from "./types";
import { normalizeAddressInput, passengerAddressToInput } from "./passengerAddress";
import { normalizeCruiseLoyaltyNumbers } from "./CruiseLineLoyaltyFields";

type PassengerFieldsProps = {
  value: RequestPassengerInput;
  onChange: (value: RequestPassengerInput) => void;
  disabled: boolean;
  showDateOfBirth?: boolean;
  showAddress?: boolean;
  showQualifiers?: boolean;
  qualifierHint?: string;
  requireContactFields?: boolean;
};

function toggleListItem(values: string[], item: string): string[] {
  return values.includes(item) ? values.filter((value) => value !== item) : [...values, item];
}

type PassengerQualifierFieldsProps = {
  value: string[];
  onChange: (value: string[]) => void;
  disabled: boolean;
  hint?: string;
};

export function PassengerQualifierFields({
  value,
  onChange,
  disabled,
  hint = "Applies to this passenger on this request only.",
}: PassengerQualifierFieldsProps) {
  return (
    <div>
      <span className="field-label">Qualifying discounts</span>
      <p className="field-hint">{hint}</p>
      <div className="passenger-qualifier-picker" role="group" aria-label="Qualifying discounts">
        {QUALIFIERS.map((qualifier) => {
          const selected = value.includes(qualifier);
          return (
            <button
              key={qualifier}
              type="button"
              className={`passenger-qualifier-picker-pill ${qualifierBadgeClass(qualifier)}${
                selected ? " is-selected" : ""
              }`}
              disabled={disabled}
              aria-pressed={selected}
              onClick={() => onChange(toggleListItem(value, qualifier))}
            >
              {qualifier}
            </button>
          );
        })}
      </div>
    </div>
  );
}
export default function PassengerFields({
  value,
  onChange,
  disabled,
  showDateOfBirth = true,
  showAddress = false,
  showQualifiers = false,
  qualifierHint,
  requireContactFields = false,
}: PassengerFieldsProps) {
  const qualifiers = value.qualifiers ?? [];

  return (
    <>
      <div className="field-row">
        <label>
          First name
          <input
            required
            disabled={disabled}
            value={value.first_name ?? ""}
            onChange={(event) => onChange({ ...value, first_name: event.target.value })}
          />
        </label>
        <label>
          Last name
          <input
            required
            disabled={disabled}
            value={value.last_name ?? ""}
            onChange={(event) => onChange({ ...value, last_name: event.target.value })}
          />
        </label>
      </div>
      <label>
        Email
        {!requireContactFields ? <span className="field-optional">Optional</span> : null}
        <input
          required={requireContactFields}
          disabled={disabled}
          type="email"
          value={value.email ?? ""}
          onChange={(event) => onChange({ ...value, email: event.target.value })}
        />
      </label>
      <label>
        Phone number
        {!requireContactFields ? <span className="field-optional">Optional</span> : null}
        <input
          required={requireContactFields}
          disabled={disabled}
          type="tel"
          value={value.phone ?? ""}
          onChange={(event) => onChange({ ...value, phone: event.target.value })}
        />
      </label>
      {showDateOfBirth ? (
        <label>
          Date of birth
          <input
            disabled={disabled}
            type="date"
            value={value.date_of_birth ?? ""}
            onChange={(event) => onChange({ ...value, date_of_birth: event.target.value })}
          />
        </label>
      ) : null}
      {showQualifiers ? (
        <PassengerQualifierFields
          value={qualifiers}
          disabled={disabled}
          hint={qualifierHint}
          onChange={(nextQualifiers) => onChange({ ...value, qualifiers: nextQualifiers })}
        />
      ) : null}
      {showAddress ? (
        <div className="passenger-address-fields">
          <p className="passenger-address-fields-heading">Home address</p>
          <label>
            Address line 1
            <input
              type="text"
              disabled={disabled}
              value={value.address_line_1 ?? ""}
              onChange={(event) => onChange({ ...value, address_line_1: event.target.value })}
            />
          </label>
          <label>
            Address line 2
            <span className="field-optional">Optional</span>
            <input
              type="text"
              disabled={disabled}
              value={value.address_line_2 ?? ""}
              onChange={(event) => onChange({ ...value, address_line_2: event.target.value })}
            />
          </label>
          <div className="field-row">
            <label>
              City
              <input
                type="text"
                disabled={disabled}
                value={value.city ?? ""}
                onChange={(event) => onChange({ ...value, city: event.target.value })}
              />
            </label>
            <label>
              State / province
              <input
                type="text"
                disabled={disabled}
                value={value.state_or_province ?? ""}
                onChange={(event) => onChange({ ...value, state_or_province: event.target.value })}
              />
            </label>
          </div>
          <div className="field-row">
            <label>
              Postal code
              <input
                type="text"
                disabled={disabled}
                value={value.postal_code ?? ""}
                onChange={(event) => onChange({ ...value, postal_code: event.target.value })}
              />
            </label>
            <label>
              Country
              <span className="field-optional">Optional</span>
              <input
                type="text"
                disabled={disabled}
                value={value.country ?? ""}
                onChange={(event) => onChange({ ...value, country: event.target.value })}
              />
            </label>
          </div>
        </div>
      ) : null}
    </>
  );
}

export function emptyPassengerInput(): RequestPassengerInput {
  return {
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    date_of_birth: "",
    qualifiers: [],
    has_annual_insurance: false,
    annual_insurance_expires_at: "",
    annual_insurance_policy_number: "",
    ...passengerAddressToInput({}),
  };
}

export function toPassengerPayload(value: RequestPassengerInput): RequestPassengerInput {
  return {
    ...value,
    first_name: value.first_name?.trim() ?? "",
    last_name: value.last_name?.trim() ?? "",
    email: value.email?.trim() || null,
    phone: value.phone?.trim() || null,
    date_of_birth: value.date_of_birth?.trim() || null,
    qualifiers: value.qualifiers ?? [],
    has_annual_insurance: value.has_annual_insurance ?? false,
    annual_insurance_expires_at: value.annual_insurance_expires_at?.trim() || null,
    annual_insurance_policy_number: value.annual_insurance_policy_number?.trim() || null,
    cruise_loyalty_numbers: normalizeCruiseLoyaltyNumbers(value.cruise_loyalty_numbers ?? []),
    ...normalizeAddressInput(value),
  };
}
