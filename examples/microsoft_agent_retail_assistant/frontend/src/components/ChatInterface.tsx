"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Box,
  Flex,
  VStack,
  HStack,
  Input,
  Button,
  Text,
  Card,
  Badge,
  Spinner,
} from "@chakra-ui/react";
import ReactMarkdown from "react-markdown";
import { streamChat } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  toolCalls?: Array<{
    name: string;
    arguments: Record<string, unknown>;
    result?: string;
  }>;
}

interface ChatInterfaceProps {
  sessionId: string;
}

export function ChatInterface({ sessionId }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hello! I'm your personal shopping assistant. I can help you find products, remember your preferences, and make personalized recommendations. What are you looking for today?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    const assistantMessageId = `assistant-${Date.now()}`;
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      timestamp: new Date(),
      isStreaming: true,
      toolCalls: [],
    };

    setMessages((prev) => [...prev, assistantMessage]);

    try {
      for await (const event of streamChat(userMessage.content, sessionId)) {
        const data = event.data as Record<string, unknown>;

        if (data.content) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMessageId
                ? { ...m, content: m.content + data.content }
                : m
            )
          );
        }

        if (data.name && data.arguments) {
          // Tool call started
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMessageId
                ? {
                    ...m,
                    toolCalls: [
                      ...(m.toolCalls || []),
                      {
                        name: data.name as string,
                        arguments: data.arguments as Record<string, unknown>,
                      },
                    ],
                  }
                : m
            )
          );
        }

        if (data.name && data.result) {
          // Tool result
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMessageId
                ? {
                    ...m,
                    toolCalls: m.toolCalls?.map((tc) =>
                      tc.name === data.name
                        ? { ...tc, result: data.result as string }
                        : tc
                    ),
                  }
                : m
            )
          );
        }

        if (data.session_id) {
          // Done event
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMessageId ? { ...m, isStreaming: false } : m
            )
          );
        }

        if (data.error) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMessageId
                ? {
                    ...m,
                    content: `Error: ${data.error}`,
                    isStreaming: false,
                  }
                : m
            )
          );
        }
      }
    } catch (error) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId
            ? {
                ...m,
                content: `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
                isStreaming: false,
              }
            : m
        )
      );
    } finally {
      setIsLoading(false);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId ? { ...m, isStreaming: false } : m
        )
      );
      inputRef.current?.focus();
    }
  };

  const examplePrompts = [
    "I'm looking for running shoes",
    "I prefer Nike brand",
    "My budget is under $150",
    "What would you recommend?",
    "What do you know about my preferences?",
  ];

  return (
    <Flex direction="column" h="calc(100vh - 220px)">
      {/* Messages */}
      <Box flex={1} overflowY="auto" pb={4}>
        <VStack gap={4} align="stretch">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
          <div ref={messagesEndRef} />
        </VStack>
      </Box>

      {/* Example prompts */}
      {messages.length <= 2 && (
        <HStack gap={2} flexWrap="wrap" mb={4}>
          {examplePrompts.map((prompt, i) => (
            <Button
              key={i}
              size="sm"
              variant="outline"
              colorPalette="teal"
              onClick={() => setInput(prompt)}
            >
              {prompt}
            </Button>
          ))}
        </HStack>
      )}

      {/* Input */}
      <Box as="form" onSubmit={handleSubmit}>
        <HStack gap={2}>
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me about products, preferences, or recommendations..."
            size="lg"
            disabled={isLoading}
            bg="white"
          />
          <Button
            type="submit"
            colorPalette="teal"
            size="lg"
            disabled={isLoading || !input.trim()}
          >
            {isLoading ? <Spinner size="sm" /> : "Send"}
          </Button>
        </HStack>
      </Box>
    </Flex>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <Flex justify={isUser ? "flex-end" : "flex-start"}>
      <Card.Root
        maxW="80%"
        bg={isUser ? "teal.500" : "white"}
        color={isUser ? "white" : "gray.800"}
        shadow="sm"
      >
        <Card.Body p={4}>
          {/* Tool calls */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <VStack align="stretch" gap={2} mb={3}>
              {message.toolCalls.map((tc, i) => (
                <Box
                  key={i}
                  bg={isUser ? "teal.600" : "gray.100"}
                  p={2}
                  borderRadius="md"
                  fontSize="sm"
                >
                  <HStack>
                    <Badge colorPalette="purple" size="sm">
                      {tc.name}
                    </Badge>
                    {!tc.result && <Spinner size="xs" />}
                  </HStack>
                </Box>
              ))}
            </VStack>
          )}

          {/* Message content */}
          {message.content ? (
            <Box
              className="markdown-content"
              css={{
                "& p": { marginBottom: "0.5em" },
                "& p:last-child": { marginBottom: 0 },
                "& ul, & ol": { paddingLeft: "1.5em", marginBottom: "0.5em" },
                "& code": {
                  background: isUser ? "rgba(255,255,255,0.2)" : "gray.100",
                  padding: "0.1em 0.3em",
                  borderRadius: "3px",
                  fontSize: "0.9em",
                },
              }}
            >
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </Box>
          ) : message.isStreaming ? (
            <HStack>
              <Spinner size="sm" />
              <Text fontSize="sm">Thinking...</Text>
            </HStack>
          ) : null}

          {/* Timestamp */}
          <Text
            fontSize="xs"
            color={isUser ? "teal.100" : "gray.400"}
            mt={2}
            textAlign="right"
          >
            {message.timestamp.toLocaleTimeString()}
          </Text>
        </Card.Body>
      </Card.Root>
    </Flex>
  );
}
