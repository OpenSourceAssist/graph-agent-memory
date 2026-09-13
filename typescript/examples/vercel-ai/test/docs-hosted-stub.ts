/** A strict HTTP stub: lesson code must pass through the real RestTransport. */
import { createServer } from "node:http";

export async function startHostedStub() {
  const conversations = new Map<string, { id: string; messages: Array<Record<string, unknown>> }>();
  const entities = new Map<string, Record<string, unknown>>();
  const steps: Array<Record<string, unknown>> = [];
  const calls: string[] = [];
  let sequence = 0;
  let extractionEnabled = true;
  let polls = 0;
  const server = createServer(async (req, res) => {
    const path = new URL(req.url!, "http://localhost").pathname.replace(/^\/v1/, "");
    calls.push(`${req.method} ${path}`);
    let raw = "";
    for await (const chunk of req) raw += String(chunk);
    const body = raw ? JSON.parse(raw) as Record<string, unknown> : {};
    let value: unknown;
    const id = path.split("/")[2];
    const conversation = id ? conversations.get(id) : undefined;
    const append = (message: Record<string, unknown>) => {
      const stored = { ...message, id: `message-${++sequence}`, createdAt: "2026-09-13T00:00:00Z" };
      conversation!.messages.push(stored);
      return stored;
    };
    if (path === "/conversations" && req.method === "POST") {
      const created = { id: `conversation-${++sequence}`, messages: [], createdAt: "2026-09-13T00:00:00Z", ...body };
      conversations.set(created.id, created);
      value = created;
    } else if (conversation && path.endsWith("/messages/bulk") && req.method === "POST") {
      value = { messages: (body.messages as Array<Record<string, unknown>>).map(append) };
    } else if (conversation && path.endsWith("/messages")) {
      value = req.method === "POST" ? append(body) : { messages: conversation.messages };
    } else if (conversation && path.endsWith("/context")) {
      value = { recentMessages: conversation.messages, observations: [], reflections: [] };
    } else if (conversation && path.endsWith("/search") && req.method === "POST") {
      value = { messages: conversation.messages.filter((message) => String(message.content).includes(String(body.query))) };
    } else if (conversation && req.method === "DELETE") {
      conversations.delete(conversation.id);
      res.writeHead(204).end();
      return;
    } else if (path === "/reasoning/steps" && req.method === "POST") {
      value = { ...body, id: `step-${++sequence}` };
      steps.push(value as Record<string, unknown>);
    } else if (path.startsWith("/reasoning/trace/")) {
      const conversationId = path.split("/").at(-1);
      value = { conversationId, steps: steps.filter((step) => step.conversationId === conversationId) };
    } else if (path === "/entities" && req.method === "POST") {
      const entity = { ...body, id: `entity-${++sequence}` };
      entities.set(entity.id, entity);
      value = entity;
    } else if (path.startsWith("/entities/") && entities.has(id!)) {
      value = entities.get(id!);
    } else if (path === "/entities/search" && req.method === "POST") {
      polls++;
      value = { entities: extractionEnabled && polls > 1 ? [{ id: "entity-docs", name: body.query, type: "organization" }] : [] };
    } else if (path === "/entities/graph" && req.method === "GET") {
      value = { nodes: [], edges: [] };
    } else {
      res.writeHead(500, { "Content-Type": "application/json" }).end(JSON.stringify({ error: `Unhandled lesson route: ${req.method} ${path}` }));
      return;
    }
    res.writeHead(200, { "Content-Type": "application/json" }).end(JSON.stringify(value));
  });
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  if (!address || typeof address === "string") throw new Error("No stub address");
  return {
    endpoint: `http://127.0.0.1:${address.port}/v1`, conversations, steps, calls,
    disableExtraction: () => { extractionEnabled = false; },
    close: () => new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve())),
  };
}
