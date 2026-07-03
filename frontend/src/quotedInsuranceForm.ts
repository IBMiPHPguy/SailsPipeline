import type { QuotedInsurance, QuotedInsuranceInput } from "./types";

export const emptyQuotedInsuranceForm: QuotedInsuranceInput = {
  carrier: "",
  premium_cost: 0,
  plan_name: "",
  cancellation_coverage: 0,
  medical_coverage: 0,
  medical_evac_coverage: 0,
};

export function quotedInsuranceToForm(quote: QuotedInsurance): QuotedInsuranceInput {
  return {
    carrier: quote.carrier,
    premium_cost: quote.premium_cost,
    plan_name: quote.plan_name,
    cancellation_coverage: quote.cancellation_coverage,
    medical_coverage: quote.medical_coverage,
    medical_evac_coverage: quote.medical_evac_coverage,
    status: quote.status,
    quote_mailed: quote.quote_mailed,
  };
}

export function quotedInsuranceStatusClass(status: string): string {
  if (status === "Accepted") {
    return "quote-status-accepted";
  }
  if (status === "Declined") {
    return "quote-status-declined";
  }
  return "quote-status-proposed";
}

export function quotedInsuranceStatusOptionClass(status: string): string {
  if (status === "Accepted") {
    return "status-option-accepted";
  }
  if (status === "Declined") {
    return "status-option-declined";
  }
  return "status-option-proposed";
}

export function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value);
}
