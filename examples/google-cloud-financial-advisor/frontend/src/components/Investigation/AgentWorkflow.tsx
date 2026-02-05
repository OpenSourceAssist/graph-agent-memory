import { Box, Flex, Text, VStack, Badge, Progress } from '@chakra-ui/react'
import {
  LuBot,
  LuSearch,
  LuShield,
  LuUsers,
  LuFileCheck,
  LuArrowRight,
} from 'react-icons/lu'

interface AgentWorkflowProps {
  activeAgent?: string
}

const agents = [
  {
    id: 'supervisor',
    name: 'Supervisor',
    icon: <LuBot size={20} />,
    color: 'blue',
    description: 'Coordinating investigation',
  },
  {
    id: 'kyc_agent',
    name: 'KYC Agent',
    icon: <LuFileCheck size={20} />,
    color: 'green',
    description: 'Verifying identity',
  },
  {
    id: 'aml_agent',
    name: 'AML Agent',
    icon: <LuSearch size={20} />,
    color: 'orange',
    description: 'Scanning transactions',
  },
  {
    id: 'relationship_agent',
    name: 'Relationship Agent',
    icon: <LuUsers size={20} />,
    color: 'purple',
    description: 'Mapping network',
  },
  {
    id: 'compliance_agent',
    name: 'Compliance Agent',
    icon: <LuShield size={20} />,
    color: 'cyan',
    description: 'Checking sanctions',
  },
]

export function AgentWorkflow({ activeAgent = 'supervisor' }: AgentWorkflowProps) {
  return (
    <Box>
      <Text fontSize="sm" fontWeight="medium" mb={3}>
        Multi-Agent Workflow
      </Text>

      <VStack gap={3} align="stretch">
        {agents.map((agent, index) => {
          const isActive = agent.id === activeAgent
          const isPast = agents.findIndex((a) => a.id === activeAgent) > index

          return (
            <Box key={agent.id}>
              <Flex align="center" gap={3}>
                <Box
                  p={2}
                  borderRadius="md"
                  bg={isActive ? `${agent.color}.500` : isPast ? `${agent.color}.100` : 'bg.subtle'}
                  color={isActive ? 'white' : isPast ? `${agent.color}.500` : 'fg.muted'}
                >
                  {agent.icon}
                </Box>
                <Box flex={1}>
                  <Flex justify="space-between" align="center">
                    <Text
                      fontWeight={isActive ? 'semibold' : 'normal'}
                      color={isActive ? 'fg' : 'fg.muted'}
                    >
                      {agent.name}
                    </Text>
                    {isActive && (
                      <Badge colorPalette={agent.color} variant="subtle">
                        Active
                      </Badge>
                    )}
                    {isPast && (
                      <Badge colorPalette="green" variant="subtle">
                        Complete
                      </Badge>
                    )}
                  </Flex>
                  <Text fontSize="xs" color="fg.muted">
                    {agent.description}
                  </Text>
                </Box>
              </Flex>

              {index < agents.length - 1 && (
                <Flex ml={5} my={1} color="fg.muted">
                  <LuArrowRight size={12} style={{ transform: 'rotate(90deg)' }} />
                </Flex>
              )}
            </Box>
          )
        })}
      </VStack>

      <Box mt={4}>
        <Text fontSize="xs" color="fg.muted" mb={1}>
          Investigation Progress
        </Text>
        <Progress.Root>
          <Progress.Track>
            <Progress.Range />
          </Progress.Track>
        </Progress.Root>
      </Box>
    </Box>
  )
}
