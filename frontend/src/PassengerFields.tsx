import { QUALIFIERS } from "./formOptions";
import type { RequestPassengerInput } from "./types";
import { normalizeAddressInput, passengerAddressToInput } from "./passengerAddress";

type PassengerFieldsProps = {
  value: RequestPassengerInput;
  onChange: (value: RequestPassengerInput) => void;
  disabled: boolean;
  showDateOfBirth?: boolean;
  showAddress?: boolean;
  showQualifiers?: boolean;
  requireContactFields?: boolean;
};

function toggleListItem(values: string[], item: string): string[] {
  return values.includes(item) ? values.filter((value) => value !== item) : [...values, item];
}

type PassengerQualifierFieldsProps = {
  value: string[];
  onChange: (value: string[]) => void;
  disabled: boolean;
};

export function PassengerQualifierFields({
  value,
  onChange,
  disabled,
}: PassengerQualifierFieldsProps) {
  return (
    <div>
      <span className="field-label">Qualifying discounts</span>
      <p className="field-hint">Applies to this passenger on this request only.</p>
      <div className="checkbox-group">
        {QUALIFIERS.map((qualifier) => (
          <label className="checkbox-inline" key={qualifier}>
            <input
              type="checkbox"
              disabled={disabled}
              checked={value.includes(qualifier)}
              onChange={() => onChange(toggleListItem(value, qualifier))}
            />
            {qualifier}
          </label>
        ))}
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
    ...normalizeAddressInput(value),
  };
}
