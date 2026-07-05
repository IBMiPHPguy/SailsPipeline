import { useEffect, useState } from "react";
import { updateTask } from "./api";
import AcceptProposedCruiseChooser from "./AcceptProposedCruiseChooser";
import { getProposedCruisesAwaitingAcceptance } from "./acceptProposedCruise";
import { formatMoney } from "./cabinPricing";
import { proposedCruiseReservationIds } from "./cabinHoldReservations";
import { proposedCruiseToCabinRooms } from "./cabinRooms";
import {
  buildCrmEntrySummaryText,
  formatProposedCruiseIncludes,
  getAcceptedQuotedInsurance,
  getCrmEntryProposedCruises,
  hasAcceptedOrDepositedProposedCruise,
} from "./crmEntrySummary";
import {
  isEnterTripInCrmChecklistComplete,
  readEnterTripInCrmChecklist,
  type EnterTripInCrmChecklist,
} from "./enterTripInCrm";
import { TASK_STATUS_DONE } from "./formOptions";
import InactiveClientBadge from "./InactiveClientBadge";
import { isInactiveClient } from "./passengerDisplay";
import { proposedRoomLabel } from "./proposedCruiseRooms";
import type { RequestPassenger, RequestTask, TravelRequestDetail, TravelRequestInput } from "./types";
import { formatDate } from "./utils";

type CreateTripInCrmTaskPanelProps = {
  requestId: number;
  request: TravelRequestDetail;
  form: TravelRequestInput;
  task: RequestTask;
  disabled: boolean;
  isDone: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  onSaved: () => void;
};
function displayValue(value: string | null | undefined): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : "—";
}

function PassengerDetailCard({
  passenger,
  cruiseLine,
}: {
  passenger: RequestPassenger;
  cruiseLine?: string;
}) {
  const matchingLoyalty =
    cruiseLine != null
      ? passenger.cruise_loyalty_numbers?.find((entry) => entry.cruise_line === cruiseLine)
      : undefined;

  return (
    <article
      className={`crm-entry-passenger-card${isInactiveClient(passenger) ? " passenger-item-inactive" : ""}`}
    >
      <h6>
        {passenger.first_name} {passenger.last_name}
        {passenger.is_primary ? " · Primary" : ""}
        {isInactiveClient(passenger) ? (
          <>
            {" "}
            <InactiveClientBadge />
          </>
        ) : null}
      </h6>
      <dl className="crm-entry-detail-grid">
        <div>
          <dt>First name</dt>
          <dd>{passenger.first_name}</dd>
        </div>
        <div>
          <dt>Last name</dt>
          <dd>{passenger.last_name}</dd>
        </div>
        <div>
          <dt>Email</dt>
          <dd>{passenger.email}</dd>
        </div>
        <div>
          <dt>Phone</dt>
          <dd>{passenger.phone}</dd>
        </div>
        <div>
          <dt>Date of birth</dt>
          <dd>{passenger.date_of_birth ? formatDate(passenger.date_of_birth) : "—"}</dd>
        </div>
        <div>
          <dt>Address line 1</dt>
          <dd>{displayValue(passenger.address_line_1)}</dd>
        </div>
        <div>
          <dt>Address line 2</dt>
          <dd>{displayValue(passenger.address_line_2)}</dd>
        </div>
        <div>
          <dt>City</dt>
          <dd>{displayValue(passenger.city)}</dd>
        </div>
        <div>
          <dt>State / province</dt>
          <dd>{displayValue(passenger.state_or_province)}</dd>
        </div>
        <div>
          <dt>Postal code</dt>
          <dd>{displayValue(passenger.postal_code)}</dd>
        </div>
        <div>
          <dt>Country</dt>
          <dd>{displayValue(passenger.country)}</dd>
        </div>
        {matchingLoyalty ? (
          <div>
            <dt>{matchingLoyalty.cruise_line} loyalty #</dt>
            <dd>{matchingLoyalty.loyalty_number}</dd>
          </div>
        ) : null}
        <div>
          <dt>Qualifying discounts</dt>
          <dd>{passenger.qualifiers?.length ? passenger.qualifiers.join(", ") : "—"}</dd>
        </div>
      </dl>
    </article>
  );
}

export default function CreateTripInCrmTaskPanel({
  requestId,
  request,
  form,
  task,
  disabled,
  isDone,
  onChanged,
  onError,
  onSaved,
}: CreateTripInCrmTaskPanelProps) {
  const [copyMessage, setCopyMessage] = useState("");
  const [checklist, setChecklist] = useState<EnterTripInCrmChecklist>(() => readEnterTripInCrmChecklist(task.result));
  const [saving, setSaving] = useState(false);
  const readOnly = disabled || isDone;
  const allComplete = isEnterTripInCrmChecklistComplete(checklist);
  const hasAcceptedCruise = hasAcceptedOrDepositedProposedCruise(request.proposed_cruises);
  const proposedCruisesAwaitingAcceptance = getProposedCruisesAwaitingAcceptance(request.proposed_cruises);
  const bookingCruises = getCrmEntryProposedCruises(request.proposed_cruises);
  const acceptedInsurance = getAcceptedQuotedInsurance(request.quoted_insurance);
  const cabinsNeeded = Math.max(1, form.cabins_needed ?? request.cabins_needed ?? 1);

  useEffect(() => {
    setChecklist(readEnterTripInCrmChecklist(task.result));
  }, [task.id, task.result]);

  async function handleCopySummary() {    setCopyMessage("");
    try {
      await navigator.clipboard.writeText(buildCrmEntrySummaryText(request, form));
      setCopyMessage("Summary copied to clipboard.");
    } catch {
      setCopyMessage("Unable to copy summary. Select and copy the text manually.");
    }
  }

  async function handleSaveAndComplete() {
    if (!allComplete) {
      onError("Check off each CRM step before completing this task.");
      return;
    }

    setSaving(true);
    onError("");
    try {
      await updateTask(requestId, task.id, {
        status: TASK_STATUS_DONE,
        result: checklist,
      });
      await onChanged();
      onSaved();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to complete Enter Trip in CRM task.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="crm-entry-summary">
      <p className="crm-entry-summary-intro meta">
        Use the booking summary below to enter this trip in your agency CRM. Check off each step as you complete it.
        Accepted or deposited cruises show every room, reservation ID, inclusion, and full passenger details.
      </p>

      {!readOnly && proposedCruisesAwaitingAcceptance.length > 0 ? (
        <section className="crm-entry-section crm-entry-accept-cruise">
          <AcceptProposedCruiseChooser
            requestId={requestId}
            cruises={request.proposed_cruises}
            disabled={readOnly || saving}
            onChanged={onChanged}
            onError={onError}
          />
        </section>
      ) : null}

      <section className="crm-entry-section">
        <h4 className="crm-entry-section-title">Request</h4>
        <dl className="crm-entry-grid">
          <div>
            <dt>Request</dt>
            <dd>#{request.id}</dd>
          </div>
          <div>
            <dt>Client</dt>
            <dd>
              {form.first_name} {form.last_name}
            </dd>
          </div>
          <div>
            <dt>Email</dt>
            <dd>{form.email}</dd>
          </div>
          <div>
            <dt>Phone</dt>
            <dd>{form.phone}</dd>
          </div>
          <div>
            <dt>Passengers / cabins</dt>
            <dd>
              {form.passengers} passenger{form.passengers === 1 ? "" : "s"}, {cabinsNeeded} cabin
              {cabinsNeeded === 1 ? "" : "s"}
            </dd>
          </div>
        </dl>
      </section>

      <section className="crm-entry-section">
        <h4 className="crm-entry-section-title">Booking details</h4>

        {bookingCruises.length === 0 ? (
          <p className="meta crm-entry-empty">
            {hasAcceptedCruise
              ? "No accepted or deposited cruises are available to show."
              : "Accept one or more proposed cruises to populate booking details for CRM entry."}
          </p>
        ) : (
          bookingCruises.map((cruise) => {
            const cabinRooms = proposedCruiseToCabinRooms(cruise, cabinsNeeded);

            return (
              <article className="crm-entry-cruise-card" key={cruise.id}>
                <header className="crm-entry-cruise-header">
                  <div>
                    <h5>
                      {cruise.cruise_line} · {cruise.ship}
                    </h5>
                    <p className="meta">
                      Departs {formatDate(cruise.departure_date)} · {cruise.number_of_nights} nights ·{" "}
                      {cruise.itinerary_name}
                    </p>
                  </div>
                  <span className="crm-entry-status-badge">{cruise.status}</span>
                </header>

                <dl className="crm-entry-grid">
                  <div>
                    <dt>Deposit due</dt>
                    <dd>{formatDate(cruise.deposit_due_date)}</dd>
                  </div>
                  <div>
                    <dt>Final payment due</dt>
                    <dd>{formatDate(cruise.final_payment_due_date)}</dd>
                  </div>
                  <div>
                    <dt>Total cost</dt>
                    <dd>{formatMoney(cruise.cost)}</dd>
                  </div>
                </dl>

                <div className="crm-entry-room-list">
                  {cabinRooms.map((room, cabinIndex) => {
                    const cabinLabel = proposedRoomLabel(cabinIndex, cabinsNeeded);
                    const reservationIds = proposedCruiseReservationIds(cruise, cabinsNeeded)[cabinIndex]
                      ?.map((value) => value.trim())
                      .filter(Boolean) ?? [];
                    const roomPassengers = cruise.room_passengers?.[cabinIndex] ?? [];

                    return (
                      <article className="crm-entry-room-card" key={`${cruise.id}-room-${cabinIndex}`}>
                        <h6>{cabinLabel}</h6>

                        <dl className="crm-entry-grid">
                          <div>
                            <dt>Category</dt>
                            <dd>{displayValue(room.room_category)}</dd>
                          </div>
                          <div>
                            <dt>Room number</dt>
                            <dd>{displayValue(room.room_number)}</dd>
                          </div>
                          <div className="crm-entry-grid-stack">
                            <div>
                              <dt>Deposit</dt>
                              <dd>{formatMoney(room.deposit_amount)}</dd>
                            </div>
                            <div>
                              <dt>Commission</dt>
                              <dd>{formatMoney(room.commission ?? 0)}</dd>
                            </div>
                          </div>
                          <div>
                            <dt>Total cost</dt>
                            <dd>{formatMoney(room.cost)}</dd>
                          </div>
                          <div>
                            <dt>Passengers in room</dt>
                            <dd>{room.passengers_in_room}</dd>
                          </div>
                          <div>
                            <dt>Reservation IDs</dt>
                            <dd>{reservationIds.length > 0 ? reservationIds.join(", ") : "—"}</dd>
                          </div>
                        </dl>

                        <div className="crm-entry-subsection">
                          <p className="crm-entry-subsection-title">Includes</p>
                          <ul className="crm-entry-list">
                            {formatProposedCruiseIncludes(room.includes).map((includeLine) => (
                              <li key={includeLine}>{includeLine}</li>
                            ))}
                          </ul>
                        </div>

                        <div className="crm-entry-subsection">
                          <p className="crm-entry-subsection-title">Passengers in this room</p>
                          {roomPassengers.length === 0 ? (
                            <p className="meta">No passengers assigned to this room.</p>
                          ) : (
                            <div className="crm-entry-passenger-list">
                              {roomPassengers.map((passenger) => (
                                <PassengerDetailCard
                                  key={passenger.id}
                                  passenger={passenger}
                                  cruiseLine={cruise.cruise_line}
                                />
                              ))}
                            </div>
                          )}
                        </div>
                      </article>
                    );
                  })}
                </div>
              </article>
            );
          })
        )}
      </section>

      {acceptedInsurance.length > 0 ? (
        <section className="crm-entry-section">
          <h4 className="crm-entry-section-title">Insurance details</h4>
          {acceptedInsurance.map((quote) => (
            <article className="crm-entry-insurance-card" key={quote.id}>
              <header className="crm-entry-cruise-header">
                <div>
                  <h5>
                    {quote.carrier} · {quote.plan_name}
                  </h5>
                  <p className="meta">Per-trip travel insurance</p>
                </div>
                <span className="crm-entry-status-badge">{quote.status}</span>
              </header>
              <dl className="crm-entry-grid">
                <div>
                  <dt>Premium</dt>
                  <dd>{formatMoney(quote.premium_cost)}</dd>
                </div>
                <div>
                  <dt>Cancellation coverage</dt>
                  <dd>{formatMoney(quote.cancellation_coverage)}</dd>
                </div>
                <div>
                  <dt>Medical coverage</dt>
                  <dd>{formatMoney(quote.medical_coverage)}</dd>
                </div>
                <div>
                  <dt>Medical evacuation coverage</dt>
                  <dd>{formatMoney(quote.medical_evac_coverage)}</dd>
                </div>
                <div>
                  <dt>Quote mailed to client</dt>
                  <dd>{quote.quote_mailed ? "Yes" : "No"}</dd>
                </div>
              </dl>
            </article>
          ))}
        </section>
      ) : null}

      <div className="crm-entry-actions">
        <button type="button" className="modal-secondary" onClick={() => void handleCopySummary()}>
          Copy CRM summary
        </button>
        {copyMessage ? <p className="meta crm-entry-copy-message">{copyMessage}</p> : null}
      </div>

      <section className="crm-entry-section">
        <h4 className="crm-entry-section-title">CRM checklist</h4>
        <div className="crm-entry-checklist">
          <label className="crm-entry-checklist-item">
            <input
              type="checkbox"
              disabled={readOnly || saving}
              checked={checklist.create_trip}
              onChange={(event) =>
                setChecklist((current) => ({ ...current, create_trip: event.target.checked }))
              }
            />
            Create trip
          </label>
          <label className="crm-entry-checklist-item">
            <input
              type="checkbox"
              disabled={readOnly || saving}
              checked={checklist.create_bookings}
              onChange={(event) =>
                setChecklist((current) => ({ ...current, create_bookings: event.target.checked }))
              }
            />
            Create bookings (one per room) with reminders and communications
          </label>
          <label className="crm-entry-checklist-item">
            <input
              type="checkbox"
              disabled={readOnly || saving}
              checked={checklist.sent_agency_invoice}
              onChange={(event) =>
                setChecklist((current) => ({ ...current, sent_agency_invoice: event.target.checked }))
              }
            />
            Sent agency invoice
          </label>
        </div>
      </section>

      {!readOnly ? (
        <button
          type="button"
          disabled={saving || !allComplete || !hasAcceptedCruise}
          onClick={() => void handleSaveAndComplete()}
        >
          {saving ? "Saving..." : "Mark CRM steps complete"}
        </button>
      ) : null}
    </div>
  );
}