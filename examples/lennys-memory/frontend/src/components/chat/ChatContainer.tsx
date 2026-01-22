"use client";

import { Box, Flex, Stack, Text } from "@chakra-ui/react";
import { useRef, useEffect } from "react";
import { MessageList } from "./MessageList";
import { PromptInput } from "./PromptInput";
import type { Message } from "@/lib/types";

interface ChatContainerProps {
  messages: Message[];
  isStreaming: boolean;
  onSendMessage: (content: string) => void;
  threadId: string | null;
}

export function ChatContainer({
  messages,
  isStreaming,
  onSendMessage,
  threadId,
}: ChatContainerProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  if (!threadId) {
    return (
      <Flex h="full" alignItems="center" justifyContent="center">
        <Stack textAlign="center" gap="4">
          <Text fontSize="lg" color="fg.muted">
            Select a conversation or create a new one
          </Text>
        </Stack>
      </Flex>
    );
  }

  return (
    <Flex direction="column" h="full" overflow="hidden" flex="1">
      {/* Messages area */}
      <Box ref={scrollRef} flex="1" overflowY="auto" p="4">
        {messages.length === 0 ? (
          <Flex h="full" alignItems="center" justifyContent="center">
            <Stack textAlign="center" gap="4" maxW="md">
              <Text fontSize="lg" fontWeight="medium">
                Ask about Lenny's Podcast
              </Text>
              <Text color="fg.muted">
                Try questions like:
              </Text>
              <Stack gap="2" color="fg.muted" fontSize="sm">
                <Text>"What did Brian Chesky say about product management?"</Text>
                <Text>"Find discussions about growth strategies"</Text>
                <Text>"What advice did guests give about career transitions?"</Text>
                <Text>"What episodes cover mental health?"</Text>
              </Stack>
            </Stack>
          </Flex>
        ) : (
          <MessageList messages={messages} />
        )}
      </Box>

      {/* Input area */}
      <Box
        p="4"
        borderTopWidth="1px"
        borderColor="border.subtle"
        bg="bg.panel"
      >
        <PromptInput
          onSend={onSendMessage}
          isLoading={isStreaming}
          placeholder="Ask about Lenny's Podcast..."
        />
      </Box>
    </Flex>
  );
}
