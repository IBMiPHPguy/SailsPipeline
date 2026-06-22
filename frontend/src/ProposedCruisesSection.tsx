import { forwardRef, useEffect, useImperativeHandle, useMemo, useState } from "react";
import { addProposedCruise, updateProposedCruise } from "./api";
import AcceptProposedCruiseChooser from "./AcceptProposedCruiseChooser";
import {
  acceptProposedCruiseForRequest,
  canQuickAcceptProposedCruise,
  canQuickRejectProposedCruise,
} from "./acceptProposedCruise";
import {
  cabinHoldReservationDisplayLines,
} from "./CabinHoldReservationFields";
import {
  proposedCruiseReservationIds,
  sanitizeCabinHoldReservationIds,
  type CabinHoldReservationIds,
} from "./cabinHoldReservations";
import {
  PROPOSED_CRUISE_STATUS_ACCEPTED,
  PROPOSED_CRUISE_STATUS_DEPOSITED,
  PROPOSED_CRUISE_STATUS_PROPOSED,
  PROPOSED_CRUISE_STATUS_REJECTED,
} from "./formOptions";
import ProposedCruiseQuoteCard from "./ProposedCruiseQuoteCard";
import ProposedCruiseModal from "./ProposedCruiseModal";
import ProposedCruiseRejectModal from "./ProposedCruiseRejectModal";
import { buildProposedCruiseRejectionPayload } from "./proposedCruiseRejection";
import type { ProposedCruise, ProposedCruiseInput, RequestPassenger } from "./types";

type ProposedCruisesSectionProps = {
  requestId: number;
  cabinsNeeded: number;
  cruises: ProposedCruise[];
  passengers: RequestPassenger[];
  requestPassengerCount: number;
  disabled: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  embedded?: boolean;
  allowAcceptProposedCruise?: boolean;
};

export type ProposedCruisesSectionHandle = {
  openCreateModal: () => void;
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

export default forwardRef<ProposedCruisesSectionHandle, ProposedCruisesSectionProps>(
  function ProposedCruisesSection(
  {
  requestId,
  cabinsNeeded,
  cruises,
  passengers,
  requestPassengerCount,
  disabled,
  onChanged,
  onError,
  embedded = false,
  allowAcceptProposedCruise = false,
}: ProposedCruisesSectionProps,
  ref,
) {
  const [activeTab, setActiveTab] = useState<CruiseTab>("active");
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCruise, setEditingCruise] = useState<ProposedCruise | null>(null);
  const [saving, setSaving] = useState(false);
  const [savingRoom, setSavingRoom] = useState(false);
  const [displayCruises, setDisplayCruises] = useState(cruises);
  const [statusUpdatingId, setStatusUpdatingId] = useState<number | null>(null);
  const [rejectingCruise, setRejectingCruise] = useState<ProposedCruise | null>(null);

  useEffect(() => {
    setDisplayCruises(cruises);
  }, [cruises]);

  const activeCruises = useMemo(() => displayCruises.filter(isActiveProposedCruise), [displayCruises]);
  const rejectedCruises = useMemo(
    () => displayCruises.filter((cruise) => cruise.status === PROPOSED_CRUISE_STATUS_REJECTED),
    [displayCruises],
  );

  function openCreateModal() {
    setEditingCruise(null);
    setModalOpen(true);
  }

  useImperativeHandle(ref, () => ({ openCreateModal }), []);

  function openEditModal(cruise: ProposedCruise) {
    setEditingCruise(cruise);
    setModalOpen(true);
  }

  function applyOptimisticAccept(cruiseId: number) {
    setDisplayCruises((current) =>
      current.map((cruise) =>
        cruise.id === cruiseId ? { ...cruise, status: PROPOSED_CRUISE_STATUS_ACCEPTED } : cruise,
      ),
    );
  }

  function applyOptimisticReject(
    cruiseId: number,
    rejection: ReturnType<typeof buildProposedCruiseRejectionPayload>,
  ) {
    setDisplayCruises((current) =>
      current.map((cruise) =>
        cruise.id === cruiseId
          ? {
              ...cruise,
              status: PROPOSED_CRUISE_STATUS_REJECTED,
              rejection_reason: rejection.rejection_reason,
              rejection_reason_detail: rejection.rejection_reason_detail ?? null,
            }
          : cruise,
      ),
    );
  }

  function openRejectModal(cruise: ProposedCruise) {
    onError("");
    setRejectingCruise(cruise);
  }

  async function handleConfirmReject(rejection: ReturnType<typeof buildProposedCruiseRejectionPayload>) {
    if (!rejectingCruise) {
      return;
    }

    const cruise = rejectingCruise;
    setStatusUpdatingId(cruise.id);
    applyOptimisticReject(cruise.id, rejection);
    try {
      await updateProposedCruise(requestId, cruise.id, {
        status: PROPOSED_CRUISE_STATUS_REJECTED,
        ...rejection,
      });
      setRejectingCruise(null);
      await onChanged();
    } catch (rejectError) {
      setDisplayCruises(cruises);
      const message = rejectError instanceof Error ? rejectError.message : "Unable to reject proposed cruise.";
      onError(message);
    } finally {
      setStatusUpdatingId(null);
    }
  }

  async function handleQuickAccept(cruise: ProposedCruise) {
    setStatusUpdatingId(cruise.id);
    onError("");
    applyOptimisticAccept(cruise.id);
    try {
      await acceptProposedCruiseForRequest(requestId, cruise.id, cruises);
      await onChanged();
    } catch (acceptError) {
      setDisplayCruises(cruises);
      const message = acceptError instanceof Error ? acceptError.message : "Unable to accept proposed cruise.";
      onError(message);
    } finally {
      setStatusUpdatingId(null);
    }
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
      const currentReservations = proposedCruiseReservationIds(editingCruise, cabinsNeeded);
      const nextReservations =
        roomReservationIds !== undefined
          ? currentReservations.map((cabinIds, index) =>
              index === cabinIndex ? (roomReservationIds.length > 0 ? roomReservationIds : [""]) : cabinIds,
            )
          : currentReservations;
      const updated = await updateProposedCruise(requestId, editingCruise.id, {
        ...payload,
        ...(roomReservationIds !== undefined
          ? {
              cabin_hold_reservation_ids: sanitizeCabinHoldReservationIds(nextReservations, cabinsNeeded),
            }
          : {}),
      });
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
        await updateProposedCruise(requestId, editingCruise.id, {
          ...payload,
          ...(nextCabinHoldReservationIds !== undefined
            ? {
                cabin_hold_reservation_ids: sanitizeCabinHoldReservationIds(
                  nextCabinHoldReservationIds,
                  cabinsNeeded,
                ),
              }
            : {}),
        });
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
      const normalizedReservations = proposedCruiseReservationIds(cruise, cabinsNeeded);
      const reservationLines = showCabinDetails
        ? cabinHoldReservationDisplayLines(normalizedReservations)
        : [];

      return (
        <ProposedCruiseQuoteCard
          key={cruise.id}
          cruise={cruise}
          cabinsNeeded={cabinsNeeded}
          cabinHoldReservationIds={normalizedReservations}
          showReservationDisplay={showCabinDetails}
          reservationLines={reservationLines}
          requestPassengerCount={requestPassengerCount}
          disabled={disabled}
          statusUpdating={statusUpdatingId === cruise.id}
          onAccept={
            !disabled && canQuickAcceptProposedCruise(cruise, displayCruises)
              ? () => void handleQuickAccept(cruise)
              : undefined
          }
          onReject={
            !disabled && canQuickRejectProposedCruise(cruise)
              ? () => openRejectModal(cruise)
              : undefined
          }
          onEdit={() => openEditModal(cruise)}
        />
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

      <ProposedCruiseRejectModal
        open={rejectingCruise !== null}
        cruise={rejectingCruise}
        rejecting={rejectingCruise !== null && statusUpdatingId === rejectingCruise.id}
        onCancel={() => {
          if (statusUpdatingId === null) {
            setRejectingCruise(null);
          }
        }}
        onConfirm={(rejection) => void handleConfirmReject(rejection)}
      />

      <ProposedCruiseModal
        open={modalOpen}
        requestId={requestId}
        cruise={editingCruise}
        passengers={passengers}
        cabinsNeeded={cabinsNeeded}
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
},
);
