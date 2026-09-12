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
    expect(nashichanStateForEvent("message.delta")?.state).toBe("thinking");
  });

  it("maps tools and read requests to working, then tool completion to thinking", () => {
    expect(nashichanStateForEvent("tool.start")?.state).toBe("working");
    expect(nashichanStateForEvent("tool.generating")?.state).toBe("working");
    expect(nashichanStateForEvent("tool.progress.download")?.state).toBe("working");
    expect(nashichanStateForEvent("terminal.read.request")?.state).toBe("working");
    expect(nashichanStateForEvent("preview.read.request")?.state).toBe("working");
    expect(nashichanStateForEvent("preview.act.request")?.state).toBe("working");
    expect(nashichanStateForEvent("window.read.request")?.state).toBe("working");
    expect(nashichanStateForEvent("tool.complete")?.state).toBe("thinking");
  });

  it("maps requests to approval or security", () => {
    expect(nashichanStateForEvent("clarify.request")?.state).toBe("approval");
    expect(nashichanStateForEvent("approval.request")?.state).toBe("approval");
    expect(nashichanStateForEvent("mcp.setup.request")?.state).toBe("approval");
    expect(nashichanStateForEvent("sudo.request")?.state).toBe("security");
    expect(nashichanStateForEvent("secret.request")?.state).toBe("security");
  });

  it("maps update lifecycle activity to update", () => {
    expect(nashichanStateForEvent("update.start")?.state).toBe("update");
    expect(nashichanStateForEvent("update.progress")?.state).toBe("update");
    expect(nashichanStateForEvent("updater.start")?.state).toBe("update");
    expect(nashichanStateForEvent("updater.progress")?.state).toBe("update");
  });

  it("maps warning and error notices by level", () => {
    expect(
      nashichanStateForEvent("notification.show", { level: "warning" })?.state,
    ).toBe("warning");
    expect(
      nashichanStateForEvent("notification.show", { level: "warn" })?.state,
    ).toBe("warning");
    expect(
      nashichanStateForEvent("notification.show", { level: "error" })?.state,
    ).toBe("error");
    expect(
      nashichanStateForEvent("notification.show", { level: "critical" })?.state,
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

  it("uses transient greeting, success, and celebration states", () => {
    expect(nashichanStateForEvent("dashboard.new_session_requested")).toMatchObject({
      state: "greeting",
      transientMs: expect.any(Number),
    });
    expect(nashichanStateForEvent("message.complete")).toMatchObject({
      state: "success",
      transientMs: expect.any(Number),
    });
    expect(nashichanStateForEvent("reaction")).toMatchObject({
      state: "celebrate",
      transientMs: expect.any(Number),
    });
  });

  it("returns to idle when a notification is cleared", () => {
    expect(nashichanStateForEvent("notification.clear")?.state).toBe("idle");
  });

  it("ignores unknown events", () => {
    expect(nashichanStateForEvent("something.unknown")).toBeNull();
    expect(nashichanStateForEvent(undefined)).toBeNull();
  });
});
