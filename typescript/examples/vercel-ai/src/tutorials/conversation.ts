import type { LanguageModelV4 } from "@ai-sdk/provider";
import { openai } from "@ai-sdk/openai";
import { generateText, wrapLanguageModel } from "ai";
import { agentMemoryMiddleware } from "@neo4j-labs/agent-memory/middleware/vercel-ai";
import { MemoryClient } from "@neo4j-labs/agent-memory";
import { pathToFileURL } from "node:url";

export async function teach(client: MemoryClient) {
  const conversation = await client.shortTerm.createConversation({ userId: "tutorial-shopper" });
  await client.shortTerm.addMessage(
    conversation.id, "user", "My fictional running club is called Lantern Orchard. I wear size 10 shoes.",
  );
  console.log(`CONVERSATION_ID=${conversation.id}`);
  console.log("Teaching message stored. Stop this process and keep the conversation id.");
  return conversation.id;
}

export async function recall(client: MemoryClient, conversationId: string, baseModel: LanguageModelV4) {
  const before = await client.shortTerm.getContext(conversationId);
  console.log(`Stored recent messages before this question: ${before.recentMessages.length}`);
  const model = wrapLanguageModel({
    model: baseModel,
    middleware: agentMemoryMiddleware(client, { conversationId }),
  });
  const { text } = await generateText({
    model,
    system: "Answer from the supplied memory. Say when a requested fact is missing.",
    prompt: "What is my running club called, and what shoe size did I tell you?",
  });
  console.log(text);
  return text;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const client = new MemoryClient({ endpoint: process.env.MEMORY_ENDPOINT });
  try {
    if (!process.env.MEMORY_API_KEY) throw new Error("Set MEMORY_API_KEY.");
    const mode = process.argv[2];
    const id = process.env.CONVERSATION_ID;
    if (mode === "teach") await teach(client);
    else if (mode === "recall" && id) {
      if (!process.env.OPENAI_API_KEY) throw new Error("Set OPENAI_API_KEY.");
      await recall(client, id, openai(process.env.OPENAI_MODEL ?? "gpt-4o-mini"));
    } else if (mode === "cleanup" && id) {
      await client.shortTerm.deleteConversation(id);
      console.log(`Deleted conversation ${id}`);
    } else throw new Error("Use teach, or set CONVERSATION_ID and use recall or cleanup.");
  } finally { await client.close(); }
}
