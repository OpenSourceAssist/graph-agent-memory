/** A fresh process for each half of the documentation's persistence lesson. */
import { MemoryClient } from "@neo4j-labs/agent-memory";
import { MockLanguageModelV4 } from "ai/test";
import { recall, teach } from "../src/tutorials/conversation.js";

const [mode, endpoint, id] = process.argv.slice(2);
const client = new MemoryClient({ endpoint, apiKey: "nams_offline_docs" });
try {
  if (mode === "teach") await teach(client);
  else {
    const model = new MockLanguageModelV4({
      doGenerate: async (options) => {
        const prompt = JSON.stringify(options.prompt);
        if (!prompt.includes("Lantern Orchard") || !prompt.includes("size 10")) {
          throw new Error("The new process did not retrieve the teaching message.");
        }
        return {
          content: [{ type: "text", text: "Lantern Orchard, size 10." }],
          finishReason: { unified: "stop", raw: "stop" },
          usage: {
            inputTokens: { total: 10, noCache: 10, cacheRead: 0, cacheWrite: 0 },
            outputTokens: { total: 10, text: 10, reasoning: 0 },
          },
          warnings: [],
        };
      },
    });
    await recall(client, id!, model);
  }
} finally { await client.close(); }
