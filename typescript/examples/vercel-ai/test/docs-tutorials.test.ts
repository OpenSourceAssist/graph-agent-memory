import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { MemoryClient } from "@neo4j-labs/agent-memory";
import { MockLanguageModelV4 } from "ai/test";
import { afterEach, describe, expect, it, vi } from "vitest";
import { firstAgent } from "../src/tutorials/first-agent.js";
import { hostedQuickstart } from "../src/tutorials/hosted-quickstart.js";
import { inspectDocuments } from "../src/tutorials/knowledge-graph.js";
import { startHostedStub } from "./docs-hosted-stub.js";

const exec = promisify(execFile);
const root = new URL("../../../../", import.meta.url);
const pairs = [
  ["first-agent-memory-typescript", "first-agent"],
  ["conversation-memory-typescript", "conversation"],
  ["hosted-quickstart-typescript", "hosted-quickstart"],
  ["knowledge-graph-typescript", "knowledge-graph"],
] as const;
afterEach(() => vi.restoreAllMocks());

describe("complete authored TypeScript lessons", () => {
  it.each(pairs)("keeps the %s program identical to its compiled executable", async (page, program) => {
    const doc = await readFile(new URL(`docs/modules/ROOT/pages/tutorials/${page}.adoc`, root), "utf8");
    const source = await readFile(new URL(`../src/tutorials/${program}.ts`, import.meta.url), "utf8");
    expect(doc).toContain(`[source,typescript]\n----\n${source}----`);
  });

  it("runs storage, scoped search, a model call and a recorded step through REST", async () => {
    const stub = await startHostedStub();
    vi.spyOn(console, "log").mockImplementation(() => {});
    const client = new MemoryClient({ endpoint: stub.endpoint, apiKey: "nams_offline" });
    const model = new MockLanguageModelV4({
      doGenerate: async (options) => {
        expect(JSON.stringify(options.prompt)).toContain("Lantern Orchard");
        return {
          content: [{ type: "text", text: "Lantern Orchard" }],
          finishReason: { unified: "stop", raw: "stop" },
          usage: {
            inputTokens: { total: 10, noCache: 10, cacheRead: 0, cacheWrite: 0 },
            outputTokens: { total: 10, text: 10, reasoning: 0 },
          }, warnings: [],
        };
      },
    });
    try {
      const quickId = await hostedQuickstart(client);
      expect(stub.conversations.get(quickId)?.messages).toHaveLength(1);
      const result = await firstAgent(client, model);
      expect(stub.conversations.get(result.conversationId)?.messages).toHaveLength(3);
      expect(stub.steps).toHaveLength(2);
      expect(stub.calls).toContain(`POST /conversations/${result.conversationId}/search`);
      expect(stub.calls.some((call) => /preference|fact|relationship/.test(call))).toBe(false);
    } finally { await client.close(); await stub.close(); }
  });

  it("recalls a sentinel in a second process without reteaching it", async () => {
    const stub = await startHostedStub();
    const child = fileURLToPath(new URL("docs-restart-child.ts", import.meta.url));
    try {
      const taught = await exec(process.execPath, ["--import", "tsx", child, "teach", stub.endpoint]);
      const id = taught.stdout.match(/CONVERSATION_ID=(\S+)/)?.[1];
      expect(id).toBeDefined();
      expect(stub.conversations.get(id!)?.messages).toHaveLength(1);
      const recalled = await exec(process.execPath, ["--import", "tsx", child, "recall", stub.endpoint, id!]);
      expect(recalled.stdout).toContain("Lantern Orchard, size 10.");
      const messages = stub.conversations.get(id!)!.messages;
      expect(messages).toHaveLength(3);
      expect(String(messages[1]!.content)).not.toContain("Lantern Orchard");
      expect(String(messages[1]!.content)).not.toContain("size 10");
    } finally { await stub.close(); }
  });

  it("waits for the run-specific entity and handles a bounded timeout", async () => {
    const stub = await startHostedStub();
    vi.spyOn(console, "log").mockImplementation(() => {});
    const client = new MemoryClient({ endpoint: stub.endpoint, apiKey: "nams_offline" });
    try {
      const found = await inspectDocuments(client, 3_000);
      expect(found.ready).toBe(true);
      expect(stub.conversations.get(found.conversationId)?.messages).toHaveLength(2);
      expect(found.entityIds).toEqual(["entity-docs"]);
      stub.disableExtraction();
      const timedOut = await inspectDocuments(client, 0);
      expect(timedOut.ready).toBe(false);
      expect(stub.conversations.get(timedOut.conversationId)?.messages).toHaveLength(2);
    } finally { await client.close(); await stub.close(); }
  });
});
