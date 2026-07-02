import { describe, expect, it } from "vitest";
import {
  formatCardNumberInput,
  formatExpirationInput,
  toCcAuthCardPayload,
  validateCcAuthCardForm,
} from "./ccAuthCardValidation";

describe("ccAuthCardValidation", () => {
  it("formats card number in groups of four", () => {
    expect(formatCardNumberInput("4111111111111111")).toBe("4111 1111 1111 1111");
  });

  it("formats expiration as MM/YY", () => {
    expect(formatExpirationInput("1230")).toBe("12/30");
  });

  it("accepts a valid card form", () => {
    const error = validateCcAuthCardForm({
      cardholderName: "Jane Cruise",
      cardNumber: "4111 1111 1111 1111",
      expiration: "12/30",
      securityCode: "123",
    });
    expect(error).toBeNull();
  });

  it("rejects invalid card numbers", () => {
    const error = validateCcAuthCardForm({
      cardholderName: "Jane Cruise",
      cardNumber: "4111 1111 1111 1112",
      expiration: "12/30",
      securityCode: "123",
    });
    expect(error).toMatch(/valid card number/i);
  });

  it("rejects expired dates", () => {
    const error = validateCcAuthCardForm({
      cardholderName: "Jane Cruise",
      cardNumber: "4111 1111 1111 1111",
      expiration: "01/20",
      securityCode: "123",
    });
    expect(error).toMatch(/expiration/i);
  });

  it("builds API payload with normalized values", () => {
    expect(
      toCcAuthCardPayload({
        cardholderName: " Jane Cruise ",
        cardNumber: "4111 1111 1111 1111",
        expiration: "12/30",
        securityCode: "123",
      }),
    ).toEqual({
      cardholder_name: "Jane Cruise",
      card_number: "4111111111111111",
      expiration: "12/30",
      security_code: "123",
    });
  });
});
