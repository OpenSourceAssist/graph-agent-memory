/**
 * Neo4j Agent Memory (NAMS) for the Vercel AI SDK.
 *
 * Four ways to add memory:
 * - Provider   `createNamsProvider()`  wraps a provider. Memory is automatic.
 * - Middleware `createNams().wrap()`   wraps a model. Memory is automatic.
 * - Tools      `createNams().tools()`  the model calls query_memory / store_memory.
 *              `.toolsWithMcp()` also adds tools from an MCP server.
 * - Hooks      `createNams().hooks()`  your code loads and saves the session.
 *              Pass `hooks` to run lifecycle hooks too.
 *
 * @example
 * ```ts
 * const nams  = createNams({ apiKey: process.env.MEMORY_API_KEY! });
 * const model = nams.wrap(openai('gpt-5.4-mini'), { userId });
 * ```
 */

export type { NamsConfig, NamsScope, NamsLogger, MemoryHit, StoreInput, GraphExtractor } from './vercel-ai-provider-client';
export type { NamsMemoryConfig } from './vercel-ai-provider-middleware';
export type {
  NamsToolsOptions, NamsToolsWithMcpOptions, NamsToolsResult, McpConnectionStatus,
  McpConfig, QueryInput, StoreInput as ToolStoreInput,
  QueryOutput, StoreOutput
} from './vercel-ai-provider-tools';
export type { NamsProviderOptions } from './vercel-ai-provider';

export { makeClient, getLogger, resolveConversation, findExistingConversation, retrieveMemories, storeMemory } from './vercel-ai-provider-client';
export { createGraphExtractor } from './vercel-ai-provider-extract';
export type { GraphExtractorOptions } from './vercel-ai-provider-extract';
export { createNamsMemory } from './vercel-ai-provider-middleware';
export { createNamsMemoryTools, createNamsTools, enforceQueryMemory, ensureMemoryStored, NamsMemoryTools, NamsMcpConnectionError } from './vercel-ai-provider-tools';
export type {
  EnforceQueryMemoryOptions, EnsureMemoryStoredOptions, EnsureMemoryStoredResult,
  FinishedTurn, UnstoredTurn,
} from './vercel-ai-provider-tools';
export { createNamsProvider } from './vercel-ai-provider';
export { createNamsHooks } from './vercel-ai-provider-hooks';
export type {
  NamsHooks, NamsHooksOptions, LoadSessionOptions, OnFinishScope,
  NamsOnFinishEvent, NamsOnFinishCallback,
  PrepareOptions, PrepareResult, NamsToolBlocked, SessionTurn,
} from './vercel-ai-provider-hooks';
export { compileHooks } from './vercel-ai-provider-hook-events';
export type {
  NamsHookEvent, NamsHookConfig, NamsHookGroup, NamsHookEntry, NamsHookHandler,
  NamsHookInputs, NamsHookOutputs, NamsHookResult, NamsHookRegistry,
  NamsHookBase, NamsSystemMessageSink,
  SessionStartInput, UserPromptSubmitInput, PreToolUseInput, PostToolUseInput,
  PostToolUseFailureInput, PreMemoryWriteInput, StopInput, SessionEndInput,
  SessionStartOutput, UserPromptSubmitOutput, PreToolUseOutput, PostToolUseOutput,
  PostToolUseFailureOutput, PreMemoryWriteOutput, StopOutput, SessionEndOutput,
} from './vercel-ai-provider-hook-events';

import type { LanguageModel } from 'ai';
import type { LanguageModelV4 } from '@ai-sdk/provider';
import type { NamsConfig, NamsScope } from './vercel-ai-provider-client';
import type { NamsMemoryConfig } from './vercel-ai-provider-middleware';
import type { GraphExtractorOptions } from './vercel-ai-provider-extract';
import type { McpConfig } from './vercel-ai-provider-tools';
import { resolveLogger } from './vercel-ai-provider-client';
import { createNamsMemory } from './vercel-ai-provider-middleware';
import { createNamsMemoryTools, createNamsTools } from './vercel-ai-provider-tools';
import { createNamsHooks, type NamsHooksOptions } from './vercel-ai-provider-hooks';

/** The four NAMS integration modes. */
export type NamsMode = 'provider' | 'middleware' | 'tools' | 'hooks';

export interface NamsFactoryConfig extends NamsConfig {
  /**
   * Tools mode only. Extracts entities and relationships from each stored
   * memory. Costs one extra model call per memory. Other modes warn and ignore it.
   */
  extractionModel?: LanguageModel;
  /** Extractor options, e.g. a custom `skipEntity` filter. */
  extractionOptions?: GraphExtractorOptions;
  maxMemories?: number;
  persistInteractions?: boolean;
}

/**
 * Create a NAMS instance for middleware, tools, and hooks modes.
 * For provider mode, use `createNamsProvider`.
 */
export function createNams(config: NamsFactoryConfig) {
  const providerConfig: NamsMemoryConfig = {
    apiKey: config.apiKey,
    endpoint: config.endpoint,
    workspaceId: config.workspaceId,
    logger: config.logger,
    maxMemories: config.maxMemories,
    persistInteractions: config.persistInteractions,
  };

  const memory = createNamsMemory(providerConfig);

  // Warn once when extractionModel is set in a mode that ignores it.
  let extractionScopeWarned = false;
  const warnExtractionIgnored = (mode: string): void => {
    if (extractionScopeWarned || !config.extractionModel) return;
    extractionScopeWarned = true;
    resolveLogger(config).warn(
      `extractionModel is ignored in ${mode} mode — NAMS extracts persisted ` +
      `turns server-side. It applies to .tools()/.toolsWithMcp() only.`,
    );
  };

  return {
    /** Middleware mode. Returns the model with memory added. No tool calls. */
    wrap(model: LanguageModelV4, scope: NamsScope): LanguageModelV4 {
      warnExtractionIgnored('middleware');
      return memory.wrap(model, scope);
    },

    /**
     * Tools mode. Returns the `query_memory` and `store_memory` tools.
     * Tell the model to query, answer, then store.
     */
    tools(scope: NamsScope) {
      return createNamsMemoryTools({
        ...config,
        userId: scope.userId,
        conversationId: scope.conversationId,
        extractionModel: config.extractionModel,
      });
    },

    /**
     * Tools mode plus the tools of an MCP server. Returns `{ tools, close, mcp }`.
     * Call `close()` when done. `mcp.toolNames` lists the tools that loaded.
     * Without `mcpConfig` it works like `.tools()`.
     *
     * Throws `NamsMcpConnectionError` if the connection fails. Set
     * `mcp.optional` to fall back to the memory tools instead.
     */
    async toolsWithMcp(scope: NamsScope, mcpConfig?: McpConfig) {
      return createNamsTools({
        ...config,
        userId: scope.userId,
        conversationId: scope.conversationId,
        extractionModel: config.extractionModel,
        mcp: mcpConfig,
      });
    },

    /**
     * Hooks mode. Your code, not the model, loads and saves the session.
     * Call `loadSession()` before a generation and pass `onFinish()` as the
     * finish callback. Scope can be set here, per call, or on `runtimeContext`.
     * Add `.tools()` if the model should also manage long-term memory.
     *
     * Pass `hooks` to register lifecycle hooks, then run them with
     * `prepare()`, `withHooks()`, and `end()`.
     */
    hooks(scope?: Partial<NamsScope> & Pick<NamsHooksOptions, 'hooks' | 'onSystemMessage' | 'sessionLimit'>) {
      warnExtractionIgnored('hooks');
      const { extractionModel: _m, extractionOptions: _o, ...hooksConfig } = config;
      return createNamsHooks({
        ...hooksConfig,
        userId: scope?.userId,
        conversationId: scope?.conversationId,
        hooks: scope?.hooks,
        onSystemMessage: scope?.onSystemMessage,
        sessionLimit: scope?.sessionLimit,
      });
    },
  };
}
