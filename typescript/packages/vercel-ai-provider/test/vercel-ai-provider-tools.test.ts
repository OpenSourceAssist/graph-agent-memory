/**
 * Tools mode — query_memory / store_memory as model-driven AI SDK tools.
 *
 * Contract points:
 *  - query_memory returns found=true with hits, found=false when empty
 *  - store_memory(interaction) → short-term message
 *  - store_memory(fact) → long-term entity + confidence feedback
 *  - existing entities are reused, not duplicated
 *  - a storage failure reports stored=false instead of throwing into the loop
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { makeFakeClient, type FakeClient } from './vercel-ai-provider-helpers';

const holder = vi.hoisted(() => ({ client: undefined as unknown }));

vi.mock('@neo4j-labs/agent-memory', () => ({
  MemoryClient: vi.fn().mockImplementation(() => holder.client),
}));

import { createNamsMemoryTools } from '../src/vercel-ai-provider-tools';
import type { QueryOutput, StoreOutput } from '../src/vercel-ai-provider-tools';

let fake: FakeClient;
let userCounter = 0;
const freshUser = () => `tools-user-${Date.now()}-${userCounter++}`;

const toolOptions = { toolCallId: 'call-1', messages: [] } as any;

/** Tool execute() is typed T | AsyncIterable<T>; our tools always return T. */
async function callTool<T>(t: { execute?: unknown }, input: unknown): Promise<T> {
  return (await (t.execute as (i: unknown, o: unknown) => Promise<unknown>)(input, toolOptions)) as T;
}

beforeEach(() => {
  fake = makeFakeClient();
  holder.client = fake;
  vi.spyOn(console, 'log').mockImplementation(() => {});
  vi.spyOn(console, 'warn').mockImplementation(() => {});
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

describe('query_memory', () => {
  it('returns found=true with ranked memories', async () => {
    fake.longTerm.searchEntities.mockResolvedValue([
      { name: 'Alex', description: 'User is named Alex', type: 'person', confidence: 0.92 },
    ]);
    fake.shortTerm.searchMessages.mockResolvedValue([
      { content: 'I love terse answers' },
    ]);

    const { query_memory } = createNamsMemoryTools({
      apiKey: 'k',
      userId: freshUser(),
      conversationId: 'conv-q',
    });

    const out = await callTool<QueryOutput>(query_memory, { query: 'who am I', limit: 5 });

    expect(out.found).toBe(true);
    expect(out.count).toBe(2);
    // Scores present → sorted descending, long-term hit first.
    expect(out.memories[0]).toMatchObject({ content: 'User is named Alex', source: 'long-term' });
    expect(out.memories[1]).toMatchObject({ content: 'I love terse answers', source: 'conversation' });
  });

  it('returns found=false when nothing matches', async () => {
    const { query_memory } = createNamsMemoryTools({
      apiKey: 'k',
      userId: freshUser(),
      conversationId: 'conv-q2',
    });

    const out = await callTool<QueryOutput>(query_memory, { query: 'anything', limit: 5 });

    expect(out.found).toBe(false);
    expect(out.memories).toEqual([]);
    expect(out.message).toMatch(/no relevant memories/i);
  });

  it('deduplicates identical content across sources', async () => {
    fake.longTerm.searchEntities.mockResolvedValue([
      { name: 'x', description: 'duplicate fact', type: 'fact' },
    ]);
    fake.shortTerm.searchMessages.mockResolvedValue([{ content: 'duplicate fact' }]);

    const { query_memory } = createNamsMemoryTools({
      apiKey: 'k',
      userId: freshUser(),
      conversationId: 'conv-q3',
    });

    const out = await callTool<QueryOutput>(query_memory, { query: 'dup', limit: 5 });
    expect(out.memories).toHaveLength(1);
  });

  it('caps the number of returned memories at the requested limit', async () => {
    fake.longTerm.searchEntities.mockResolvedValue(
      Array.from({ length: 5 }, (_, i) => ({ name: `e${i}`, description: `fact ${i}`, type: 'fact' })),
    );
    fake.shortTerm.searchMessages.mockResolvedValue(
      Array.from({ length: 5 }, (_, i) => ({ content: `message ${i}` })),
    );

    const { query_memory } = createNamsMemoryTools({
      apiKey: 'k',
      userId: freshUser(),
      conversationId: 'conv-q4',
    });

    const out = await callTool<QueryOutput>(query_memory, { query: 'lots', limit: 3 });
    expect(out.memories).toHaveLength(3);
  });
});

describe('store_memory', () => {
  it('stores an interaction as a short-term message', async () => {
    const { store_memory } = createNamsMemoryTools({
      apiKey: 'k',
      userId: freshUser(),
      conversationId: 'conv-s1',
    });

    const out = await callTool<StoreOutput>(store_memory,
      { content: 'User asked about pricing', type: 'interaction', confidence: 0.7, tags: [] },
    );

    expect(out.stored).toBe(true);
    expect(fake.shortTerm.addMessage).toHaveBeenCalledWith(
      'conv-s1', 'assistant', 'User asked about pricing',
    );
    expect(fake.longTerm.addEntity).not.toHaveBeenCalled();
  });

  it('stores a fact as a long-term entity with confidence feedback', async () => {
    const { store_memory } = createNamsMemoryTools({
      apiKey: 'k',
      userId: freshUser(),
      conversationId: 'conv-s2',
    });

    const out = await callTool<StoreOutput>(store_memory,
      { content: 'Prefers dark mode', type: 'user_preference', confidence: 0.9, tags: [] },
    );

    expect(out.stored).toBe(true);
    expect(fake.longTerm.addEntity).toHaveBeenCalledWith(
      'Prefers dark mode', 'user_preference', { description: 'Prefers dark mode' },
    );
    expect(fake.longTerm.setEntityFeedback).toHaveBeenCalledWith(
      'ent-Prefers dark mode', { userScore: 0.9, confirmed: true },
    );
  });

  it('reuses an existing entity instead of duplicating it', async () => {
    fake.longTerm.getEntityByName.mockResolvedValue({ id: 'ent-existing', name: 'Prefers dark mode' });

    const { store_memory } = createNamsMemoryTools({
      apiKey: 'k',
      userId: freshUser(),
      conversationId: 'conv-s3',
    });

    await callTool<StoreOutput>(store_memory,
      { content: 'Prefers dark mode', type: 'fact', confidence: 0.7, tags: [] },
    );

    expect(fake.longTerm.addEntity).not.toHaveBeenCalled();
    expect(fake.longTerm.setEntityFeedback).toHaveBeenCalledWith(
      'ent-existing', expect.objectContaining({ userScore: 0.7 }),
    );
  });

  it('reports stored=false on failure instead of throwing', async () => {
    fake.shortTerm.addMessage.mockRejectedValue(new Error('write failed'));

    const { store_memory } = createNamsMemoryTools({
      apiKey: 'k',
      userId: freshUser(),
      conversationId: 'conv-s4',
    });

    const out = await callTool<StoreOutput>(store_memory,
      { content: 'x', type: 'interaction', confidence: 0.7, tags: [] },
    );

    expect(out.stored).toBe(false);
    expect(out.message).toMatch(/failed/i);
  });
});
