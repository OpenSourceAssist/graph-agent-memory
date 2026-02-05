import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Box,
  Heading,
  Text,
  Card,
  Badge,
  VStack,
  HStack,
  Spinner,
  Button,
  Input,
  Select,
  createListCollection,
} from '@chakra-ui/react'
import { FiPlay, FiPlus, FiClock, FiCheckCircle, FiAlertCircle } from 'react-icons/fi'
import {
  getInvestigations,
  createInvestigation,
  startInvestigation,
  getAuditTrail,
  Investigation,
} from '../../lib/api'

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { color: string; icon: React.ElementType }> = {
    pending: { color: 'gray', icon: FiClock },
    in_progress: { color: 'blue', icon: FiPlay },
    completed: { color: 'green', icon: FiCheckCircle },
    escalated: { color: 'red', icon: FiAlertCircle },
  }
  const { color } = config[status] || { color: 'gray' }

  return (
    <Badge colorPalette={color} variant="solid">
      {status.replace('_', ' ')}
    </Badge>
  )
}

function RiskBadge({ level }: { level?: string }) {
  if (!level) return null
  const colorMap: Record<string, string> = {
    LOW: 'green',
    MEDIUM: 'yellow',
    HIGH: 'orange',
    CRITICAL: 'red',
  }
  return (
    <Badge colorPalette={colorMap[level] || 'gray'} variant="solid">
      Risk: {level}
    </Badge>
  )
}

function InvestigationCard({
  investigation,
  onStart,
  isStarting,
}: {
  investigation: Investigation
  onStart: (id: string) => void
  isStarting: boolean
}) {
  const [showAuditTrail, setShowAuditTrail] = useState(false)

  const { data: auditTrail, isLoading: loadingAudit } = useQuery({
    queryKey: ['auditTrail', investigation.id],
    queryFn: () => getAuditTrail(investigation.id),
    enabled: showAuditTrail,
  })

  return (
    <Card.Root mb={4}>
      <Card.Header>
        <HStack justify="space-between">
          <VStack align="start" gap={1}>
            <HStack>
              <Text fontFamily="mono" fontSize="sm" color="gray.500">
                {investigation.id}
              </Text>
              <StatusBadge status={investigation.status} />
              <RiskBadge level={investigation.overall_risk_level} />
            </HStack>
            <Text fontWeight="medium">
              Customer: {investigation.customer_id}
            </Text>
          </VStack>
          <HStack>
            {investigation.status === 'pending' && (
              <Button
                size="sm"
                colorPalette="blue"
                onClick={() => onStart(investigation.id)}
                disabled={isStarting}
              >
                {isStarting ? <Spinner size="sm" /> : <FiPlay />}
                Start Investigation
              </Button>
            )}
          </HStack>
        </HStack>
      </Card.Header>
      <Card.Body>
        <Text color="gray.600" mb={2}>{investigation.reason}</Text>

        <HStack gap={4} fontSize="sm" color="gray.500">
          <Text>Type: {investigation.type}</Text>
          <Text>Priority: {investigation.priority}</Text>
          <Text>Created: {new Date(investigation.created_at).toLocaleString()}</Text>
        </HStack>

        {investigation.summary && (
          <Box mt={4} p={3} bg="gray.50" borderRadius="md">
            <Text fontSize="sm" fontWeight="medium" mb={2}>Summary:</Text>
            <Text fontSize="sm" whiteSpace="pre-wrap">
              {investigation.summary.slice(0, 500)}
              {investigation.summary.length > 500 && '...'}
            </Text>
          </Box>
        )}

        {investigation.agents_consulted.length > 0 && (
          <HStack mt={3} gap={1}>
            <Text fontSize="sm" color="gray.500">Agents:</Text>
            {investigation.agents_consulted.map((agent) => (
              <Badge key={agent} size="sm" variant="outline">
                {agent.replace('_agent', '')}
              </Badge>
            ))}
          </HStack>
        )}

        <Button
          size="sm"
          variant="ghost"
          mt={3}
          onClick={() => setShowAuditTrail(!showAuditTrail)}
        >
          {showAuditTrail ? 'Hide' : 'Show'} Audit Trail
        </Button>

        {showAuditTrail && (
          <Box mt={3} p={3} bg="gray.50" borderRadius="md">
            {loadingAudit ? (
              <Spinner size="sm" />
            ) : (
              <VStack align="stretch" gap={2}>
                {auditTrail?.map((entry, i) => (
                  <HStack key={i} fontSize="xs" gap={2}>
                    <Text color="gray.400" minW="150px">
                      {new Date(entry.timestamp).toLocaleString()}
                    </Text>
                    <Badge size="sm" variant="outline">
                      {entry.action}
                    </Badge>
                    {entry.agent && (
                      <Badge size="sm" colorPalette="blue">
                        {entry.agent}
                      </Badge>
                    )}
                    {entry.tool_used && (
                      <Text color="gray.600">
                        Tool: {entry.tool_used}
                      </Text>
                    )}
                  </HStack>
                ))}
              </VStack>
            )}
          </Box>
        )}
      </Card.Body>
    </Card.Root>
  )
}

export default function InvestigationPanel() {
  const [showCreate, setShowCreate] = useState(false)
  const [newInvestigation, setNewInvestigation] = useState({
    customer_id: '',
    reason: '',
    type: 'comprehensive',
    priority: 'normal',
  })
  const queryClient = useQueryClient()

  const { data: investigations, isLoading } = useQuery({
    queryKey: ['investigations'],
    queryFn: () => getInvestigations(),
  })

  const createMutation = useMutation({
    mutationFn: createInvestigation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['investigations'] })
      setShowCreate(false)
      setNewInvestigation({ customer_id: '', reason: '', type: 'comprehensive', priority: 'normal' })
    },
  })

  const startMutation = useMutation({
    mutationFn: startInvestigation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['investigations'] })
    },
  })

  const typeOptions = createListCollection({
    items: [
      { label: 'Comprehensive', value: 'comprehensive' },
      { label: 'KYC Review', value: 'kyc_review' },
      { label: 'AML Investigation', value: 'aml_investigation' },
      { label: 'Fraud Investigation', value: 'fraud_investigation' },
    ],
  })

  const priorityOptions = createListCollection({
    items: [
      { label: 'Normal', value: 'normal' },
      { label: 'High', value: 'high' },
      { label: 'Urgent', value: 'urgent' },
    ],
  })

  if (isLoading) {
    return (
      <Box textAlign="center" py={10}>
        <Spinner size="xl" />
        <Text mt={4}>Loading investigations...</Text>
      </Box>
    )
  }

  return (
    <Box>
      <HStack justify="space-between" mb={6}>
        <Heading size="lg">Investigations</Heading>
        <Button
          colorPalette="blue"
          onClick={() => setShowCreate(!showCreate)}
        >
          <FiPlus /> New Investigation
        </Button>
      </HStack>

      {showCreate && (
        <Card.Root mb={6}>
          <Card.Header>
            <Heading size="sm">Create New Investigation</Heading>
          </Card.Header>
          <Card.Body>
            <VStack gap={4} align="stretch">
              <Box>
                <Text fontSize="sm" mb={1}>Customer ID</Text>
                <Input
                  placeholder="e.g., CUST-003"
                  value={newInvestigation.customer_id}
                  onChange={(e) => setNewInvestigation({
                    ...newInvestigation,
                    customer_id: e.target.value,
                  })}
                />
              </Box>
              <Box>
                <Text fontSize="sm" mb={1}>Reason for Investigation</Text>
                <Input
                  placeholder="Describe the reason for this investigation"
                  value={newInvestigation.reason}
                  onChange={(e) => setNewInvestigation({
                    ...newInvestigation,
                    reason: e.target.value,
                  })}
                />
              </Box>
              <HStack>
                <Box flex={1}>
                  <Text fontSize="sm" mb={1}>Type</Text>
                  <Select.Root
                    collection={typeOptions}
                    value={[newInvestigation.type]}
                    onValueChange={(e) => setNewInvestigation({
                      ...newInvestigation,
                      type: e.value[0],
                    })}
                  >
                    <Select.Trigger>
                      <Select.ValueText />
                    </Select.Trigger>
                    <Select.Content>
                      {typeOptions.items.map((option) => (
                        <Select.Item key={option.value} item={option}>
                          {option.label}
                        </Select.Item>
                      ))}
                    </Select.Content>
                  </Select.Root>
                </Box>
                <Box flex={1}>
                  <Text fontSize="sm" mb={1}>Priority</Text>
                  <Select.Root
                    collection={priorityOptions}
                    value={[newInvestigation.priority]}
                    onValueChange={(e) => setNewInvestigation({
                      ...newInvestigation,
                      priority: e.value[0],
                    })}
                  >
                    <Select.Trigger>
                      <Select.ValueText />
                    </Select.Trigger>
                    <Select.Content>
                      {priorityOptions.items.map((option) => (
                        <Select.Item key={option.value} item={option}>
                          {option.label}
                        </Select.Item>
                      ))}
                    </Select.Content>
                  </Select.Root>
                </Box>
              </HStack>
              <HStack justify="flex-end">
                <Button variant="ghost" onClick={() => setShowCreate(false)}>
                  Cancel
                </Button>
                <Button
                  colorPalette="blue"
                  onClick={() => createMutation.mutate(newInvestigation)}
                  disabled={!newInvestigation.customer_id || !newInvestigation.reason || createMutation.isPending}
                >
                  {createMutation.isPending ? <Spinner size="sm" /> : 'Create'}
                </Button>
              </HStack>
            </VStack>
          </Card.Body>
        </Card.Root>
      )}

      {investigations?.length === 0 ? (
        <Card.Root>
          <Card.Body textAlign="center" py={10}>
            <Text color="gray.500">No investigations found</Text>
            <Text fontSize="sm" color="gray.400" mt={2}>
              Create a new investigation to get started
            </Text>
          </Card.Body>
        </Card.Root>
      ) : (
        investigations?.map((investigation) => (
          <InvestigationCard
            key={investigation.id}
            investigation={investigation}
            onStart={(id) => startMutation.mutate(id)}
            isStarting={startMutation.isPending}
          />
        ))
      )}
    </Box>
  )
}
