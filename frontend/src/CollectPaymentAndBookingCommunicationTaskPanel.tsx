import { useEffect, useMemo, useState } from "react";
import { updateProposedCruise, updateTask } from "./api";
import {
  buildCabinPaymentRows,
  formatMoney,
  normalizeCabinPricing,
  readPaymentCollectionState,
} from "./cabinPricing";
import { normalizeCabinHoldReservationDrafts, type CabinHoldReservationIds } from "./cabinHoldReservations";
import {
  PROPOSED_CRUISE_STATUS_DEPOSITED,
  TASK_STATUS_DONE,
} from "./formOptions";
import type { ProposedCruise, RequestTask } from "./types";
import { formatDate } from "./utils";
import { formatPassengerNames } from "./proposedCruiseRooms";

type CollectPaymentAndBookingCommunicationTaskPanelProps = {
  requestId: number;
  cabinsNeeded: number;
  reservationIds: CabinHoldReservationIds | null | undefined;
  acceptedCruise: ProposedCruise | null;
  task: RequestTask;
  disabled: boolean;
  isDone: boolean;
  onChanged: () => Promise<void>;
  onError: (message: string) => void;
  onSaved: () => void;
};

export default function CollectPaymentAndBookingCommunicationTaskPanel({
  requestId,
  cabinsNeeded,
  reservationIds,
  acceptedCruise,
  task,
  disabled,
  isDone,
  onChanged,
  onError,
  onSaved,
}: CollectPaymentAndBookingCommunicationTaskPanelProps) {
  const safeCabinsNeeded = Math.max(1, cabinsNeeded);
  const normalizedReservations = useMemo(
    () => normalizeCabinHoldReservationDrafts(reservationIds, safeCabinsNeeded),
    [reservationIds, safeCabinsNeeded],
  );
  const cabinPricing = useMemo(
    () =>
      acceptedCruise
        ? normalizeCabinPricing(acceptedCruise.cabin_pricing, safeCabinsNeeded, {
            deposit_amount: acceptedCruise.deposit_amount,
            cost: acceptedCruise.cost,
          })
        : [],
    [acceptedCruise, safeCabinsNeeded],
  );
  const paymentRows = useMemo(() => {
    if (!acceptedCruise) {
      return [];
    }

    return buildCabinPaymentRows(
      normalizedReservations.map((cabinIds) => cabinIds.map((value) => value.trim()).filter(Boolean)),
      cabinPricing,
      acceptedCruise.deposit_due_date,
      acceptedCruise.final_payment_due_date,
    );
  }, [acceptedCruise, cabinPricing, normalizedReservations]);

  const [collected, setCollected] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState(false);
  const readOnly = disabled || isDone;

  useEffect(() => {
    setCollected(readPaymentCollectionState(task.result));
  }, [task.id, task.result]);

  const allCollected = paymentRows.length > 0 && paymentRows.every((row) => collected[row.key]);

  async function handleSaveAndComplete() {
    if (!acceptedCruise) {
      onError("An accepted cruise is required before collecting payment.");
      return;
    }

    if (paymentRows.length === 0) {
      onError("Enter cabin hold reservation IDs before collecting payment.");
      return;
    }

    if (!allCollected) {
      onError("Mark payment collected for every reservation before completing this task.");
      return;
    }

    setSaving(true);
    onError("");
    try {
      await updateProposedCruise(requestId, acceptedCruise.id, {
        status: PROPOSED_CRUISE_STATUS_DEPOSITED,
        cabin_pricing: cabinPricing,
      });
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

  if (!acceptedCruise) {
    return (
      <div className="workflow-task-guidance">
        <p>Record an accepted cruise before collecting deposit or final payment.</p>
      </div>
    );
  }

  if (acceptedCruise.status === PROPOSED_CRUISE_STATUS_DEPOSITED) {
    return (
      <div className="workflow-task-guidance">
        <p>The accepted cruise is already marked as Deposited.</p>
      </div>
    );
  }

  if (paymentRows.length === 0) {
    return (
      <div className="workflow-task-guidance">
        <p>Enter cabin hold reservation IDs for each required cabin before collecting payment.</p>
      </div>
    );
  }

  return (
    <div className="collect-payment-booking-panel">
      <p className="field-hint">
        Send the cruise line booking communication for each reservation, collect the amount shown, then check payment
        collected for every reservation. Deposit due dates and final payment due dates come from the accepted cruise.
      </p>

      <div className="collect-payment-booking-summary meta">
        <span>Deposit due: {formatDate(acceptedCruise.deposit_due_date)}</span>
        <span>Final payment due: {formatDate(acceptedCruise.final_payment_due_date)}</span>
      </div>

      <div className="collect-payment-booking-list">
        {paymentRows.map((row) => (
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
                  Passengers: {formatPassengerNames(acceptedCruise.room_passengers?.[row.cabinIndex] ?? [])}
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

      {!readOnly ? (
        <button type="button" disabled={saving || !allCollected} onClick={() => void handleSaveAndComplete()}>
          {saving ? "Saving..." : "Mark payments collected and complete task"}
        </button>
      ) : null}
    </div>
  );
}
