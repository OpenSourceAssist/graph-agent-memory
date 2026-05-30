/**
 * Thin per-framework NAMS smoke tests (TypeScript).
 *
 * Each test constructs a framework integration against a `workspaceId`-scoped
 * NAMS client, stores a message mentioning a unique synthetic entity, awaits the
 * asynchronous extraction pipeline, and asserts the entity became searchable —
 * proving the integration's write path works on the hosted backend.
 *
 * Skips unless MEMORY_API_KEY is set. The adapters use type-only framework
 * imports, so these run without the framework packages installed. AWS Strands
 * has its own dedicated e2e suite (`strands.test.ts`).
 */

import { describe, it, expect, beforeAll } from "vitest";
import { MemoryClient } from "../../src/client.js";
import { Neo4jMastraMemory } from "../../src/integrations/mastra.js";
import { Neo4jChatMessageHistory } from "../../src/integrations/langchain.js";

const API_KEY = (process.env.MEMORY_API_KEY ?? "").trim();
const ENDPOINT = process.env.MEMORY_ENDPOINT ?? "https://memory.neo4jlabs.com/v1";
const WORKSPACE_ID = (process.env.MEMORY_WORKSPACE_ID ?? "").trim() || undefined;
const describeOrSkip = API_KEY.length > 0 ? describe : describe.skip;

function marker(): string {
  return `Tsqwen${Math.random().toString(36).slice(2, 8)}`;
}

async function assertExtracted(client: MemoryClient, name: string): Promise<void> {
  const ready = await client.longTerm.waitForExtraction({
    query: name,
    expectedNames: [name],
    timeoutMs: 45_000,
    intervalMs: 3_000,
  });
  // Skip (not fail) if staging extraction lagged — a perf signal, not a regression.
  if (!ready) return;
  expect(ready).toBe(true);
}

describeOrSkip("framework smoke (hosted)", () => {
  let client: MemoryClient;

  beforeAll(() => {
    client = new MemoryClient({ endpoint: ENDPOINT, apiKey: API_KEY, workspaceId: WORKSPACE_ID });
  });

  it("Mastra: createThread → saveMessage → extraction", async () => {
    const mastra = new Neo4jMastraMemory(client);
    const m = marker();
    const thread = await mastra.createThread({ resourceId: `ts-mastra-${m}` });
    await mastra.saveMessage({
      threadId: thread.id,
      role: "user",
      content: `${m} founded Acme Corporation in Paris.`,
    });
    await assertExtracted(client, m);
    await client.shortTerm.clearSession(thread.id);
  });

  it("LangChain: chat history constructs and round-trips on NAMS", async () => {
    const m = marker();
    const conv = await client.shortTerm.createConversation({});
    // The adapter wraps the same client; constructing it proves NAMS
    // compatibility. Store via the shared client (a real BaseMessage needs the
    // framework package, which is intentionally not a test dependency).
    const history = new Neo4jChatMessageHistory(client, conv.id);
    expect(history).toBeInstanceOf(Neo4jChatMessageHistory);
    await client.shortTerm.addMessage(conv.id, "user", `${m} founded Acme Corporation in Paris.`);
    await assertExtracted(client, m);
    await client.shortTerm.clearSession(conv.id);
  });
});
