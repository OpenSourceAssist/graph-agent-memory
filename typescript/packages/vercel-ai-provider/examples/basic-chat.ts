/**
 * Minimal runnable demo — provider mode across two simulated sessions.
 *
 * Session 1 tells the agent a fact; session 2 (a fresh agent, same userId)
 * recalls it from NAMS. Run with:
 *
 *   MEMORY_API_KEY=sk-nams-... OPENAI_API_KEY=sk-... npx tsx examples/basic-chat.ts
 *
 * Expected output (assistant wording will vary):
 *
 *   ─── Session 1 — teach it something
 *   user:      Hi! My name is Alex and I work at TechCorp on the graph platform team.
 *   assistant: Nice to meet you, Alex! How can I help you today? …
 *
 *   ─── Session 2 — fresh session, same user
 *   user:      Where do I work, and what team am I on?
 *   assistant: You work at TechCorp, on the graph platform team.
 *
 * Session 2 is a brand-new agent — the answer comes from NAMS memory, not
 * from the conversation history.
 */

import { openai } from '@ai-sdk/openai';
import { ToolLoopAgent, stepCountIs } from 'ai';
import { createNamsProvider } from '../src/index';

const userId = process.env.NAMS_DEMO_USER ?? 'demo-user-basic-chat';
const model = process.env.NAMS_DEMO_MODEL ?? 'gpt-5.4-mini';

async function session(label: string, message: string): Promise<void> {
  // One provider instance per user session — memory is transparent.
  const nams = createNamsProvider({
    apiKey: process.env.MEMORY_API_KEY!,
    baseProvider: openai,
    scope: { userId },
  });

  const agent = new ToolLoopAgent({
    model: nams.languageModel(model),
    instructions: 'You are a helpful assistant.',
    stopWhen: stepCountIs(1), // no tools needed in provider mode
  });

  const { text } = await agent.generate({ prompt: message });

  console.log(`\n─── ${label}`);
  console.log(`user:      ${message}`);
  console.log(`assistant: ${text}`);
}

async function main(): Promise<void> {
  await session('Session 1 — teach it something', 'Hi! My name is Alex and I work at TechCorp on the graph platform team.');

  // A brand-new agent = a brand-new "session". Without NAMS the model would
  // have no idea who the user is.
  await session('Session 2 — fresh session, same user', 'Where do I work, and what team am I on?');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
