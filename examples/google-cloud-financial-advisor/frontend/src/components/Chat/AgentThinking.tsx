import { Box, Flex, Text, Spinner, VStack, Badge } from '@chakra-ui/react'
import { LuBot, LuSearch, LuShield, LuUsers, LuFileCheck } from 'react-icons/lu'

interface ThinkingStep {
  agent: string
  status: string
}

interface AgentThinkingProps {
  steps: ThinkingStep[]
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
  kyc_agent: 'green',
  aml_agent: 'orange',
  relationship_agent: 'purple',
  compliance_agent: 'cyan',
}

const agentLabels: Record<string, string> = {
  supervisor: 'Supervisor',
  kyc_agent: 'KYC Agent',
  aml_agent: 'AML Agent',
  relationship_agent: 'Relationship Agent',
  compliance_agent: 'Compliance Agent',
}

export function AgentThinking({ steps }: AgentThinkingProps) {
  return (
    <Flex justify="flex-start">
      <Box maxW="80%" p={3} bg="bg.subtle" borderRadius="lg">
        <VStack align="start" gap={2}>
          <Flex align="center" gap={2}>
            <Spinner size="sm" />
            <Text fontSize="sm" fontWeight="medium">
              Processing...
            </Text>
          </Flex>

          {steps.map((step, index) => (
            <Flex key={index} align="center" gap={2}>
              <Box color={`${agentColors[step.agent] || 'gray'}.500`}>
                {agentIcons[step.agent] || <LuBot size={14} />}
              </Box>
              <Badge
                size="sm"
                colorPalette={agentColors[step.agent] || 'gray'}
                variant="subtle"
              >
                {agentLabels[step.agent] || step.agent}
              </Badge>
              <Text fontSize="xs" color="fg.muted">
                {step.status}
              </Text>
            </Flex>
          ))}
        </VStack>
      </Box>
    </Flex>
  )
}
