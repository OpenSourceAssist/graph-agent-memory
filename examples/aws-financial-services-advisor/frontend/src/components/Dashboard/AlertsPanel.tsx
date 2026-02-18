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
} from '@chakra-ui/react'
import { useQuery } from '@tanstack/react-query'
import { FiAlertTriangle, FiClock, FiCheckCircle } from 'react-icons/fi'
import { alertApi } from '../../lib/api'

function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'red'
    case 'high':
      return 'orange'
    case 'medium':
      return 'yellow'
    case 'low':
      return 'green'
    default:
      return 'gray'
  }
}

function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'new':
      return 'blue'
    case 'under_review':
      return 'purple'
    case 'escalated':
      return 'red'
    case 'acknowledged':
      return 'teal'
    case 'closed':
      return 'gray'
    default:
      return 'gray'
  }
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function AlertsPanel() {
  const { data: alertsData, isLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => alertApi.list(),
  })

  const { data: summary } = useQuery({
    queryKey: ['alertSummary'],
    queryFn: () => alertApi.getSummary(),
  })

  const alerts = alertsData?.alerts || []

  return (
    <Box>
      <Flex justify="space-between" align="center" mb={6}>
        <Box>
          <Heading size="lg" color="gray.800">
            Alerts
          </Heading>
          <Text color="gray.500">Compliance alerts and notifications</Text>
        </Box>
      </Flex>

      {/* Summary Stats */}
      <SimpleGrid columns={{ base: 1, md: 3 }} gap={6} mb={8}>
        <Card.Root>
          <Card.Body>
            <Flex align="center">
              <Box p={3} borderRadius="full" bg="blue.100" mr={4}>
                <FiAlertTriangle size={24} color="var(--chakra-colors-blue-500)" />
              </Box>
              <Box>
                <Text color="gray.500" fontSize="sm">
                  New Alerts
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {summary?.by_status?.new || 0}
                </Text>
              </Box>
            </Flex>
          </Card.Body>
        </Card.Root>

        <Card.Root>
          <Card.Body>
            <Flex align="center">
              <Box p={3} borderRadius="full" bg="orange.100" mr={4}>
                <FiClock size={24} color="var(--chakra-colors-orange-500)" />
              </Box>
              <Box>
                <Text color="gray.500" fontSize="sm">
                  Under Review
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {summary?.by_status?.under_review || 0}
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
                  Resolved Today
                </Text>
                <Text fontSize="2xl" fontWeight="bold">
                  {summary?.by_status?.closed || 0}
                </Text>
              </Box>
            </Flex>
          </Card.Body>
        </Card.Root>
      </SimpleGrid>

      {/* Alerts Table */}
      <Card.Root>
        <Card.Header>
          <Heading size="md">All Alerts</Heading>
        </Card.Header>
        <Card.Body>
          {isLoading ? (
            <Flex justify="center" py={8}>
              <Spinner size="lg" color="teal.500" />
            </Flex>
          ) : alerts.length === 0 ? (
            <Text color="gray.500" textAlign="center" py={8}>
              No alerts found.
            </Text>
          ) : (
            <Table.Root>
              <Table.Header>
                <Table.Row>
                  <Table.ColumnHeader>ID</Table.ColumnHeader>
                  <Table.ColumnHeader>Title</Table.ColumnHeader>
                  <Table.ColumnHeader>Type</Table.ColumnHeader>
                  <Table.ColumnHeader>Severity</Table.ColumnHeader>
                  <Table.ColumnHeader>Status</Table.ColumnHeader>
                  <Table.ColumnHeader>Customer</Table.ColumnHeader>
                  <Table.ColumnHeader>Created</Table.ColumnHeader>
                  <Table.ColumnHeader>Actions</Table.ColumnHeader>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {alerts.map((alert) => (
                  <Table.Row key={alert.id}>
                    <Table.Cell fontFamily="mono" fontSize="sm">
                      {alert.id}
                    </Table.Cell>
                    <Table.Cell fontWeight="medium" maxW="200px" truncate>
                      {alert.title}
                    </Table.Cell>
                    <Table.Cell>
                      <Text fontSize="sm" textTransform="capitalize">
                        {alert.type.replace(/_/g, ' ')}
                      </Text>
                    </Table.Cell>
                    <Table.Cell>
                      <Badge colorPalette={getSeverityColor(alert.severity)}>
                        {alert.severity}
                      </Badge>
                    </Table.Cell>
                    <Table.Cell>
                      <Badge colorPalette={getStatusColor(alert.status)}>
                        {alert.status.replace(/_/g, ' ')}
                      </Badge>
                    </Table.Cell>
                    <Table.Cell fontFamily="mono" fontSize="sm">
                      {alert.customer_id}
                    </Table.Cell>
                    <Table.Cell fontSize="sm" color="gray.500">
                      {formatDate(alert.created_at)}
                    </Table.Cell>
                    <Table.Cell>
                      <Flex gap={2}>
                        <Button size="sm" variant="ghost">
                          View
                        </Button>
                        {alert.status === 'new' && (
                          <Button size="sm" colorPalette="teal" variant="outline">
                            Acknowledge
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
    </Box>
  )
}
