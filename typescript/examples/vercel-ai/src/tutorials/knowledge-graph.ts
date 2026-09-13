import { MemoryClient } from "@neo4j-labs/agent-memory";
import { pathToFileURL } from "node:url";

export async function inspectDocuments(client: MemoryClient, timeoutMs = 30_000) {
  const conversation = await client.shortTerm.createConversation({ userId: "tutorial-documents" });
  console.log(`CONVERSATION_ID=${conversation.id}`);
  const name = `Lantern Orchard ${conversation.id}`;
  await client.shortTerm.bulkAddMessages(conversation.id, [
    { role: "user", content: `${name} is a fictional organization that designs garden sensors.` },
    { role: "user", content: `Mira Vale is an engineer at ${name}. The team works in Willow Harbor.` },
  ]);
  const stored = await client.shortTerm.getConversation(conversation.id);
  console.log(`Stored documents: ${stored.messages.length}`);
  // Match this run's synthetic name; an arbitrary non-empty search is not readiness.
  const ready = await client.longTerm.waitForExtraction({
    query: name, expectedNames: [name], timeoutMs, intervalMs: 1_000,
  });
  if (!ready) {
    console.log("The expected entity was not found before the deadline. Messages remain stored.");
    return { conversationId: conversation.id, ready, entityIds: [] as string[] };
  }
  const entities = await client.longTerm.searchEntities(name, { limit: 10 });
  const matches = entities.filter((entity) => entity.name.toLowerCase() === name.toLowerCase());
  for (const entity of matches) console.log(`Entity: ${entity.id} ${entity.name} (${entity.type})`);
  const graph = await client.longTerm.getEntityGraph();
  console.log(`Workspace graph: ${graph.nodes.length} nodes, ${graph.edges.length} edges`);
  return { conversationId: conversation.id, ready, entityIds: matches.map((entity) => entity.id) };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const client = new MemoryClient({ endpoint: process.env.MEMORY_ENDPOINT });
  try {
    if (!process.env.MEMORY_API_KEY) throw new Error("Set MEMORY_API_KEY.");
    await inspectDocuments(client);
  } finally { await client.close(); }
}
