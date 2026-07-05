import { describe, expect, it } from "vitest";
import { getLastOrganizationHandle, setLastOrganizationHandle } from "./organizationHandleStorage";

describe("organizationHandleStorage", () => {
  it("stores and reads the last organization handle from a cookie", () => {
    document.cookie = "sailspipeline_org_handle=; Path=/; Max-Age=0";
    setLastOrganizationHandle("sea-kers-travel");
    expect(getLastOrganizationHandle()).toBe("sea-kers-travel");
  });
});
