import { describe, expect, it } from "vitest";
import { normalizeCabinPricing, sumCabinPricing } from "./cabinPricing";
import { formatPassengerContact } from "./passengerDisplay";
import { formatDate, isHtmlCommunicationBody, isRequestStale } from "./utils";

describe("cabinPricing", () => {
  it("splits fallback totals across cabins", () => {
    const pricing = normalizeCabinPricing(null, 2, { deposit_amount: 100, cost: 2000 });
    expect(pricing).toEqual([
      { deposit_amount: 50, cost: 1000 },
      { deposit_amount: 50, cost: 1000 },
    ]);
  });

  it("sums cabin pricing entries", () => {
    expect(
      sumCabinPricing([
        { deposit_amount: 50, cost: 1000 },
        { deposit_amount: 75, cost: 1500 },
      ]),
    ).toEqual({ deposit_amount: 125, cost: 2500 });
  });
});

describe("passengerDisplay", () => {
  it("returns null when contact fields are empty", () => {
    expect(formatPassengerContact(null, "  ")).toBeNull();
  });

  it("joins email and phone when both are present", () => {
    expect(formatPassengerContact("jane@example.com", "5551234567")).toBe(
      "jane@example.com · 5551234567",
    );
  });
});

describe("utils", () => {
  it("formats ISO dates as MM/DD/YYYY", () => {
    expect(formatDate("2026-06-14")).toBe("06/14/2026");
  });

  it("detects HTML communication bodies", () => {
    expect(isHtmlCommunicationBody("<!DOCTYPE html><html></html>")).toBe(true);
    expect(isHtmlCommunicationBody("Plain text email")).toBe(false);
  });

  it("marks requests older than three days as stale", () => {
    const fourDaysAgo = new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString();
    expect(isRequestStale(fourDaysAgo)).toBe(true);
  });
});
