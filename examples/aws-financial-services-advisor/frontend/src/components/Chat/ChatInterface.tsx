import { useState, useRef, useEffect } from 'react'
import {
  Box,
  Heading,
  Text,
  Card,
  Flex,
  Input,
  Button,
  VStack,
  Spinner,
} from '@chakra-ui/react'
import { FiSend, FiUser, FiCpu } from 'react-icons/fi'
import { chatApi, ChatMessage } from '../../lib/api'

interface Message extends ChatMessage {
  id: string
  isLoading?: boolean
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    // Add loading message
    const loadingId = Date.now().toString() + '-loading'
    setMessages((prev) => [
      ...prev,
      { id: loadingId, role: 'assistant', content: '', isLoading: true },
    ])

    try {
      const response = await chatApi.sendMessage(userMessage.content, sessionId || undefined)

      // Update session ID
      if (!sessionId) {
        setSessionId(response.session_id)
      }

      // Replace loading message with actual response
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === loadingId
            ? { id: loadingId, role: 'assistant', content: response.response, isLoading: false }
            : msg
        )
      )
    } catch (error) {
      // Replace loading with error message
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === loadingId
            ? {
                id: loadingId,
                role: 'assistant',
                content: 'Sorry, an error occurred. Please try again.',
                isLoading: false,
              }
            : msg
        )
      )
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <Box h="calc(100vh - 48px)">
      <Flex direction="column" h="full">
        {/* Header */}
        <Box mb={4}>
          <Heading size="lg" color="gray.800">
            AI Compliance Advisor
          </Heading>
          <Text color="gray.500">
            Ask questions about customers, investigations, or compliance requirements
          </Text>
        </Box>

        {/* Chat Area */}
        <Card.Root flex="1" overflow="hidden">
          <Card.Body p={0} display="flex" flexDirection="column" h="full">
            {/* Messages */}
            <Box flex="1" overflowY="auto" p={4}>
              {messages.length === 0 ? (
                <Flex
                  direction="column"
                  align="center"
                  justify="center"
                  h="full"
                  color="gray.400"
                >
                  <FiCpu size={48} />
                  <Text mt={4} fontSize="lg">
                    Start a conversation
                  </Text>
                  <Text fontSize="sm" mt={2} textAlign="center" maxW="400px">
                    Ask about customer risk assessments, investigation findings, or compliance
                    requirements
                  </Text>
                  <VStack mt={6} gap={2}>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setInput('What are the high-risk customers?')}
                    >
                      What are the high-risk customers?
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        setInput('Run a compliance check for customer CUST-001')
                      }
                    >
                      Run a compliance check
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() =>
                        setInput('What patterns should I look for in AML investigations?')
                      }
                    >
                      AML investigation patterns
                    </Button>
                  </VStack>
                </Flex>
              ) : (
                <VStack gap={4} align="stretch">
                  {messages.map((message) => (
                    <Flex
                      key={message.id}
                      justify={message.role === 'user' ? 'flex-end' : 'flex-start'}
                    >
                      <Flex
                        maxW="80%"
                        bg={message.role === 'user' ? 'teal.500' : 'gray.100'}
                        color={message.role === 'user' ? 'white' : 'gray.800'}
                        borderRadius="lg"
                        p={4}
                        gap={3}
                      >
                        <Box
                          p={2}
                          borderRadius="full"
                          bg={message.role === 'user' ? 'teal.600' : 'gray.200'}
                          h="fit-content"
                        >
                          {message.role === 'user' ? (
                            <FiUser size={16} />
                          ) : (
                            <FiCpu size={16} />
                          )}
                        </Box>
                        <Box>
                          {message.isLoading ? (
                            <Flex align="center" gap={2}>
                              <Spinner size="sm" />
                              <Text>Thinking...</Text>
                            </Flex>
                          ) : (
                            <Text whiteSpace="pre-wrap">{message.content}</Text>
                          )}
                        </Box>
                      </Flex>
                    </Flex>
                  ))}
                  <div ref={messagesEndRef} />
                </VStack>
              )}
            </Box>

            {/* Input */}
            <Box p={4} borderTop="1px" borderColor="gray.200">
              <Flex gap={2}>
                <Input
                  placeholder="Ask about compliance, customers, or investigations..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={isLoading}
                />
                <Button
                  colorPalette="teal"
                  onClick={handleSend}
                  disabled={!input.trim() || isLoading}
                >
                  <FiSend />
                </Button>
              </Flex>
              {sessionId && (
                <Text fontSize="xs" color="gray.400" mt={2}>
                  Session: {sessionId.substring(0, 8)}...
                </Text>
              )}
            </Box>
          </Card.Body>
        </Card.Root>
      </Flex>
    </Box>
  )
}
