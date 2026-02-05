import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
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
} from '@chakra-ui/react'
import { FiSend, FiUser, FiCpu } from 'react-icons/fi'
import { sendChatMessage, ChatMessage as ChatMessageType, ChatResponse } from '../../lib/api'

interface Message extends ChatMessageType {
  agents_consulted?: string[]
  tool_calls?: Array<{ tool_name: string; agent?: string }>
  response_time_ms?: number
}

function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <Box
      alignSelf={isUser ? 'flex-end' : 'flex-start'}
      maxW="80%"
      mb={4}
    >
      <HStack gap={2} mb={1} justify={isUser ? 'flex-end' : 'flex-start'}>
        <Box
          p={1}
          borderRadius="full"
          bg={isUser ? 'blue.100' : 'green.100'}
        >
          {isUser ? <FiUser /> : <FiCpu />}
        </Box>
        <Text fontSize="xs" color="gray.500">
          {isUser ? 'You' : 'Financial Advisor'}
        </Text>
      </HStack>

      <Box
        bg={isUser ? 'blue.500' : 'white'}
        color={isUser ? 'white' : 'gray.800'}
        px={4}
        py={3}
        borderRadius="lg"
        shadow={isUser ? 'none' : 'sm'}
        border={isUser ? 'none' : '1px solid'}
        borderColor="gray.200"
      >
        <Text whiteSpace="pre-wrap">{message.content}</Text>
      </Box>

      {/* Agent info for assistant messages */}
      {!isUser && message.agents_consulted && message.agents_consulted.length > 0 && (
        <HStack mt={2} gap={1} flexWrap="wrap">
          <Text fontSize="xs" color="gray.400">Agents:</Text>
          {message.agents_consulted.map((agent) => (
            <Badge key={agent} size="sm" variant="outline" colorPalette="green">
              {agent.replace('_agent', '')}
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
  )
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | undefined>()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const chatMutation = useMutation({
    mutationFn: (message: string) => sendChatMessage({
      message,
      session_id: sessionId,
    }),
    onSuccess: (response: ChatResponse) => {
      setSessionId(response.session_id)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.message.content,
          agents_consulted: response.agents_consulted,
          tool_calls: response.tool_calls,
          response_time_ms: response.response_time_ms,
        },
      ])
    },
  })

  const handleSend = () => {
    if (!input.trim()) return

    // Add user message
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: input },
    ])

    // Send to API
    chatMutation.mutate(input)
    setInput('')
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const suggestedPrompts = [
    "Investigate customer CUST-003 for potential money laundering",
    "What are the risk factors for Global Holdings Ltd?",
    "Show me the relationship network for CUST-003",
    "Check sanctions status for all customers",
  ]

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
        <Card.Body
          overflowY="auto"
          display="flex"
          flexDirection="column"
          p={4}
        >
          {messages.length === 0 ? (
            <VStack justify="center" flex="1" gap={4}>
              <Text color="gray.500" textAlign="center">
                Start a conversation with the AI Financial Advisor.
                <br />
                Ask about customer investigations, risk assessments, or compliance checks.
              </Text>
              <VStack gap={2}>
                <Text fontSize="sm" color="gray.400">Try asking:</Text>
                {suggestedPrompts.map((prompt, i) => (
                  <Button
                    key={i}
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setInput(prompt)
                    }}
                  >
                    {prompt}
                  </Button>
                ))}
              </VStack>
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
  )
}
