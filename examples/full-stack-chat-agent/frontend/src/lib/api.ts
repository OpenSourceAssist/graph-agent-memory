/**
 * API client for the chat backend.
 */

import type {
  Thread,
  ThreadWithMessages,
  Preference,
  Entity,
  MemoryContext,
  MemoryGraph,
  SSEEvent,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

/**
 * Generic fetch wrapper with error handling.
 */
async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP ${response.status}`);
  }

  return response.json();
}

// Thread API
export const threads = {
  list: () => fetchAPI<Thread[]>("/threads"),

  create: (title?: string) =>
    fetchAPI<Thread>("/threads", {
      method: "POST",
      body: JSON.stringify({ title }),
    }),

  get: (id: string) => fetchAPI<ThreadWithMessages>(`/threads/${id}`),

  delete: (id: string) =>
    fetchAPI<{ status: string }>(`/threads/${id}`, { method: "DELETE" }),

  update: (id: string, title: string) =>
    fetchAPI<Thread>(`/threads/${id}?title=${encodeURIComponent(title)}`, {
      method: "PATCH",
    }),
};

// Preferences API
export const preferences = {
  list: (category?: string) =>
    fetchAPI<Preference[]>(
      `/preferences${category ? `?category=${category}` : ""}`,
    ),

  add: (category: string, preference: string, context?: string) =>
    fetchAPI<Preference>("/preferences", {
      method: "POST",
      body: JSON.stringify({ category, preference, context }),
    }),

  delete: (id: string) =>
    fetchAPI<{ status: string }>(`/preferences/${id}`, { method: "DELETE" }),
};

// Entities API
export const entities = {
  list: (type?: string, query?: string) => {
    const params = new URLSearchParams();
    if (type) params.set("type", type);
    if (query) params.set("query", query);
    const queryStr = params.toString();
    return fetchAPI<Entity[]>(`/entities${queryStr ? `?${queryStr}` : ""}`);
  },
};

// Memory API
export const memory = {
  getContext: (threadId?: string, query?: string) => {
    const params = new URLSearchParams();
    if (threadId) params.set("thread_id", threadId);
    if (query) params.set("query", query);
    const queryStr = params.toString();
    return fetchAPI<MemoryContext>(
      `/memory/context${queryStr ? `?${queryStr}` : ""}`,
    );
  },

  getGraph: (threadId?: string) => {
    const params = new URLSearchParams();
    if (threadId) {
      params.set("session_id", threadId);
    }
    const query = params.toString();
    return fetchAPI<MemoryGraph>(`/memory/graph${query ? `?${query}` : ""}`);
  },

  getNodeNeighbors: (nodeId: string, depth: number = 1, limit: number = 50) => {
    const params = new URLSearchParams({
      depth: String(depth),
      limit: String(limit),
    });
    return fetchAPI<MemoryGraph>(
      `/memory/graph/neighbors/${encodeURIComponent(nodeId)}?${params}`,
    );
  },
};

// Chat API with SSE streaming
export async function* streamChat(
  threadId: string,
  message: string,
  memoryEnabled: boolean = true,
): AsyncGenerator<SSEEvent> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      thread_id: threadId,
      message,
      memory_enabled: memoryEnabled,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data) {
            try {
              const event: SSEEvent = JSON.parse(data);
              yield event;
            } catch {
              // Skip invalid JSON
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export const api = {
  threads,
  preferences,
  entities,
  memory,
  streamChat,
};
