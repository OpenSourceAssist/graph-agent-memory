import {
  Box,
  Text,
  Badge,
  HStack,
  VStack,
  Timeline,
  Code,
  Collapsible,
} from '@chakra-ui/react'
import { motion } from 'framer-motion'
import { useState } from 'react'
import {
  LuBot,
  LuFileCheck,
  LuSearch,
  LuUsers,
  LuShield,
  LuWrench,
  LuCheck,
  LuX,
  LuChevronDown,
  LuChevronRight,
} from 'react-icons/lu'
import type { AgentState } from '../../hooks/useAgentStream'

interface AgentActivityTimelineProps {
  agentStates: Map<string, AgentState>
  agentsConsulted: string[]
  totalDurationMs?: number
  traceId?: string | null
}

const agentIcons: Record<string, React.ReactNode> = {
  supervisor: <LuBot size={14} />,
  kyc_agent: <LuFileCheck size={14} />,
  aml_agent: <LuSearch size={14} />,
  relationship_agent: <LuUsers size={14} />,
  compliance_agent: <LuShield size={14} />,
}

const agentColors: Record<string, string> = {
  supervisor: 'blue',
  kyc_agent: 'teal',
  aml_agent: 'orange',
  relationship_agent: 'purple',
  compliance_agent: 'red',
}

const agentLabels: Record<string, string> = {
  supervisor: 'Supervisor',
  kyc_agent: 'KYC Agent',
  aml_agent: 'AML Agent',
  relationship_agent: 'Relationship Agent',
  compliance_agent: 'Compliance Agent',
}

export function AgentActivityTimeline({
  agentStates,
  agentsConsulted,
  totalDurationMs,
  traceId,
}: AgentActivityTimelineProps) {
  const [expanded, setExpanded] = useState(false)
  const agents = Array.from(agentStates.entries())

  if (agents.length === 0 && agentsConsulted.length === 0) return null

  const totalTools = agents.reduce((sum, [, s]) => sum + s.toolCalls.length, 0)

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <Box mt={2}>
        <HStack
          gap={2}
          cursor="pointer"
          onClick={() => setExpanded(!expanded)}
          _hover={{ color: 'blue.500' }}
          transition="color 0.15s"
        >
          <Box color="fg.muted">
            {expanded ? <LuChevronDown size={12} /> : <LuChevronRight size={12} />}
          </Box>
          <Text fontSize="xs" color="fg.muted" fontWeight="medium">
            Agent Activity
          </Text>
          <Badge size="sm" variant="outline">
            {agentsConsulted.length || agents.length} agents
          </Badge>
          {totalTools > 0 && (
            <Badge size="sm" variant="outline" colorPalette="blue">
              {totalTools} tools
            </Badge>
          )}
          {totalDurationMs && (
            <Text fontSize="xs" color="fg.muted">
              {(totalDurationMs / 1000).toFixed(1)}s
            </Text>
          )}
        </HStack>

        <Collapsible.Root open={expanded}>
          <Collapsible.Content>
            <Box mt={2} ml={2}>
              <Timeline.Root size="sm" variant="subtle">
                {agents.map(([name, state]) => {
                  const color = agentColors[name] || 'gray'
                  const icon = agentIcons[name] || <LuBot size={14} />
                  const label = agentLabels[name] || name

                  return (
                    <Timeline.Item key={name}>
                      <Timeline.Connector>
                        <Timeline.Separator />
                        <Timeline.Indicator
                          bg={`${color}.solid`}
                          color={`${color}.contrast`}
                        >
                          {icon}
                        </Timeline.Indicator>
                      </Timeline.Connector>
                      <Timeline.Content>
                        <Timeline.Title>
                          <HStack gap={2}>
                            <Text fontWeight="medium" fontSize="sm">
                              {label}
                            </Text>
                            <Badge size="sm" colorPalette={color} variant="subtle">
                              {state.status === 'complete' ? 'Done' : state.status}
                            </Badge>
                          </HStack>
                        </Timeline.Title>

                        {/* Tool calls summary */}
                        {state.toolCalls.length > 0 && (
                          <VStack gap={1} align="start" mt={1}>
                            {state.toolCalls.map((tc, i) => (
                              <HStack key={i} gap={1}>
                                <LuWrench size={10} />
                                <Code size="sm" variant="plain">
                                  {tc.tool}
                                </Code>
                                {tc.result !== undefined ? (
                                  <Box color="green.500"><LuCheck size={10} /></Box>
                                ) : (
                                  <Box color="red.500"><LuX size={10} /></Box>
                                )}
                              </HStack>
                            ))}
                          </VStack>
                        )}

                        {/* Memory accesses */}
                        {state.memoryAccesses.length > 0 && (
                          <HStack gap={1} mt={1}>
                            <Badge size="sm" variant="subtle" colorPalette="blue">
                              {state.memoryAccesses.length} Neo4j ops
                            </Badge>
                          </HStack>
                        )}
                      </Timeline.Content>
                    </Timeline.Item>
                  )
                })}

                {/* If no agent states but have consulted list, show simple timeline */}
                {agents.length === 0 &&
                  agentsConsulted.map((name) => (
                    <Timeline.Item key={name}>
                      <Timeline.Connector>
                        <Timeline.Separator />
                        <Timeline.Indicator>
                          {agentIcons[name] || <LuBot size={14} />}
                        </Timeline.Indicator>
                      </Timeline.Connector>
                      <Timeline.Content>
                        <Timeline.Title>
                          {agentLabels[name] || name}
                        </Timeline.Title>
                      </Timeline.Content>
                    </Timeline.Item>
                  ))}
              </Timeline.Root>

              {traceId && (
                <Text fontSize="xs" color="fg.muted" mt={2}>
                  Trace: {traceId.slice(0, 8)}...
                </Text>
              )}
            </Box>
          </Collapsible.Content>
        </Collapsible.Root>
      </Box>
    </motion.div>
  )
}
