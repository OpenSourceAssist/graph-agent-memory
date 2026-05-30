/**
 * Unit tests — conversationId alias + waitForExtraction (TS mirror of A.3/A.4).
 */

import { describe, it, expect, vi } from "vitest";
import { ShortTermMemory } from "../../src/short-term/index.js";
import { LongTermMemory } from "../../src/long-term/index.js";
import { ValidationError } from "../../src/errors.js";

function mockTransport(handler: (method: string, params: Record<string, unknown>) => unknown) {
  return { request: vi.fn(async (m: string, p: Record<string, unknown>) => handler(m, p)) };
}

describe("conversationId alias", () => {
  it("addMessage accepts conversationId alias", async () => {
    const t = mockTransport(() => ({ id: "m1", role: "user", content: "hi" }));
    const st = new ShortTermMemory(t as never);
    await st.addMessage(undefined, "user", "hi", { conversationId: "conv-9" });
    expect(t.request.mock.calls[0]?.[1]).toMatchObject({ session_id: "conv-9" });
  });

  it("sessionId wins over conversationId", async () => {
    const t = mockTransport(() => ({ id: "m1", role: "user", content: "hi" }));
    const st = new ShortTermMemory(t as never);
    await st.addMessage("real", "user", "hi", { conversationId: "BOGUS" });
    expect(t.request.mock.calls[0]?.[1]).toMatchObject({ session_id: "real" });
  });

  it("addMessage throws when neither id supplied", async () => {
    const st = new ShortTermMemory(mockTransport(() => ({})) as never);
    await expect(st.addMessage(undefined, "user", "hi")).rejects.toBeInstanceOf(ValidationError);
  });

  it("searchMessages does not throw when unscoped (bridge)", async () => {
    const t = mockTransport(() => []);
    const st = new ShortTermMemory(t as never);
    await st.searchMessages("q", { limit: 5 });
    expect(t.request.mock.calls[0]?.[1]).toMatchObject({ session_id: undefined });
  });

  it("searchMessages resolves conversationId alias", async () => {
    const t = mockTransport(() => []);
    const st = new ShortTermMemory(t as never);
    await st.searchMessages("q", { conversationId: "conv-7" });
    expect(t.request.mock.calls[0]?.[1]).toMatchObject({ session_id: "conv-7" });
  });
});

describe("waitForExtraction", () => {
  it("returns true when expected name appears", async () => {
    const t = mockTransport(() => [{ id: "e1", name: "Alice", type: "person" }]);
    const lt = new LongTermMemory(t as never);
    const ok = await lt.waitForExtraction({
      query: "Alice",
      expectedNames: ["Alice"],
      timeoutMs: 100,
      intervalMs: 10,
    });
    expect(ok).toBe(true);
  });

  it("returns false on timeout", async () => {
    const t = mockTransport(() => [{ id: "e1", name: "Bob", type: "person" }]);
    const lt = new LongTermMemory(t as never);
    const ok = await lt.waitForExtraction({
      query: "x",
      expectedNames: ["NeverAppears"],
      timeoutMs: 30,
      intervalMs: 10,
    });
    expect(ok).toBe(false);
  });

  it("throws without a signal", async () => {
    const lt = new LongTermMemory(mockTransport(() => []) as never);
    await expect(lt.waitForExtraction({})).rejects.toBeInstanceOf(ValidationError);
  });
});
