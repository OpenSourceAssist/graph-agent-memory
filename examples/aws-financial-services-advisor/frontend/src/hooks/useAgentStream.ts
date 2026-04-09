import { useState, useCallback, useRef } from 'react'
import { streamChatMessage, AgentEvent } from '../lib/api'

export interface AgentToolCall {
  tool: string
  args: Record<string, unknown>
  result?: string
  timestamp: number
}

export interface MemoryAccess {
  operation: string
  tool: string
  query?: string
  timestamp: number
}

export interface AgentState {
  status: 'pending' | 'active' | 'complete'
  toolCalls: AgentToolCall[]
  memoryAccesses: MemoryAccess[]
  thoughts: string[]
  startedAt?: number
  completedAt?: number
}

export interface StreamResult {
  sessionId: string | null
  agentsConsulted: string[]
  toolCallCount: number
  totalDurationMs: number
  traceId: string | null
}

export function useAgentStream() {
  const [isStreaming, setIsStreaming] = useState(false)
  const [activeAgent, setActiveAgent] = useState<string | null>(null)
  const [agentStates, setAgentStates] = useState<Map<string, AgentState>>(new Map())
  const [finalResponse, setFinalResponse] = useState<string | null>(null)
  const [streamResult, setStreamResult] = useState<StreamResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [delegationChain, setDelegationChain] = useState<Array<{ from: string; to: string }>>([])

  const agentStatesRef = useRef(agentStates)

  const getOrCreateAgent = useCallback((name: string): AgentState => {
    const current = agentStatesRef.current.get(name)
    if (current) return current
    return {
      status: 'pending',
      toolCalls: [],
      memoryAccesses: [],
      thoughts: [],
    }
  }, [])

  const updateAgent = useCallback((name: string, updater: (state: AgentState) => AgentState) => {
    setAgentStates(prev => {
      const next = new Map(prev)
      const current = next.get(name) || {
        status: 'pending' as const,
        toolCalls: [],
        memoryAccesses: [],
        thoughts: [],
      }
      next.set(name, updater(current))
      agentStatesRef.current = next
      return next
    })
  }, [])

  const startStream = useCallback(async (
    message: string,
    sessionId?: string,
    customerId?: string,
  ) => {
    setIsStreaming(true)
    setFinalResponse(null)
    setStreamResult(null)
    setError(null)
    setAgentStates(new Map())
    setDelegationChain([])
    agentStatesRef.current = new Map()

    try {
      await streamChatMessage(
        { message, session_id: sessionId, customer_id: customerId },
        (event: AgentEvent) => {
          switch (event.type) {
            case 'agent_start':
              setActiveAgent(event.agent)
              updateAgent(event.agent, s => ({
                ...s,
                status: 'active',
                startedAt: event.timestamp,
              }))
              break

            case 'agent_complete':
              updateAgent(event.agent, s => ({
                ...s,
                status: 'complete',
                completedAt: event.timestamp,
              }))
              if (event.agent === activeAgent) {
                setActiveAgent(null)
              }
              break

            case 'agent_delegate':
              setDelegationChain(prev => [...prev, { from: event.from, to: event.to }])
              break

            case 'tool_call':
              updateAgent(event.agent, s => ({
                ...s,
                toolCalls: [...s.toolCalls, {
                  tool: event.tool,
                  args: event.args,
                  timestamp: event.timestamp,
                }],
              }))
              break

            case 'tool_result':
              updateAgent(event.agent, s => ({
                ...s,
                toolCalls: s.toolCalls.map((tc, i) =>
                  i === s.toolCalls.length - 1 && tc.tool === event.tool
                    ? { ...tc, result: event.result }
                    : tc
                ),
              }))
              break

            case 'memory_access':
              updateAgent(event.agent, s => ({
                ...s,
                memoryAccesses: [...s.memoryAccesses, {
                  operation: event.operation,
                  tool: event.tool,
                  query: event.query,
                  timestamp: event.timestamp,
                }],
              }))
              break

            case 'thinking':
              updateAgent(event.agent, s => ({
                ...s,
                thoughts: [...s.thoughts, event.thought],
              }))
              break

            case 'response':
              setFinalResponse(event.content)
              break

            case 'done':
              setStreamResult({
                sessionId: event.session_id,
                agentsConsulted: event.agents_consulted,
                toolCallCount: event.tool_call_count,
                totalDurationMs: event.total_duration_ms,
                traceId: event.trace_id || null,
              })
              break

            case 'error':
              setError(event.message)
              break
          }
        },
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Stream failed')
    } finally {
      setIsStreaming(false)
      setActiveAgent(null)
    }
  }, [updateAgent, activeAgent])

  const reset = useCallback(() => {
    setIsStreaming(false)
    setActiveAgent(null)
    setAgentStates(new Map())
    setFinalResponse(null)
    setStreamResult(null)
    setError(null)
    setDelegationChain([])
    agentStatesRef.current = new Map()
  }, [])

  return {
    isStreaming,
    activeAgent,
    agentStates,
    finalResponse,
    streamResult,
    error,
    delegationChain,
    startStream,
    reset,
  }
}
