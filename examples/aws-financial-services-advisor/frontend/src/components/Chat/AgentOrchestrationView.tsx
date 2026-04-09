import { useState } from 'react'
import {
  Box,
  Card,
  Flex,
  Heading,
  Text,
  Badge,
  HStack,
  VStack,
} from '@chakra-ui/react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LuFileCheck,
  LuSearch,
  LuNetwork,
  LuShield,
  LuBrain,
  LuDatabase,
  LuChevronDown,
  LuChevronRight,
} from 'react-icons/lu'
import type { AgentState } from '../../hooks/useAgentStream'
import ToolCallCard, { agentColorMap } from './ToolCallCard'
import MemoryAccessIndicator from './MemoryAccessIndicator'

const agentConfig: Record<string, { label: string; icon: React.ElementType; color: string; description: string }> = {
  supervisor: { label: 'Supervisor', icon: LuBrain, color: 'blue', description: 'Orchestrating investigation' },
  kyc: { label: 'KYC Agent', icon: LuFileCheck, color: 'teal', description: 'Identity verification' },
  kyc_agent: { label: 'KYC Agent', icon: LuFileCheck, color: 'teal', description: 'Identity verification' },
  aml: { label: 'AML Agent', icon: LuSearch, color: 'orange', description: 'Transaction monitoring' },
  aml_agent: { label: 'AML Agent', icon: LuSearch, color: 'orange', description: 'Transaction monitoring' },
  relationship: { label: 'Relationship Agent', icon: LuNetwork, color: 'purple', description: 'Network analysis' },
  relationship_agent: { label: 'Relationship Agent', icon: LuNetwork, color: 'purple', description: 'Network analysis' },
  compliance: { label: 'Compliance Agent', icon: LuShield, color: 'red', description: 'Regulatory compliance' },
  compliance_agent: { label: 'Compliance Agent', icon: LuShield, color: 'red', description: 'Regulatory compliance' },
}

interface AgentOrchestrationViewProps {
  agentStates: Map<string, AgentState>
  activeAgent: string | null
  isStreaming: boolean
}

function ActiveDot() {
  return (
    <motion.div
      animate={{ scale: [1, 1.3, 1], opacity: [1, 0.7, 1] }}
      transition={{ duration: 1.5, repeat: Infinity }}
      style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#3182CE', display: 'inline-block' }}
    />
  )
}

function AgentCard({ name, state, isActive }: { name: string; state: AgentState; isActive: boolean }) {
  const [expanded, setExpanded] = useState(true)
  const config = agentConfig[name] || { label: name, icon: LuBrain, color: 'gray', description: '' }
  const Icon = config.icon
  const hasDetails = state.toolCalls.length > 0 || state.memoryAccesses.length > 0 || state.thoughts.length > 0

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      transition={{ duration: 0.3 }}
    >
      <Card.Root
        size="sm"
        borderLeft="3px solid"
        borderLeftColor={isActive ? `${config.color}.500` : state.status === 'complete' ? 'green.400' : 'gray.300'}
        bg={isActive ? `${config.color}.50` : undefined}
      >
        <Card.Body py={2} px={3}>
          <Flex
            justify="space-between"
            align="center"
            cursor={hasDetails ? 'pointer' : 'default'}
            onClick={() => hasDetails && setExpanded(!expanded)}
          >
            <HStack gap={2}>
              {isActive && <ActiveDot />}
              <Icon size={16} />
              <Text fontWeight="semibold" fontSize="sm">{config.label}</Text>
            </HStack>
            <HStack gap={1}>
              {state.toolCalls.length > 0 && (
                <Badge size="sm" colorPalette={config.color}>
                  {state.toolCalls.length} tools
                </Badge>
              )}
              {state.memoryAccesses.length > 0 && (
                <Badge size="sm" colorPalette="cyan">
                  <LuDatabase size={10} /> {state.memoryAccesses.length}
                </Badge>
              )}
              <Badge size="sm" colorPalette={state.status === 'active' ? 'blue' : state.status === 'complete' ? 'green' : 'gray'}>
                {state.status}
              </Badge>
              {hasDetails && (expanded ? <LuChevronDown size={14} /> : <LuChevronRight size={14} />)}
            </HStack>
          </Flex>

          <AnimatePresence>
            {expanded && hasDetails && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                style={{ overflow: 'hidden' }}
              >
                <VStack gap={1.5} align="stretch" mt={2}>
                  {state.thoughts.slice(-2).map((thought, i) => (
                    <Text key={i} fontSize="xs" color="gray.500" fontStyle="italic">
                      {thought.slice(0, 100)}
                    </Text>
                  ))}

                  {state.memoryAccesses.map((ma, i) => (
                    <MemoryAccessIndicator key={i} operation={ma.operation} tool={ma.tool} query={ma.query} />
                  ))}

                  {state.toolCalls.map((tc, i) => (
                    <ToolCallCard
                      key={i}
                      tool={tc.tool}
                      args={tc.args}
                      result={tc.result}
                      color={config.color}
                    />
                  ))}
                </VStack>
              </motion.div>
            )}
          </AnimatePresence>
        </Card.Body>
      </Card.Root>
    </motion.div>
  )
}

export default function AgentOrchestrationView({
  agentStates,
  activeAgent,
  isStreaming,
}: AgentOrchestrationViewProps) {
  if (!isStreaming && agentStates.size === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <Box p={3} bg="gray.50" borderRadius="md" mb={3}>
        <HStack mb={2}>
          <LuBrain size={16} />
          <Heading size="xs">Agent Activity</Heading>
          {isStreaming && (
            <Badge colorPalette="blue" size="sm">
              <motion.span animate={{ opacity: [1, 0.5, 1] }} transition={{ duration: 1.5, repeat: Infinity }}>
                Live
              </motion.span>
            </Badge>
          )}
        </HStack>
        <VStack gap={2} align="stretch">
          <AnimatePresence>
            {Array.from(agentStates.entries()).map(([name, state]) => (
              <AgentCard key={name} name={name} state={state} isActive={name === activeAgent} />
            ))}
          </AnimatePresence>
        </VStack>
      </Box>
    </motion.div>
  )
}
