import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Types
export interface Customer {
  id: string
  name: string
  type: string
  jurisdiction: string
  risk_level: string
  alerts_count: number
  industry?: string
  onboarding_date: string
}

export interface CustomerRisk {
  customer_id: string
  overall_risk: string
  risk_score: number
  geographic_risk: number
  customer_type_risk: number
  transaction_risk: number
  network_risk: number
  risk_factors: string[]
  recommendations: string[]
}

export interface Alert {
  id: string
  type: string
  severity: string
  status: string
  customer_id: string
  title: string
  description: string
  created_at: string
}

export interface Investigation {
  id: string
  customer_id: string
  title: string
  status: string
  priority: string
  created_at: string
  findings_count: number
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export interface ChatResponse {
  response: string
  session_id: string
  agent: string
  metadata: Record<string, unknown>
}

// SSE Event Types
export type AgentEvent =
  | { type: 'agent_start'; agent: string; timestamp: number }
  | { type: 'agent_complete'; agent: string; timestamp: number }
  | { type: 'agent_delegate'; from: string; to: string; timestamp: number }
  | { type: 'tool_call'; agent: string; tool: string; args: Record<string, unknown>; timestamp: number }
  | { type: 'tool_result'; agent: string; tool: string; result: string; timestamp: number }
  | { type: 'memory_access'; agent: string; operation: string; tool: string; query?: string; timestamp: number }
  | { type: 'thinking'; agent: string; thought: string; timestamp: number }
  | { type: 'response'; content: string; session_id: string }
  | { type: 'trace_saved'; trace_id: string; step_count: number; tool_call_count: number }
  | { type: 'done'; session_id: string; agents_consulted: string[]; tool_call_count: number; total_duration_ms: number; trace_id?: string }
  | { type: 'error'; message: string }

// Reasoning Trace Types
export interface TraceToolCall {
  tool_name: string
  arguments: Record<string, unknown>
  result: unknown
  status: string
  duration_ms?: number
}

export interface TraceStep {
  id: string
  step_number: number
  thought?: string
  action?: string
  observation?: string
  tool_calls: TraceToolCall[]
}

export interface ReasoningTrace {
  id: string
  session_id: string
  task: string
  outcome?: string
  success?: boolean
  started_at?: string
  completed_at?: string
  steps: TraceStep[]
}

// SSE Streaming
export async function streamChatMessage(
  params: {
    message: string
    session_id?: string
    customer_id?: string
  },
  onEvent: (event: AgentEvent) => void,
): Promise<void> {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })

  if (!response.ok) {
    throw new Error(`Stream failed: ${response.statusText}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    let currentEventType = ''
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEventType = line.slice(7).trim()
      } else if (line.startsWith('data: ') && currentEventType) {
        try {
          const data = JSON.parse(line.slice(6))
          onEvent({ type: currentEventType, ...data } as AgentEvent)
        } catch {
          // Skip malformed events
        }
        currentEventType = ''
      }
    }
  }
}

// API functions
export const chatApi = {
  sendMessage: async (message: string, sessionId?: string, customerId?: string): Promise<ChatResponse> => {
    const { data } = await api.post('/chat', {
      message,
      session_id: sessionId,
      customer_id: customerId,
    })
    return data
  },

  getHistory: async (sessionId: string): Promise<ChatMessage[]> => {
    const { data } = await api.get(`/chat/history/${sessionId}`)
    return data
  },
}

export const customerApi = {
  list: async (page = 1, pageSize = 20): Promise<{ customers: Customer[]; total: number }> => {
    const { data } = await api.get('/customers', { params: { page, page_size: pageSize } })
    return data
  },

  get: async (customerId: string): Promise<Customer> => {
    const { data } = await api.get(`/customers/${customerId}`)
    return data
  },

  getRisk: async (customerId: string): Promise<CustomerRisk> => {
    const { data } = await api.get(`/customers/${customerId}/risk`)
    return data
  },

  getNetwork: async (customerId: string, depth = 2): Promise<{ nodes: unknown[]; edges: unknown[] }> => {
    const { data } = await api.get(`/customers/${customerId}/network`, { params: { depth } })
    return data
  },
}

export const alertApi = {
  list: async (params?: { status?: string; severity?: string }): Promise<{ alerts: Alert[]; total: number }> => {
    const { data } = await api.get('/alerts', { params })
    return data
  },

  get: async (alertId: string): Promise<Alert> => {
    const { data } = await api.get(`/alerts/${alertId}`)
    return data
  },

  acknowledge: async (alertId: string, analystId: string): Promise<Alert> => {
    const { data } = await api.post(`/alerts/${alertId}/acknowledge`, { analyst_id: analystId })
    return data
  },

  getSummary: async (): Promise<{
    total_count: number
    by_status: Record<string, number>
    by_severity: Record<string, number>
  }> => {
    const { data } = await api.get('/alerts/summary')
    return data
  },
}

export const investigationApi = {
  list: async (params?: { status?: string; customer_id?: string }): Promise<{ investigations: Investigation[]; total: number }> => {
    const { data } = await api.get('/investigations', { params })
    return data
  },

  get: async (investigationId: string): Promise<Investigation> => {
    const { data } = await api.get(`/investigations/${investigationId}`)
    return data
  },

  create: async (investigation: {
    customer_id: string
    title: string
    description: string
    trigger: string
  }): Promise<Investigation> => {
    const { data } = await api.post('/investigations', investigation)
    return data
  },

  start: async (investigationId: string): Promise<{ status: string; preliminary_response: string }> => {
    const { data } = await api.post(`/investigations/${investigationId}/start`, {
      run_kyc: true,
      run_aml: true,
      run_relationship: true,
      run_compliance: true,
    })
    return data
  },

  getAuditTrail: async (investigationId: string): Promise<{ trace: unknown }> => {
    const { data } = await api.get(`/investigations/${investigationId}/audit-trail`)
    return data
  },
}

export const tracesApi = {
  getSessionTraces: async (sessionId: string): Promise<ReasoningTrace[]> => {
    const { data } = await api.get(`/traces/${sessionId}`)
    return data
  },

  getTraceDetail: async (traceId: string): Promise<ReasoningTrace> => {
    const { data } = await api.get(`/traces/detail/${traceId}`)
    return data
  },
}

export const graphApi = {
  getEntity: async (entityName: string, depth = 2): Promise<{ nodes: unknown[]; edges: unknown[] }> => {
    const { data } = await api.get(`/graph/entity/${encodeURIComponent(entityName)}`, { params: { depth } })
    return data
  },

  search: async (query: string, limit = 10): Promise<unknown[]> => {
    const { data } = await api.post('/graph/search', null, { params: { query, limit } })
    return data
  },
}

export default api
