import { useState } from 'react'
import {
  Box,
  Heading,
  Text,
  Card,
  Flex,
  Badge,
  Button,
  Table,
  Spinner,
  SimpleGrid,
  VStack,
} from '@chakra-ui/react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { FiSearch, FiClock, FiCheckCircle, FiPlay } from 'react-icons/fi'
import { investigationApi } from '../../lib/api'

function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'pending':
      return 'gray'
    case 'in_progress':
      return 'blue'
    case 'completed':
      return 'green'
    case 'escalated':
      return 'red'
    default:
      return 'gray'
  }
}

function getPriorityColor(priority: string): string {
  switch (priority.toLowerCase()) {
    case 'high':
      return 'red'
    case 'medium':
      return 'orange'
    case 'low':
      return 'green'
    default:
      return 'gray'
  }
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export default function InvestigationPanel() {
  const [selectedInvestigation, setSelectedInvestigation] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: investigationsData, isLoading } = useQuery({
    queryKey: ['investigations'],
    queryFn: () => investigationApi.list(),
  })

  const startMutation = useMutation({
    mutationFn: (id: string) => investigationApi.start(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['investigations'] })
    },
  })

  const investigations = investigationsData?.investigations || []

  const pendingCount = investigations.filter((i) => i.status === 'pending').length
  const inProgressCount = investigations.filter((i) => i.status === 'in_progress').length
  const completedCount = investigations.filter((i) => i.status === 'completed').length

  return (
    <Box>
      <Flex justify="space-between" align="center" mb={6}>
        <Box>
          <Heading size="lg" color="gray.800">
            Investigations
          </Heading>
          <Text color="gray.500">Compliance investigations with AI-powered analysis</Text>
        </Box>
        <Button colorPalette="teal">New Investigation</Button>
      </Flex>

      {/* Summary Stats */}
      <SimpleGrid columns={{ base: 1, md: 3 }} gap={6} mb={8}>
        <Card.Root>
          <Card.Body>
            <Flex align="center">
              <Box p={3} borderRadius="full" bg="gray.100" mr={4}>
                <FiClock size={24} color="var(--chakra-colors-gray-500)" />
              </Box>
              <Box>
                <Text color="gray.500" fontSize="sm">
                  Pending
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {pendingCount}
                </Text>
              </Box>
            </Flex>
          </Card.Body>
        </Card.Root>

        <Card.Root>
          <Card.Body>
            <Flex align="center">
              <Box p={3} borderRadius="full" bg="blue.100" mr={4}>
                <FiSearch size={24} color="var(--chakra-colors-blue-500)" />
              </Box>
              <Box>
                <Text color="gray.500" fontSize="sm">
                  In Progress
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {inProgressCount}
                </Text>
              </Box>
            </Flex>
          </Card.Body>
        </Card.Root>

        <Card.Root>
          <Card.Body>
            <Flex align="center">
              <Box p={3} borderRadius="full" bg="green.100" mr={4}>
                <FiCheckCircle size={24} color="var(--chakra-colors-green-500)" />
              </Box>
              <Box>
                <Text color="gray.500" fontSize="sm">
                  Completed
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {completedCount}
                </Text>
              </Box>
            </Flex>
          </Card.Body>
        </Card.Root>
      </SimpleGrid>

      {/* Investigations Table */}
      <Card.Root>
        <Card.Header>
          <Heading size="md">All Investigations</Heading>
        </Card.Header>
        <Card.Body>
          {isLoading ? (
            <Flex justify="center" py={8}>
              <Spinner size="lg" color="teal.500" />
            </Flex>
          ) : investigations.length === 0 ? (
            <VStack py={8} gap={4}>
              <FiSearch size={48} color="var(--chakra-colors-gray-300)" />
              <Text color="gray.500">No investigations found.</Text>
              <Button colorPalette="teal">Create First Investigation</Button>
            </VStack>
          ) : (
            <Table.Root>
              <Table.Header>
                <Table.Row>
                  <Table.ColumnHeader>ID</Table.ColumnHeader>
                  <Table.ColumnHeader>Title</Table.ColumnHeader>
                  <Table.ColumnHeader>Customer</Table.ColumnHeader>
                  <Table.ColumnHeader>Status</Table.ColumnHeader>
                  <Table.ColumnHeader>Priority</Table.ColumnHeader>
                  <Table.ColumnHeader>Findings</Table.ColumnHeader>
                  <Table.ColumnHeader>Created</Table.ColumnHeader>
                  <Table.ColumnHeader>Actions</Table.ColumnHeader>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {investigations.map((investigation) => (
                  <Table.Row
                    key={investigation.id}
                    cursor="pointer"
                    _hover={{ bg: 'gray.50' }}
                    onClick={() => setSelectedInvestigation(investigation.id)}
                    bg={selectedInvestigation === investigation.id ? 'teal.50' : undefined}
                  >
                    <Table.Cell fontFamily="mono" fontSize="sm">
                      {investigation.id}
                    </Table.Cell>
                    <Table.Cell fontWeight="medium" maxW="250px" truncate>
                      {investigation.title}
                    </Table.Cell>
                    <Table.Cell fontFamily="mono" fontSize="sm">
                      {investigation.customer_id}
                    </Table.Cell>
                    <Table.Cell>
                      <Badge colorPalette={getStatusColor(investigation.status)}>
                        {investigation.status.replace(/_/g, ' ')}
                      </Badge>
                    </Table.Cell>
                    <Table.Cell>
                      <Badge colorPalette={getPriorityColor(investigation.priority)}>
                        {investigation.priority}
                      </Badge>
                    </Table.Cell>
                    <Table.Cell>
                      <Badge variant="outline">{investigation.findings_count}</Badge>
                    </Table.Cell>
                    <Table.Cell fontSize="sm" color="gray.500">
                      {formatDate(investigation.created_at)}
                    </Table.Cell>
                    <Table.Cell>
                      <Flex gap={2}>
                        <Button size="sm" variant="ghost">
                          View
                        </Button>
                        {investigation.status === 'pending' && (
                          <Button
                            size="sm"
                            colorPalette="teal"
                            variant="outline"
                            onClick={(e) => {
                              e.stopPropagation()
                              startMutation.mutate(investigation.id)
                            }}
                            loading={startMutation.isPending}
                          >
                            <FiPlay />
                            Start
                          </Button>
                        )}
                      </Flex>
                    </Table.Cell>
                  </Table.Row>
                ))}
              </Table.Body>
            </Table.Root>
          )}
        </Card.Body>
      </Card.Root>

      {/* Agent Workflow Info */}
      <Card.Root mt={6}>
        <Card.Header>
          <Heading size="md">Multi-Agent Investigation Workflow</Heading>
        </Card.Header>
        <Card.Body>
          <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} gap={4}>
            <Box p={4} bg="blue.50" borderRadius="md">
              <Text fontWeight="bold" color="blue.700">
                1. KYC Agent
              </Text>
              <Text fontSize="sm" color="blue.600">
                Identity verification and document checking
              </Text>
            </Box>
            <Box p={4} bg="orange.50" borderRadius="md">
              <Text fontWeight="bold" color="orange.700">
                2. AML Agent
              </Text>
              <Text fontSize="sm" color="orange.600">
                Transaction analysis and pattern detection
              </Text>
            </Box>
            <Box p={4} bg="purple.50" borderRadius="md">
              <Text fontWeight="bold" color="purple.700">
                3. Relationship Agent
              </Text>
              <Text fontSize="sm" color="purple.600">
                Network analysis using Context Graph
              </Text>
            </Box>
            <Box p={4} bg="teal.50" borderRadius="md">
              <Text fontWeight="bold" color="teal.700">
                4. Compliance Agent
              </Text>
              <Text fontSize="sm" color="teal.600">
                Sanctions/PEP screening and reporting
              </Text>
            </Box>
          </SimpleGrid>
        </Card.Body>
      </Card.Root>
    </Box>
  )
}
