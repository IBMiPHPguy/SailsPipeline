import { describe, expect, it } from "vitest";
import { contrastTextColor } from "./portalBranding";

describe("contrastTextColor", () => {
  it("returns dark text on light brand colors", () => {
    expect(contrastTextColor("#ffffff")).toBe("#111111");
    expect(contrastTextColor("#17a2b8")).toBe("#111111");
  });

  it("returns light text on dark brand colors", () => {
    expect(contrastTextColor("#0d5c75")).toBe("#ffffff");
    expect(contrastTextColor("#111111")).toBe("#ffffff");
  });
});
