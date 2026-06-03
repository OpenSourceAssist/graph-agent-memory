/**
 * Unit tests — AuthClient (API-key management; transport mocked).
 */

import { describe, it, expect, vi } from "vitest";
import { AuthClient } from "../../src/auth/index.js";

const KEY = {
  id: "key_1",
  label: "ci",
  scopes: ["memory:read"],
  workspace_id: "ws_1",
  created_at: "2026-05-30T00:00:00Z",
};

function mockTransport(handler: (method: string, params: Record<string, unknown>) => unknown) {
  return { request: vi.fn(async (m: string, p: Record<string, unknown>) => handler(m, p)) };
}

describe("AuthClient", () => {
  it("listApiKeys passes workspace_id and maps records", async () => {
    const t = mockTransport(() => [KEY]);
    const a = new AuthClient(t as never);
    const keys = await a.listApiKeys("ws_1");
    expect(t.request.mock.calls[0]?.[1]).toMatchObject({ workspace_id: "ws_1" });
    expect(keys[0].workspaceId).toBe("ws_1");
    expect(keys[0].scopes).toEqual(["memory:read"]);
  });

  it("createApiKey sends label/scopes and returns plaintext once", async () => {
    const t = mockTransport(() => ({ ...KEY, key: "nams_secret" }));
    const a = new AuthClient(t as never);
    const key = await a.createApiKey({ label: "ci", scopes: ["memory:read"], workspaceId: "ws_1" });
    expect(t.request.mock.calls[0]?.[1]).toMatchObject({
      label: "ci",
      scopes: ["memory:read"],
      workspace_id: "ws_1",
    });
    expect(key.key).toBe("nams_secret");
  });

  it("revealApiKey passes keyId + workspace_id", async () => {
    const t = mockTransport(() => ({ ...KEY, key: "nams_revealed" }));
    const a = new AuthClient(t as never);
    const key = await a.revealApiKey("key_1", "ws_1");
    expect(t.request.mock.calls[0]?.[1]).toMatchObject({ key_id: "key_1", workspace_id: "ws_1" });
    expect(key.key).toBe("nams_revealed");
  });

  it("rotateApiKey mints a replacement", async () => {
    const t = mockTransport(() => ({ ...KEY, id: "key_2", key: "nams_rotated" }));
    const a = new AuthClient(t as never);
    const key = await a.rotateApiKey("key_1");
    expect(t.request.mock.calls[0]?.[0]).toBe("rotate_api_key");
    expect(t.request.mock.calls[0]?.[1]).toMatchObject({ key_id: "key_1" });
    expect(key.id).toBe("key_2");
  });

  it("revokeApiKey deletes by id", async () => {
    const t = mockTransport(() => undefined);
    const a = new AuthClient(t as never);
    await a.revokeApiKey("key_1");
    expect(t.request.mock.calls[0]?.[0]).toBe("revoke_api_key");
    expect(t.request.mock.calls[0]?.[1]).toMatchObject({ key_id: "key_1" });
  });

  it("refreshAccessToken maps the token pair", async () => {
    const t = mockTransport(() => ({ access_token: "a", refresh_token: "r", expires_in: 3600 }));
    const a = new AuthClient(t as never);
    const pair = await a.refreshAccessToken("old");
    expect(pair.accessToken).toBe("a");
    expect(pair.refreshToken).toBe("r");
    expect(pair.expiresIn).toBe(3600);
  });
});
