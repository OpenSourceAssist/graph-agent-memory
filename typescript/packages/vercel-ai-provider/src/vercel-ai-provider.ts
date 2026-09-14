/**
 * Provider mode. Wraps any AI SDK provider so every call loads memory first
 * and saves the turn after.
 *
 * No entity extraction here. NAMS extracts saved turns server-side. Use tools
 * mode for long-term memory.
 */

import type { ProviderV4, LanguageModelV4, EmbeddingModelV4, ImageModelV4 } from '@ai-sdk/provider';
import { NoSuchModelError } from '@ai-sdk/provider';
import { createNamsMemory } from './vercel-ai-provider-middleware';
import { NamsConfig, NamsScope } from './vercel-ai-provider-types';

export interface NamsProviderOptions extends NamsConfig {
  baseProvider: (modelId: string) => LanguageModelV4;
  /** User and conversation. Create one provider per user session. */
  scope: NamsScope;
  /** Max memories added to the prompt per turn (default: 6). */
  maxMemories?: number;
  /** Save each turn to NAMS (default: true). */
  persistInteractions?: boolean;
}

/** Create a NAMS provider. Works with `createProviderRegistry`. */
export function createNamsProvider(options: NamsProviderOptions): ProviderV4 {
  const { baseProvider, scope, ...memoryConfig } = options;
  const memory = createNamsMemory(memoryConfig);

  return {
    specificationVersion: 'v4',

    languageModel(modelId: string): LanguageModelV4 {
      const base = baseProvider(modelId);
      return memory.wrap(base, scope, 'nams');
    },

    embeddingModel(modelId: string): EmbeddingModelV4 {
      throw new NoSuchModelError({ modelId, modelType: 'embeddingModel' });
    },

    imageModel(modelId: string): ImageModelV4 {
      throw new NoSuchModelError({ modelId, modelType: 'imageModel' });
    },
  };
}
