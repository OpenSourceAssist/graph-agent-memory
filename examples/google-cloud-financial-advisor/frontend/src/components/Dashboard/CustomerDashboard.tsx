import { useQuery } from '@tanstack/react-query'
import {
  Box,
  Heading,
  Text,
  SimpleGrid,
  Card,
  Badge,
  VStack,
  HStack,
  Spinner,
  Table,
} from '@chakra-ui/react'
import { getCustomers, getAlertSummary, Customer, AlertSummary } from '../../lib/api'

function RiskBadge({ level }: { level: string }) {
  const colorMap: Record<string, string> = {
    LOW: 'green',
    MEDIUM: 'yellow',
    HIGH: 'orange',
    CRITICAL: 'red',
  }
  return (
    <Badge colorPalette={colorMap[level] || 'gray'} variant="solid">
      {level}
    </Badge>
  )
}

function StatCard({ label, value, color }: { label: string; value: number; color?: string }) {
  return (
    <Card.Root>
      <Card.Body>
        <Text color="gray.500" fontSize="sm">{label}</Text>
        <Text fontSize="3xl" fontWeight="bold" color={color || 'gray.800'}>
          {value}
        </Text>
      </Card.Body>
    </Card.Root>
  )
}

export default function CustomerDashboard() {
  const { data: customers, isLoading: loadingCustomers } = useQuery({
    queryKey: ['customers'],
    queryFn: getCustomers,
  })

  const { data: alertSummary, isLoading: loadingAlerts } = useQuery({
    queryKey: ['alertSummary'],
    queryFn: getAlertSummary,
  })

  if (loadingCustomers || loadingAlerts) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" />
        <Text mt={4}>Loading dashboard...</Text>
      </Box>
    )
  }

  return (
    <Box>
      <Heading size="lg" mb={6}>Dashboard</Heading>

      {/* Alert Summary */}
      <SimpleGrid columns={{ base: 2, md: 4 }} gap={4} mb={8}>
        <StatCard
          label="Total Alerts"
          value={alertSummary?.total || 0}
        />
        <StatCard
          label="Critical Unresolved"
          value={alertSummary?.critical_unresolved || 0}
          color="red.500"
        />
        <StatCard
          label="High Unresolved"
          value={alertSummary?.high_unresolved || 0}
          color="orange.500"
        />
        <StatCard
          label="Total Customers"
          value={customers?.length || 0}
        />
      </SimpleGrid>

      {/* Customer List */}
      <Card.Root>
        <Card.Header>
          <Heading size="md">Customers</Heading>
        </Card.Header>
        <Card.Body>
          <Table.Root size="sm">
            <Table.Header>
              <Table.Row>
                <Table.ColumnHeader>ID</Table.ColumnHeader>
                <Table.ColumnHeader>Name</Table.ColumnHeader>
                <Table.ColumnHeader>Type</Table.ColumnHeader>
                <Table.ColumnHeader>KYC Status</Table.ColumnHeader>
                <Table.ColumnHeader>Risk Level</Table.ColumnHeader>
                <Table.ColumnHeader>Risk Score</Table.ColumnHeader>
              </Table.Row>
            </Table.Header>
            <Table.Body>
              {customers?.map((customer: Customer) => (
                <Table.Row key={customer.id}>
                  <Table.Cell fontFamily="mono" fontSize="sm">{customer.id}</Table.Cell>
                  <Table.Cell fontWeight="medium">{customer.name}</Table.Cell>
                  <Table.Cell>
                    <Badge variant="outline">
                      {customer.type}
                    </Badge>
                  </Table.Cell>
                  <Table.Cell>{customer.kyc_status}</Table.Cell>
                  <Table.Cell>
                    <RiskBadge level={customer.risk_level} />
                  </Table.Cell>
                  <Table.Cell>{customer.risk_score}</Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table.Root>
        </Card.Body>
      </Card.Root>
    </Box>
  )
}
