/**
 * Unit tests — workspace addressing (X-Workspace-Id header injection).
 *
 * Mirrors the Python A.1 surface: `workspaceId` → `X-Workspace-Id`, with an
 * explicit `headers` entry winning over the configured workspace id.
 */

import { describe, it, expect } from "vitest";
import { MemoryClient } from "../../src/client.js";

function transportHeaders(client: MemoryClient): Record<string, string> {
  const t = (client as unknown as { transport: unknown }).transport;
  const inner =
    t && typeof t === "object" && "inner" in t ? (t as { inner: unknown }).inner : t;
  return (inner as { headers: Record<string, string> }).headers;
}

describe("workspace addressing", () => {
  it("injects X-Workspace-Id from workspaceId", () => {
    const c = new MemoryClient({
      endpoint: "https://memory.test/v1",
      apiKey: "k",
      workspaceId: "ws-123",
    });
    expect(transportHeaders(c)["X-Workspace-Id"]).toBe("ws-123");
  });

  it("sends no header when workspaceId is unset", () => {
    const c = new MemoryClient({ endpoint: "https://memory.test/v1", apiKey: "k" });
    const headers = transportHeaders(c);
    const hasWs = Object.keys(headers).some((k) => k.toLowerCase() === "x-workspace-id");
    expect(hasWs).toBe(false);
  });

  it("explicit header overrides workspaceId", () => {
    const c = new MemoryClient({
      endpoint: "https://memory.test/v1",
      apiKey: "k",
      workspaceId: "ws-123",
      headers: { "X-Workspace-Id": "explicit-override" },
    });
    expect(transportHeaders(c)["X-Workspace-Id"]).toBe("explicit-override");
  });
});
