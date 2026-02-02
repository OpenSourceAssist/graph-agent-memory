"use client";

import {
  Box,
  Flex,
  Stack,
  Text,
  SimpleGrid,
  Spinner,
  Wrap,
  Tag,
  useBreakpointValue,
} from "@chakra-ui/react";
import { useRef, useEffect, useState } from "react";
import { LuMessageSquare, LuBot, LuBrain, LuSparkles } from "react-icons/lu";
import { MessageList } from "./MessageList";
import { PromptInput } from "./PromptInput";
import type { Message } from "@/lib/types";

// Suggested prompts for the empty state
const SUGGESTED_PROMPTS = [
  {
    title: "Product-Market Fit",
    prompt: "Who has talked about product-market fit and what did they say?",
  },
  {
    title: "Growth Strategies",
    prompt: "What are the best growth strategies discussed by podcast guests?",
  },
  {
    title: "Find Connections",
    prompt: "Find connections between Reid Hoffman and other guests",
  },
  {
    title: "Top Companies",
    prompt: "What companies are mentioned most often in the podcast?",
  },
  {
    title: "Leadership",
    prompt: "What do successful leaders say about managing teams effectively?",
  },
  {
    title: "Locations",
    prompt: "Show me locations mentioned in recent episodes",
  },
];

// Quick chips that appear above the input
const QUICK_CHIPS = [
  "Popular guests",
  "Product-market fit",
  "Find connections",
  "Show locations",
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

  // Responsive values - 2x2 grid on mobile for better use of space
  const isMobile = useBreakpointValue({ base: true, sm: false });
  const promptColumns = useBreakpointValue({ base: 2, sm: 2, lg: 3 });

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
              <Stack gap="2" align="center">
                <Box
                  color="brand.500"
                  mb={2}
                  p={{ base: 3, md: 4 }}
                  bg="brand.subtle"
                  borderRadius="full"
                >
                  <LuBrain size={isMobile ? 32 : 40} />
                </Box>
                <Text
                  fontSize={{ base: "lg", md: "xl" }}
                  fontWeight="semibold"
                  fontFamily="heading"
                >
                  Ask about Lenny's Podcast
                </Text>
                <Text
                  color="fg.muted"
                  fontSize={{ base: "xs", md: "sm" }}
                  maxW="md"
                  px={2}
                >
                  Explore insights from 299 podcast episodes with AI-powered
                  graph memory. Click a topic or type your own question.
                </Text>
              </Stack>

              <SimpleGrid columns={promptColumns} gap={{ base: 2, md: 3 }}>
                {SUGGESTED_PROMPTS.slice(0, isMobile ? 4 : 6).map((item) => (
                  <Box
                    key={item.title}
                    as="button"
                    p={{ base: 2.5, md: 4 }}
                    borderRadius="lg"
                    border="1px solid"
                    borderColor="border.subtle"
                    bg="bg.panel"
                    textAlign="left"
                    cursor="pointer"
                    transition="all 0.2s"
                    _hover={{
                      borderColor: "brand.500",
                      bg: "brand.subtle",
                      transform: "translateY(-1px)",
                      boxShadow: "sm",
                    }}
                    _active={{
                      transform: "scale(0.98)",
                    }}
                    _focusVisible={{
                      outline: "2px solid",
                      outlineColor: "brand.500",
                      outlineOffset: "2px",
                    }}
                    onClick={() => !isStreaming && onSendMessage(item.prompt)}
                    opacity={isStreaming ? 0.5 : 1}
                    pointerEvents={isStreaming ? "none" : "auto"}
                    minH={{ base: "auto", md: "auto" }}
                  >
                    <Flex align="center" gap={1.5} mb={{ base: 0.5, md: 2 }}>
                      <Box color="brand.500" flexShrink={0}>
                        <LuSparkles size={isMobile ? 14 : 16} />
                      </Box>
                      <Text
                        fontSize={{ base: "xs", md: "sm" }}
                        fontWeight="medium"
                        color="fg.default"
                        lineClamp={1}
                      >
                        {item.title}
                      </Text>
                    </Flex>
                    <Text
                      fontSize="xs"
                      color="fg.muted"
                      lineHeight="tall"
                      lineClamp={{ base: 2, md: 3 }}
                      hideBelow="sm"
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
                  bg="brand.subtle"
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
                  bg="brand.subtle"
                  borderRadius="lg"
                  border="1px solid"
                  borderColor="brand.muted"
                >
                  <Spinner size="sm" color="brand.500" borderWidth="2px" />
                  <Text fontSize="sm" color="brand.fg" fontWeight="medium">
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
