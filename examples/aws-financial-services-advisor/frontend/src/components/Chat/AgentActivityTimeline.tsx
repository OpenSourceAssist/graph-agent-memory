import {
  Box,
  Badge,
  Flex,
  HStack,
  Text,
  VStack,
} from '@chakra-ui/react'
import {
  LuFileCheck,
  LuSearch,
  LuNetwork,
  LuShield,
  LuBrain,
  LuClock,
  LuWrench,
} from 'react-icons/lu'
import type { AgentState, StreamResult } from '../../hooks/useAgentStream'

const agentConfig: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  supervisor: { label: 'Supervisor', icon: LuBrain, color: 'blue' },
  kyc: { label: 'KYC Agent', icon: LuFileCheck, color: 'teal' },
  kyc_agent: { label: 'KYC Agent', icon: LuFileCheck, color: 'teal' },
  aml: { label: 'AML Agent', icon: LuSearch, color: 'orange' },
  aml_agent: { label: 'AML Agent', icon: LuSearch, color: 'orange' },
  relationship: { label: 'Relationship Agent', icon: LuNetwork, color: 'purple' },
  relationship_agent: { label: 'Relationship Agent', icon: LuNetwork, color: 'purple' },
  compliance: { label: 'Compliance Agent', icon: LuShield, color: 'red' },
  compliance_agent: { label: 'Compliance Agent', icon: LuShield, color: 'red' },
}

interface AgentActivityTimelineProps {
  agentStates: Map<string, AgentState>
  streamResult: StreamResult | null
}

export default function AgentActivityTimeline({
  agentStates,
  streamResult,
}: AgentActivityTimelineProps) {
  if (agentStates.size === 0 && !streamResult) return null

  const totalTools = Array.from(agentStates.values()).reduce(
    (sum, s) => sum + s.toolCalls.length, 0
  )

  return (
    <Box p={3} bg="gray.50" borderRadius="md" mt={2} mb={2}>
      <Text fontWeight="semibold" fontSize="sm" mb={2}>
        Investigation Summary
      </Text>

      <VStack gap={2} align="stretch">
        {Array.from(agentStates.entries()).map(([name, state]) => {
          const config = agentConfig[name] || { label: name, icon: LuBrain, color: 'gray' }
          const Icon = config.icon

          return (
            <Flex key={name} align="start" gap={2}>
              <Box
                p={1}
                borderRadius="full"
                bg={`${config.color}.100`}
                color={`${config.color}.600`}
                mt={0.5}
              >
                <Icon size={12} />
              </Box>
              <Box flex={1}>
                <HStack gap={1} mb={0.5}>
                  <Text fontSize="xs" fontWeight="medium">{config.label}</Text>
                  <Badge size="sm" colorPalette="green">complete</Badge>
                </HStack>
                {state.toolCalls.length > 0 && (
                  <HStack gap={1} flexWrap="wrap">
                    {state.toolCalls.map((tc, i) => (
                      <Badge key={i} size="sm" variant="outline" fontFamily="mono">
                        <LuWrench size={10} /> {tc.tool}
                      </Badge>
                    ))}
                  </HStack>
                )}
              </Box>
            </Flex>
          )
        })}
      </VStack>

      {streamResult && (
        <Flex mt={3} pt={2} borderTop="1px solid" borderColor="gray.200" gap={4} fontSize="xs" color="gray.500">
          <HStack gap={1}>
            <LuBrain size={12} />
            <Text>{streamResult.agentsConsulted.length} agents</Text>
          </HStack>
          <HStack gap={1}>
            <LuWrench size={12} />
            <Text>{totalTools} tools</Text>
          </HStack>
          <HStack gap={1}>
            <LuClock size={12} />
            <Text>{(streamResult.totalDurationMs / 1000).toFixed(1)}s</Text>
          </HStack>
          {streamResult.traceId && (
            <Text fontFamily="mono" color="gray.400">
              trace: {streamResult.traceId.slice(0, 8)}...
            </Text>
          )}
        </Flex>
      )}
    </Box>
  )
}
