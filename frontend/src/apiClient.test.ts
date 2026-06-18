import { describe, expect, it } from "vitest";
import { parseApiError } from "./apiClient";

describe("parseApiError", () => {
  it("returns string detail from API errors", async () => {
    const response = new Response(JSON.stringify({ detail: "Only draft communications can be deleted." }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });

    await expect(parseApiError(response, "Fallback")).resolves.toBe(
      "Only draft communications can be deleted.",
    );
  });

  it("joins validation error messages", async () => {
    const response = new Response(
      JSON.stringify({ detail: [{ msg: "Field required" }, { msg: "Invalid email" }] }),
      { status: 422, headers: { "Content-Type": "application/json" } },
    );

    await expect(parseApiError(response, "Fallback")).resolves.toBe("Field required Invalid email");
  });

  it("falls back when response is not JSON", async () => {
    const response = new Response("not json", { status: 500 });
    await expect(parseApiError(response, "Something failed")).resolves.toBe("Something failed");
  });
});
