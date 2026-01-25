"use client";

import { Flex, useBreakpointValue, IconButton } from "@chakra-ui/react";
import { useState } from "react";
import { LuBrain } from "react-icons/lu";
import { AppLayout } from "@/components/layout/AppLayout";
import { ChatContainer } from "@/components/chat/ChatContainer";
import { MemoryContextPanel } from "@/components/memory/MemoryContext";
import { useThreads } from "@/hooks/useThreads";
import { useChat } from "@/hooks/useChat";

export default function Home() {
  const { threads, activeThreadId, createThread, deleteThread, selectThread } =
    useThreads();

  const {
    messages,
    isStreaming,
    memoryEnabled,
    setMemoryEnabled,
    sendMessage,
  } = useChat(activeThreadId);

  // Mobile memory panel state (separate from memoryEnabled toggle)
  const [mobileMemoryOpen, setMobileMemoryOpen] = useState(false);
  const isMobile = useBreakpointValue({ base: true, lg: false });

  return (
    <AppLayout
      threads={threads}
      activeThreadId={activeThreadId}
      onSelectThread={selectThread}
      onCreateThread={createThread}
      onDeleteThread={deleteThread}
      memoryEnabled={memoryEnabled}
      onToggleMemory={setMemoryEnabled}
    >
      <Flex h="full" position="relative">
        <ChatContainer
          messages={messages}
          isStreaming={isStreaming}
          onSendMessage={sendMessage}
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
            colorPalette="blue"
            boxShadow="lg"
            onClick={() => setMobileMemoryOpen(true)}
          >
            <LuBrain />
          </IconButton>
        )}
      </Flex>
    </AppLayout>
  );
}
