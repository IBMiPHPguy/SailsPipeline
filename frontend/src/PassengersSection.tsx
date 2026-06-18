import { useState } from "react";
import { addPassenger, deletePassenger, updatePassenger } from "./api";
import PassengerFields, { emptyPassengerInput, toPassengerPayload } from "./PassengerFields";
import PassengerPickerModal from "./PassengerPickerModal";
import { formatPassengerAddressLine, passengerAddressToInput } from "./passengerAddress";
import InactiveClientBadge from "./InactiveClientBadge";
import { formatPassengerContact, isInactiveClient } from "./passengerDisplay";
import type { PassengerProfile, RequestPassenger, RequestPassengerInput } from "./types";
import { formatDate } from "./utils";

type PassengersSectionProps = {
  requestId: number;
  passengers: RequestPassenger[];
  disabled: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
};

function EditIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 6h18" />
      <path d="M8 6V4h8v2" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
    </svg>
  );
}

export default function PassengersSection({
  requestId,
  passengers,
  disabled,
  onChanged,
  onError,
}: PassengersSectionProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<RequestPassengerInput>(emptyPassengerInput());
  const [pickerOpen, setPickerOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  if (passengers.length === 0) {
    return null;
  }

  function startEdit(passenger: RequestPassenger) {
    setEditingId(passenger.id);
    setEditForm({
      first_name: passenger.first_name,
      last_name: passenger.last_name,
      email: passenger.email,
      phone: passenger.phone,
      date_of_birth: passenger.date_of_birth ?? "",
      qualifiers: passenger.qualifiers ?? [],
      ...passengerAddressToInput(passenger),
    });
  }

  async function handleSaveEdit(passengerId: number) {
    setSaving(true);
    onError("");
    try {
      await updatePassenger(requestId, passengerId, toPassengerPayload(editForm));
      setEditingId(null);
      await onChanged();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to update passenger.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(passengerId: number) {
    if (!window.confirm("Remove this passenger from the request?")) {
      return;
    }
    setSaving(true);
    onError("");
    try {
      await deletePassenger(requestId, passengerId);
      if (editingId === passengerId) {
        setEditingId(null);
      }
      await onChanged();
    } catch (deleteError) {
      onError(deleteError instanceof Error ? deleteError.message : "Unable to remove passenger.");
    } finally {
      setSaving(false);
    }
  }

  async function handleAttachExisting(passenger: PassengerProfile, qualifiers: string[]) {
    setSaving(true);
    onError("");
    try {
      await addPassenger(requestId, { passenger_id: passenger.id, qualifiers });
      setPickerOpen(false);
      await onChanged();
    } catch (attachError) {
      onError(attachError instanceof Error ? attachError.message : "Unable to attach passenger.");
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateNew(payload: RequestPassengerInput) {
    setSaving(true);
    onError("");
    try {
      await addPassenger(requestId, payload);
      setPickerOpen(false);
      await onChanged();
    } catch (addError) {
      onError(addError instanceof Error ? addError.message : "Unable to add passenger.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <section className="section-card passengers-card">
        <header className="section-card-header">
          <h3>Passengers</h3>
        </header>
        <div className="section-card-body">
          <div className="passenger-list">
            {passengers.map((passenger) => {
              const addressLine = formatPassengerAddressLine(passenger);
              const contact = formatPassengerContact(passenger.email, passenger.phone);

              return (
              <article
                className={`passenger-item${isInactiveClient(passenger) ? " passenger-item-inactive" : ""}`}
                key={passenger.id}
              >
                {editingId === passenger.id ? (
                  <div className="passenger-edit-form">
                    <PassengerFields
                      value={editForm}
                      onChange={setEditForm}
                      disabled={disabled || saving}
                      showAddress
                      showQualifiers
                    />
                    <p className="field-hint">
                      Updates apply to this person across all requests where they appear.
                    </p>
                    <div className="passenger-actions">
                      <button type="button" disabled={saving} onClick={() => handleSaveEdit(passenger.id)}>
                        {saving ? "Saving..." : "Save passenger"}
                      </button>
                      <button
                        type="button"
                        className="modal-secondary"
                        disabled={saving}
                        onClick={() => setEditingId(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="passenger-item-header">
                      <div>
                        <div className="passenger-item-title">
                          <strong>
                            {passenger.is_primary ? "Primary · " : ""}
                            {passenger.first_name} {passenger.last_name}
                          </strong>
                          {isInactiveClient(passenger) ? <InactiveClientBadge /> : null}
                        </div>
                        {passenger.date_of_birth ? (
                          <div className="meta">{formatDate(passenger.date_of_birth)}</div>
                        ) : null}
                        {contact ? <div className="meta">{contact}</div> : null}
                        {addressLine ? (
                          <div className="meta passenger-address-line">{addressLine}</div>
                        ) : null}
                        {passenger.qualifiers?.length ? (
                          <div className="meta">
                            Qualifying discounts: {passenger.qualifiers.join(", ")}
                          </div>
                        ) : null}
                      </div>
                      {!disabled ? (
                        <div className="passenger-icon-actions item-icon-actions">
                          <button
                            type="button"
                            className="icon-button"
                            aria-label={`Edit ${passenger.first_name} ${passenger.last_name}`}
                            onClick={() => startEdit(passenger)}
                          >
                            <EditIcon />
                          </button>
                          <button
                            type="button"
                            className="icon-button icon-button-danger"
                            aria-label={`Remove ${passenger.first_name} ${passenger.last_name}`}
                            disabled={saving || passengers.length <= 1 || passenger.is_primary}
                            onClick={() => handleDelete(passenger.id)}
                          >
                            <TrashIcon />
                          </button>
                        </div>
                      ) : null}
                    </div>
                  </>
                )}
              </article>
              );
            })}
          </div>

          {!disabled ? (
            <div className="passenger-add">
              <button type="button" onClick={() => setPickerOpen(true)}>
                Add passenger
              </button>
            </div>
          ) : null}
        </div>
      </section>

      <PassengerPickerModal
        open={pickerOpen}
        title="Add passenger to request"
        saving={saving}
        excludePassengerIds={passengers.map((passenger) => passenger.passenger_id)}
        showQualifiers
        onClose={() => setPickerOpen(false)}
        onAttachExisting={handleAttachExisting}
        onCreateNew={handleCreateNew}
      />
    </>
  );
}
