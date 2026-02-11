import { useState, useCallback, useRef } from "react";
import { streamChatMessage, AgentEvent } from "../lib/api";

export interface AgentState {
  status: "pending" | "active" | "complete";
  toolCalls: Array<{
    tool: string;
    args: Record<string, unknown>;
    result?: unknown;
    timestamp: number;
  }>;
  memoryAccesses: Array<{
    operation: "search" | "store";
    tool: string;
    query?: string;
    timestamp: number;
  }>;
  thoughts: string[];
  startedAt?: number;
  completedAt?: number;
}

export interface StreamResult {
  sessionId: string | null;
  agentsConsulted: string[];
  toolCallCount: number;
  totalDurationMs: number;
  traceId: string | null;
}

export function useAgentStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [agentStates, setAgentStates] = useState<Map<string, AgentState>>(
    new Map(),
  );
  const [finalResponse, setFinalResponse] = useState<string | null>(null);
  const [streamResult, setStreamResult] = useState<StreamResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Track delegation chain
  const [delegationChain, setDelegationChain] = useState<
    Array<{ from: string; to: string }>
  >([]);

  // Use ref to avoid stale closures in event handler
  const agentStatesRef = useRef<Map<string, AgentState>>(new Map());

  const getOrCreateAgent = useCallback((agentName: string): AgentState => {
    const existing = agentStatesRef.current.get(agentName);
    if (existing) return existing;
    const newState: AgentState = {
      status: "pending",
      toolCalls: [],
      memoryAccesses: [],
      thoughts: [],
    };
    return newState;
  }, []);

  const updateAgent = useCallback(
    (agentName: string, updater: (state: AgentState) => AgentState) => {
      const current = getOrCreateAgent(agentName);
      const updated = updater(current);
      const newMap = new Map(agentStatesRef.current);
      newMap.set(agentName, updated);
      agentStatesRef.current = newMap;
      setAgentStates(newMap);
    },
    [getOrCreateAgent],
  );

  const startStream = useCallback(
    async (
      message: string,
      sessionId?: string,
      customerId?: string,
      investigationId?: string,
    ) => {
      setIsStreaming(true);
      setActiveAgent(null);
      setFinalResponse(null);
      setStreamResult(null);
      setError(null);
      setDelegationChain([]);
      agentStatesRef.current = new Map();
      setAgentStates(new Map());

      try {
        await streamChatMessage(
          {
            message,
            session_id: sessionId,
            customer_id: customerId,
            investigation_id: investigationId,
          },
          (event: AgentEvent) => {
            switch (event.type) {
              case "agent_start":
                setActiveAgent(event.agent);
                updateAgent(event.agent, (s) => ({
                  ...s,
                  status: "active",
                  startedAt: event.timestamp,
                }));
                break;

              case "agent_complete":
                updateAgent(event.agent, (s) => ({
                  ...s,
                  status: "complete",
                  completedAt: event.timestamp,
                }));
                break;

              case "agent_delegate":
                setDelegationChain((prev) => [
                  ...prev,
                  { from: event.from, to: event.to },
                ]);
                break;

              case "thinking":
                updateAgent(event.agent, (s) => ({
                  ...s,
                  thoughts: [...s.thoughts, event.thought],
                }));
                break;

              case "tool_call":
                updateAgent(event.agent, (s) => ({
                  ...s,
                  toolCalls: [
                    ...s.toolCalls,
                    {
                      tool: event.tool,
                      args: event.args,
                      timestamp: event.timestamp,
                    },
                  ],
                }));
                break;

              case "tool_result":
                updateAgent(event.agent, (s) => ({
                  ...s,
                  toolCalls: s.toolCalls.map((tc, i) =>
                    i === s.toolCalls.length - 1 && tc.tool === event.tool
                      ? { ...tc, result: event.result }
                      : tc,
                  ),
                }));
                break;

              case "memory_access":
                updateAgent(event.agent, (s) => ({
                  ...s,
                  memoryAccesses: [
                    ...s.memoryAccesses,
                    {
                      operation: event.operation,
                      tool: event.tool,
                      query: event.query,
                      timestamp: event.timestamp,
                    },
                  ],
                }));
                break;

              case "response":
                setFinalResponse(event.content);
                break;

              case "done":
                setStreamResult({
                  sessionId: event.session_id,
                  agentsConsulted: event.agents_consulted,
                  toolCallCount: event.tool_call_count,
                  totalDurationMs: event.total_duration_ms,
                  traceId: event.trace_id ?? null,
                });
                setActiveAgent(null);
                break;

              case "error":
                setError(event.message);
                break;
            }
          },
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "Stream failed");
      } finally {
        setIsStreaming(false);
      }
    },
    [updateAgent],
  );

  const reset = useCallback(() => {
    setIsStreaming(false);
    setActiveAgent(null);
    setAgentStates(new Map());
    setFinalResponse(null);
    setStreamResult(null);
    setError(null);
    setDelegationChain([]);
    agentStatesRef.current = new Map();
  }, []);

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
  };
}
