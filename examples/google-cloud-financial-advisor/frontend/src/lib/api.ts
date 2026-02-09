/**
 * API client for Google Cloud Financial Advisor backend.
 */

const API_BASE = "/api";

export interface Customer {
  id: string;
  name: string;
  type: "individual" | "corporate";
  email?: string;
  phone?: string;
  nationality?: string;
  address?: string;
  occupation?: string;
  employer?: string;
  jurisdiction?: string;
  business_type?: string;
  kyc_status: string;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  risk_score: number;
  risk_factors: string[];
}

export interface CustomerRisk {
  customer_id: string;
  customer_name: string;
  risk_score: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  contributing_factors: Array<{
    factor: string;
    weight: number;
    description: string;
  }>;
  kyc_status: string;
  recommendation: string;
}

export interface Alert {
  id: string;
  customer_id: string;
  customer_name?: string;
  type: string;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  status: string;
  title: string;
  description: string;
  transaction_id?: string;
  evidence: string[];
  requires_sar: boolean;
  created_at: string;
}

export interface AlertSummary {
  total: number;
  by_severity: Record<string, number>;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  critical_unresolved: number;
  high_unresolved: number;
}

export interface Investigation {
  id: string;
  customer_id: string;
  type: string;
  reason: string;
  status: string;
  priority: string;
  overall_risk_level?: string;
  risk_score?: number;
  summary?: string;
  recommendations: string[];
  agents_consulted: string[];
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
}

export interface ChatResponse {
  session_id: string;
  message: ChatMessage;
  agents_consulted: string[];
  tool_calls: Array<{
    tool_name: string;
    agent?: string;
  }>;
  response_time_ms?: number;
}

export interface NetworkData {
  nodes: Array<{
    id: string;
    label: string;
    type: string;
    isRoot?: boolean;
  }>;
  edges: Array<{
    from: string;
    to: string;
    relationship: string;
  }>;
  total_connections: number;
}

// Customer API
export async function getCustomers(): Promise<Customer[]> {
  const res = await fetch(`${API_BASE}/customers`);
  if (!res.ok) throw new Error("Failed to fetch customers");
  return res.json();
}

export async function getCustomer(id: string): Promise<Customer> {
  const res = await fetch(`${API_BASE}/customers/${id}`);
  if (!res.ok) throw new Error("Failed to fetch customer");
  return res.json();
}

export async function getCustomerRisk(id: string): Promise<CustomerRisk> {
  const res = await fetch(`${API_BASE}/customers/${id}/risk`);
  if (!res.ok) throw new Error("Failed to fetch customer risk");
  return res.json();
}

export async function getCustomerNetwork(
  id: string,
  depth = 2,
): Promise<NetworkData> {
  const res = await fetch(`${API_BASE}/customers/${id}/network?depth=${depth}`);
  if (!res.ok) throw new Error("Failed to fetch customer network");
  return res.json();
}

// Alert API
export async function getAlerts(params?: {
  status?: string;
  severity?: string;
  customer_id?: string;
}): Promise<Alert[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.severity) searchParams.set("severity", params.severity);
  if (params?.customer_id) searchParams.set("customer_id", params.customer_id);

  const url = `${API_BASE}/alerts${searchParams.toString() ? "?" + searchParams : ""}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch alerts");
  return res.json();
}

export async function getAlertSummary(): Promise<AlertSummary> {
  const res = await fetch(`${API_BASE}/alerts/summary`);
  if (!res.ok) throw new Error("Failed to fetch alert summary");
  return res.json();
}

export async function updateAlert(
  id: string,
  update: {
    status?: string;
    severity?: string;
    notes?: string;
  },
): Promise<Alert> {
  const res = await fetch(`${API_BASE}/alerts/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });
  if (!res.ok) throw new Error("Failed to update alert");
  return res.json();
}

// Investigation API
export async function getInvestigations(params?: {
  status?: string;
  customer_id?: string;
}): Promise<Investigation[]> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.customer_id) searchParams.set("customer_id", params.customer_id);

  const url = `${API_BASE}/investigations${searchParams.toString() ? "?" + searchParams : ""}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch investigations");
  return res.json();
}

export async function createInvestigation(data: {
  customer_id: string;
  type?: string;
  reason: string;
  priority?: string;
}): Promise<Investigation> {
  const res = await fetch(`${API_BASE}/investigations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create investigation");
  return res.json();
}

export async function startInvestigation(id: string): Promise<{
  investigation_id: string;
  status: string;
  overall_risk_level: string;
  summary: string;
  agents_consulted: string[];
  duration_seconds: number;
}> {
  const res = await fetch(`${API_BASE}/investigations/${id}/start`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to start investigation");
  return res.json();
}

export async function getAuditTrail(investigationId: string): Promise<
  Array<{
    timestamp: string;
    action: string;
    agent?: string;
    details?: string;
    tool_used?: string;
  }>
> {
  const res = await fetch(
    `${API_BASE}/investigations/${investigationId}/audit-trail`,
  );
  if (!res.ok) throw new Error("Failed to fetch audit trail");
  return res.json();
}

// Chat API
export async function sendChatMessage(data: {
  message: string;
  session_id?: string;
  customer_id?: string;
  investigation_id?: string;
}): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to send message");
  return res.json();
}

export async function getChatHistory(sessionId: string): Promise<{
  session_id: string;
  messages: ChatMessage[];
}> {
  const res = await fetch(`${API_BASE}/chat/history/${sessionId}`);
  if (!res.ok) throw new Error("Failed to fetch chat history");
  return res.json();
}

export async function searchMemory(
  query: string,
  limit = 10,
): Promise<{
  query: string;
  results: Array<{
    content: string;
    type: string;
    score?: number;
  }>;
  total: number;
}> {
  const res = await fetch(`${API_BASE}/chat/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit }),
  });
  if (!res.ok) throw new Error("Failed to search memory");
  return res.json();
}

// SSE Streaming Chat API

export type AgentEvent =
  | { type: "agent_start"; agent: string; timestamp: number }
  | { type: "agent_delegate"; from: string; to: string; timestamp: number }
  | { type: "agent_complete"; agent: string; timestamp: number }
  | { type: "thinking"; agent: string; thought: string; timestamp: number }
  | {
      type: "tool_call";
      agent: string;
      tool: string;
      args: Record<string, unknown>;
      timestamp: number;
    }
  | {
      type: "tool_result";
      agent: string;
      tool: string;
      result: unknown;
      timestamp: number;
    }
  | {
      type: "memory_access";
      agent: string;
      operation: "search" | "store";
      tool: string;
      query?: string;
      timestamp: number;
    }
  | { type: "response"; content: string; session_id: string }
  | {
      type: "trace_saved";
      trace_id: string;
      step_count: number;
      tool_call_count: number;
    }
  | {
      type: "done";
      session_id: string;
      agents_consulted: string[];
      tool_call_count: number;
      total_duration_ms: number;
      trace_id?: string;
    }
  | { type: "error"; message: string };

export async function streamChatMessage(
  data: {
    message: string;
    session_id?: string;
    customer_id?: string;
    investigation_id?: string;
  },
  onEvent: (event: AgentEvent) => void,
): Promise<void> {
  const res = await fetch(`${API_BASE}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) throw new Error("Failed to start stream");

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events from buffer
    const lines = buffer.split("\n");
    buffer = lines.pop() || ""; // Keep incomplete last line

    let eventType = "";
    let eventData = "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        eventData = line.slice(6);
      } else if (line === "" && eventType && eventData) {
        // Empty line signals end of SSE event
        try {
          const parsed = JSON.parse(eventData);
          onEvent({ type: eventType, ...parsed } as AgentEvent);
        } catch {
          // Skip malformed events
        }
        eventType = "";
        eventData = "";
      }
    }
  }
}

// Reasoning Traces API

export interface TraceToolCall {
  id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  result: unknown;
  status: string | null;
  duration_ms: number | null;
  error: string | null;
}

export interface TraceStep {
  id: string;
  step_number: number;
  thought: string | null;
  action: string | null;
  observation: string | null;
  tool_calls: TraceToolCall[];
}

export interface ReasoningTrace {
  id: string;
  session_id: string;
  task: string;
  outcome: string | null;
  success: boolean | null;
  started_at: string | null;
  completed_at: string | null;
  steps: TraceStep[];
}

export async function getSessionTraces(
  sessionId: string,
): Promise<ReasoningTrace[]> {
  const res = await fetch(`${API_BASE}/traces/${sessionId}`);
  if (!res.ok) throw new Error("Failed to fetch traces");
  return res.json();
}

export async function getTraceDetail(traceId: string): Promise<ReasoningTrace> {
  const res = await fetch(`${API_BASE}/traces/detail/${traceId}`);
  if (!res.ok) throw new Error("Failed to fetch trace");
  return res.json();
}

// Graph API
export async function getGraphStats(): Promise<{
  total_nodes: number;
  total_relationships: number;
  nodes_by_label: Record<string, number>;
  relationships_by_type: Record<string, number>;
}> {
  const res = await fetch(`${API_BASE}/graph/stats`);
  if (!res.ok) throw new Error("Failed to fetch graph stats");
  return res.json();
}
