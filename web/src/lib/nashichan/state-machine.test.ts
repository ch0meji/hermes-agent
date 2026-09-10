import { describe, expect, it } from "vitest";

import {
  nashichanStateForConnection,
  nashichanStateForEvent,
} from "./state-machine";

describe("nashichanStateForConnection", () => {
  it("maps connection failures to offline", () => {
    expect(nashichanStateForConnection("closed")).toEqual({ state: "offline" });
    expect(nashichanStateForConnection("error")).toEqual({ state: "offline" });
    expect(nashichanStateForConnection("open", true)).toEqual({ state: "offline" });
  });

  it("maps connecting to working without overriding an open connection", () => {
    expect(nashichanStateForConnection("connecting")).toEqual({ state: "working" });
    expect(nashichanStateForConnection("open")).toBeNull();
  });
});

describe("nashichanStateForEvent", () => {
  it("maps model activity to thinking", () => {
    expect(nashichanStateForEvent("thinking.delta")?.state).toBe("thinking");
    expect(nashichanStateForEvent("reasoning.delta")?.state).toBe("thinking");
    expect(nashichanStateForEvent("message.start")?.state).toBe("thinking");
  });

  it("maps tools to working and then back to thinking", () => {
    expect(nashichanStateForEvent("tool.start")?.state).toBe("working");
    expect(nashichanStateForEvent("tool.generating")?.state).toBe("working");
    expect(nashichanStateForEvent("tool.complete")?.state).toBe("thinking");
  });

  it("maps requests to approval or security", () => {
    expect(nashichanStateForEvent("clarify.request")?.state).toBe("approval");
    expect(nashichanStateForEvent("mcp.setup.request")?.state).toBe("approval");
    expect(nashichanStateForEvent("sudo.request")?.state).toBe("security");
    expect(nashichanStateForEvent("secret.request")?.state).toBe("security");
  });

  it("maps warning and error notices by level", () => {
    expect(
      nashichanStateForEvent("notification.show", { level: "warning" })?.state,
    ).toBe("warning");
    expect(
      nashichanStateForEvent("notification.show", { level: "error" })?.state,
    ).toBe("error");
  });

  it("prefers security for credential notices", () => {
    expect(
      nashichanStateForEvent("notification.show", {
        level: "warning",
        kind: "credential_missing",
      })?.state,
    ).toBe("security");
  });

  it("uses transient success and celebration states", () => {
    expect(nashichanStateForEvent("message.complete")).toMatchObject({
      state: "success",
      transientMs: expect.any(Number),
    });
    expect(nashichanStateForEvent("reaction")).toMatchObject({
      state: "celebrate",
      transientMs: expect.any(Number),
    });
  });

  it("ignores unknown events", () => {
    expect(nashichanStateForEvent("something.unknown")).toBeNull();
    expect(nashichanStateForEvent(undefined)).toBeNull();
  });
});
