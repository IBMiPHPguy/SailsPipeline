import { useEffect, useMemo, useState } from "react";
import { updatePassenger, updateTask } from "./api";
import { TASK_STATUS_DONE } from "./formOptions";
import InactiveClientBadge from "./InactiveClientBadge";
import { isInactiveClient } from "./passengerDisplay";
import type { RequestPassenger } from "./types";

type PassengerDraft = {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  email: string;
  phone: string;
};

type VerifyPassengerDetailsTaskPanelProps = {
  requestId: number;
  passengers: RequestPassenger[];
  taskId: number;
  disabled: boolean;
  isDone: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  onSaved: () => void;
};

function passengerToDraft(passenger: RequestPassenger): PassengerDraft {
  return {
    first_name: passenger.first_name,
    last_name: passenger.last_name,
    date_of_birth: passenger.date_of_birth ?? "",
    email: passenger.email ?? "",
    phone: passenger.phone ?? "",
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

function normalizeDateOfBirth(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  if (!/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
    return null;
  }
  const parsed = new Date(`${trimmed}T00:00:00`);
  if (Number.isNaN(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== trimmed) {
    return null;
  }
  return trimmed;
}

function isValidEmail(value: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function buildPassengerUpdates(
  original: RequestPassenger,
  draft: PassengerDraft,
): Record<string, string | null> | null {
  const updates: Record<string, string | null> = {};
  const firstName = draft.first_name.trim();
  const lastName = draft.last_name.trim();

  if (firstName !== original.first_name) {
    updates.first_name = firstName;
  }
  if (lastName !== original.last_name) {
    updates.last_name = lastName;
  }

  const draftDob = normalizeDateOfBirth(draft.date_of_birth);
  const originalDob = original.date_of_birth ?? null;
  if (draftDob !== originalDob) {
    updates.date_of_birth = draftDob;
  }

  const draftEmail = draft.email.trim();
  const originalEmail = (original.email ?? "").trim();
  if (draftEmail !== originalEmail) {
    updates.email = draftEmail || null;
  }

  const draftPhone = draft.phone.trim();
  const originalPhone = (original.phone ?? "").trim();
  if (draftPhone !== originalPhone) {
    updates.phone = draftPhone || null;
  }

  return Object.keys(updates).length > 0 ? updates : null;
}

export default function VerifyPassengerDetailsTaskPanel({
  requestId,
  passengers,
  taskId,
  disabled,
  isDone,
  onChanged,
  onError,
  onSaved,
}: VerifyPassengerDetailsTaskPanelProps) {
  const sortedPassengers = useMemo(() => sortPassengers(passengers), [passengers]);
  const [drafts, setDrafts] = useState<Record<number, PassengerDraft>>({});
  const [saving, setSaving] = useState(false);
  const readOnly = disabled || isDone;

  useEffect(() => {
    const nextDrafts: Record<number, PassengerDraft> = {};
    for (const passenger of sortedPassengers) {
      nextDrafts[passenger.id] = passengerToDraft(passenger);
    }
    setDrafts(nextDrafts);
  }, [sortedPassengers]);

  function updateDraft(passengerId: number, field: keyof PassengerDraft, value: string) {
    setDrafts((current) => ({
      ...current,
      [passengerId]: {
        ...current[passengerId],
        [field]: value,
      },
    }));
  }

  function validateDrafts(): string | null {
    if (sortedPassengers.length === 0) {
      return "Add at least one passenger to the request before completing this task.";
    }

    for (const passenger of sortedPassengers) {
      const draft = drafts[passenger.id];
      if (!draft) {
        continue;
      }

      if (!draft.first_name.trim() || !draft.last_name.trim()) {
        return `Enter first and last name for ${passenger.first_name} ${passenger.last_name}.`;
      }

      if (!normalizeDateOfBirth(draft.date_of_birth)) {
        return `Enter a valid date of birth (YYYY-MM-DD) for ${draft.first_name.trim()} ${draft.last_name.trim()}.`;
      }

      const email = draft.email.trim();
      const phone = draft.phone.trim();
      if (email && !isValidEmail(email)) {
        return `Enter a valid email address for ${draft.first_name.trim()} ${draft.last_name.trim()}, or leave it blank.`;
      }
      if (phone && phone.length < 7) {
        return `Enter a phone number with at least 7 characters for ${draft.first_name.trim()} ${draft.last_name.trim()}, or leave it blank.`;
      }
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
        const updates = buildPassengerUpdates(passenger, draft);
        if (updates) {
          await updatePassenger(requestId, passenger.id, updates);
        }
      }

      await updateTask(requestId, taskId, { status: TASK_STATUS_DONE });
      await onChanged();
      onSaved();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to save passenger details.");
    } finally {
      setSaving(false);
    }
  }

  if (sortedPassengers.length === 0) {
    return (
      <div className="workflow-task-guidance">
        <p>Add passengers to this request before verifying passenger details.</p>
      </div>
    );
  }

  return (
    <div className="verify-passenger-details-panel">
      <p className="field-hint">
        Confirm or correct each passenger&apos;s details. Date of birth is required. Email and phone are optional for
        all passengers.
      </p>

      <div className="verify-passenger-details-list">
        {sortedPassengers.map((passenger) => {
          const draft = drafts[passenger.id] ?? passengerToDraft(passenger);
          return (
            <article
              className={`verify-passenger-details-item${isInactiveClient(passenger) ? " passenger-item-inactive" : ""}`}
              key={passenger.id}
            >
              <h4>
                {passenger.is_primary ? "Primary passenger" : "Passenger"}
                <span className="verify-passenger-details-name meta">
                  {" "}
                  · {passenger.first_name} {passenger.last_name}
                </span>
                {isInactiveClient(passenger) ? (
                  <>
                    {" "}
                    <InactiveClientBadge />
                  </>
                ) : null}
              </h4>

              <div className="verify-passenger-details-fields">
                <div className="field-row">
                  <label>
                    First name
                    <input
                      type="text"
                      required
                      disabled={readOnly || saving}
                      value={draft.first_name}
                      onChange={(event) => updateDraft(passenger.id, "first_name", event.target.value)}
                    />
                  </label>
                  <label>
                    Last name
                    <input
                      type="text"
                      required
                      disabled={readOnly || saving}
                      value={draft.last_name}
                      onChange={(event) => updateDraft(passenger.id, "last_name", event.target.value)}
                    />
                  </label>
                </div>

                <label>
                  Date of birth
                  <input
                    type="text"
                    required
                    disabled={readOnly || saving}
                    placeholder="YYYY-MM-DD"
                    value={draft.date_of_birth}
                    onChange={(event) => updateDraft(passenger.id, "date_of_birth", event.target.value)}
                  />
                </label>

                <div className="field-row">
                  <label>
                    Email
                    <span className="field-optional">Optional</span>
                    <input
                      type="text"
                      disabled={readOnly || saving}
                      value={draft.email}
                      onChange={(event) => updateDraft(passenger.id, "email", event.target.value)}
                    />
                  </label>
                  <label>
                    Phone
                    <span className="field-optional">Optional</span>
                    <input
                      type="text"
                      disabled={readOnly || saving}
                      value={draft.phone}
                      onChange={(event) => updateDraft(passenger.id, "phone", event.target.value)}
                    />
                  </label>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      {!readOnly ? (
        <button type="button" disabled={saving} onClick={() => void handleSaveAndComplete()}>
          {saving ? "Saving..." : "Save passenger details and mark task done"}
        </button>
      ) : null}
    </div>
  );
}
