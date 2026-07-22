/**
 * Graph extraction — entities and relationships extracted from a stored
 * memory must land in the long-term graph via the real SDK API:
 * addEntity(name, type, options) and addRelationship(sourceId, targetId, type).
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { makeFakeClient, type FakeClient } from './vercel-ai-provider-helpers';

vi.mock('ai', async (importOriginal) => ({
  ...(await importOriginal<typeof import('ai')>()),
  generateText: vi.fn(),
}));

import { generateText } from 'ai';
import { createGraphExtractor } from '../src/vercel-ai-provider-extract';

const mockedGenerateText = vi.mocked(generateText);

const graphResult = (entities: any[], relationships: any[] = []) =>
  ({ output: { entities, relationships } }) as any;

let fake: FakeClient;

beforeEach(() => {
  vi.clearAllMocks();
  fake = makeFakeClient();
  vi.spyOn(console, 'warn').mockImplementation(() => {});
});

describe('createGraphExtractor', () => {
  it('stores extracted entities and links them with positional addRelationship args', async () => {
    mockedGenerateText.mockResolvedValue(graphResult(
      [
        { name: 'Alex', type: 'person', description: 'A user' },
        { name: 'TechCorp', type: 'organization' },
      ],
      [{ from: 'Alex', to: 'TechCorp', type: 'WORKS_AT' }],
    ));

    const extract = createGraphExtractor({} as any);
    await extract(fake as any, { content: 'Alex works at TechCorp', type: 'fact' });

    expect(fake.longTerm.addEntity).toHaveBeenCalledWith('Alex', 'person', { description: 'A user' });
    expect(fake.longTerm.addEntity).toHaveBeenCalledWith('TechCorp', 'organization', {
      description: 'Alex works at TechCorp',
    });
    // SDK signature: addRelationship(sourceId, targetId, relationshipType)
    expect(fake.longTerm.addRelationship).toHaveBeenCalledWith('ent-Alex', 'ent-TechCorp', 'WORKS_AT');
  });

  it('skips relationships whose endpoints were not extracted', async () => {
    mockedGenerateText.mockResolvedValue(graphResult(
      [{ name: 'Alex', type: 'person' }],
      [{ from: 'Alex', to: 'Ghost', type: 'KNOWS' }],
    ));

    const extract = createGraphExtractor({} as any);
    await extract(fake as any, { content: 'Alex', type: 'fact' });

    expect(fake.longTerm.addRelationship).not.toHaveBeenCalled();
  });

  it('treats relationship write failures as non-fatal', async () => {
    mockedGenerateText.mockResolvedValue(graphResult(
      [
        { name: 'A', type: 'concept' },
        { name: 'B', type: 'concept' },
      ],
      [{ from: 'A', to: 'B', type: 'RELATES_TO' }],
    ));
    fake.longTerm.addRelationship.mockRejectedValue(new Error('write failed'));

    const extract = createGraphExtractor({} as any);
    await expect(
      extract(fake as any, { content: 'A relates to B', type: 'fact' }),
    ).resolves.toBeUndefined();
  });

  it('records confidence feedback on stored entities when provided', async () => {
    mockedGenerateText.mockResolvedValue(graphResult([{ name: 'Alex', type: 'person' }]));

    const extract = createGraphExtractor({} as any);
    await extract(fake as any, { content: 'Alex', type: 'fact', confidence: 0.9 });

    expect(fake.longTerm.setEntityFeedback).toHaveBeenCalledWith('ent-Alex', {
      userScore: 0.9,
      confirmed: true,
    });
  });
});
