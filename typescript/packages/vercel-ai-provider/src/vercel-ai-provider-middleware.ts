/**
 * Middleware mode. `createNamsMemory(config).wrap(model, scope)` returns a model
 * that adds relevant memories before each call and saves the turn after.
 * Provider mode uses this too.
 *
 * No entity extraction here. NAMS extracts saved turns server-side. Use tools
 * mode for long-term memory.
 */

import { wrapLanguageModel } from 'ai';
import type { LanguageModelV4, LanguageModelV4Middleware } from '@ai-sdk/provider';
import {
  makeClient,
  getLogger,
  resolveConversation,
  retrieveMemories,
} from './vercel-ai-provider-client';
import { MemoryHit, NamsConfig, NamsScope } from './vercel-ai-provider-types';

export interface NamsMemoryConfig extends NamsConfig {
  /** Max memories added to the prompt per turn (default: 6). */
  maxMemories?: number;
  /** Save each turn to NAMS (default: true). */
  persistInteractions?: boolean;
}


const lastUserIndex = (prompt: any[]): number => {
  for (let i = prompt.length - 1; i >= 0; i--) {
    if (prompt[i]?.role === 'user') return i;
  }
  return -1;
}

/** Copy the prompt, with `block` added to the start of the last user message. */
const withMemoryBlock = (prompt: any[], block: string): any[] => {
  const i = lastUserIndex(prompt);
  if (i < 0) return prompt;

  const msg = prompt[i];
  let content: unknown;
  if (typeof msg.content === 'string') content = `${block}\n\n${msg.content}`;
  else if (Array.isArray(msg.content)) content = [{ type: 'text', text: `${block}\n\n` }, ...msg.content];
  else return prompt;

  const next = [...prompt];
  next[i] = { ...msg, content };
  return next;
}

const toolCallInput = (part: any): string => {
  if (typeof part?.input === 'string') return part.input;
  const args = part?.input ?? part?.args;
  if (args === undefined) return '';
  try { return JSON.stringify(args) ?? ''; } catch { return ''; }
}

// Assistant text from a result. Falls back to tool-call input (e.g. generateObject).
const textFromResult = (result: any): string => {
  if (typeof result?.text === 'string' && result.text) return result.text;
  if (Array.isArray(result?.content)) {
    const textParts = (result.content as any[])
      .filter(p => p?.type === 'text')
      .map(p => p.text as string)
      .join('');
    if (textParts) return textParts;
    return (result.content as any[])
      .filter(p => p?.type === 'tool-call')
      .map(toolCallInput)
      .join('');
  }
  return '';
}

const formatMemoryBlock = (memories: MemoryHit[]): string => {
  return (
    'Relevant long-term memory about this user (use it to personalise your answer):\n' +
    memories.map((m, i) => `${i + 1}. [${m.source}] ${m.content}`).join('\n')
  );
}

// Text of the last user message.
const lastUserText = (prompt: any[]): string => {
  const i = lastUserIndex(prompt);
  if (i < 0) return '';
  const msg = prompt[i];
  if (typeof msg.content === 'string') return msg.content;
  if (Array.isArray(msg.content))
    return msg.content
      .filter((p: any) => p?.type === 'text')
      .map((p: any) => p.text as string)
      .join('')
      .trim();
  return '';
}

const buildMiddleware = (
  config: NamsMemoryConfig,
  scope: NamsScope,
  maxMemories: number,
  persist: boolean,
): LanguageModelV4Middleware => {
  const client = makeClient(config);
  const log = getLogger(client);

  let convIdPromise: Promise<string> | null = null;
  const getConvId = (): Promise<string> =>
    (convIdPromise ??= resolveConversation(client, config, scope));

  const originalUserText = new WeakMap<object, string>();

  // Every step of a tool loop repeats the user message. Track it so it is saved once.
  let lastPersistedUserText: string | undefined;

  async function persistTurn(params: any, assistantText: string): Promise<void> {
    if (!persist) return;
    const convId = await getConvId();
    const userText = originalUserText.get(params as object) ?? lastUserText(params.prompt);
    if (userText && userText !== lastPersistedUserText) {
      lastPersistedUserText = userText;
      await client.shortTerm.addMessage(convId, 'user', userText)
        .catch(e => log.error('persist user message failed', e));
    }
    if (assistantText) await client.shortTerm.addMessage(convId, 'assistant', assistantText)
      .catch(e => log.error('persist assistant message failed', e));
  }

  return {
    specificationVersion: 'v4',
    // Find memories for the user message and add them to the prompt.
    transformParams: async ({ params }) => {
      const userText = lastUserText(params.prompt);
      if (!userText) return params;
      originalUserText.set(params as object, userText);

      let convId: string;
      try {
        convId = await getConvId();
      } catch (e) {
        log.warn('resolveConversation failed', e);
        return params;
      }

      const memories = await retrieveMemories(client, scope, convId, userText, maxMemories)
        .catch(e => { log.warn('retrieve failed', e); return [] as MemoryHit[]; });

      if (memories.length === 0) return params;

      const augmented = { ...params, prompt: withMemoryBlock(params.prompt, formatMemoryBlock(memories)) };
      originalUserText.set(augmented as object, userText);
      return augmented;
    },

    wrapGenerate: async ({ doGenerate, params }) => {
      const result = await doGenerate();
      await persistTurn(params, textFromResult(result))
        .catch(e => log.warn('persist failed', e));
      return result;
    },

    // Collect text and tool-call input from the stream. Save the turn when it closes.
    wrapStream: async ({ doStream, params }) => {
      const { stream, ...rest } = await doStream();
      let text = '';
      const pendingToolArgs = new Map<string, string>();

      const tap = new TransformStream({
        transform(chunk: any, controller) {
          if (chunk?.type === 'text-delta')
            text += (chunk.delta ?? chunk.textDelta ?? chunk.text ?? '') as string;
          else if (chunk?.type === 'text')
            text += (chunk.text ?? '') as string;
          else if (chunk?.type === 'tool-input-delta') {
            const id = chunk.id as string;
            pendingToolArgs.set(id, (pendingToolArgs.get(id) ?? '') + (chunk.delta ?? ''));
          } else if (chunk?.type === 'tool-call-delta') {
            const id = chunk.toolCallId as string;
            pendingToolArgs.set(id, (pendingToolArgs.get(id) ?? '') + (chunk.argsTextDelta ?? ''));
          } else if (chunk?.type === 'tool-call') {
            pendingToolArgs.set((chunk.toolCallId ?? chunk.id) as string, toolCallInput(chunk));
          }
          controller.enqueue(chunk);
        },
        async flush() {
          for (const args of pendingToolArgs.values()) {
            if (args) text += args;
          }
          await persistTurn(params, text)
            .catch(e => log.warn('persist failed', e));
        },
      });

      return { stream: stream.pipeThrough(tap), ...rest };
    },
  };
}

/** Create memory middleware. `wrap(model, scope)` returns the model with memory. */
export function createNamsMemory(config: NamsMemoryConfig) {
  const maxMemories = config.maxMemories ?? 6;
  const persist = config.persistInteractions ?? true;

  return {
    wrap(model: LanguageModelV4, scope: NamsScope, providerId?: string): LanguageModelV4 {
      const middleware = buildMiddleware(config, scope, maxMemories, persist);
      return wrapLanguageModel({ model, middleware, ...(providerId && { providerId }) });
    },
  };
}
