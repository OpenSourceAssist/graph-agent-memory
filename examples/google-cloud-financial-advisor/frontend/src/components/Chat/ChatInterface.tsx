import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Box,
  Heading,
  Text,
  Card,
  VStack,
  HStack,
  Input,
  Button,
  Badge,
  Spinner,
  SimpleGrid,
} from "@chakra-ui/react";
import {
  FiSend,
  FiUser,
  FiCpu,
  FiShield,
  FiSearch,
  FiUsers,
  FiAlertTriangle,
  FiFileText,
  FiActivity,
} from "react-icons/fi";
import {
  sendChatMessage,
  ChatMessage as ChatMessageType,
  ChatResponse,
} from "../../lib/api";

interface Message extends ChatMessageType {
  agents_consulted?: string[];
  tool_calls?: Array<{ tool_name: string; agent?: string }>;
  response_time_ms?: number;
}

function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <Box alignSelf={isUser ? "flex-end" : "flex-start"} maxW="80%" mb={4}>
      <HStack gap={2} mb={1} justify={isUser ? "flex-end" : "flex-start"}>
        <Box p={1} borderRadius="full" bg={isUser ? "blue.100" : "green.100"}>
          {isUser ? <FiUser /> : <FiCpu />}
        </Box>
        <Text fontSize="xs" color="gray.500">
          {isUser ? "You" : "Financial Advisor"}
        </Text>
      </HStack>

      <Box
        bg={isUser ? "blue.500" : "white"}
        color={isUser ? "white" : "gray.800"}
        px={4}
        py={3}
        borderRadius="lg"
        shadow={isUser ? "none" : "sm"}
        border={isUser ? "none" : "1px solid"}
        borderColor="gray.200"
      >
        <Text whiteSpace="pre-wrap">{message.content}</Text>
      </Box>

      {/* Agent info for assistant messages */}
      {!isUser &&
        message.agents_consulted &&
        message.agents_consulted.length > 0 && (
          <HStack mt={2} gap={1} flexWrap="wrap">
            <Text fontSize="xs" color="gray.400">
              Agents:
            </Text>
            {message.agents_consulted.map((agent) => (
              <Badge
                key={agent}
                size="sm"
                variant="outline"
                colorPalette="green"
              >
                {agent.replace("_agent", "")}
              </Badge>
            ))}
          </HStack>
        )}

      {!isUser && message.tool_calls && message.tool_calls.length > 0 && (
        <Text fontSize="xs" color="gray.400" mt={1}>
          {message.tool_calls.length} tool calls
        </Text>
      )}

      {!isUser && message.response_time_ms && (
        <Text fontSize="xs" color="gray.400" mt={1}>
          Response time: {message.response_time_ms}ms
        </Text>
      )}
    </Box>
  );
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const chatMutation = useMutation({
    mutationFn: (message: string) =>
      sendChatMessage({
        message,
        session_id: sessionId,
      }),
    onSuccess: (response: ChatResponse) => {
      setSessionId(response.session_id);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.message.content,
          agents_consulted: response.agents_consulted,
          tool_calls: response.tool_calls,
          response_time_ms: response.response_time_ms,
        },
      ]);
    },
  });

  const handleSend = () => {
    if (!input.trim()) return;

    // Add user message
    setMessages((prev) => [...prev, { role: "user", content: input }]);

    // Send to API
    chatMutation.mutate(input);
    setInput("");
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestedPrompts = [
    {
      title: "Full Compliance Investigation",
      agents: ["KYC", "AML", "Relationship", "Compliance"],
      icon: FiShield,
      color: "red",
      prompt:
        "Run a full compliance investigation on CUST-003 Global Holdings Ltd — check KYC documents, scan for structuring patterns, trace the shell company network, and screen against sanctions lists",
    },
    {
      title: "Detect Structuring Pattern",
      agents: ["AML"],
      icon: FiAlertTriangle,
      color: "orange",
      prompt:
        "I see four cash deposits of $9,500 each from CUST-003 in late January. Analyze whether this is a structuring pattern and identify where the funds went",
    },
    {
      title: "Compare Customer Risk Profiles",
      agents: ["KYC", "Compliance"],
      icon: FiActivity,
      color: "blue",
      prompt:
        "Compare the risk profiles of all three customers and flag which ones need enhanced due diligence",
    },
    {
      title: "Trace Beneficial Ownership",
      agents: ["Relationship"],
      icon: FiUsers,
      color: "purple",
      prompt:
        "Trace the beneficial ownership chain from Global Holdings Ltd through Shell Corp Cayman and Anonymous Trust Seychelles — who ultimately controls these entities?",
    },
    {
      title: "Investigate Wire Transfers",
      agents: ["AML", "KYC"],
      icon: FiSearch,
      color: "teal",
      prompt:
        "Maria Garcia (CUST-002) has rapid wire transfers totaling over $280K. Investigate whether her import/export business justifies this transaction volume",
    },
    {
      title: "Generate SAR Report",
      agents: ["Compliance", "AML"],
      icon: FiFileText,
      color: "yellow",
      prompt:
        "Generate a Suspicious Activity Report for the $250,000 wire from an unknown offshore entity to CUST-003 that was moved to Shell Corp Cayman the next day",
    },
  ];

  return (
    <Box h="calc(100vh - 100px)" display="flex" flexDirection="column">
      <HStack justify="space-between" mb={4}>
        <Heading size="lg">AI Financial Advisor</Heading>
        {sessionId && (
          <Badge variant="outline">Session: {sessionId.slice(0, 8)}...</Badge>
        )}
      </HStack>

      {/* Messages area */}
      <Card.Root flex="1" mb={4} overflow="hidden">
        <Card.Body overflowY="auto" display="flex" flexDirection="column" p={4}>
          {messages.length === 0 ? (
            <VStack justify="center" flex="1" gap={6} py={4}>
              <VStack gap={1}>
                <Heading size="md" color="gray.600">
                  AI Financial Advisor
                </Heading>
                <Text color="gray.500" textAlign="center" fontSize="sm">
                  Multi-agent compliance investigations powered by Google ADK
                  and Neo4j
                </Text>
              </VStack>
              <SimpleGrid
                columns={{ base: 1, md: 2, lg: 3 }}
                gap={3}
                w="full"
                px={2}
              >
                {suggestedPrompts.map((item, i) => {
                  const Icon = item.icon;
                  return (
                    <Card.Root
                      key={i}
                      variant="outline"
                      size="sm"
                      cursor="pointer"
                      _hover={{
                        shadow: "md",
                        borderColor: `${item.color}.300`,
                        bg: `${item.color}.50`,
                      }}
                      transition="all 0.2s"
                      onClick={() => setInput(item.prompt)}
                    >
                      <Card.Body gap={2}>
                        <HStack gap={2}>
                          <Box color={`${item.color}.500`}>
                            <Icon size={16} />
                          </Box>
                          <Text fontWeight="semibold" fontSize="sm">
                            {item.title}
                          </Text>
                        </HStack>
                        <Text fontSize="xs" color="gray.500" lineClamp={2}>
                          {item.prompt}
                        </Text>
                        <HStack gap={1} flexWrap="wrap" mt={1}>
                          {item.agents.map((agent) => (
                            <Badge
                              key={agent}
                              size="sm"
                              variant="subtle"
                              colorPalette={item.color}
                            >
                              {agent}
                            </Badge>
                          ))}
                        </HStack>
                      </Card.Body>
                    </Card.Root>
                  );
                })}
              </SimpleGrid>
            </VStack>
          ) : (
            <VStack align="stretch" gap={0}>
              {messages.map((msg, i) => (
                <ChatMessage key={i} message={msg} />
              ))}
              {chatMutation.isPending && (
                <HStack alignSelf="flex-start" gap={2} p={4}>
                  <Spinner size="sm" />
                  <Text fontSize="sm" color="gray.500">
                    Agents analyzing...
                  </Text>
                </HStack>
              )}
              <div ref={messagesEndRef} />
            </VStack>
          )}
        </Card.Body>
      </Card.Root>

      {/* Input area */}
      <HStack>
        <Input
          placeholder="Ask about customer investigations, risk assessments..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={chatMutation.isPending}
          size="lg"
        />
        <Button
          colorPalette="blue"
          onClick={handleSend}
          disabled={!input.trim() || chatMutation.isPending}
          size="lg"
        >
          <FiSend />
        </Button>
      </HStack>

      {chatMutation.isError && (
        <Text color="red.500" fontSize="sm" mt={2}>
          Error: {(chatMutation.error as Error).message}
        </Text>
      )}
    </Box>
  );
}
