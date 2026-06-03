/**
 * Unit test — LongTermMemory.expandGraph (transport mocked).
 */

import { describe, it, expect, vi } from "vitest";
import { LongTermMemory } from "../../src/long-term/index.js";

function mockTransport(handler: (method: string, params: Record<string, unknown>) => unknown) {
  return { request: vi.fn(async (m: string, p: Record<string, unknown>) => handler(m, p)) };
}

describe("LongTermMemory.expandGraph", () => {
  it("sends nodeId/loadedIds and returns the fragment", async () => {
    const t = mockTransport(() => ({
      nodes: [{ id: "n1", labels: ["Entity"], properties: { name: "Alice" } }],
      edges: [{ id: "e1", source: "n1", target: "n2", type: "KNOWS" }],
    }));
    const lt = new LongTermMemory(t as never);
    const graph = await lt.expandGraph("n1", ["n0"]);
    expect(t.request.mock.calls[0]?.[0]).toBe("expand_graph");
    expect(t.request.mock.calls[0]?.[1].body).toMatchObject({ nodeId: "n1", loadedIds: ["n0"] });
    expect(graph.nodes[0].id).toBe("n1");
    expect(graph.nodes[0].properties?.name).toBe("Alice");
    expect(graph.edges.length).toBe(1);
  });

  it("defaults loadedIds to empty", async () => {
    const t = mockTransport(() => ({ nodes: [], edges: [] }));
    const lt = new LongTermMemory(t as never);
    await lt.expandGraph("n1");
    expect(t.request.mock.calls[0]?.[1].body).toMatchObject({ nodeId: "n1", loadedIds: [] });
  });
});
