/**
 * Two things are checked here:
 *
 *  1. Doc-page fidelity: each program is embedded byte-for-byte on its how-to
 *     page, exactly like `typescript/examples/vercel-ai/test/docs-tutorials.test.ts`.
 *     The pages don't exist yet -- another worker embeds these files verbatim
 *     at `docs/modules/ROOT/pages/how-to/typescript/nams-ai-provider-<mode>-mode.adoc`.
 *     Until then this half of the suite fails with a clear diff, on purpose,
 *     rather than silently skipping.
 *
 *  2. Offline behavior: each program runs against the hosted-service stub
 *     shared with `typescript/examples/vercel-ai` and the AI SDK's own
 *     `MockLanguageModelV4` -- no API key, no network, no Neo4j. The
 *     assertions are the ones that fail if memory stops working: the second
 *     session/turn recalls (or explicitly queries and gets back) what the
 *     first one stored.
 */
import { readFile } from "node:fs/promises";
import type {
  LanguageModelV4CallOptions,
  LanguageModelV4FinishReason,
  LanguageModelV4GenerateResult,
  LanguageModelV4Usage,
} from "@ai-sdk/provider";
import { MockLanguageModelV4 } from "ai/test";
import { afterEach, describe, expect, it } from "vitest";
import { hooksModeDemo } from "../src/hooks-mode.js";
import { middlewareModeDemo } from "../src/middleware-mode.js";
import { providerModeDemo } from "../src/provider-mode.js";
import { toolsModeDemo } from "../src/tools-mode.js";
import { startHostedStub } from "../../vercel-ai/test/docs-hosted-stub.js";

const root = new URL("../../../../", import.meta.url);
const modes = ["provider", "middleware", "tools", "hooks"] as const;

const FINISH: LanguageModelV4FinishReason = { unified: "stop", raw: "stop" };
const TOOL_CALLS: LanguageModelV4FinishReason = { unified: "tool-calls", raw: "tool_calls" };
const USAGE: LanguageModelV4Usage = {
  inputTokens: { total: 10, noCache: 10, cacheRead: 0, cacheWrite: 0 },
  outputTokens: { total: 10, text: 10, reasoning: 0 },
};

function textResult(text: string): LanguageModelV4GenerateResult {
  return { content: [{ type: "text", text }], finishReason: FINISH, usage: USAGE, warnings: [] };
}

function toolCallResult(toolCallId: string, toolName: string, input: unknown): LanguageModelV4GenerateResult {
  // Real providers return tool arguments as a raw JSON string; the AI SDK
  // parses it with the tool's schema, so a plain object here is rejected.
  return {
    content: [{ type: "tool-call", toolCallId, toolName, input: JSON.stringify(input) }],
    finishReason: TOOL_CALLS,
    usage: USAGE,
    warnings: [],
  };
}

/** A mock model that returns the next answer in `answers` on each call, repeating the last one. */
function sequencedMockModel(answers: string[]) {
  const calls: LanguageModelV4CallOptions[] = [];
  let i = 0;
  const model = new MockLanguageModelV4({
    doGenerate: async options => {
      calls.push(options);
      const text = answers[i] ?? answers[answers.length - 1]!;
      i++;
      return textResult(text);
    },
  });
  return { model, calls };
}

function promptText(call: LanguageModelV4CallOptions): string {
  return JSON.stringify(call.prompt);
}

/** The current turn's user text: the *last* user-role message, since restored history carries earlier turns too. */
function currentTurnText(options: LanguageModelV4CallOptions): string {
  const users = options.prompt.filter(m => m.role === "user");
  return JSON.stringify(users.at(-1)?.content ?? "");
}

function toolResultCount(options: LanguageModelV4CallOptions): number {
  return options.prompt.filter(m => m.role === "tool").length;
}

async function withOfflineEnv<T>(stub: Awaited<ReturnType<typeof startHostedStub>>, run: () => Promise<T>): Promise<T> {
  process.env.MEMORY_API_KEY = "nams_offline";
  process.env.MEMORY_ENDPOINT = stub.endpoint;
  try {
    return await run();
  } finally {
    delete process.env.MEMORY_API_KEY;
    delete process.env.MEMORY_ENDPOINT;
  }
}

afterEach(() => {
  delete process.env.MEMORY_API_KEY;
  delete process.env.MEMORY_ENDPOINT;
});

describe("NAMS AI provider doc pages", () => {
  it.each(modes)("keeps the %s-mode program identical to its embedded doc page", async mode => {
    const doc = await readFile(
      new URL(`docs/modules/ROOT/pages/how-to/typescript/nams-ai-provider-${mode}-mode.adoc`, root),
      "utf8",
    );
    const source = await readFile(new URL(`../src/${mode}-mode.ts`, import.meta.url), "utf8");
    expect(doc).toContain(`[source,typescript]\n----\n${source}----`);
  });
});

describe("NAMS AI provider offline runs", () => {
  it("provider mode: teaches a fact in session 1 and recalls it in session 2 via NAMS", async () => {
    const stub = await startHostedStub();
    try {
      await withOfflineEnv(stub, async () => {
        const { model, calls } = sequencedMockModel([
          "Nice to meet you, Alex!",
          "You work at TechCorp, on the graph platform team.",
        ]);
        const { taught, recalled } = await providerModeDemo(() => model);

        expect(taught).toBe("Nice to meet you, Alex!");
        expect(recalled).toBe("You work at TechCorp, on the graph platform team.");
        // Session 2's prompt carries session 1's fact back out of NAMS -- the
        // script never passed it in a second time.
        expect(promptText(calls[1]!)).toContain("TechCorp");
      });

      expect(stub.calls).toContain("POST /conversations");
      // The query string isn't recorded in `calls` (pathname only) -- the
      // path itself is shared with the POST above, so check the method pairs up.
      expect(stub.calls).toContain("GET /conversations");
      expect(stub.conversations.size).toBe(1);
      expect([...stub.conversations.values()][0]!.messages).toHaveLength(4);
    } finally {
      await stub.close();
    }
  });

  it("middleware mode: teaches a fact in turn 1 and recalls it in turn 2 via NAMS", async () => {
    const stub = await startHostedStub();
    try {
      await withOfflineEnv(stub, async () => {
        const { model, calls } = sequencedMockModel([
          "Great choice! Rust is loved for its safety and performance.",
          "Your favourite programming language is Rust.",
        ]);
        const { taught, recalled } = await middlewareModeDemo(() => model);

        expect(taught).toContain("Rust");
        expect(recalled).toBe("Your favourite programming language is Rust.");
        expect(promptText(calls[1]!)).toContain("Rust");
      });

      expect(stub.calls).toContain("POST /conversations");
      expect(stub.conversations.size).toBe(1);
      expect([...stub.conversations.values()][0]!.messages).toHaveLength(4);
    } finally {
      await stub.close();
    }
  });

  it("tools mode: turn 1 stores a preference via store_memory, turn 2 recalls it via query_memory", async () => {
    const stub = await startHostedStub();
    try {
      await withOfflineEnv(stub, async () => {
        const model = new MockLanguageModelV4({
          doGenerate: async options => {
            const turn1 = currentTurnText(options).includes("Got any editor tips");
            const steps = toolResultCount(options);
            if (turn1) {
              if (steps === 0) return toolCallResult("call-q1", "query_memory", { query: "editor preferences", limit: 5 });
              if (steps === 1) {
                return toolCallResult("call-s1", "store_memory", {
                  content: "User uses Neovim and prefers short answers",
                  type: "user_preference",
                  confidence: 0.9,
                  tags: [],
                });
              }
              return textResult("Got it -- short answers, and I'll remember you use Neovim.");
            }
            // Turn 2: fresh tool set, same user -- recall only, no store_memory.
            if (steps === 0) return toolCallResult("call-q2", "query_memory", { query: "editor preferences", limit: 5 });
            return textResult("You use Neovim, and you like short answers.");
          },
        });

        const { taught, recalled } = await toolsModeDemo(() => model);
        expect(taught).toContain("Neovim");
        expect(recalled).toBe("You use Neovim, and you like short answers.");
      });

      expect(stub.calls).toContain("POST /entities");
      expect(stub.calls.filter(c => c === "POST /entities/search").length).toBeGreaterThanOrEqual(2);
      expect(stub.entities.size).toBe(1);
      expect([...stub.entities.values()][0]!["name"]).toContain("Neovim");
    } finally {
      await stub.close();
    }
  });

  it("hooks mode: runs all eight lifecycle events and persists the transcript via bulk write", async () => {
    const stub = await startHostedStub();
    try {
      const answers = await withOfflineEnv(stub, async () => {
        const model = new MockLanguageModelV4({
          doGenerate: async options => {
            const text = currentTurnText(options);
            const steps = toolResultCount(options);
            if (text.includes("weather in Oslo")) {
              return steps === 0 ? toolCallResult("call-weather", "get_weather", { city: "Oslo" }) : textResult("It's sunny in Oslo, 21C.");
            }
            if (text.includes("graph databases")) {
              return steps === 0 ? toolCallResult("call-flaky", "flaky_lookup", { topic: "graph databases" }) : textResult("Graph databases are well documented.");
            }
            if (text.includes("delete my account")) {
              return steps === 0 ? toolCallResult("call-delete", "delete_account", { confirm: true }) : textResult("I can't do that -- account deletion is disabled in this demo.");
            }
            // Turn 4: sensitive input, answered directly -- no tool call.
            return textResult("Got it, but I can't store card numbers.");
          },
        });
        return hooksModeDemo(() => model);
      });

      expect(answers).toHaveLength(4);
      expect(answers[0]).toContain("Oslo");
      expect(answers[1]).toContain("documented"); // survived the flaky_lookup retry
      expect(answers[2]).toContain("disabled"); // delete_account was denied, never executed
      expect(answers[3]).toContain("card numbers");

      expect(stub.calls.some(c => c.endsWith("/messages/bulk"))).toBe(true);
      expect(stub.conversations.size).toBe(1);
      const stored = [...stub.conversations.values()][0]!.messages;
      // The card number sent in turn 4 must never reach storage unredacted.
      expect(JSON.stringify(stored)).not.toContain("4111 1111 1111 1111");
      expect(JSON.stringify(stored)).toContain("redacted card");
    } finally {
      await stub.close();
    }
  });
});
