import type { CabinHoldReservationIds } from "./cabinHoldReservations";

export type CabinPricingEntry = {
  deposit_amount: number;
  cost: number;
};

export type CabinPricing = CabinPricingEntry[];

export type CabinPaymentRow = {
  key: string;
  cabinIndex: number;
  reservationIndex: number;
  cabinLabel: string;
  reservationId: string;
  amount: number;
  amountLabel: string;
};

export function normalizeCabinPricing(
  raw: CabinPricing | null | undefined,
  cabinsNeeded: number,
  fallback?: { deposit_amount: number; cost: number },
): CabinPricing {
  const safeCabinsNeeded = Math.max(1, cabinsNeeded);
  const source = raw ?? [];
  const perDeposit = fallback ? fallback.deposit_amount / safeCabinsNeeded : 0;
  const perCost = fallback ? fallback.cost / safeCabinsNeeded : 0;
  const pricing: CabinPricing = [];

  for (let cabinIndex = 0; cabinIndex < safeCabinsNeeded; cabinIndex += 1) {
    const entry = source[cabinIndex];
    pricing.push({
      deposit_amount: entry?.deposit_amount ?? perDeposit,
      cost: entry?.cost ?? perCost,
    });
  }

  return pricing;
}

export function sumCabinPricing(pricing: CabinPricing): { deposit_amount: number; cost: number } {
  return pricing.reduce(
    (totals, entry) => ({
      deposit_amount: totals.deposit_amount + Number(entry.deposit_amount || 0),
      cost: totals.cost + Number(entry.cost || 0),
    }),
    { deposit_amount: 0, cost: 0 },
  );
}

export function getPaymentAmountDue(
  cabin: CabinPricingEntry,
  depositDueDate: string,
  finalPaymentDueDate: string,
): { amount: number; amountLabel: string } {
  if (depositDueDate < finalPaymentDueDate) {
    return {
      amount: Number(cabin.deposit_amount),
      amountLabel: "Deposit due",
    };
  }

  return {
    amount: Number(cabin.cost),
    amountLabel: "Total cost",
  };
}

export function buildCabinPaymentRows(
  reservationIds: CabinHoldReservationIds,
  cabinPricing: CabinPricing,
  depositDueDate: string,
  finalPaymentDueDate: string,
): CabinPaymentRow[] {
  const rows: CabinPaymentRow[] = [];

  cabinPricing.forEach((cabin, cabinIndex) => {
    const cabinReservations = (reservationIds[cabinIndex] ?? [])
      .map((reservationId) => reservationId.trim())
      .filter(Boolean);
    const { amount, amountLabel } = getPaymentAmountDue(cabin, depositDueDate, finalPaymentDueDate);
    const cabinLabel = cabinPricing.length === 1 ? "Cabin" : `Cabin ${cabinIndex + 1}`;

    cabinReservations.forEach((reservationId, reservationIndex) => {
      rows.push({
        key: `${cabinIndex}:${reservationIndex}`,
        cabinIndex,
        reservationIndex,
        cabinLabel,
        reservationId,
        amount,
        amountLabel,
      });
    });
  });

  return rows;
}

export function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}

export function paymentCollectionKey(cabinIndex: number, reservationIndex: number): string {
  return `${cabinIndex}:${reservationIndex}`;
}

export function readPaymentCollectionState(
  result: Record<string, unknown> | null | undefined,
): Record<string, boolean> {
  const raw = result?.payments_collected;
  if (!raw || typeof raw !== "object") {
    return {};
  }

  const collected: Record<string, boolean> = {};
  for (const [key, value] of Object.entries(raw)) {
    collected[key] = Boolean(value);
  }
  return collected;
}
