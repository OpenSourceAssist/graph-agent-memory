import { MemoryClient } from "@neo4j-labs/agent-memory";
import { pathToFileURL } from "node:url";

export async function hostedQuickstart(client: MemoryClient) {
  const conversation = await client.shortTerm.createConversation({ userId: "tutorial-reader" });
  console.log(`CONVERSATION_ID=${conversation.id}`);
  await client.shortTerm.addMessage(conversation.id, "user", "I am planning the fictional Lantern Orchard project.");
  const stored = await client.shortTerm.getConversation(conversation.id);
  const context = await client.shortTerm.getContext(conversation.id);
  console.log(`Stored messages: ${stored.messages.length}`);
  console.log(`Recent context messages: ${context.recentMessages.length}`);
  await client.reasoning.recordStep({
    conversationId: conversation.id,
    reasoning: "Verified that the submitted message can be read back.",
    actionTaken: "verify_storage",
    result: `Read ${stored.messages.length} message(s)`,
  });
  const trace = await client.reasoning.getTraceByConversation(conversation.id);
  console.log(`Recorded steps: ${trace.steps.length}`);
  return conversation.id;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const client = new MemoryClient({ endpoint: process.env.MEMORY_ENDPOINT });
  try {
    if (!process.env.MEMORY_API_KEY) throw new Error("Set MEMORY_API_KEY.");
    await hostedQuickstart(client);
  } finally { await client.close(); }
}
