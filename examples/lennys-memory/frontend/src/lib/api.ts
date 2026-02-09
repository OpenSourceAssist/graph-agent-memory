/**
 * API client for the chat backend.
 */

import type {
  Thread,
  ThreadWithMessages,
  MemoryGraph,
  LocationEntity,
  SSEEvent,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

// Default timeout for API requests (10 seconds)
const DEFAULT_TIMEOUT = 10000;

/**
 * Generic fetch wrapper with error handling and timeout.
 */
async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit & { timeout?: number },
): Promise<T> {
  const { timeout = DEFAULT_TIMEOUT, ...fetchOptions } = options || {};

  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...fetchOptions?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || `HTTP ${response.status}`);
    }

    return response.json();
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("Request timed out");
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
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

// Memory API
export const memory = {
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
  memory,
  locations,
  streamChat,
};
