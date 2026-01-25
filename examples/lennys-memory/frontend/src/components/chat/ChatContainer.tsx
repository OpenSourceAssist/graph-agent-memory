"use client";

import {
  Box,
  Flex,
  Stack,
  Text,
  SimpleGrid,
  Spinner,
  useBreakpointValue,
} from "@chakra-ui/react";
import { useRef, useEffect } from "react";
import { LuMessageSquare, LuBot } from "react-icons/lu";
import { MessageList } from "./MessageList";
import { PromptInput } from "./PromptInput";
import type { Message } from "@/lib/types";

// Suggested prompts for the empty state
const SUGGESTED_PROMPTS = [
  {
    title: "Product Management",
    prompt:
      "What did Brian Chesky say about building products that users love?",
  },
  {
    title: "Growth Strategies",
    prompt: "What are the best growth strategies discussed by podcast guests?",
  },
  {
    title: "Career Advice",
    prompt: "What advice did guests give about career transitions and growth?",
  },
  {
    title: "Leadership",
    prompt: "What do successful leaders say about managing teams effectively?",
  },
  {
    title: "Startup Lessons",
    prompt: "What are the most important lessons for early-stage startups?",
  },
  {
    title: "Hiring & Culture",
    prompt:
      "What did guests say about hiring great people and building culture?",
  },
];

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

  // Responsive values
  const isMobile = useBreakpointValue({ base: true, sm: false });
  const promptColumns = useBreakpointValue({ base: 1, sm: 2, lg: 3 });

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
      <Box ref={scrollRef} flex="1" overflowY="auto" p={{ base: 2, md: 4 }}>
        {messages.length === 0 ? (
          <Flex
            h="full"
            alignItems="center"
            justifyContent="center"
            p={{ base: 2, md: 4 }}
          >
            <Stack
              textAlign="center"
              gap={{ base: 4, md: 6 }}
              maxW="3xl"
              w="full"
            >
              <Stack gap="2">
                <Text fontSize={{ base: "lg", md: "xl" }} fontWeight="semibold">
                  Ask about Lenny's Podcast
                </Text>
                <Text color="fg.muted" fontSize={{ base: "xs", md: "sm" }}>
                  Explore insights from 299 podcast episodes. Click a topic
                  below or type your own question.
                </Text>
              </Stack>

              <SimpleGrid columns={promptColumns} gap={{ base: 2, md: 3 }}>
                {SUGGESTED_PROMPTS.slice(0, isMobile ? 4 : 6).map((item) => (
                  <Box
                    key={item.title}
                    as="button"
                    p={{ base: 3, md: 4 }}
                    borderRadius="lg"
                    border="1px solid"
                    borderColor="border.subtle"
                    bg="bg.panel"
                    textAlign="left"
                    cursor="pointer"
                    transition="all 0.2s"
                    _hover={{
                      borderColor: "blue.500",
                      bg: "blue.50",
                      transform: "translateY(-1px)",
                      boxShadow: "sm",
                    }}
                    _active={{
                      transform: "scale(0.98)",
                    }}
                    onClick={() => !isStreaming && onSendMessage(item.prompt)}
                    opacity={isStreaming ? 0.5 : 1}
                    pointerEvents={isStreaming ? "none" : "auto"}
                    minH={{ base: "80px", md: "auto" }}
                  >
                    <Flex align="center" gap={2} mb={{ base: 1, md: 2 }}>
                      <Box color="blue.500">
                        <LuMessageSquare size={16} />
                      </Box>
                      <Text
                        fontSize={{ base: "xs", md: "sm" }}
                        fontWeight="medium"
                        color="fg.default"
                      >
                        {item.title}
                      </Text>
                    </Flex>
                    <Text
                      fontSize="xs"
                      color="fg.muted"
                      lineHeight="tall"
                      lineClamp={{ base: 2, md: 3 }}
                    >
                      {item.prompt}
                    </Text>
                  </Box>
                ))}
              </SimpleGrid>
            </Stack>
          </Flex>
        ) : (
          <Stack gap={{ base: 3, md: 4 }} maxW="4xl" mx="auto">
            <MessageList messages={messages} />

            {/* Streaming indicator */}
            {isStreaming && (
              <Flex gap="3" alignItems="flex-start" px="4" pb="4">
                <Flex
                  w="8"
                  h="8"
                  borderRadius="full"
                  bg="green.subtle"
                  alignItems="center"
                  justifyContent="center"
                  flexShrink={0}
                >
                  <LuBot size={16} />
                </Flex>
                <Flex
                  alignItems="center"
                  gap="3"
                  px="4"
                  py="3"
                  bg="blue.subtle"
                  borderRadius="lg"
                  border="1px solid"
                  borderColor="blue.200"
                >
                  <Spinner size="sm" color="blue.500" borderWidth="2px" />
                  <Text fontSize="sm" color="blue.700" fontWeight="medium">
                    Thinking and searching podcasts...
                  </Text>
                </Flex>
              </Flex>
            )}
          </Stack>
        )}
      </Box>

      {/* Input area */}
      <Box
        p={{ base: 2, md: 4 }}
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
