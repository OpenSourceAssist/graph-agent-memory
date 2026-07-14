/**
 * Tools mode — model-driven memory.
 *
 * createNamsMemoryTools() returns { query_memory, store_memory } AI SDK tools.
 * createNamsTools() is the async variant that can also merge in MCP tools
 * (an optional extension of tools mode, not a separate mode).
 */

import { tool, zodSchema, type LanguageModel, type ToolSet } from 'ai';
import { z } from 'zod';
import {
  makeClient,
  getLogger,
  resolveLogger,
  resolveConversation,
  retrieveMemories,
  storeMemory,
  type NamsConfig,
  type NamsScope,
  type MemoryHit,
} from './vercel-ai-provider-client';
import { createGraphExtractor } from './vercel-ai-provider-extract';

//Schemas

const querySchema = z.object({
  query: z.string().describe('Keywords or phrase to search in memory'),
  limit: z.number().int().min(1).max(20).default(5),
});

const storeSchema = z.object({
  content: z.string().min(1).max(2000).describe('The information to remember'),
  type: z.enum(['fact', 'interaction', 'pattern', 'user_preference']).describe(
    'fact=persistent knowledge | interaction=conversation event | ' +
    'pattern=recurring behaviour | user_preference=explicit setting',
  ),
  confidence: z.number().min(0).max(1).default(0.7).describe(
    'Confidence 0–1: 0.8–1.0 very high · 0.6–0.8 high · 0.3–0.6 medium · 0–0.3 low',
  ),
  tags: z.array(z.string().max(40)).max(10).default([]),
});

export type QueryInput = z.infer<typeof querySchema>;
export type StoreInput = z.infer<typeof storeSchema>;
export type QueryOutput = { found: boolean; count?: number; message?: string; memories: MemoryHit[] };
export type StoreOutput = { stored: boolean; type: string; preview: string; message: string };

//Options

export interface NamsToolsOptions extends NamsConfig, NamsScope {
  extractionModel?: LanguageModel;
}

/** MCP server connection config. Headers are sent on every request (e.g. Authorization). */
export interface McpConfig {
  url: string;
  headers?: Record<string, string>;
}

export interface NamsToolsWithMcpOptions extends NamsToolsOptions {
  mcp?: McpConfig;
}

export interface NamsToolsResult {
  /** Merged NAMS + MCP tools, ready to pass to ToolLoopAgent `tools:`. */
  tools: ToolSet;
  /** Close the MCP connection (no-op when MCP was not configured). Call in `onFinish`. */
  close: () => Promise<void>;
}

export function createNamsMemoryTools(options: NamsToolsOptions) {
  const client = makeClient(options);
  const scope: NamsScope = { userId: options.userId, conversationId: options.conversationId };
  const extractor = options.extractionModel ? createGraphExtractor(options.extractionModel) : undefined;

  let convIdPromise: Promise<string> | null = null;
  const getConvId = (): Promise<string> =>
    (convIdPromise ??= resolveConversation(client, options, scope));

  const query_memory = tool<QueryInput, QueryOutput>({
    description:
      'Search NAMS (Neo4j Agent Memory System) for context relevant to the current message. ' +
      'Call this FIRST every turn before answering.',
    inputSchema: zodSchema(querySchema),
    execute: async ({ query, limit }) => {
      try {
        const convId = await getConvId();
        const memories = await retrieveMemories(client, scope, convId, query, limit);
        if (memories.length === 0)
          return { found: false, message: 'No relevant memories found.', memories: [] };
        return { found: true, count: memories.length, memories };
      } catch (err) {
        getLogger(client).error('query_memory failed', err);
        return { found: false, message: 'Memory lookup failed.', memories: [] };
      }
    },
  });

  const store_memory = tool<StoreInput, StoreOutput>({
    description:
      'Persist important information to NAMS (Neo4j graph). ' +
      'Call this AFTER your response to save facts, preferences, and patterns.',
    inputSchema: zodSchema(storeSchema),
    execute: async ({ content, type, confidence, tags }) => {
      try {
        const convId = await getConvId();
        await storeMemory(client, convId, { content, type, confidence, tags }, { extractor });
        return {
          stored: true,
          type,
          preview: content.slice(0, 80),
          message: `Memory stored (${type}, confidence=${confidence})`,
        };
      } catch (err) {
        getLogger(client).error('store_memory failed', err);
        return { stored: false, type, preview: content.slice(0, 80), message: 'Failed to store memory.' };
      }
    },
  });

  return { query_memory, store_memory };
}

/**
 * Async variant of createNamsMemoryTools. Optionally connects to an MCP
 * server and merges its tools with the NAMS memory tools.
 */
export async function createNamsTools(options: NamsToolsWithMcpOptions): Promise<NamsToolsResult> {
  const namsTools = createNamsMemoryTools(options);

  if (!options.mcp) {
    return { tools: namsTools, close: async () => {} };
  }

  const { createMCPClient } = await import('@ai-sdk/mcp');
  const mcpClient = await createMCPClient({
    transport: { type: 'http', url: options.mcp.url, headers: options.mcp.headers },
  });

  const mcpTools = await mcpClient.tools();

  const collisions = Object.keys(mcpTools).filter(name => name in namsTools);
  if (collisions.length > 0) {
    resolveLogger(options).warn(
      `MCP tool(s) [${collisions.join(', ')}] share a name with NAMS memory tools and will override them`,
    );
  }

  return {
    tools: { ...namsTools, ...mcpTools },
    close: () => mcpClient.close(),
  };
}

export class NamsMemoryTools {
  constructor(private readonly base: Omit<NamsToolsOptions, 'userId' | 'conversationId'>) { }

  /** Synchronous — returns NAMS memory tools only. */
  forUser(userId: string, conversationId?: string) {
    return createNamsMemoryTools({ ...this.base, userId, conversationId });
  }

  /** Async — returns NAMS + optional MCP tools merged, plus a close() handle. */
  async forUserWithMcp(
    userId: string,
    mcp?: McpConfig,
    conversationId?: string,
  ): Promise<NamsToolsResult> {
    return createNamsTools({ ...this.base, userId, conversationId, mcp });
  }
}
