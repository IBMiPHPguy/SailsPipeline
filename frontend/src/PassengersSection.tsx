import { Fragment, useState } from "react";
import { addPassenger, deletePassenger, updatePassenger } from "./api";
import ChickenSwitchModal from "./ChickenSwitchModal";
import CruiseLineLoyaltyFields from "./CruiseLineLoyaltyFields";
import EditIcon from "./EditIcon";
import PassengerFields, { emptyPassengerInput, toPassengerPayload } from "./PassengerFields";
import PassengerPickerModal from "./PassengerPickerModal";
import PassengerQualifierBadges from "./PassengerQualifierBadges";
import { formatPassengerAddressLine, passengerAddressToInput } from "./passengerAddress";
import InactiveClientBadge from "./InactiveClientBadge";
import IconTooltip from "./IconTooltip";
import TabHeaderAddButton from "./TabHeaderAddButton";
import WorkspaceBandHeader from "./WorkspaceBandHeader";
import { formatDisplayPhone, formatPassengerContact, isInactiveClient } from "./passengerDisplay";
import type { PassengerProfile, RequestPassenger, RequestPassengerInput } from "./types";
import { formatDate } from "./utils";

type PassengersSectionProps = {
  requestId: number;
  passengers: RequestPassenger[];
  disabled: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  layout?: "cards" | "table";
  embeddedInWorkspace?: boolean;
};

type PendingRemovePassenger = {
  id: number;
  name: string;
};

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
  layout = "cards",
  embeddedInWorkspace = false,
}: PassengersSectionProps) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editForm, setEditForm] = useState<RequestPassengerInput>(emptyPassengerInput());
  const [pickerOpen, setPickerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pendingRemove, setPendingRemove] = useState<PendingRemovePassenger | null>(null);
  const [removingId, setRemovingId] = useState<number | null>(null);

  function startEdit(passenger: RequestPassenger) {
    setEditingId(passenger.id);
    setEditForm({
      first_name: passenger.first_name,
      last_name: passenger.last_name,
      email: passenger.email,
      phone: passenger.phone,
      date_of_birth: passenger.date_of_birth ?? "",
      qualifiers: passenger.qualifiers ?? [],
      cruise_loyalty_numbers:
        passenger.cruise_loyalty_numbers?.map((entry) => ({
          cruise_line: entry.cruise_line,
          loyalty_number: entry.loyalty_number,
        })) ?? [],
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

  function requestRemovePassenger(passenger: RequestPassenger) {
    if (disabled || saving || passengers.length <= 1 || passenger.is_primary) {
      return;
    }
    onError("");
    setPendingRemove({
      id: passenger.id,
      name: `${passenger.first_name} ${passenger.last_name}`.trim(),
    });
  }

  async function confirmRemovePassenger() {
    if (!pendingRemove) {
      return;
    }

    setRemovingId(pendingRemove.id);
    onError("");
    try {
      await deletePassenger(requestId, pendingRemove.id);
      if (editingId === pendingRemove.id) {
        setEditingId(null);
      }
      setPendingRemove(null);
      await onChanged();
    } catch (deleteError) {
      onError(deleteError instanceof Error ? deleteError.message : "Unable to remove passenger.");
    } finally {
      setRemovingId(null);
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

  function renderEditForm(passengerId: number) {
    return (
      <div className="passenger-edit-form">
        <PassengerFields
          value={editForm}
          onChange={setEditForm}
          disabled={disabled || saving}
          showAddress
          showQualifiers
        />
        <CruiseLineLoyaltyFields
          value={editForm.cruise_loyalty_numbers ?? []}
          onChange={(cruise_loyalty_numbers) =>
            setEditForm((current) => ({
              ...current,
              cruise_loyalty_numbers,
            }))
          }
          disabled={disabled || saving}
        />
        <p className="field-hint">
          Updates apply to this person across all requests where they appear.
        </p>
        <div className="passenger-actions">
          <button type="button" disabled={saving} onClick={() => handleSaveEdit(passengerId)}>
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
    );
  }

  function renderCardList() {
    return (
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
                renderEditForm(passenger.id)
              ) : (
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
                    {addressLine ? <div className="meta passenger-address-line">{addressLine}</div> : null}
                    {passenger.qualifiers?.length ? (
                      <div className="passenger-item-qualifiers">
                        <PassengerQualifierBadges qualifiers={passenger.qualifiers} />
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
                        disabled={saving || removingId !== null || passengers.length <= 1 || passenger.is_primary}
                        onClick={() => requestRemovePassenger(passenger)}
                      >
                        <TrashIcon />
                      </button>
                    </div>
                  ) : null}
                </div>
              )}
            </article>
          );
        })}
      </div>
    );
  }

  function renderTable() {
    return (
      <div className="passengers-table-wrap">
        <table className="passengers-table">
          <thead>
            <tr>
              <th scope="col">Passenger</th>
              <th scope="col">Date of birth</th>
              <th scope="col">Contact</th>
              <th scope="col">Address</th>
              <th scope="col">Qualifiers</th>
              {!disabled ? <th scope="col" className="passengers-table-actions-col">Actions</th> : null}
            </tr>
          </thead>
          <tbody>
            {passengers.length === 0 ? (
              <tr>
                <td colSpan={disabled ? 5 : 6} className="passengers-table-empty">
                  No passengers on this request yet.
                </td>
              </tr>
            ) : (
              passengers.map((passenger) => {
                const addressLine = formatPassengerAddressLine(passenger);
                const fullName = `${passenger.first_name} ${passenger.last_name}`;

                return (
                  <Fragment key={passenger.id}>
                    <tr
                      className={isInactiveClient(passenger) ? "passenger-table-row-inactive" : undefined}
                    >
                      <td>
                        <div className="passengers-table-name">
                          <strong>
                            {passenger.is_primary ? "Primary · " : ""}
                            {fullName}
                          </strong>
                          {isInactiveClient(passenger) ? <InactiveClientBadge /> : null}
                        </div>
                      </td>
                      <td>{passenger.date_of_birth ? formatDate(passenger.date_of_birth) : "—"}</td>
                      <td>{renderTableContact(passenger)}</td>
                      <td>{addressLine || "—"}</td>
                      <td>
                        <PassengerQualifierBadges qualifiers={passenger.qualifiers ?? []} />
                      </td>
                      {!disabled ? (
                        <td className="passengers-table-actions-col">
                          <div className="item-icon-actions">
                            <IconTooltip label={`Edit ${fullName}`}>
                              <button
                                type="button"
                                className="icon-button"
                                aria-label={`Edit ${fullName}`}
                                onClick={() => startEdit(passenger)}
                              >
                                <EditIcon />
                              </button>
                            </IconTooltip>
                            <IconTooltip label={`Remove ${fullName}`}>
                              <button
                                type="button"
                                className="icon-button icon-button-danger"
                                aria-label={`Remove ${fullName}`}
                                disabled={saving || removingId !== null || passengers.length <= 1 || passenger.is_primary}
                                onClick={() => requestRemovePassenger(passenger)}
                              >
                                <TrashIcon />
                              </button>
                            </IconTooltip>
                          </div>
                        </td>
                      ) : null}
                    </tr>
                    {editingId === passenger.id ? (
                      <tr className="passenger-table-edit-row">
                        <td colSpan={disabled ? 5 : 6}>{renderEditForm(passenger.id)}</td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    );
  }

  function renderTableContact(passenger: RequestPassenger) {
    const email = passenger.email?.trim() || null;
    const phone = formatDisplayPhone(passenger.phone);

    if (!email && !phone) {
      return "—";
    }

    return (
      <div className="passengers-table-contact">
        {email ? <span>{email}</span> : null}
        {phone ? <span>{phone}</span> : null}
      </div>
    );
  }

  function renderAddPassengerButton() {
    if (disabled) {
      return null;
    }

    return <TabHeaderAddButton label="Add Passenger" onClick={() => setPickerOpen(true)} />;
  }

  const pickerModal = (
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
  );

  const removePassengerModal = (
    <ChickenSwitchModal
      open={pendingRemove !== null}
      title="Remove passenger from request?"
      description="This removes the passenger from this request only. Their client record is not deleted."
      itemName={pendingRemove?.name}
      switchLabel="Yes, remove this passenger from the request"
      confirmLabel="Remove passenger"
      confirmingLabel="Removing..."
      hint="If they are assigned to a proposed cruise room, that assignment will also be cleared."
      confirming={pendingRemove !== null && removingId === pendingRemove.id}
      onCancel={() => setPendingRemove(null)}
      onConfirm={() => void confirmRemovePassenger()}
    />
  );

  const body = (
    <>
      {layout === "table" ? renderTable() : renderCardList()}
      {pickerModal}
      {removePassengerModal}
    </>
  );

  if (embeddedInWorkspace) {
    return (
      <div className="workspace-panel passengers-panel">
        <section className="request-form-band">
          <WorkspaceBandHeader
            title="Passenger information"
            meta={`${passengers.length} on request`}
            actions={renderAddPassengerButton()}
          />
          <div className="request-form-band-body">{body}</div>
        </section>
      </div>
    );
  }

  if (passengers.length === 0 && layout === "cards") {
    return null;
  }

  const addPassengerButton = renderAddPassengerButton();

  return (
    <section className="section-card passengers-card">
      <header className="section-card-header workspace-band-header--with-actions">
        <div className="workspace-band-header-title-group">
          <h3>Passengers</h3>
        </div>
        {addPassengerButton ? (
          <div className="workspace-band-header-actions">{addPassengerButton}</div>
        ) : null}
      </header>
      <div className="section-card-body">{body}</div>
    </section>
  );
}
