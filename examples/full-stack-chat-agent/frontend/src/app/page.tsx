"use client";

import { Flex } from "@chakra-ui/react";
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
  } = useThreads();

  const {
    messages,
    isStreaming,
    memoryEnabled,
    setMemoryEnabled,
    sendMessage,
  } = useChat(activeThreadId);

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
      <Flex h="full">
        <ChatContainer
          messages={messages}
          isStreaming={isStreaming}
          onSendMessage={sendMessage}
          threadId={activeThreadId}
        />
        <MemoryContextPanel
          threadId={activeThreadId}
          isVisible={memoryEnabled}
        />
      </Flex>
    </AppLayout>
  );
}
