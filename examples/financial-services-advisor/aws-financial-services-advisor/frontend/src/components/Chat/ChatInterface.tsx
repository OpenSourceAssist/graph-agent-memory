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
import { useAgentStream } from '../../hooks/useAgentStream'
import AgentOrchestrationView from './AgentOrchestrationView'
import AgentActivityTimeline from './AgentActivityTimeline'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  isLoading?: boolean
  agentStates?: Map<string, import('../../hooks/useAgentStream').AgentState>
  streamResult?: import('../../hooks/useAgentStream').StreamResult | null
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const {
    isStreaming,
    activeAgent,
    agentStates,
    finalResponse,
    streamResult,
    error,
    startStream,
  } = useAgentStream()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isStreaming])

  // When streaming completes with a response, update the loading message
  useEffect(() => {
    if (finalResponse && !isStreaming) {
      setMessages(prev =>
        prev.map(msg =>
          msg.isLoading
            ? {
                ...msg,
                content: finalResponse,
                isLoading: false,
                agentStates: new Map(agentStates),
                streamResult: streamResult,
              }
            : msg
        )
      )
      if (streamResult?.sessionId) {
        setSessionId(streamResult.sessionId)
      }
    }
  }, [finalResponse, isStreaming, agentStates, streamResult])

  // Handle error
  useEffect(() => {
    if (error && !isStreaming) {
      setMessages(prev =>
        prev.map(msg =>
          msg.isLoading
            ? {
                ...msg,
                content: `Error: ${error}`,
                isLoading: false,
              }
            : msg
        )
      )
    }
  }, [error, isStreaming])

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
    }

    const loadingMessage: Message = {
      id: Date.now().toString() + '-loading',
      role: 'assistant',
      content: '',
      isLoading: true,
    }

    setMessages(prev => [...prev, userMessage, loadingMessage])
    setInput('')

    // Start SSE stream
    startStream(userMessage.content, sessionId || undefined)
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
                    requirements. All agent tools now query real data from Neo4j.
                  </Text>
                  <VStack mt={6} gap={2}>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setInput('Investigate customer CUST-003 for potential money laundering')}
                    >
                      Investigate CUST-003 for money laundering
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
                        setInput('Analyze the network connections of Global Holdings Ltd')
                      }
                    >
                      Analyze network connections
                    </Button>
                  </VStack>
                </Flex>
              ) : (
                <VStack gap={4} align="stretch">
                  {messages.map((message) => (
                    <Box key={message.id}>
                      <Flex
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
                                <Text>Investigating...</Text>
                              </Flex>
                            ) : (
                              <Text whiteSpace="pre-wrap">{message.content}</Text>
                            )}
                          </Box>
                        </Flex>
                      </Flex>

                      {/* Show agent activity after assistant messages */}
                      {message.role === 'assistant' && !message.isLoading && message.agentStates && (
                        <AgentActivityTimeline
                          agentStates={message.agentStates}
                          streamResult={message.streamResult || null}
                        />
                      )}
                    </Box>
                  ))}

                  {/* Live orchestration view during streaming */}
                  {isStreaming && (
                    <AgentOrchestrationView
                      agentStates={agentStates}
                      activeAgent={activeAgent}
                      isStreaming={isStreaming}
                    />
                  )}

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
                  disabled={isStreaming}
                />
                <Button
                  colorPalette="teal"
                  onClick={handleSend}
                  disabled={!input.trim() || isStreaming}
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
