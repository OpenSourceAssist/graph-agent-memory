"use client";

import { useState, useCallback, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import type { Message, ToolCall, SSEEvent } from "@/lib/types";
import { api, streamChat } from "@/lib/api";

/**
 * Simplified chat hook that manages thread lifecycle internally.
 * - Creates threads automatically when needed
 * - Uses AbortController to cancel in-flight requests
 * - Memory is always enabled (no toggle)
 */
export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // AbortController ref for cancelling in-flight requests
  const abortControllerRef = useRef<AbortController | null>(null);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Start a new conversation, optionally with an initial message
  const startNewConversation = useCallback(async (initialMessage?: string) => {
    // Cancel any in-flight requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setError(null);
    setMessages([]);
    setThreadId(null);
    setIsStreaming(false);

    if (initialMessage) {
      // Create thread and send message
      try {
        const thread = await api.threads.create();
        setThreadId(thread.id);
        // Send the initial message
        await sendMessageToThread(thread.id, initialMessage);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to create conversation",
        );
      }
    }
  }, []);

  // Internal function to send message to a specific thread
  const sendMessageToThread = useCallback(
    async (targetThreadId: string, content: string) => {
      if (!content.trim() || isStreaming) return;

      // Cancel any previous streaming
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

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

        // Stream response (memory always enabled)
        for await (const event of streamChat(targetThreadId, content, true)) {
          // Check if aborted
          if (abortControllerRef.current?.signal.aborted) {
            break;
          }

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
        // Handle AbortError gracefully (user cancelled)
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
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
    [isStreaming],
  );

  // Public sendMessage - creates thread if needed
  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      if (!threadId) {
        // Create thread first, then send message
        try {
          const thread = await api.threads.create();
          setThreadId(thread.id);
          await sendMessageToThread(thread.id, content);
        } catch (err) {
          setError(
            err instanceof Error
              ? err.message
              : "Failed to create conversation",
          );
        }
      } else {
        await sendMessageToThread(threadId, content);
      }
    },
    [threadId, sendMessageToThread],
  );

  return {
    messages,
    threadId,
    isStreaming,
    error,
    sendMessage,
    startNewConversation,
    clearError,
  };
}
