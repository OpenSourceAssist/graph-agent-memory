"use client";

import { useState, useCallback, useEffect } from "react";
import type { QuickStartSuggestion } from "@/lib/types";
import { api } from "@/lib/api";

/**
 * Hook to fetch quick-start suggestions from previous conversations.
 * Returns the first user message from each thread as a suggestion.
 */
export function useQuickStart(limit: number = 10) {
  const [suggestions, setSuggestions] = useState<QuickStartSuggestion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSuggestions = useCallback(async () => {
    const controller = new AbortController();

    setIsLoading(true);
    setError(null);

    try {
      // Fetch thread list
      const threads = await api.threads.list();

      // Get first user message from each thread (up to limit)
      const suggestionsWithMessages: QuickStartSuggestion[] = [];

      for (const thread of threads.slice(0, limit)) {
        try {
          const threadData = await api.threads.get(thread.id);
          const firstUserMessage = threadData.messages?.find(
            (m) => m.role === "user"
          );
          if (firstUserMessage) {
            suggestionsWithMessages.push({
              id: thread.id,
              firstMessage: firstUserMessage.content,
              timestamp: firstUserMessage.timestamp,
            });
          }
        } catch {
          // Skip threads that fail to load
        }
      }

      if (!controller.signal.aborted) {
        setSuggestions(suggestionsWithMessages);
      }
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(
          err instanceof Error ? err.message : "Failed to fetch suggestions"
        );
      }
    } finally {
      if (!controller.signal.aborted) {
        setIsLoading(false);
      }
    }

    return () => controller.abort();
  }, [limit]);

  useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  return {
    suggestions,
    isLoading,
    error,
    refresh: fetchSuggestions,
  };
}
