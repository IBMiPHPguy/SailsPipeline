import { FormEvent, useEffect, useRef, useState } from "react";
import {
  cloneCabinRooms,
  emptyCabinRooms,
  getPassengersInRoomLimits,
  mergeRoomIntoCabinRooms,
  normalizeCabinRooms,
  proposedCruiseToCabinRooms,
  syncLegacyFieldsFromCabinRooms,
  validateCabinRoom,
} from "./cabinRooms";
import {
  normalizeCabinHoldReservationDrafts,
  type CabinHoldReservationIds,
} from "./cabinHoldReservations";
import { acceptProposedCruiseForRequest } from "./acceptProposedCruise";
import { hasAcceptedOrDepositedProposedCruise } from "./crmEntrySummary";
import {
  PROPOSED_CRUISE_STATUSES,
  PROPOSED_CRUISE_STATUS_ACCEPTED,
  PROPOSED_CRUISE_STATUS_DEPOSITED,
  PROPOSED_CRUISE_STATUS_PROPOSED,
} from "./formOptions";
import {
  buildProposedCruisePayload,
  emptyProposedCruiseForm,
  proposedCruiseStatusOptionClass,
  proposedCruiseToForm,
} from "./proposedCruiseForm";
import ProposedCruiseRoomEditor from "./ProposedCruiseRoomEditor";
import {
  flattenRoomPassengerIds,
  normalizeRoomPassengerIds,
  proposedCruiseToRoomPassengerIds,
  proposedRoomLabel,
  validateRoomPassengerIds,
} from "./proposedCruiseRooms";
import CruiseLineSelect from "./CruiseLineSelect";
import StatusPicker from "./StatusPicker";
import type { ProposedCruise, ProposedCruiseInput, RequestPassenger } from "./types";

type PersistedRoomState = {
  cabin_rooms: ReturnType<typeof cloneCabinRooms>;
  room_passenger_ids: number[][];
  reservationDrafts: CabinHoldReservationIds;
};

type ProposedCruiseModalProps = {
  open: boolean;
  requestId: number;
  cruise: ProposedCruise | null;
  passengers: RequestPassenger[];
  cabinsNeeded: number;
  cabinHoldReservationIds: CabinHoldReservationIds;
  allCruises?: ProposedCruise[];
  allowAcceptProposedCruise?: boolean;
  saving: boolean;
  savingRoom: boolean;
  disabled: boolean;
  onCancel: () => void;
  onSave: (payload: ProposedCruiseInput, cabinHoldReservationIds?: CabinHoldReservationIds) => Promise<void>;
  onSaveRoom: (
    cabinIndex: number,
    payload: ProposedCruiseInput,
    roomReservationIds?: string[],
  ) => Promise<ProposedCruise>;
  onAccepted?: () => Promise<void>;
  onError?: (message: string) => void;
};

export default function ProposedCruiseModal({
  open,
  requestId,
  cruise,
  passengers,
  cabinsNeeded,
  cabinHoldReservationIds,
  allCruises = [],
  allowAcceptProposedCruise = false,
  saving,
  savingRoom,
  disabled,
  onCancel,
  onSave,
  onSaveRoom,
  onAccepted,
  onError,
}: ProposedCruiseModalProps) {
  const [form, setForm] = useState<ProposedCruiseInput>(emptyProposedCruiseForm);
  const [reservationDrafts, setReservationDrafts] = useState<CabinHoldReservationIds>([]);
  const [error, setError] = useState("");
  const [roomSaveMessage, setRoomSaveMessage] = useState("");
  const [accepting, setAccepting] = useState(false);
  const initSessionRef = useRef<string | null>(null);
  const persistedRef = useRef<PersistedRoomState | null>(null);
  const effectiveStatus = form.status ?? cruise?.status;
  const showAcceptThisCruise =
    allowAcceptProposedCruise &&
    Boolean(cruise) &&
    effectiveStatus === PROPOSED_CRUISE_STATUS_PROPOSED &&
    !hasAcceptedOrDepositedProposedCruise(allCruises);
  const showCabinHoldFields =
    effectiveStatus === PROPOSED_CRUISE_STATUS_ACCEPTED ||
    effectiveStatus === PROPOSED_CRUISE_STATUS_DEPOSITED;
  const cabinRooms = normalizeCabinRooms(form.cabin_rooms, cabinsNeeded, {
    room_category: form.room_category,
    room_number: form.room_number,
    passengers_in_room: form.passengers_in_room,
    deposit_amount: form.deposit_amount,
    cost: form.cost,
    includes: form.includes,
    cabin_pricing: form.cabin_pricing,
  });

  function syncPersistedFromForm(
    nextForm: ProposedCruiseInput,
    nextReservationDrafts: CabinHoldReservationIds,
  ) {
    persistedRef.current = {
      cabin_rooms: cloneCabinRooms(
        normalizeCabinRooms(nextForm.cabin_rooms, cabinsNeeded, {
          room_category: nextForm.room_category,
          room_number: nextForm.room_number,
          passengers_in_room: nextForm.passengers_in_room,
          deposit_amount: nextForm.deposit_amount,
          cost: nextForm.cost,
          includes: nextForm.includes,
          cabin_pricing: nextForm.cabin_pricing,
        }),
      ),
      room_passenger_ids: normalizeRoomPassengerIds(nextForm.room_passenger_ids, cabinsNeeded),
      reservationDrafts: normalizeCabinHoldReservationDrafts(nextReservationDrafts, cabinsNeeded),
    };
  }

  useEffect(() => {
    if (!open) {
      initSessionRef.current = null;
      persistedRef.current = null;
      setForm(emptyProposedCruiseForm);
      setReservationDrafts([]);
      setError("");
      setRoomSaveMessage("");
      return;
    }

    const sessionKey = `${cruise?.id ?? "new"}:${cabinsNeeded}`;
    if (initSessionRef.current === sessionKey) {
      return;
    }

    initSessionRef.current = sessionKey;
    const nextForm = cruise
      ? proposedCruiseToForm(cruise, cabinsNeeded)
      : {
          ...emptyProposedCruiseForm,
          room_passenger_ids: normalizeRoomPassengerIds([], cabinsNeeded),
          cabin_rooms: emptyCabinRooms(cabinsNeeded),
        };
    const nextReservationDrafts = normalizeCabinHoldReservationDrafts(cabinHoldReservationIds, cabinsNeeded);

    setForm(nextForm);
    setReservationDrafts(nextReservationDrafts);
    syncPersistedFromForm(nextForm, nextReservationDrafts);
    setError("");
    setRoomSaveMessage("");
  }, [open, cruise, cabinsNeeded, cabinHoldReservationIds]);

  if (!open) {
    return null;
  }

  function updateCabinRooms(nextCabinRooms: typeof cabinRooms) {
    const legacy = syncLegacyFieldsFromCabinRooms(nextCabinRooms);
    setForm((current) => ({
      ...current,
      cabin_rooms: nextCabinRooms,
      room_category: legacy.room_category,
      room_number: legacy.room_number,
      passengers_in_room: legacy.passengers_in_room,
      deposit_amount: legacy.deposit_amount,
      cost: legacy.cost,
      includes: legacy.includes,
      cabin_pricing: legacy.cabin_pricing,
    }));
  }

  async function handleSaveRoom(cabinIndex: number) {
    if (disabled || !cruise || !persistedRef.current) {
      return;
    }

    const room = cabinRooms[cabinIndex];
    const roomError = validateCabinRoom(room, cabinIndex, cabinsNeeded);
    if (roomError) {
      setError(roomError);
      setRoomSaveMessage("");
      return;
    }

    const roomPassengerIds = normalizeRoomPassengerIds(form.room_passenger_ids, cabinsNeeded);
    const activeRoomPassengers = roomPassengerIds[cabinIndex] ?? [];
    if (activeRoomPassengers.length > room.passengers_in_room) {
      setError(
        `${proposedRoomLabel(cabinIndex, cabinsNeeded)} exceeds the passengers-in-room limit.`,
      );
      setRoomSaveMessage("");
      return;
    }

    const duplicateElsewhere = activeRoomPassengers.some((passengerId) =>
      roomPassengerIds.some(
        (roomIds, index) => index !== cabinIndex && roomIds.includes(passengerId),
      ),
    );
    if (duplicateElsewhere) {
      setError("Each passenger can only be assigned to one room.");
      setRoomSaveMessage("");
      return;
    }

    if (form.final_payment_due_date < form.deposit_due_date) {
      setError("Final payment due date must be on or after the deposit due date.");
      setRoomSaveMessage("");
      return;
    }

    const persisted = persistedRef.current;
    const mergedRooms = mergeRoomIntoCabinRooms(persisted.cabin_rooms, cabinRooms, cabinIndex);
    const mergedPassengerIds = persisted.room_passenger_ids.map((roomIds, index) => {
      if (index === cabinIndex) {
        return [...activeRoomPassengers];
      }
      return roomIds.filter((passengerId) => !activeRoomPassengers.includes(passengerId));
    });
    const payload = buildProposedCruisePayload(
      {
        ...form,
        cabin_rooms: mergedRooms,
        room_passenger_ids: mergedPassengerIds,
      },
      cabinsNeeded,
    );

    const roomReservationIds = showCabinHoldFields
      ? (reservationDrafts[cabinIndex] ?? []).map((value) => value.trim()).filter(Boolean)
      : undefined;

    setError("");
    try {
      const updated = await onSaveRoom(cabinIndex, payload, roomReservationIds);
      const updatedReservations = normalizeCabinHoldReservationDrafts(
        roomReservationIds !== undefined
          ? persisted.reservationDrafts.map((cabinIds, index) =>
              index === cabinIndex ? (roomReservationIds.length > 0 ? roomReservationIds : [""]) : cabinIds,
            )
          : persisted.reservationDrafts,
        cabinsNeeded,
      );

      persistedRef.current = {
        cabin_rooms: cloneCabinRooms(proposedCruiseToCabinRooms(updated, cabinsNeeded)),
        room_passenger_ids: proposedCruiseToRoomPassengerIds(updated, cabinsNeeded),
        reservationDrafts: updatedReservations,
      };

      const savedPassengerIds = proposedCruiseToRoomPassengerIds(updated, cabinsNeeded);

      setForm((current) => {
        const savedRooms = proposedCruiseToCabinRooms(updated, cabinsNeeded);
        const nextRooms = normalizeCabinRooms(current.cabin_rooms, cabinsNeeded, {
          room_category: current.room_category,
          room_number: current.room_number,
          passengers_in_room: current.passengers_in_room,
          deposit_amount: current.deposit_amount,
          cost: current.cost,
          includes: current.includes,
          cabin_pricing: current.cabin_pricing,
        }).map((draftRoom, index) => (index === cabinIndex ? savedRooms[cabinIndex] : draftRoom));
        const legacy = syncLegacyFieldsFromCabinRooms(nextRooms);

        return {
          ...current,
          cabin_rooms: nextRooms,
          room_passenger_ids: savedPassengerIds,
          passenger_ids: flattenRoomPassengerIds(savedPassengerIds),
          room_category: legacy.room_category,
          room_number: legacy.room_number,
          passengers_in_room: legacy.passengers_in_room,
          deposit_amount: legacy.deposit_amount,
          cost: legacy.cost,
          includes: legacy.includes,
          cabin_pricing: legacy.cabin_pricing,
        };
      });

      if (roomReservationIds !== undefined) {
        setReservationDrafts(updatedReservations);
      }

      setRoomSaveMessage(`${proposedRoomLabel(cabinIndex, cabinsNeeded)} saved.`);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save room.");
      setRoomSaveMessage("");
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (disabled) {
      return;
    }

    if (form.final_payment_due_date < form.deposit_due_date) {
      setError("Final payment due date must be on or after the deposit due date.");
      return;
    }

    const roomPassengerIds = normalizeRoomPassengerIds(form.room_passenger_ids, cabinsNeeded);
    const roomPassengerError = validateRoomPassengerIds(
      roomPassengerIds,
      getPassengersInRoomLimits(cabinRooms),
    );
    if (roomPassengerError) {
      setError(roomPassengerError);
      return;
    }

    for (let cabinIndex = 0; cabinIndex < cabinRooms.length; cabinIndex += 1) {
      const roomValidationError = validateCabinRoom(cabinRooms[cabinIndex], cabinIndex, cabinsNeeded);
      if (roomValidationError) {
        setError(roomValidationError);
        return;
      }
    }

    setError("");
    const savingWithReservations =
      (form.status ?? cruise?.status) === PROPOSED_CRUISE_STATUS_ACCEPTED ||
      (form.status ?? cruise?.status) === PROPOSED_CRUISE_STATUS_DEPOSITED;

    try {
      await onSave(
        buildProposedCruisePayload({ ...form, room_passenger_ids: roomPassengerIds }, cabinsNeeded),
        savingWithReservations ? reservationDrafts : undefined,
      );
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to save proposed cruise.");
    }
  }

  async function handleAcceptThisCruise() {
    if (!cruise || disabled) {
      return;
    }

    setAccepting(true);
    setError("");
    onError?.("");
    try {
      await acceptProposedCruiseForRequest(requestId, cruise.id, allCruises);
      if (onAccepted) {
        await onAccepted();
      }
    } catch (acceptError) {
      const message = acceptError instanceof Error ? acceptError.message : "Unable to accept proposed cruise.";
      setError(message);
      onError?.(message);
    } finally {
      setAccepting(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onClick={onCancel}>
      <div
        className="modal-card modal-card-wide modal-card-proposed-cruise"
        role="dialog"
        aria-modal="true"
        aria-labelledby="proposed-cruise-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="modal-card-header">
          <h3 id="proposed-cruise-title">{cruise ? "Edit proposed cruise" : "Proposed cruise"}</h3>
        </header>

        <form className="modal-form-layout" onSubmit={handleSubmit} noValidate>
          <div className="modal-scroll-body proposed-cruise-form">
            <section className="proposed-cruise-cruise-level">
              <p className="field-label">Cruise details</p>
              <div className="field-row field-row--aligned">
                <label className="field-stack">
                  <span className="field-stack-label">Departure date</span>
                  <span className="field-hint field-hint--placeholder" aria-hidden="true">
                    &nbsp;
                  </span>
                  <input
                    required
                    disabled={disabled || saving || savingRoom}
                    type="date"
                    value={form.departure_date}
                    onChange={(event) => setForm({ ...form, departure_date: event.target.value })}
                  />
                </label>
                <label className="field-stack">
                  <span className="field-stack-label">Number of nights</span>
                  <span className="field-hint field-hint--placeholder" aria-hidden="true">
                    &nbsp;
                  </span>
                  <input
                    required
                    disabled={disabled || saving || savingRoom}
                    type="number"
                    min={1}
                    max={365}
                    value={form.number_of_nights}
                    onChange={(event) =>
                      setForm({ ...form, number_of_nights: Number(event.target.value) })
                    }
                  />
                </label>
              </div>

              <div className="field-row field-row--aligned">
                <label className="field-stack">
                  <span className="field-stack-label">Cruise line</span>
                  <span className="field-hint field-hint--placeholder" aria-hidden="true">
                    &nbsp;
                  </span>
                  <CruiseLineSelect
                    required
                    disabled={disabled || saving || savingRoom}
                    value={form.cruise_line}
                    onChange={(cruise_line) => setForm({ ...form, cruise_line })}
                  />
                </label>
                <label className="field-stack">
                  <span className="field-stack-label">Ship</span>
                  <span className="field-hint field-hint--placeholder" aria-hidden="true">
                    &nbsp;
                  </span>
                  <input
                    required
                    disabled={disabled || saving || savingRoom}
                    value={form.ship}
                    onChange={(event) => setForm({ ...form, ship: event.target.value })}
                  />
                </label>
              </div>

              <label className="field-stack">
                <span className="field-stack-label">Itinerary name</span>
                <span className="field-hint field-hint--placeholder" aria-hidden="true">
                  &nbsp;
                </span>
                <input
                  required
                  disabled={disabled || saving || savingRoom}
                  value={form.itinerary_name}
                  onChange={(event) => setForm({ ...form, itinerary_name: event.target.value })}
                />
              </label>

              <label className="field-stack">
                <span className="field-stack-label">Itinerary details</span>
                <span className="field-hint">
                  One day or port per line. Used in the client proposal email instead of AI-generated guesses.
                </span>
                <textarea
                  rows={6}
                  disabled={disabled || saving || savingRoom}
                  value={form.itinerary_details ?? ""}
                  placeholder={"Day 1 — Miami, Florida (Embarkation)\nDay 2 — At sea\nDay 3 — Cozumel, Mexico"}
                  onChange={(event) => setForm({ ...form, itinerary_details: event.target.value })}
                />
              </label>

              <div className="field-row field-row--aligned">
                <label className="field-stack">
                  <span className="field-stack-label">Deposit due date</span>
                  <span className="field-hint field-hint--placeholder" aria-hidden="true">
                    &nbsp;
                  </span>
                  <input
                    required
                    disabled={disabled || saving || savingRoom}
                    type="date"
                    value={form.deposit_due_date}
                    onChange={(event) => setForm({ ...form, deposit_due_date: event.target.value })}
                  />
                </label>
                <label className="field-stack">
                  <span className="field-stack-label">Final payment due date</span>
                  <span className="field-hint field-hint--placeholder" aria-hidden="true">
                    &nbsp;
                  </span>
                  <input
                    required
                    disabled={disabled || saving || savingRoom}
                    type="date"
                    value={form.final_payment_due_date}
                    onChange={(event) =>
                      setForm({ ...form, final_payment_due_date: event.target.value })
                    }
                  />
                </label>
              </div>
            </section>

            {showAcceptThisCruise ? (
              <section className="proposed-cruise-accept-section">
                <p className="field-hint">
                  Enter Trip in CRM is active. Mark this cruise as the accepted booking before continuing.
                </p>
                <button
                  type="button"
                  className="modal-secondary"
                  disabled={disabled || saving || savingRoom || accepting}
                  onClick={() => void handleAcceptThisCruise()}
                >
                  {accepting ? "Saving..." : "Accept this cruise"}
                </button>
              </section>
            ) : null}

            {cruise && !showAcceptThisCruise ? (
              <section className="proposed-cruise-status-section">
                <StatusPicker
                  label="Proposed cruise status"
                  value={form.status ?? cruise.status}
                  options={PROPOSED_CRUISE_STATUSES}
                  onChange={(status) => setForm({ ...form, status })}
                  disabled={disabled || saving || savingRoom}
                  getOptionClassName={proposedCruiseStatusOptionClass}
                />
              </section>
            ) : null}

            <div className="proposed-cruise-section-divider" role="separator" aria-hidden="true" />

            <ProposedCruiseRoomEditor
              cabinsNeeded={cabinsNeeded}
              cabinRooms={cabinRooms}
              roomPassengerIds={normalizeRoomPassengerIds(form.room_passenger_ids, cabinsNeeded)}
              passengers={passengers}
              reservationDrafts={reservationDrafts}
              showReservationFields={showCabinHoldFields}
              disabled={disabled || saving || savingRoom}
              canSaveRoom={Boolean(cruise)}
              savingRoom={savingRoom}
              roomSaveMessage={roomSaveMessage}
              onSaveRoom={(cabinIndex) => {
                setRoomSaveMessage("");
                void handleSaveRoom(cabinIndex);
              }}
              onActiveRoomChange={() => setRoomSaveMessage("")}
              onCabinRoomsChange={updateCabinRooms}
              onRoomPassengerIdsChange={(room_passenger_ids) =>
                setForm((current) => ({
                  ...current,
                  room_passenger_ids,
                  passenger_ids: flattenRoomPassengerIds(room_passenger_ids),
                }))
              }
              onReservationDraftsChange={setReservationDrafts}
            />

            {error ? <p className="status error">{error}</p> : null}
          </div>

          <div className="modal-actions modal-actions-footer">
            <button type="button" className="modal-secondary" disabled={saving || savingRoom} onClick={onCancel}>
              Cancel
            </button>
            {!disabled ? (
              <button type="submit" disabled={saving || savingRoom}>
                {saving
                  ? "Saving..."
                  : cruise
                    ? "Save & close"
                    : "Add proposed cruise"}
              </button>
            ) : null}
          </div>
        </form>
      </div>
    </div>
  );
}
