/**
 * Middleware mode demo — wrap an existing model instance with memory.
 *
 * Unlike provider mode there is no ProviderV3 registration: you keep whatever
 * model you already configured and decorate it with `createNams().wrap()`.
 * MEMORY_API_KEY authenticates with NAMS; OPENAI_API_KEY authenticates the
 * base model call made by `@ai-sdk/openai` (swap for another provider's key
 * if you use a different `baseProvider`). 
 * Run with:
 *
 *   MEMORY_API_KEY=sk-nams-... OPENAI_API_KEY=sk-... npx tsx examples/middleware-chat.ts
 *
 * Expected output (assistant wording will vary):
 *
 *   ─── Turn 1 — teach it something
 *   user:      My favourite programming language is Rust.
 *   assistant: Great choice! Rust is loved for its safety and performance. …
 *
 *   ─── Turn 2 — fresh model instance, same user
 *   user:      What is my favourite programming language?
 *   assistant: Your favourite programming language is Rust.
 *
 * Turn 2 only answers correctly because the middleware injected the memory
 * persisted in turn 1 — the model instance itself is brand new.
 */

import { openai } from '@ai-sdk/openai';
import { ToolLoopAgent, stepCountIs } from 'ai';
import { createNams } from '../src/index';

const userId = process.env.NAMS_DEMO_USER ?? 'demo-user-middleware-chat';
const model = process.env.NAMS_DEMO_MODEL ?? 'gpt-5.4-mini';

async function turn(label: string, message: string): Promise<void> {
  // A fresh wrapped model per turn — memory continuity comes from NAMS.
  const nams = createNams({ apiKey: process.env.MEMORY_API_KEY! });
  const wrappedModel = nams.wrap(openai(model), { userId });

  const agent = new ToolLoopAgent({
    model: wrappedModel,
    instructions: 'You are a helpful assistant.',
    stopWhen: stepCountIs(1), // no tools needed in middleware mode
  });

  const { text } = await agent.generate({ prompt: message });

  console.log(`\n─── ${label}`);
  console.log(`user:      ${message}`);
  console.log(`assistant: ${text}`);
}

async function main(): Promise<void> {
  await turn('Turn 1 — teach it something', 'My favourite programming language is Rust.');
  await turn('Turn 2 — fresh model instance, same user', 'What is my favourite programming language?');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
