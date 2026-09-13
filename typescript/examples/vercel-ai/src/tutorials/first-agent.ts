import type { LanguageModelV4 } from "@ai-sdk/provider";
import { openai } from "@ai-sdk/openai";
import { generateText, wrapLanguageModel } from "ai";
import { agentMemoryMiddleware } from "@neo4j-labs/agent-memory/middleware/vercel-ai";
import { MemoryClient } from "@neo4j-labs/agent-memory";
import { pathToFileURL } from "node:url";

export async function firstAgent(client: MemoryClient, baseModel: LanguageModelV4) {
  const conversation = await client.shortTerm.createConversation({ userId: "tutorial-alice" });
  console.log(`CONVERSATION_ID=${conversation.id}`);
  const message = await client.shortTerm.addMessage(
    conversation.id, "user", "My fictional project is called Lantern Orchard.",
  );
  console.log(`Stored message: ${message.id}`);
  const matches = await client.shortTerm.searchMessages("Lantern Orchard", {
    conversationId: conversation.id, limit: 5,
  });
  console.log(`Conversation search matches: ${matches.length}`);

  const entity = await client.longTerm.addEntity(`Lantern Orchard ${conversation.id}`, "organization", {
    description: "Fictional organization used by this tutorial run.",
  });
  const storedEntity = await client.longTerm.getEntity(entity.id);
  console.log(`ENTITY_ID=${storedEntity.id} name=${storedEntity.name}`);

  const model = wrapLanguageModel({
    model: baseModel,
    middleware: agentMemoryMiddleware(client, { conversationId: conversation.id }),
  });
  const answer = await generateText({
    model,
    system: "Use the supplied conversation history. If a fact is missing, say so.",
    prompt: "What is my project called?",
  });
  console.log(answer.text);
  // This is an application-authored activity record, not hidden model reasoning.
  await client.reasoning.recordStep({
    conversationId: conversation.id,
    reasoning: "Loaded the same conversation before answering the recall question.",
    actionTaken: "answer_with_memory",
    result: answer.text,
  });
  const trace = await client.reasoning.getTraceByConversation(conversation.id);
  console.log(`Recorded steps: ${trace.steps.length}`);
  return { conversationId: conversation.id, entityId: entity.id, answer: answer.text };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const client = new MemoryClient({ endpoint: process.env.MEMORY_ENDPOINT });
  try {
    if (!process.env.MEMORY_API_KEY || !process.env.OPENAI_API_KEY) {
      throw new Error("Set MEMORY_API_KEY and OPENAI_API_KEY.");
    }
    await firstAgent(client, openai(process.env.OPENAI_MODEL ?? "gpt-4o-mini"));
  } finally { await client.close(); }
}
