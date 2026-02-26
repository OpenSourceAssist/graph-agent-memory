"use client";

import { useState, useCallback, useEffect } from "react";
import type { Thread } from "@/lib/types";
import { api } from "@/lib/api";

export function useThreads() {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);
  // Start with loading true since we fetch on mount
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch threads on mount
  useEffect(() => {
    const controller = new AbortController();

    const fetchThreads = async () => {
      setIsLoading(true);
      try {
        const data = await api.threads.list();
        if (!controller.signal.aborted) {
          setThreads(data);
          // Don't auto-select thread - let user start fresh or pick one
          // This avoids a second API call to fetch messages on initial load
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error ? err.message : "Failed to fetch threads",
          );
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    fetchThreads();

    return () => controller.abort();
  }, []);

  const createThread = useCallback(async (title?: string) => {
    try {
      const thread = await api.threads.create(title);
      setThreads((prev) => [thread, ...prev]);
      setActiveThreadId(thread.id);
      return thread;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create thread");
      throw err;
    }
  }, []);

  const deleteThread = useCallback(
    async (id: string) => {
      try {
        await api.threads.delete(id);
        setThreads((prev) => prev.filter((t) => t.id !== id));
        if (activeThreadId === id) {
          const remaining = threads.filter((t) => t.id !== id);
          setActiveThreadId(remaining.length > 0 ? remaining[0].id : null);
        }
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to delete thread",
        );
        throw err;
      }
    },
    [activeThreadId, threads],
  );

  const selectThread = useCallback((id: string) => {
    setActiveThreadId(id);
  }, []);

  const updateThreadTitle = useCallback(async (id: string, title: string) => {
    try {
      const updated = await api.threads.update(id, title);
      setThreads((prev) =>
        prev.map((t) => (t.id === id ? { ...t, title: updated.title } : t)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update thread");
      throw err;
    }
  }, []);

  return {
    threads,
    activeThreadId,
    activeThread: threads.find((t) => t.id === activeThreadId) || null,
    isLoading,
    error,
    createThread,
    deleteThread,
    selectThread,
    updateThreadTitle,
  };
}
