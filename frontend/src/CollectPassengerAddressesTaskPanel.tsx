import { useEffect, useMemo, useState } from "react";
import { updatePassenger, updateTask } from "./api";
import {
  LEGACY_TASK_KEY_COLLECT_LEAD_PASSENGER_ADDRESSES,
  TASK_KEY_COLLECT_PASSENGER_ADDRESSES,
  TASK_STATUS_DONE,
} from "./formOptions";
import type { RequestPassenger, RequestPassengerInput } from "./types";

type AddressDraft = {
  address_line_1: string;
  address_line_2: string;
  city: string;
  state_or_province: string;
  postal_code: string;
  country: string;
};

type CollectPassengerAddressesTaskPanelProps = {
  requestId: number;
  passengers: RequestPassenger[];
  taskId: string;
  disabled: boolean;
  isDone: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  onSaved: () => void;
};

const ADDRESS_FIELDS: (keyof AddressDraft)[] = [
  "address_line_1",
  "address_line_2",
  "city",
  "state_or_province",
  "postal_code",
  "country",
];

function emptyAddressDraft(): AddressDraft {
  return {
    address_line_1: "",
    address_line_2: "",
    city: "",
    state_or_province: "",
    postal_code: "",
    country: "",
  };
}

function passengerToAddressDraft(passenger: RequestPassenger): AddressDraft {
  return {
    address_line_1: passenger.address_line_1 ?? "",
    address_line_2: passenger.address_line_2 ?? "",
    city: passenger.city ?? "",
    state_or_province: passenger.state_or_province ?? "",
    postal_code: passenger.postal_code ?? "",
    country: passenger.country ?? "",
  };
}

function sortPassengers(passengers: RequestPassenger[] | undefined): RequestPassenger[] {
  if (!passengers?.length) {
    return [];
  }
  return [...passengers].sort((left, right) => {
    if (left.is_primary !== right.is_primary) {
      return left.is_primary ? -1 : 1;
    }
    return left.id - right.id;
  });
}

function normalizeOptional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed || null;
}

function isPrimaryAddressComplete(draft: AddressDraft): boolean {
  return Boolean(
    draft.address_line_1.trim() &&
      draft.city.trim() &&
      draft.state_or_province.trim() &&
      draft.postal_code.trim(),
  );
}

function buildAddressUpdates(
  original: RequestPassenger,
  draft: AddressDraft,
): RequestPassengerInput | null {
  const updates: RequestPassengerInput = {};

  for (const field of ADDRESS_FIELDS) {
    const nextValue = normalizeOptional(draft[field]);
    const previousValue = original[field] ?? null;
    if (nextValue !== previousValue) {
      updates[field] = nextValue;
    }
  }

  return Object.keys(updates).length > 0 ? updates : null;
}

export function isCollectPassengerAddressesTask(taskKey: string): boolean {
  return (
    taskKey === TASK_KEY_COLLECT_PASSENGER_ADDRESSES ||
    taskKey === LEGACY_TASK_KEY_COLLECT_LEAD_PASSENGER_ADDRESSES
  );
}

export default function CollectPassengerAddressesTaskPanel({
  requestId,
  passengers,
  taskId,
  disabled,
  isDone,
  onChanged,
  onError,
  onSaved,
}: CollectPassengerAddressesTaskPanelProps) {
  const sortedPassengers = useMemo(() => sortPassengers(passengers), [passengers]);
  const primaryPassenger = sortedPassengers.find((passenger) => passenger.is_primary) ?? null;
  const [drafts, setDrafts] = useState<Record<number, AddressDraft>>({});
  const [saving, setSaving] = useState(false);
  const readOnly = disabled || isDone;

  useEffect(() => {
    const nextDrafts: Record<number, AddressDraft> = {};
    for (const passenger of sortedPassengers) {
      nextDrafts[passenger.id] = passengerToAddressDraft(passenger);
    }
    setDrafts(nextDrafts);
  }, [sortedPassengers]);

  function updateDraft(passengerId: number, field: keyof AddressDraft, value: string) {
    setDrafts((current) => ({
      ...current,
      [passengerId]: {
        ...current[passengerId],
        [field]: value,
      },
    }));
  }

  function copyPrimaryAddressToPassenger(passengerId: number) {
    if (!primaryPassenger) {
      return;
    }

    const primaryDraft = drafts[primaryPassenger.id] ?? passengerToAddressDraft(primaryPassenger);
    setDrafts((current) => ({
      ...current,
      [passengerId]: { ...primaryDraft },
    }));
  }

  function validateDrafts(): string | null {
    if (!primaryPassenger) {
      return "Add a primary passenger to the request before completing this task.";
    }

    const primaryDraft = drafts[primaryPassenger.id] ?? passengerToAddressDraft(primaryPassenger);
    if (!isPrimaryAddressComplete(primaryDraft)) {
      return "Enter address line 1, city, state/province, and postal code for the primary passenger.";
    }

    return null;
  }

  async function handleSaveAndComplete() {
    const validationError = validateDrafts();
    if (validationError) {
      onError(validationError);
      return;
    }

    setSaving(true);
    onError("");
    try {
      for (const passenger of sortedPassengers) {
        const draft = drafts[passenger.id];
        if (!draft) {
          continue;
        }
        const updates = buildAddressUpdates(passenger, draft);
        if (updates) {
          await updatePassenger(requestId, passenger.id, updates);
        }
      }

      await updateTask(requestId, taskId, { status: TASK_STATUS_DONE });
      await onChanged();
      onSaved();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to save passenger addresses.");
    } finally {
      setSaving(false);
    }
  }

  if (sortedPassengers.length === 0) {
    return (
      <div className="workflow-task-guidance">
        <p>Add passengers to this request before collecting addresses.</p>
      </div>
    );
  }

  if (!primaryPassenger) {
    return (
      <div className="workflow-task-guidance">
        <p>Mark one passenger as primary before collecting addresses.</p>
      </div>
    );
  }

  return (
    <div className="collect-passenger-addresses-panel">
      <p className="field-hint">
        The primary passenger&apos;s home address is required. Other passenger addresses are optional.
      </p>

      <div className="collect-passenger-addresses-list">
        {sortedPassengers.map((passenger) => {
          const draft = drafts[passenger.id] ?? passengerToAddressDraft(passenger);
          const isPrimary = passenger.is_primary;

          return (
            <article className="collect-passenger-addresses-item" key={passenger.id}>
              <div className="collect-passenger-addresses-item-header">
                <h4>
                  {isPrimary ? "Primary passenger" : "Passenger"}
                  <span className="collect-passenger-addresses-name meta">
                    {" "}
                    · {passenger.first_name} {passenger.last_name}
                  </span>
                </h4>
                {isPrimary ? (
                  <span className="collect-passenger-addresses-required">Required</span>
                ) : (
                  <span className="collect-passenger-addresses-optional">Optional</span>
                )}
              </div>

              <div className="collect-passenger-addresses-fields">
                <label>
                  Address line 1
                  <input
                    type="text"
                    required={isPrimary}
                    disabled={readOnly || saving}
                    value={draft.address_line_1}
                    onChange={(event) => updateDraft(passenger.id, "address_line_1", event.target.value)}
                  />
                </label>

                <label>
                  Address line 2
                  <span className="field-optional">Optional</span>
                  <input
                    type="text"
                    disabled={readOnly || saving}
                    value={draft.address_line_2}
                    onChange={(event) => updateDraft(passenger.id, "address_line_2", event.target.value)}
                  />
                </label>

                <div className="field-row">
                  <label>
                    City
                    <input
                      type="text"
                      required={isPrimary}
                      disabled={readOnly || saving}
                      value={draft.city}
                      onChange={(event) => updateDraft(passenger.id, "city", event.target.value)}
                    />
                  </label>
                  <label>
                    State / province
                    <input
                      type="text"
                      required={isPrimary}
                      disabled={readOnly || saving}
                      value={draft.state_or_province}
                      onChange={(event) => updateDraft(passenger.id, "state_or_province", event.target.value)}
                    />
                  </label>
                </div>

                <div className="field-row">
                  <label>
                    Postal code
                    <input
                      type="text"
                      required={isPrimary}
                      disabled={readOnly || saving}
                      value={draft.postal_code}
                      onChange={(event) => updateDraft(passenger.id, "postal_code", event.target.value)}
                    />
                  </label>
                  <label>
                    Country
                    <span className="field-optional">Optional</span>
                    <input
                      type="text"
                      disabled={readOnly || saving}
                      value={draft.country}
                      onChange={(event) => updateDraft(passenger.id, "country", event.target.value)}
                    />
                  </label>
                </div>
              </div>

              {!isPrimary && !readOnly ? (
                <button
                  type="button"
                  className="modal-secondary collect-passenger-addresses-copy"
                  disabled={saving}
                  onClick={() => copyPrimaryAddressToPassenger(passenger.id)}
                >
                  Copy primary passenger address
                </button>
              ) : null}
            </article>
          );
        })}
      </div>

      {!readOnly ? (
        <button type="button" disabled={saving} onClick={() => void handleSaveAndComplete()}>
          {saving ? "Saving..." : "Save addresses and mark task done"}
        </button>
      ) : null}
    </div>
  );
}
