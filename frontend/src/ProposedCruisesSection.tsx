import { useMemo, useState } from "react";
import { addProposedCruise, updateProposedCruise, updateRequest } from "./api";
import AcceptProposedCruiseChooser from "./AcceptProposedCruiseChooser";
import {
  CabinHoldReservationDisplay,
  cabinHoldReservationDisplayLines,
} from "./CabinHoldReservationFields";
import {
  normalizeCabinHoldReservationDrafts,
  sanitizeCabinHoldReservationIds,
  type CabinHoldReservationIds,
} from "./cabinHoldReservations";
import { proposedCruiseToCabinRooms } from "./cabinRooms";
import { formatMoney } from "./cabinPricing";
import {
  PROPOSED_CRUISE_STATUS_ACCEPTED,
  PROPOSED_CRUISE_STATUS_DEPOSITED,
  PROPOSED_CRUISE_STATUS_PROPOSED,
  PROPOSED_CRUISE_STATUS_REJECTED,
} from "./formOptions";
import ProposedCruiseModal from "./ProposedCruiseModal";
import { proposedCruiseStatusClass } from "./proposedCruiseForm";
import { formatPassengerNames, proposedRoomLabel } from "./proposedCruiseRooms";
import type { ProposedCruise, ProposedCruiseInput, RequestPassenger } from "./types";
import { formatDate } from "./utils";

type ProposedCruisesSectionProps = {
  requestId: number;
  cabinsNeeded: number;
  cabinHoldReservationIds: CabinHoldReservationIds;
  cruises: ProposedCruise[];
  passengers: RequestPassenger[];
  disabled: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  embedded?: boolean;
  allowAcceptProposedCruise?: boolean;
};

type CruiseTab = "active" | "rejected";

function isActiveProposedCruise(cruise: ProposedCruise): boolean {
  return (
    cruise.status === PROPOSED_CRUISE_STATUS_PROPOSED ||
    cruise.status === PROPOSED_CRUISE_STATUS_ACCEPTED ||
    cruise.status === PROPOSED_CRUISE_STATUS_DEPOSITED
  );
}

function cruiseHasCabinDetails(cruise: ProposedCruise): boolean {
  return (
    cruise.status === PROPOSED_CRUISE_STATUS_ACCEPTED ||
    cruise.status === PROPOSED_CRUISE_STATUS_DEPOSITED
  );
}

export default function ProposedCruisesSection({
  requestId,
  cabinsNeeded,
  cabinHoldReservationIds,
  cruises,
  passengers,
  disabled,
  onChanged,
  onError,
  embedded = false,
  allowAcceptProposedCruise = false,
}: ProposedCruisesSectionProps) {
  const [activeTab, setActiveTab] = useState<CruiseTab>("active");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCruise, setEditingCruise] = useState<ProposedCruise | null>(null);
  const [saving, setSaving] = useState(false);
  const [savingRoom, setSavingRoom] = useState(false);

  const activeCruises = useMemo(() => cruises.filter(isActiveProposedCruise), [cruises]);
  const rejectedCruises = useMemo(
    () => cruises.filter((cruise) => cruise.status === PROPOSED_CRUISE_STATUS_REJECTED),
    [cruises],
  );
  const hasLockedCruise = useMemo(
    () =>
      cruises.some(
        (cruise) =>
          cruise.status === PROPOSED_CRUISE_STATUS_ACCEPTED ||
          cruise.status === PROPOSED_CRUISE_STATUS_DEPOSITED,
      ),
    [cruises],
  );

  function openCreateModal() {
    setEditingCruise(null);
    setModalOpen(true);
  }

  function openEditModal(cruise: ProposedCruise) {
    setEditingCruise(cruise);
    setModalOpen(true);
  }

  async function handleSaveRoom(
    cabinIndex: number,
    payload: ProposedCruiseInput,
    roomReservationIds?: string[],
  ): Promise<ProposedCruise> {
    if (!editingCruise) {
      throw new Error("Save the proposed cruise first.");
    }

    setSavingRoom(true);
    onError("");
    try {
      const updated = await updateProposedCruise(requestId, editingCruise.id, payload);
      if (roomReservationIds !== undefined) {
        const nextReservations = normalizeCabinHoldReservationDrafts(
          cabinHoldReservationIds,
          cabinsNeeded,
        ).map((cabinIds, index) =>
          index === cabinIndex ? (roomReservationIds.length > 0 ? roomReservationIds : [""]) : cabinIds,
        );
        await updateRequest(requestId, {
          cabin_hold_reservation_ids: sanitizeCabinHoldReservationIds(nextReservations, cabinsNeeded),
        });
      }
      setEditingCruise(updated);
      await onChanged();
      return updated;
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : "Unable to save room.";
      onError(message);
      throw saveError instanceof Error ? saveError : new Error(message);
    } finally {
      setSavingRoom(false);
    }
  }

  async function handleSave(
    payload: ProposedCruiseInput,
    nextCabinHoldReservationIds?: CabinHoldReservationIds,
  ): Promise<void> {
    setSaving(true);
    onError("");
    try {
      if (editingCruise) {
        await updateProposedCruise(requestId, editingCruise.id, payload);
        if (nextCabinHoldReservationIds !== undefined) {
          await updateRequest(requestId, {
            cabin_hold_reservation_ids: sanitizeCabinHoldReservationIds(
              nextCabinHoldReservationIds,
              cabinsNeeded,
            ),
          });
        }
      } else {
        await addProposedCruise(requestId, payload);
      }
      setModalOpen(false);
      setEditingCruise(null);
      await onChanged();
    } catch (saveError) {
      const message = saveError instanceof Error ? saveError.message : "Unable to save proposed cruise.";
      onError(message);
      throw saveError instanceof Error ? saveError : new Error(message);
    } finally {
      setSaving(false);
    }
  }

  function renderCruiseList(cruiseList: ProposedCruise[], emptyMessage: string) {
    if (cruiseList.length === 0) {
      return <p className="meta">{emptyMessage}</p>;
    }

    return cruiseList.map((cruise) => {
      const showCabinDetails = cruiseHasCabinDetails(cruise);
      const reservationLines = showCabinDetails
        ? cabinHoldReservationDisplayLines(cabinHoldReservationIds)
        : [];
      const cabinRooms = proposedCruiseToCabinRooms(cruise, cabinsNeeded);
      const normalizedReservations = normalizeCabinHoldReservationDrafts(
        cabinHoldReservationIds,
        cabinsNeeded,
      );

      return (
      <article className="proposed-cruise-item" key={cruise.id}>
        <div className="proposed-cruise-item-header">
          <div>
            <strong>
              {cruise.cruise_line} · {cruise.ship}
            </strong>
            <div className="meta">
              Departs {formatDate(cruise.departure_date)} · {cruise.number_of_nights} nights · {cruise.itinerary_name}
            </div>
            <div className="meta">
              Deposit due {formatDate(cruise.deposit_due_date)} · Final payment due{" "}
              {formatDate(cruise.final_payment_due_date)} · {formatMoney(cruise.cost)} total
            </div>
            <div className="proposed-cruise-cabin-pricing-display">
              {cabinRooms.map((room, cabinIndex) => {
                const cabinLabel = proposedRoomLabel(cabinIndex, cabinsNeeded);
                const reservationIds = (normalizedReservations[cabinIndex] ?? [])
                  .map((value) => value.trim())
                  .filter(Boolean);
                const roomPassengerNames = formatPassengerNames(cruise.room_passengers?.[cabinIndex] ?? []);

                return (
                  <div className="proposed-cruise-cabin-pricing-line meta" key={`${cruise.id}-cabin-${cabinIndex}`}>
                    <strong>{cabinLabel}</strong>
                    <span>
                      {room.room_category} · {room.room_number}
                    </span>
                    <span>
                      Deposit {formatMoney(room.deposit_amount)} · Total {formatMoney(room.cost)} · Up to{" "}
                      {room.passengers_in_room} passenger{room.passengers_in_room === 1 ? "" : "s"}
                    </span>
                    <span>{roomPassengerNames}</span>
                    {reservationIds.length > 0 ? (
                      <span>Reservations: {reservationIds.join(", ")}</span>
                    ) : null}
                  </div>
                );
              })}
            </div>
            {reservationLines.length > 0 && cabinsNeeded === 1 ? (
              <CabinHoldReservationDisplay lines={reservationLines} />
            ) : null}
          </div>
          <span className={`proposed-cruise-status ${proposedCruiseStatusClass(cruise.status)}`}>
            {cruise.status}
          </span>
        </div>
        {!disabled ? (
          <button type="button" className="modal-secondary" onClick={() => openEditModal(cruise)}>
            Edit
          </button>
        ) : null}
      </article>
      );
    });
  }

  const body = (
    <div className="proposed-cruises-section-body">
      {allowAcceptProposedCruise ? (
        <AcceptProposedCruiseChooser
          requestId={requestId}
          cruises={cruises}
          disabled={disabled}
          onChanged={onChanged}
          onError={onError}
          intro="Enter Trip in CRM is active. Choose which proposed cruise this booking is for before continuing."
        />
      ) : null}

      <div className="proposed-cruises-toolbar">
        <div className="proposed-cruises-subtabs" role="tablist" aria-label="Proposed cruise status">
          <button
            type="button"
            role="tab"
            id="proposed-cruises-tab-active"
            aria-selected={activeTab === "active"}
            aria-controls="proposed-cruises-panel-active"
            className={`proposed-cruises-subtab proposed-cruises-subtab--active${
              activeTab === "active" ? " is-active" : ""
            }`}
            onClick={() => setActiveTab("active")}
          >
            <span className="proposed-cruises-subtab-label">Proposed &amp; accepted</span>
            <span className="proposed-cruises-subtab-count">{activeCruises.length}</span>
          </button>
          <button
            type="button"
            role="tab"
            id="proposed-cruises-tab-rejected"
            aria-selected={activeTab === "rejected"}
            aria-controls="proposed-cruises-panel-rejected"
            className={`proposed-cruises-subtab proposed-cruises-subtab--rejected${
              activeTab === "rejected" ? " is-active" : ""
            }`}
            onClick={() => setActiveTab("rejected")}
          >
            <span className="proposed-cruises-subtab-label">Rejected</span>
            <span className="proposed-cruises-subtab-count">{rejectedCruises.length}</span>
          </button>
        </div>

        {activeTab === "active" && !disabled && !hasLockedCruise ? (
          <button type="button" className="proposed-cruises-add-button" onClick={openCreateModal}>
            Add proposed cruise
          </button>
        ) : null}
      </div>

      {activeTab === "active" ? (
        <div
          className="proposed-cruises-panel"
          role="tabpanel"
          id="proposed-cruises-panel-active"
          aria-labelledby="proposed-cruises-tab-active"
        >
          <div className="proposed-cruise-list">
            {renderCruiseList(activeCruises, "No proposed or accepted cruises yet.")}
          </div>
        </div>
      ) : (
        <div
          className="proposed-cruises-panel"
          role="tabpanel"
          id="proposed-cruises-panel-rejected"
          aria-labelledby="proposed-cruises-tab-rejected"
        >
          <div className="proposed-cruise-list">
            {renderCruiseList(rejectedCruises, "No rejected cruises yet.")}
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      {embedded ? (
        body
      ) : (
        <section className="section-card proposed-cruises-card">
          <header className="section-card-header">
            <h3>Proposed Cruises</h3>
          </header>
          <div className="section-card-body">{body}</div>
        </section>
      )}

      <ProposedCruiseModal
        open={modalOpen}
        requestId={requestId}
        cruise={editingCruise}
        passengers={passengers}
        cabinsNeeded={cabinsNeeded}
        cabinHoldReservationIds={cabinHoldReservationIds}
        allCruises={cruises}
        allowAcceptProposedCruise={allowAcceptProposedCruise}
        saving={saving}
        savingRoom={savingRoom}
        disabled={disabled}
        onCancel={() => {
          setModalOpen(false);
          setEditingCruise(null);
        }}
        onSave={handleSave}
        onSaveRoom={handleSaveRoom}
        onAccepted={async () => {
          setModalOpen(false);
          setEditingCruise(null);
          await onChanged();
        }}
        onError={onError}
      />
    </>
  );
}
