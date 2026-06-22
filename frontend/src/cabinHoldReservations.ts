export type CabinHoldReservationIds = string[][];

export function normalizeCabinHoldReservationDrafts(
  raw: CabinHoldReservationIds | null | undefined,
  cabinsNeeded: number,
): CabinHoldReservationIds {
  const safeCabinsNeeded = Math.max(1, cabinsNeeded);
  const source = raw ?? [];
  const drafts: CabinHoldReservationIds = [];

  for (let cabinIndex = 0; cabinIndex < safeCabinsNeeded; cabinIndex += 1) {
    const cabinIds = source[cabinIndex];
    if (!Array.isArray(cabinIds) || cabinIds.length === 0) {
      drafts.push([""]);
      continue;
    }
    drafts.push(cabinIds.map((reservationId) => reservationId ?? ""));
  }

  return drafts;
}

export function proposedCruiseReservationIds(
  cruise: { cabin_hold_reservation_ids?: CabinHoldReservationIds | null },
  cabinsNeeded: number,
): CabinHoldReservationIds {
  return normalizeCabinHoldReservationDrafts(cruise.cabin_hold_reservation_ids, cabinsNeeded);
}

export function sanitizeCabinHoldReservationIds(
  drafts: CabinHoldReservationIds,
  cabinsNeeded: number,
): CabinHoldReservationIds {
  return normalizeCabinHoldReservationDrafts(drafts, cabinsNeeded).map((cabinIds) =>
    cabinIds.map((reservationId) => reservationId.trim()).filter(Boolean),
  );
}

export function validateCabinHoldReservationDrafts(
  drafts: CabinHoldReservationIds,
  cabinsNeeded: number,
): string | null {
  const normalizedDrafts = normalizeCabinHoldReservationDrafts(drafts, cabinsNeeded);

  for (let cabinIndex = 0; cabinIndex < normalizedDrafts.length; cabinIndex += 1) {
    const reservationIds = normalizedDrafts[cabinIndex].map((value) => value.trim()).filter(Boolean);
    if (reservationIds.length === 0) {
      return `Enter at least one reservation ID for cabin ${cabinIndex + 1}.`;
    }
  }

  return null;
}

export type CabinHoldReservationDisplayLine = {
  label: string;
  reservationIds: string[];
};

export function buildCabinHoldReservationDisplayLines(
  reservationIds: CabinHoldReservationIds | null | undefined,
): CabinHoldReservationDisplayLine[] {
  if (!reservationIds?.length) {
    return [];
  }

  const multiCabin = reservationIds.length > 1;

  return reservationIds
    .map((cabinIds, cabinIndex) => {
      const reservationIdList = cabinIds.map((value) => value.trim()).filter(Boolean);
      if (reservationIdList.length === 0) {
        return null;
      }

      return {
        label: multiCabin ? `Cabin ${cabinIndex + 1}` : "Reservation ID",
        reservationIds: reservationIdList,
      };
    })
    .filter((line): line is CabinHoldReservationDisplayLine => line !== null);
}

export function cabinHoldReservationLabel(cabinIndex: number, cabinsNeeded: number): string {
  return cabinsNeeded === 1 ? "Reservation ID" : `Cabin ${cabinIndex + 1} reservation ID`;
}
