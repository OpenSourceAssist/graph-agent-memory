"use client";

import { Flex, useBreakpointValue, IconButton } from "@chakra-ui/react";
import { useState, useCallback, useEffect, useRef } from "react";
import { LuBrain } from "react-icons/lu";
import { AppLayout } from "@/components/layout/AppLayout";
import { ChatContainer } from "@/components/chat/ChatContainer";
import { MemoryContextPanel } from "@/components/memory/MemoryContext";
import { useThreads } from "@/hooks/useThreads";
import { useChat } from "@/hooks/useChat";

export default function Home() {
  const {
    threads,
    activeThreadId,
    createThread,
    deleteThread,
    selectThread,
    isLoading: isLoadingThreads,
  } = useThreads();

  const {
    messages,
    isStreaming,
    memoryEnabled,
    setMemoryEnabled,
    sendMessage: sendMessageToThread,
  } = useChat(activeThreadId);

  // Track pending message to send after thread creation
  const pendingMessageRef = useRef<string | null>(null);

  // Send pending message when thread becomes available
  useEffect(() => {
    if (pendingMessageRef.current && activeThreadId && !isStreaming) {
      const msg = pendingMessageRef.current;
      pendingMessageRef.current = null;
      sendMessageToThread(msg);
    }
  }, [activeThreadId, isStreaming, sendMessageToThread]);

  // Wrapper that creates a thread if needed before sending
  const handleSendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      // If no active thread, create one first then send
      if (!activeThreadId) {
        pendingMessageRef.current = content;
        try {
          await createThread();
          // Message will be sent by the effect when activeThreadId updates
        } catch (err) {
          console.error("Failed to create thread:", err);
          pendingMessageRef.current = null;
        }
      } else {
        await sendMessageToThread(content);
      }
    },
    [activeThreadId, createThread, sendMessageToThread],
  );

  // Mobile memory panel state (separate from memoryEnabled toggle)
  const [mobileMemoryOpen, setMobileMemoryOpen] = useState(false);
  // Default to false during SSR to avoid hydration mismatch
  const isMobile = useBreakpointValue({ base: true, lg: false }) ?? false;

  return (
    <>
      <AppLayout
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={selectThread}
        onCreateThread={createThread}
        onDeleteThread={deleteThread}
        memoryEnabled={memoryEnabled}
        onToggleMemory={setMemoryEnabled}
        isLoadingThreads={isLoadingThreads}
      >
        <Flex h="full" position="relative">
          <ChatContainer
            messages={messages}
            isStreaming={isStreaming}
            onSendMessage={handleSendMessage}
            threadId={activeThreadId}
          />

          {/* Desktop: Always show panel when memoryEnabled */}
          {/* Mobile: Show bottom sheet only when mobileMemoryOpen */}
          <MemoryContextPanel
            threadId={activeThreadId}
            isVisible={isMobile ? mobileMemoryOpen : memoryEnabled}
            onClose={() => setMobileMemoryOpen(false)}
          />

          {/* Mobile FAB to open memory context */}
          {isMobile && memoryEnabled && !mobileMemoryOpen && (
            <IconButton
              aria-label="View memory context"
              position="absolute"
              bottom="100px"
              right="4"
              borderRadius="full"
              size="lg"
              colorPalette="brand"
              boxShadow="lg"
              onClick={() => setMobileMemoryOpen(true)}
            >
              <LuBrain />
            </IconButton>
          )}
        </Flex>
      </AppLayout>
    </>
  );
}
