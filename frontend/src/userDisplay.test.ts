import { describe, expect, it } from "vitest";
import {
  formatUsernameDisplayName,
  initialsFromUsername,
  usernameFirstLast,
} from "./userDisplay";

describe("userDisplay", () => {
  it("formats dotted usernames", () => {
    expect(formatUsernameDisplayName("robert.binetti")).toBe("Robert Binetti");
    expect(usernameFirstLast("robert.binetti")).toEqual({
      firstName: "Robert",
      lastName: "Binetti",
    });
    expect(initialsFromUsername("robert.binetti")).toBe("RB");
  });

  it("handles single-part usernames", () => {
    expect(formatUsernameDisplayName("admin")).toBe("Admin");
    expect(usernameFirstLast("admin")).toEqual({ firstName: "Admin", lastName: "" });
    expect(initialsFromUsername("admin")).toBe("AD");
  });
});
