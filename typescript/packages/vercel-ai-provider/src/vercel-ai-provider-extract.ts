import { generateText, Output, zodSchema } from 'ai';
import type { LanguageModel } from 'ai';
import { z } from 'zod';
import type { MemoryClient } from '@neo4j-labs/agent-memory';
import { GraphExtractor, StoreInput } from './vercel-ai-provider-types';
import { getLogger } from './vercel-ai-provider-client';

const graphSchema = z.object({
  entities: z
    .array(
      z.object({
        name: z.string().describe('Canonical entity name, e.g. "Alex", "Neovim", "TechCorp"'),
        type: z.string().describe('person | organization | tool | place | concept | preference | event'),
        description: z.string().optional(),
      }),
    )
    .describe('Distinct, real, named entities only. Do not invent.'),
  relationships: z
    .array(
      z.object({
        from: z.string().describe('Source entity name (must match an entity above)'),
        to: z.string().describe('Target entity name (must match an entity above)'),
        type: z.string().describe('Relationship label, e.g. PREFERS, WORKS_AT, USES, LOCATED_IN'),
      }),
    )
    .default([]),
});

/**
 * Build a graph extractor backed by an AI SDK model. Extracts entities and
 * relationships from a stored memory so the graph actually forms, instead of
 * one sentence-shaped node. Costs one extra model call per stored memory.
 */
export function createGraphExtractor(model: LanguageModel): GraphExtractor {
  return async function extractAndStore(client: MemoryClient, input: StoreInput): Promise<void> {
    const { output: object } = await generateText({
      model,
      output: Output.object({ schema: zodSchema(graphSchema) }),
      prompt:
        `Extract entities and the relationships between them from the memory below. ` +
        `Be conservative: only real, named entities; skip filler.\n\n` +
        `Memory (${input.type}): ${input.content}`,
    });

    const nameToId = new Map<string, string>();
    for (const e of object.entities) {
      const entity = await client.longTerm.addEntity(e.name, e.type, {
        description: e.description ?? input.content,
      });
      if (entity?.id) nameToId.set(e.name, entity.id);
      if (entity?.id && input.confidence !== undefined) {
        await client.longTerm
          .setEntityFeedback(entity.id, { userScore: input.confidence, confirmed: input.confidence >= 0.8 })
          .catch((e: unknown) => getLogger(client).warn('setEntityFeedback failed', e));
      }
    }

    const log = getLogger(client);
    for (const r of object.relationships) {
      const from = nameToId.get(r.from);
      const to = nameToId.get(r.to);
      if (from && to) {
        await client.longTerm
          .addRelationship(from, to, r.type)
          .catch((e: unknown) => log.warn('addRelationship failed', e));
      }
    }
  };
}
