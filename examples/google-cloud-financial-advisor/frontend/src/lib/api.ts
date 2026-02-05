/**
 * API client for Google Cloud Financial Advisor backend.
 */

const API_BASE = '/api'

export interface Customer {
  id: string
  name: string
  type: 'individual' | 'corporate'
  email?: string
  phone?: string
  nationality?: string
  address?: string
  occupation?: string
  employer?: string
  jurisdiction?: string
  business_type?: string
  kyc_status: string
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  risk_score: number
  risk_factors: string[]
}

export interface CustomerRisk {
  customer_id: string
  customer_name: string
  risk_score: number
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  contributing_factors: Array<{
    factor: string
    weight: number
    description: string
  }>
  kyc_status: string
  recommendation: string
}

export interface Alert {
  id: string
  customer_id: string
  customer_name?: string
  type: string
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  status: string
  title: string
  description: string
  transaction_id?: string
  evidence: string[]
  requires_sar: boolean
  created_at: string
}

export interface AlertSummary {
  total: number
  by_severity: Record<string, number>
  by_status: Record<string, number>
  by_type: Record<string, number>
  critical_unresolved: number
  high_unresolved: number
}

export interface Investigation {
  id: string
  customer_id: string
  type: string
  reason: string
  status: string
  priority: string
  overall_risk_level?: string
  risk_score?: number
  summary?: string
  recommendations: string[]
  agents_consulted: string[]
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export interface ChatResponse {
  session_id: string
  message: ChatMessage
  agents_consulted: string[]
  tool_calls: Array<{
    tool_name: string
    agent?: string
  }>
  response_time_ms?: number
}

export interface NetworkData {
  nodes: Array<{
    id: string
    label: string
    type: string
    isRoot?: boolean
  }>
  edges: Array<{
    from: string
    to: string
    relationship: string
  }>
  total_connections: number
}

// Customer API
export async function getCustomers(): Promise<Customer[]> {
  const res = await fetch(`${API_BASE}/customers`)
  if (!res.ok) throw new Error('Failed to fetch customers')
  return res.json()
}

export async function getCustomer(id: string): Promise<Customer> {
  const res = await fetch(`${API_BASE}/customers/${id}`)
  if (!res.ok) throw new Error('Failed to fetch customer')
  return res.json()
}

export async function getCustomerRisk(id: string): Promise<CustomerRisk> {
  const res = await fetch(`${API_BASE}/customers/${id}/risk`)
  if (!res.ok) throw new Error('Failed to fetch customer risk')
  return res.json()
}

export async function getCustomerNetwork(id: string, depth = 2): Promise<NetworkData> {
  const res = await fetch(`${API_BASE}/customers/${id}/network?depth=${depth}`)
  if (!res.ok) throw new Error('Failed to fetch customer network')
  return res.json()
}

// Alert API
export async function getAlerts(params?: {
  status?: string
  severity?: string
  customer_id?: string
}): Promise<Alert[]> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.severity) searchParams.set('severity', params.severity)
  if (params?.customer_id) searchParams.set('customer_id', params.customer_id)

  const url = `${API_BASE}/alerts${searchParams.toString() ? '?' + searchParams : ''}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to fetch alerts')
  return res.json()
}

export async function getAlertSummary(): Promise<AlertSummary> {
  const res = await fetch(`${API_BASE}/alerts/summary`)
  if (!res.ok) throw new Error('Failed to fetch alert summary')
  return res.json()
}

export async function updateAlert(id: string, update: {
  status?: string
  severity?: string
  notes?: string
}): Promise<Alert> {
  const res = await fetch(`${API_BASE}/alerts/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  })
  if (!res.ok) throw new Error('Failed to update alert')
  return res.json()
}

// Investigation API
export async function getInvestigations(params?: {
  status?: string
  customer_id?: string
}): Promise<Investigation[]> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.customer_id) searchParams.set('customer_id', params.customer_id)

  const url = `${API_BASE}/investigations${searchParams.toString() ? '?' + searchParams : ''}`
  const res = await fetch(url)
  if (!res.ok) throw new Error('Failed to fetch investigations')
  return res.json()
}

export async function createInvestigation(data: {
  customer_id: string
  type?: string
  reason: string
  priority?: string
}): Promise<Investigation> {
  const res = await fetch(`${API_BASE}/investigations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create investigation')
  return res.json()
}

export async function startInvestigation(id: string): Promise<{
  investigation_id: string
  status: string
  overall_risk_level: string
  summary: string
  agents_consulted: string[]
  duration_seconds: number
}> {
  const res = await fetch(`${API_BASE}/investigations/${id}/start`, {
    method: 'POST',
  })
  if (!res.ok) throw new Error('Failed to start investigation')
  return res.json()
}

export async function getAuditTrail(investigationId: string): Promise<Array<{
  timestamp: string
  action: string
  agent?: string
  details?: string
  tool_used?: string
}>> {
  const res = await fetch(`${API_BASE}/investigations/${investigationId}/audit-trail`)
  if (!res.ok) throw new Error('Failed to fetch audit trail')
  return res.json()
}

// Chat API
export async function sendChatMessage(data: {
  message: string
  session_id?: string
  customer_id?: string
  investigation_id?: string
}): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to send message')
  return res.json()
}

export async function getChatHistory(sessionId: string): Promise<{
  session_id: string
  messages: ChatMessage[]
}> {
  const res = await fetch(`${API_BASE}/chat/history/${sessionId}`)
  if (!res.ok) throw new Error('Failed to fetch chat history')
  return res.json()
}

export async function searchMemory(query: string, limit = 10): Promise<{
  query: string
  results: Array<{
    content: string
    type: string
    score?: number
  }>
  total: number
}> {
  const res = await fetch(`${API_BASE}/chat/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, limit }),
  })
  if (!res.ok) throw new Error('Failed to search memory')
  return res.json()
}

// Graph API
export async function getGraphStats(): Promise<{
  total_nodes: number
  total_relationships: number
  nodes_by_label: Record<string, number>
  relationships_by_type: Record<string, number>
}> {
  const res = await fetch(`${API_BASE}/graph/stats`)
  if (!res.ok) throw new Error('Failed to fetch graph stats')
  return res.json()
}
