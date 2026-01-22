"use client";

import { useState, useCallback, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import type { Message, ToolCall, SSEEvent } from "@/lib/types";
import { api, streamChat } from "@/lib/api";

export function useChat(threadId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [memoryEnabled, setMemoryEnabled] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load messages when thread changes
  useEffect(() => {
    if (!threadId) {
      setMessages([]);
      return;
    }

    const loadMessages = async () => {
      try {
        const thread = await api.threads.get(threadId);
        setMessages(thread.messages || []);
      } catch (err) {
        // Thread might be new, no messages yet
        setMessages([]);
      }
    };

    loadMessages();
  }, [threadId]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!threadId || !content.trim() || isStreaming) return;

      setError(null);
      setIsStreaming(true);

      // Add user message
      const userMessage: Message = {
        id: uuidv4(),
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Create assistant message placeholder
      const assistantId = uuidv4();
      const assistantMessage: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
        toolCalls: [],
      };
      setMessages((prev) => [...prev, assistantMessage]);

      try {
        // Track tool calls by ID
        const toolCallsMap = new Map<string, ToolCall>();

        // Stream response
        for await (const event of streamChat(
          threadId,
          content,
          memoryEnabled,
        )) {
          switch (event.type) {
            case "token":
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? { ...msg, content: msg.content + event.content }
                    : msg,
                ),
              );
              break;

            case "tool_call":
              const toolCall: ToolCall = {
                id: event.id,
                name: event.name,
                args: event.args,
                status: "pending",
              };
              toolCallsMap.set(event.id, toolCall);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? {
                        ...msg,
                        toolCalls: Array.from(toolCallsMap.values()),
                      }
                    : msg,
                ),
              );
              break;

            case "tool_result":
              const existing = toolCallsMap.get(event.id);
              if (existing) {
                existing.result = event.result;
                existing.status = "success";
                existing.duration_ms = event.duration_ms;
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantId
                      ? {
                          ...msg,
                          toolCalls: Array.from(toolCallsMap.values()),
                        }
                      : msg,
                  ),
                );
              }
              break;

            case "done":
              // Message complete
              break;

            case "error":
              setError(event.message);
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? {
                        ...msg,
                        content: msg.content || `Error: ${event.message}`,
                      }
                    : msg,
                ),
              );
              break;
          }
        }
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to send message";
        setError(errorMessage);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content: `Error: ${errorMessage}` }
              : msg,
          ),
        );
      } finally {
        setIsStreaming(false);
      }
    },
    [threadId, isStreaming, memoryEnabled],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  return {
    messages,
    isStreaming,
    memoryEnabled,
    setMemoryEnabled,
    error,
    sendMessage,
    clearMessages,
  };
}
