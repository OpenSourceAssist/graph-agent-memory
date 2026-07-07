/**
 * Tools mode demo — the agent decides when to query/store memory, and every
 * memory operation is visible as a tool call. Run with:
 *
 *   MEMORY_API_KEY=sk-nams-... OPENAI_API_KEY=sk-... npx tsx examples/tools-chat.ts
 *
 * Expected output (tool arguments and assistant wording will vary):
 *
 *   tool call: query_memory({"query":"user editor preferences","limit":5})
 *   tool call: store_memory({"content":"User prefers very short answers","type":"user_preference","confidence":0.9,"tags":[…
 *   tool call: store_memory({"content":"User uses Neovim as their editor","type":"fact","confidence":0.9,"tags":["editor"…
 *
 *   assistant: Try Telescope for fuzzy finding and Harpoon for quick file
 *   switching.
 *
 * Unlike provider/middleware mode, the memory operations appear here as
 * visible tool calls the model chose to make.
 */

import { openai } from '@ai-sdk/openai';
import { ToolLoopAgent, stepCountIs } from 'ai';
import { createNams } from '../src/index';

const userId = process.env.NAMS_DEMO_USER ?? 'demo-user-tools-chat';

async function main(): Promise<void> {
  const nams = createNams({ apiKey: process.env.MEMORY_API_KEY! });
  const tools = nams.tools({ userId });

  const agent = new ToolLoopAgent({
    model: openai('gpt-4o-mini'),
    instructions:
      'Always call query_memory first to check what you know about the user. ' +
      'After answering, call store_memory to save anything worth remembering.',
    tools,
    stopWhen: stepCountIs(6),
  });

  const result = await agent.generate({
    prompt: 'I prefer very short answers, and I use Neovim. Got any editor tips for me?',
  });

  for (const step of result.steps) {
    for (const call of step.toolCalls) {
      console.log(`tool call: ${call.toolName}(${JSON.stringify(call.input).slice(0, 120)})`);
    }
  }
  console.log(`\nassistant: ${result.text}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
