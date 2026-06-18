import { FormEvent } from "react";
import CruiseLineMultiSelect from "./CruiseLineMultiSelect";
import DestinationFields from "./DestinationFields";
import TravelDatesField, { isReturnAfterDeparture } from "./TravelDatesField";
import { CABIN_TYPES, DESTINATIONS } from "./formOptions";
import type { DestinationDetailField, TravelRequestInput } from "./types";

type RequestFormProps = {
  form: TravelRequestInput;
  setForm: (form: TravelRequestInput) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  submitting: boolean;
  submitLabel: string;
  disabled?: boolean;
  showCloseButton?: boolean;
  onCloseClick?: () => void;
  showPrimaryPassengerDob?: boolean;
  onFindExistingClient?: () => void;
  formId?: string;
  hideActions?: boolean;
};

function toggleListItem(values: string[], item: string): string[] {
  return values.includes(item) ? values.filter((value) => value !== item) : [...values, item];
}

export default function RequestForm({
  form,
  setForm,
  onSubmit,
  submitting,
  submitLabel,
  disabled = false,
  showCloseButton = false,
  onCloseClick,
  showPrimaryPassengerDob = false,
  onFindExistingClient,
  formId,
  hideActions = false,
}: RequestFormProps) {
  function patchForm(patch: Partial<TravelRequestInput>, clearLinkedPassenger = false) {
    setForm({
      ...form,
      ...patch,
      ...(clearLinkedPassenger ? { primary_passenger_id: undefined } : {}),
    });
  }

  function updateDestination(destination: string) {
    setForm({
      ...form,
      destination,
      destination_details: {},
    });
  }

  function toggleDestinationDetail(field: DestinationDetailField, value: string) {
    const current = form.destination_details?.[field] ?? [];
    setForm({
      ...form,
      destination_details: {
        ...form.destination_details,
        [field]: toggleListItem(current, value),
      },
    });
  }

  return (
    <form id={formId} onSubmit={onSubmit}>
      {showPrimaryPassengerDob && onFindExistingClient ? (
        <div className="requestor-picker">
          <button type="button" className="modal-secondary" disabled={disabled} onClick={onFindExistingClient}>
            Find existing client
          </button>
          {form.primary_passenger_id ? (
            <p className="field-hint">
              Linked to an existing passenger record. Edit the requestor contact fields below to enter someone new
              instead.
            </p>
          ) : (
            <p className="field-hint">
              The requestor is always the primary passenger. Search for a returning client or enter new contact details
              below.
            </p>
          )}
        </div>
      ) : null}

      <div className="field-row">
        <label>
          First name
          <input
            required
            disabled={disabled}
            value={form.first_name}
            onChange={(event) => patchForm({ first_name: event.target.value }, true)}
          />
        </label>

        <label>
          Last name
          <input
            required
            disabled={disabled}
            value={form.last_name}
            onChange={(event) => patchForm({ last_name: event.target.value }, true)}
          />
        </label>
      </div>

      <label>
        Email
        <input
          required
          disabled={disabled}
          type="email"
          value={form.email}
          onChange={(event) => patchForm({ email: event.target.value }, true)}
        />
      </label>

      <label>
        Phone number
        <input
          required
          disabled={disabled}
          type="tel"
          value={form.phone}
          onChange={(event) => patchForm({ phone: event.target.value }, true)}
        />
      </label>

      {showPrimaryPassengerDob ? (
        <label>
          Date of birth (primary passenger)
          <input
            disabled={disabled}
            type="date"
            value={form.first_passenger_date_of_birth ?? ""}
            onChange={(event) =>
              setForm({ ...form, first_passenger_date_of_birth: event.target.value })
            }
          />
        </label>
      ) : null}

      <CruiseLineMultiSelect
        label="Preferred cruise lines"
        hint="Search and select every cruise line the client is open to sailing."
        value={form.cruise_lines}
        onChange={(cruise_lines) => setForm({ ...form, cruise_lines })}
        disabled={disabled}
      />

      <CruiseLineMultiSelect
        label="Cruise lines to avoid"
        hint="Search and select any cruise line the client absolutely does not want to sail."
        value={form.excluded_cruise_lines ?? []}
        onChange={(excluded_cruise_lines) => setForm({ ...form, excluded_cruise_lines })}
        disabled={disabled}
        placeholder="Search lines to avoid..."
      />

      <label>
        Destination
        <select
          required
          disabled={disabled}
          value={form.destination}
          onChange={(event) => updateDestination(event.target.value)}
        >
          <option value="" disabled>
            Select a destination
          </option>
          {DESTINATIONS.map((destination) => (
            <option key={destination} value={destination}>
              {destination}
            </option>
          ))}
        </select>
      </label>

      <DestinationFields
        destination={form.destination}
        details={form.destination_details ?? {}}
        onToggleDetail={toggleDestinationDetail}
      />

      <TravelDatesField
        departureDate={form.departure_date}
        returnDate={form.return_date}
        disabled={disabled}
        onChange={(departureDate, returnDate) =>
          setForm({ ...form, departure_date: departureDate, return_date: returnDate })
        }
      />

      <div>
        <span className="field-label">Cabin types (select all that apply)</span>
        <div className="checkbox-group">
          {CABIN_TYPES.map((cabinType) => (
            <label className="checkbox-inline" key={cabinType}>
              <input
                type="checkbox"
                disabled={disabled}
                checked={form.cabin_types.includes(cabinType)}
                onChange={() =>
                  setForm({
                    ...form,
                    cabin_types: toggleListItem(form.cabin_types, cabinType),
                  })
                }
              />
              {cabinType}
            </label>
          ))}
        </div>
      </div>

      <div className="field-row">
        <label>
          Passengers
          <input
            required
            disabled={disabled}
            type="number"
            min={1}
            max={20}
            value={form.passengers}
            onChange={(event) => setForm({ ...form, passengers: Number(event.target.value) })}
          />
        </label>

        <label>
          Max cabins needed
          <input
            required
            disabled={disabled}
            type="number"
            min={1}
            max={10}
            value={form.cabins_needed}
            onChange={(event) =>
              setForm({ ...form, cabins_needed: Number(event.target.value) })
            }
          />
        </label>
      </div>

      {!disabled && !hideActions ? (
        <button type="submit" disabled={submitting}>
          {submitting ? "Saving..." : submitLabel}
        </button>
      ) : null}

      {!disabled && !hideActions && showCloseButton ? (
        <div className="close-panel">
          <button type="button" className="danger-button" onClick={onCloseClick}>
            Close request
          </button>
        </div>
      ) : null}
    </form>
  );
}

export const emptyRequestForm: TravelRequestInput = {
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  cruise_lines: [],
  excluded_cruise_lines: [],
  destination: "",
  destination_details: {},
  departure_date: "",
  return_date: "",
  cabin_types: [],
  passengers: 2,
  cabins_needed: 1,
  first_passenger_date_of_birth: "",
};

export { isReturnAfterDeparture };
