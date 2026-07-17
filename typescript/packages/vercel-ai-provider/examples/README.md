# Examples

One runnable example per integration mode — provider, middleware, and tools —
plus a Next.js route template. All examples need a free NAMS API key from
[memory.neo4jlabs.com](https://memory.neo4jlabs.com) and an OpenAI key (swap in
any `@ai-sdk/*` provider if you prefer). No other environment changes are
needed to switch modes — mode selection is code-level.

```bash
export MEMORY_API_KEY=sk-nams-...
export OPENAI_API_KEY=sk-...
```

| Example | Mode | Run |
|---------|------|-----|
| [`basic-chat.ts`](./basic-chat.ts) | Provider (transparent memory) — teaches a fact in session 1, recalls it in session 2 | `npx tsx examples/basic-chat.ts` |
| [`middleware-chat.ts`](./middleware-chat.ts) | Middleware — wraps an existing model instance; a fresh model in turn 2 recalls turn 1 | `npx tsx examples/middleware-chat.ts` |
| [`tools-chat.ts`](./tools-chat.ts) | Tools (model-driven) — `query_memory` / `store_memory` visible as tool calls; retrieval guaranteed via `enforceQueryMemory()` | `npx tsx examples/tools-chat.ts` |
| [`nextjs-chat-route.ts`](./nextjs-chat-route.ts) | Provider inside a Next.js App Router endpoint — copy into `app/api/chat/route.ts` | n/a (template) |

Each script's header comment shows the **expected output**, so you can compare
what you see locally — in provider and middleware mode the recall happens
silently inside the model call, while in tools mode the same memory operations
appear as visible `query_memory` / `store_memory` tool calls.

The scripts import from `../src` so they run directly against the source tree — no build step needed. In your own app, import from `@neo4j-labs/nams-ai-provider` instead.
