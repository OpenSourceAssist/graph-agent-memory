/**
 * API client for the retail assistant backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  category: string;
  brand: string;
  in_stock: boolean;
  inventory?: number;
  image_url?: string;
  attributes?: Record<string, string>;
  relevance_score?: number;
}

export interface MemoryContext {
  short_term: Array<{
    id: string;
    role: string;
    content: string;
    timestamp?: string;
  }>;
  long_term: {
    entities: Array<{
      id: string;
      name: string;
      type: string;
      description?: string;
    }>;
    preferences: Array<{
      id: string;
      category: string;
      preference: string;
      context?: string;
    }>;
  };
  reasoning: Array<{
    id: string;
    task: string;
    outcome: string;
    steps: number;
  }>;
}

export interface GraphData {
  nodes: Array<{
    id: string;
    label: string;
    type: string;
    properties?: Record<string, unknown>;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
    type: string;
  }>;
}

/**
 * Stream a chat message and receive SSE responses.
 */
export async function* streamChat(
  message: string,
  sessionId?: string,
  userId?: string
): AsyncGenerator<{
  event: string;
  data: unknown;
}> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      user_id: userId,
    }),
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("event:")) {
        const event = line.slice(6).trim();
        continue;
      }
      if (line.startsWith("data:")) {
        const dataStr = line.slice(5).trim();
        if (dataStr) {
          try {
            const data = JSON.parse(dataStr);
            yield { event: "message", data };
          } catch {
            // Skip malformed JSON
          }
        }
      }
    }
  }
}

/**
 * Send a synchronous chat message.
 */
export async function sendChat(
  message: string,
  sessionId?: string,
  userId?: string
): Promise<{ response: string; session_id: string }> {
  const response = await fetch(`${API_BASE}/chat/sync`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      user_id: userId,
    }),
  });

  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get memory context for a session.
 */
export async function getMemoryContext(
  sessionId: string,
  query?: string
): Promise<MemoryContext> {
  const params = new URLSearchParams({ session_id: sessionId });
  if (query) params.append("query", query);

  const response = await fetch(`${API_BASE}/memory/context?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to get memory context: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get memory graph for visualization.
 */
export async function getMemoryGraph(
  sessionId: string,
  centerEntity?: string,
  maxHops?: number
): Promise<GraphData> {
  const params = new URLSearchParams({ session_id: sessionId });
  if (centerEntity) params.append("center_entity", centerEntity);
  if (maxHops) params.append("max_hops", maxHops.toString());

  const response = await fetch(`${API_BASE}/memory/graph?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to get memory graph: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get user preferences.
 */
export async function getPreferences(
  sessionId: string,
  category?: string
): Promise<{
  preferences: Array<{
    id: string;
    category: string;
    preference: string;
    context?: string;
    confidence?: number;
  }>;
}> {
  const params = new URLSearchParams({ session_id: sessionId });
  if (category) params.append("category", category);

  const response = await fetch(`${API_BASE}/memory/preferences?${params}`);

  if (!response.ok) {
    throw new Error(`Failed to get preferences: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Search products.
 */
export async function searchProducts(
  query: string,
  options?: {
    category?: string;
    brand?: string;
    maxPrice?: number;
    limit?: number;
  }
): Promise<{ products: Product[]; total: number }> {
  const params = new URLSearchParams({ query });
  if (options?.category) params.append("category", options.category);
  if (options?.brand) params.append("brand", options.brand);
  if (options?.maxPrice) params.append("max_price", options.maxPrice.toString());
  if (options?.limit) params.append("limit", options.limit.toString());

  const response = await fetch(`${API_BASE}/products/search?${params}`);

  if (!response.ok) {
    throw new Error(`Product search failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get product details.
 */
export async function getProduct(productId: string): Promise<Product> {
  const response = await fetch(`${API_BASE}/products/${productId}`);

  if (!response.ok) {
    throw new Error(`Failed to get product: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get related products.
 */
export async function getRelatedProducts(
  productId: string,
  limit?: number
): Promise<{ related_products: Product[] }> {
  const params = new URLSearchParams();
  if (limit) params.append("limit", limit.toString());

  const url = `${API_BASE}/products/${productId}/related${params.toString() ? "?" + params : ""}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to get related products: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Check API health.
 */
export async function checkHealth(): Promise<{
  status: string;
  database: string;
}> {
  const response = await fetch(`${API_BASE}/health`);
  return response.json();
}
