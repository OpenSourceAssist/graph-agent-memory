import { useState } from 'react'
import {
  Box,
  Heading,
  Text,
  SimpleGrid,
  Card,
  Flex,
  Badge,
  Button,
  Input,
  Table,
  Spinner,
} from '@chakra-ui/react'
import { useQuery } from '@tanstack/react-query'
import { FiUsers, FiAlertTriangle, FiTrendingUp, FiSearch } from 'react-icons/fi'
import { customerApi, alertApi } from '../../lib/api'

interface StatCardProps {
  label: string
  value: string | number
  icon: React.ElementType
  color: string
}

function StatCard({ label, value, icon: IconComponent, color }: StatCardProps) {
  return (
    <Card.Root>
      <Card.Body>
        <Flex justify="space-between" align="center">
          <Box>
            <Text color="gray.500" fontSize="sm" fontWeight="medium">
              {label}
            </Text>
            <Text fontSize="2xl" fontWeight="bold" color="gray.800">
              {value}
            </Text>
          </Box>
          <Box p={3} borderRadius="full" bg={`${color}.100`}>
            <IconComponent size={24} color={`var(--chakra-colors-${color}-500)`} />
          </Box>
        </Flex>
      </Card.Body>
    </Card.Root>
  )
}

function getRiskBadgeColor(riskLevel: string): string {
  switch (riskLevel.toLowerCase()) {
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

export default function CustomerDashboard() {
  const [searchQuery, setSearchQuery] = useState('')

  const { data: customersData, isLoading: customersLoading } = useQuery({
    queryKey: ['customers'],
    queryFn: () => customerApi.list(),
  })

  const { data: alertSummary } = useQuery({
    queryKey: ['alertSummary'],
    queryFn: () => alertApi.getSummary(),
  })

  const customers = customersData?.customers || []
  const totalCustomers = customersData?.total || 0

  const filteredCustomers = customers.filter(
    (c) =>
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.id.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const highRiskCount = customers.filter(
    (c) => c.risk_level === 'high' || c.risk_level === 'critical'
  ).length

  return (
    <Box>
      <Flex justify="space-between" align="center" mb={6}>
        <Box>
          <Heading size="lg" color="gray.800">
            Dashboard
          </Heading>
          <Text color="gray.500">Financial compliance overview</Text>
        </Box>
        <Button colorPalette="teal">New Investigation</Button>
      </Flex>

      {/* Stats */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} gap={6} mb={8}>
        <StatCard
          label="Total Customers"
          value={totalCustomers}
          icon={FiUsers}
          color="blue"
        />
        <StatCard
          label="High Risk"
          value={highRiskCount}
          icon={FiTrendingUp}
          color="red"
        />
        <StatCard
          label="Open Alerts"
          value={alertSummary?.by_status?.new || 0}
          icon={FiAlertTriangle}
          color="orange"
        />
        <StatCard
          label="Active Investigations"
          value={alertSummary?.by_status?.under_review || 0}
          icon={FiSearch}
          color="purple"
        />
      </SimpleGrid>

      {/* Customer List */}
      <Card.Root>
        <Card.Header>
          <Flex justify="space-between" align="center">
            <Heading size="md">Customers</Heading>
            <Input
              placeholder="Search customers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              maxW="300px"
            />
          </Flex>
        </Card.Header>
        <Card.Body>
          {customersLoading ? (
            <Flex justify="center" py={8}>
              <Spinner size="lg" color="teal.500" />
            </Flex>
          ) : filteredCustomers.length === 0 ? (
            <Text color="gray.500" textAlign="center" py={8}>
              No customers found. Add customers to get started.
            </Text>
          ) : (
            <Table.Root>
              <Table.Header>
                <Table.Row>
                  <Table.ColumnHeader>ID</Table.ColumnHeader>
                  <Table.ColumnHeader>Name</Table.ColumnHeader>
                  <Table.ColumnHeader>Type</Table.ColumnHeader>
                  <Table.ColumnHeader>Jurisdiction</Table.ColumnHeader>
                  <Table.ColumnHeader>Risk Level</Table.ColumnHeader>
                  <Table.ColumnHeader>Alerts</Table.ColumnHeader>
                  <Table.ColumnHeader>Actions</Table.ColumnHeader>
                </Table.Row>
              </Table.Header>
              <Table.Body>
                {filteredCustomers.map((customer) => (
                  <Table.Row key={customer.id}>
                    <Table.Cell fontFamily="mono" fontSize="sm">
                      {customer.id}
                    </Table.Cell>
                    <Table.Cell fontWeight="medium">{customer.name}</Table.Cell>
                    <Table.Cell textTransform="capitalize">{customer.type}</Table.Cell>
                    <Table.Cell>{customer.jurisdiction}</Table.Cell>
                    <Table.Cell>
                      <Badge colorPalette={getRiskBadgeColor(customer.risk_level)}>
                        {customer.risk_level}
                      </Badge>
                    </Table.Cell>
                    <Table.Cell>
                      {customer.alerts_count > 0 ? (
                        <Badge colorPalette="red">{customer.alerts_count}</Badge>
                      ) : (
                        <Text color="gray.400">-</Text>
                      )}
                    </Table.Cell>
                    <Table.Cell>
                      <Button size="sm" variant="ghost">
                        View
                      </Button>
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
