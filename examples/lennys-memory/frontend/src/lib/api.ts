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
  LocationEntity,
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

  /**
   * Get most mentioned entities across all podcasts.
   */
  top: (entityType?: string, limit: number = 10) => {
    const params = new URLSearchParams();
    if (entityType) params.set("entity_type", entityType);
    params.set("limit", String(limit));
    return fetchAPI<
      Array<{
        id: string;
        name: string;
        type: string;
        subtype?: string;
        description?: string;
        wikipedia_url?: string;
        enriched_description?: string;
        mentions: number;
      }>
    >(`/entities/top?${params}`);
  },

  /**
   * Get full context for an entity including enrichment and mentions.
   */
  context: (entityName: string) =>
    fetchAPI<{
      entity: {
        id: string;
        name: string;
        type: string;
        subtype?: string;
        description?: string;
        enriched_description?: string;
        wikipedia_url?: string;
      };
      mentions: Array<{
        content: string;
        speaker: string;
        session_id: string;
      }>;
    }>(`/entities/${encodeURIComponent(entityName)}/context`),

  /**
   * Get entities related to a given entity through co-occurrence.
   */
  related: (entityName: string, limit: number = 10) =>
    fetchAPI<
      Array<{
        id: string;
        name: string;
        type: string;
        subtype?: string;
        description?: string;
        co_occurrences: number;
      }>
    >(`/entities/related/${encodeURIComponent(entityName)}?limit=${limit}`),
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

  getGraph: (threadId?: string, episodeSessionIds?: string[]) => {
    const params = new URLSearchParams();
    if (threadId) {
      params.set("session_id", threadId);
    }
    if (episodeSessionIds && episodeSessionIds.length > 0) {
      params.set("episode_session_ids", episodeSessionIds.join(","));
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

  /**
   * Find similar past reasoning traces for a given task.
   */
  getSimilarTraces: (
    task: string,
    limit: number = 3,
    successOnly: boolean = true,
  ) => {
    const params = new URLSearchParams({
      task,
      limit: String(limit),
      success_only: String(successOnly),
    });
    return fetchAPI<
      Array<{
        id: string;
        session_id?: string;
        task: string;
        outcome?: string;
        success?: boolean;
        started_at?: string;
        completed_at?: string;
        similarity?: number;
      }>
    >(`/memory/similar-traces?${params}`);
  },
};

// Locations API (for map view)
export const locations = {
  /**
   * Get locations, optionally filtered by conversation thread.
   */
  list: (options?: {
    threadId?: string;
    hasCoordinates?: boolean;
    limit?: number;
  }) => {
    const params = new URLSearchParams();
    if (options?.threadId) params.set("session_id", options.threadId);
    if (options?.hasCoordinates !== undefined)
      params.set("has_coordinates", String(options.hasCoordinates));
    if (options?.limit) params.set("limit", String(options.limit));
    const query = params.toString();
    return fetchAPI<LocationEntity[]>(`/locations${query ? `?${query}` : ""}`);
  },

  /**
   * Find locations near a point.
   */
  nearby: (
    lat: number,
    lon: number,
    radiusKm: number = 10,
    threadId?: string,
  ) => {
    const params = new URLSearchParams({
      lat: String(lat),
      lon: String(lon),
      radius_km: String(radiusKm),
    });
    if (threadId) params.set("session_id", threadId);
    return fetchAPI<LocationEntity[]>(`/locations/nearby?${params}`);
  },

  /**
   * Find locations within a bounding box.
   */
  inBounds: (
    bounds: {
      minLat: number;
      maxLat: number;
      minLon: number;
      maxLon: number;
    },
    threadId?: string,
  ) => {
    const params = new URLSearchParams({
      min_lat: String(bounds.minLat),
      max_lat: String(bounds.maxLat),
      min_lon: String(bounds.minLon),
      max_lon: String(bounds.maxLon),
    });
    if (threadId) params.set("session_id", threadId);
    return fetchAPI<LocationEntity[]>(`/locations/bounds?${params}`);
  },

  /**
   * Get shortest path between two locations in the graph.
   */
  shortestPath: (fromId: string, toId: string) =>
    fetchAPI<{
      nodes: Array<{
        id: string;
        name: string;
        type: string;
        labels: string[];
        latitude?: number;
        longitude?: number;
      }>;
      relationships: Array<{
        type: string;
        from_id: string;
        to_id: string;
      }>;
      hops: number;
      found: boolean;
    }>(
      `/locations/path?from_location_id=${encodeURIComponent(fromId)}&to_location_id=${encodeURIComponent(toId)}`,
    ),

  /**
   * Get location clusters for heatmap visualization.
   */
  clusters: (threadId?: string) => {
    const params = new URLSearchParams();
    if (threadId) params.set("session_id", threadId);
    const query = params.toString();
    return fetchAPI<
      Array<{
        country: string;
        location_count: number;
        locations: Array<{
          name: string;
          latitude: number;
          longitude: number;
        }>;
        center_lat: number;
        center_lon: number;
      }>
    >(`/locations/clusters${query ? `?${query}` : ""}`);
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
  locations,
  streamChat,
};
