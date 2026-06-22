import { useEffect, useMemo, useState } from "react";
import { updateProposedCruise, updateTask } from "./api";
import {
  buildCabinPaymentRows,
  formatMoney,
  normalizeCabinPricing,
  readPaymentCollectionState,
  type CabinPaymentRow,
  type CabinPricing,
} from "./cabinPricing";
import { proposedCruiseReservationIds } from "./cabinHoldReservations";
import {
  PROPOSED_CRUISE_STATUS_ACCEPTED,
  PROPOSED_CRUISE_STATUS_DEPOSITED,
  TASK_STATUS_DONE,
} from "./formOptions";
import type { ProposedCruise, RequestTask } from "./types";
import AcceptedCruiseSummary from "./AcceptedCruiseSummary";
import { formatDate } from "./utils";
import { formatPassengerNames, proposedRoomLabel } from "./proposedCruiseRooms";

type CollectPaymentAndBookingCommunicationTaskPanelProps = {
  requestId: number;
  cabinsNeeded: number;
  bookingCruises: ProposedCruise[];
  task: RequestTask;
  disabled: boolean;
  isDone: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  onSaved: () => void;
};

type CruisePaymentSection = {
  cruise: ProposedCruise;
  cabinPricing: CabinPricing;
  rows: CabinPaymentRow[];
};

function sortBookingCruises(cruises: ProposedCruise[]): ProposedCruise[] {
  return [...cruises].sort(
    (left, right) => left.departure_date.localeCompare(right.departure_date) || left.id - right.id,
  );
}

function buildCruisePaymentSection(cruise: ProposedCruise, cabinsNeeded: number): CruisePaymentSection {
  const safeCabinsNeeded = Math.max(1, cabinsNeeded);
  const reservationIds = proposedCruiseReservationIds(cruise, safeCabinsNeeded).map((cabinIds) =>
    cabinIds.map((value) => value.trim()).filter(Boolean),
  );
  const cabinPricing = normalizeCabinPricing(cruise.cabin_pricing, safeCabinsNeeded, {
    deposit_amount: cruise.deposit_amount,
    cost: cruise.cost,
  });
  const rows = buildCabinPaymentRows(
    reservationIds,
    cabinPricing,
    cruise.deposit_due_date,
    cruise.final_payment_due_date,
  ).map((row) => ({
    ...row,
    key: `${cruise.id}:${row.key}`,
    cabinLabel: proposedRoomLabel(row.cabinIndex, safeCabinsNeeded),
  }));

  return { cruise, cabinPricing, rows };
}

export default function CollectPaymentAndBookingCommunicationTaskPanel({
  requestId,
  cabinsNeeded,
  bookingCruises,
  task,
  disabled,
  isDone,
  onChanged,
  onError,
  onSaved,
}: CollectPaymentAndBookingCommunicationTaskPanelProps) {
  const safeCabinsNeeded = Math.max(1, cabinsNeeded);
  const readOnly = disabled || isDone;
  const sortedBookingCruises = useMemo(() => sortBookingCruises(bookingCruises), [bookingCruises]);
  const acceptedCruises = useMemo(
    () => sortedBookingCruises.filter((cruise) => cruise.status === PROPOSED_CRUISE_STATUS_ACCEPTED),
    [sortedBookingCruises],
  );
  const paymentSections = useMemo(
    () => acceptedCruises.map((cruise) => buildCruisePaymentSection(cruise, safeCabinsNeeded)),
    [acceptedCruises, safeCabinsNeeded],
  );
  const paymentRows = useMemo(() => paymentSections.flatMap((section) => section.rows), [paymentSections]);

  const [collected, setCollected] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setCollected(readPaymentCollectionState(task.result));
  }, [task.id, task.result]);

  const allCollected = paymentRows.length > 0 && paymentRows.every((row) => collected[row.key]);
  const allCruisesHaveReservations = paymentSections.every((section) => section.rows.length > 0);

  async function handleSaveAndComplete() {
    if (acceptedCruises.length === 0) {
      onError("An accepted cruise is required before collecting payment.");
      return;
    }

    if (paymentRows.length === 0) {
      onError("Enter cabin hold reservation IDs for each accepted cruise before collecting payment.");
      return;
    }

    if (!allCruisesHaveReservations) {
      const missing = paymentSections.find((section) => section.rows.length === 0);
      onError(
        missing
          ? `Enter reservation IDs for every room on ${missing.cruise.ship} before collecting payment.`
          : "Enter cabin hold reservation IDs for each accepted cruise before collecting payment.",
      );
      return;
    }

    if (!allCollected) {
      onError("Mark payment collected for every reservation before completing this task.");
      return;
    }

    setSaving(true);
    onError("");
    try {
      for (const section of paymentSections) {
        if (section.rows.length === 0) {
          continue;
        }
        await updateProposedCruise(requestId, section.cruise.id, {
          status: PROPOSED_CRUISE_STATUS_DEPOSITED,
          cabin_pricing: section.cabinPricing,
        });
      }

      await updateTask(requestId, task.id, {
        status: TASK_STATUS_DONE,
        result: { payments_collected: collected },
      });
      await onChanged();
      onSaved();
    } catch (saveError) {
      onError(saveError instanceof Error ? saveError.message : "Unable to complete payment collection task.");
    } finally {
      setSaving(false);
    }
  }

  if (sortedBookingCruises.length === 0) {
    return (
      <div className="workflow-task-guidance">
        <p>Record an accepted cruise before collecting deposit or final payment.</p>
      </div>
    );
  }

  if (acceptedCruises.length === 0) {
    return (
      <div className="workflow-task-guidance">
        <p>All accepted cruises are already marked as Deposited.</p>
      </div>
    );
  }

  if (paymentRows.length === 0) {
    return (
      <div className="workflow-task-guidance">
        <p>Enter cabin hold reservation IDs for each room on every accepted cruise before collecting payment.</p>
      </div>
    );
  }

  return (
    <div className="collect-payment-booking-panel">
      <p className="field-hint">
        {paymentSections.length === 1
          ? "Send the cruise line booking communication for each reservation, collect the amount shown, then check payment collected for every room."
          : "This request has multiple accepted cruises. Send booking communications and collect payment for each reservation on every accepted cruise below."}
      </p>

      <div className="collect-payment-booking-cruise-list">
        {paymentSections.map((section) => (
          <section className="collect-payment-booking-cruise-card" key={section.cruise.id}>
            <header className="collect-payment-booking-cruise-header">
              <AcceptedCruiseSummary cruise={section.cruise} />
              <p className="meta">
                {section.cruise.number_of_nights} nights · {section.cruise.itinerary_name}
              </p>
              <div className="collect-payment-booking-summary meta">
                <span>Deposit due: {formatDate(section.cruise.deposit_due_date)}</span>
                <span>Final payment due: {formatDate(section.cruise.final_payment_due_date)}</span>
              </div>
            </header>

            {section.rows.length === 0 ? (
              <p className="meta">Enter reservation IDs for this cruise before collecting payment.</p>
            ) : (
              <div className="collect-payment-booking-list">
                {section.rows.map((row) => (
                  <article className="collect-payment-booking-item" key={row.key}>
                    <div className="collect-payment-booking-item-header">
                      <div>
                        <strong>
                          {row.cabinLabel} · Reservation {row.reservationId}
                        </strong>
                        <div className="meta">
                          {row.amountLabel}: {formatMoney(row.amount)}
                        </div>
                        <div className="meta">
                          Passengers:{" "}
                          {formatPassengerNames(section.cruise.room_passengers?.[row.cabinIndex] ?? [])}
                        </div>
                      </div>
                    </div>
                    <label className="collect-payment-booking-checkbox">
                      <input
                        type="checkbox"
                        disabled={readOnly || saving}
                        checked={Boolean(collected[row.key])}
                        onChange={(event) =>
                          setCollected((current) => ({
                            ...current,
                            [row.key]: event.target.checked,
                          }))
                        }
                      />
                      Payment collected
                    </label>
                  </article>
                ))}
              </div>
            )}
          </section>
        ))}
      </div>

      {!readOnly ? (
        <button
          type="button"
          disabled={saving || !allCollected || !allCruisesHaveReservations}
          onClick={() => void handleSaveAndComplete()}
        >
          {saving ? "Saving..." : "Mark payments collected and complete task"}
        </button>
      ) : null}
    </div>
  );
}
