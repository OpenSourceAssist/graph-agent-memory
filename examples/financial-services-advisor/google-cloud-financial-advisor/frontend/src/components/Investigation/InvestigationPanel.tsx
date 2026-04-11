import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
  Skeleton,
  Timeline,
  Collapsible,
  EmptyState,
  createListCollection,
} from "@chakra-ui/react";
import {
  LuPlay,
  LuPlus,
  LuClock,
  LuChevronDown,
  LuChevronRight,
  LuWrench,
  LuBot,
  LuSearch,
} from "react-icons/lu";
import {
  getInvestigations,
  createInvestigation,
  startInvestigation,
  getAuditTrail,
  Investigation,
} from "../../lib/api";

function StatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    pending: "gray",
    in_progress: "blue",
    completed: "green",
    escalated: "red",
  };
  return (
    <Badge colorPalette={colorMap[status] || "gray"} variant="solid">
      {status.replace("_", " ")}
    </Badge>
  );
}

function RiskBadge({ level }: { level?: string }) {
  if (!level) return null;
  const colorMap: Record<string, string> = {
    LOW: "green",
    MEDIUM: "yellow",
    HIGH: "orange",
    CRITICAL: "red",
  };
  return (
    <Badge colorPalette={colorMap[level] || "gray"} variant="solid">
      Risk: {level}
    </Badge>
  );
}

function InvestigationCard({
  investigation,
  onStart,
  isStarting,
}: {
  investigation: Investigation;
  onStart: (id: string) => void;
  isStarting: boolean;
}) {
  const [showAuditTrail, setShowAuditTrail] = useState(false);

  const { data: auditTrail, isLoading: loadingAudit } = useQuery({
    queryKey: ["auditTrail", investigation.id],
    queryFn: () => getAuditTrail(investigation.id),
    enabled: showAuditTrail,
  });

  return (
    <Card.Root mb={3} _hover={{ shadow: "sm" }} transition="shadow 0.15s">
      <Card.Header py={3}>
        <HStack justify="space-between">
          <VStack align="start" gap={1}>
            <HStack>
              <Text fontFamily="mono" fontSize="sm" color="fg.muted">
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
            {investigation.status === "pending" && (
              <Button
                size="sm"
                colorPalette="blue"
                onClick={() => onStart(investigation.id)}
                disabled={isStarting}
              >
                {isStarting ? <Spinner size="sm" /> : <LuPlay size={14} />}
                Start
              </Button>
            )}
          </HStack>
        </HStack>
      </Card.Header>
      <Card.Body pt={0}>
        <Text color="fg.muted" mb={2}>
          {investigation.reason}
        </Text>

        <HStack gap={4} fontSize="sm" color="fg.muted">
          <Text>Type: {investigation.type}</Text>
          <Text>Priority: {investigation.priority}</Text>
          <Text>
            Created: {new Date(investigation.created_at).toLocaleString()}
          </Text>
        </HStack>

        {investigation.summary && (
          <Box mt={4} p={3} bg="bg.subtle" borderRadius="md">
            <Text fontSize="sm" fontWeight="medium" mb={2}>
              Summary:
            </Text>
            <Text fontSize="sm" whiteSpace="pre-wrap">
              {investigation.summary.slice(0, 500)}
              {investigation.summary.length > 500 && "..."}
            </Text>
          </Box>
        )}

        {investigation.agents_consulted.length > 0 && (
          <HStack mt={3} gap={1}>
            <Text fontSize="sm" color="fg.muted">
              Agents:
            </Text>
            {investigation.agents_consulted.map((agent) => (
              <Badge key={agent} size="sm" variant="outline">
                {agent.replace("_agent", "")}
              </Badge>
            ))}
          </HStack>
        )}

        {/* Audit trail with Timeline component */}
        <Box mt={3}>
          <HStack
            gap={1}
            cursor="pointer"
            onClick={() => setShowAuditTrail(!showAuditTrail)}
            color="fg.muted"
            _hover={{ color: "blue.500" }}
            transition="color 0.15s"
          >
            {showAuditTrail ? (
              <LuChevronDown size={14} />
            ) : (
              <LuChevronRight size={14} />
            )}
            <Text fontSize="sm" fontWeight="medium">
              Audit Trail
            </Text>
          </HStack>

          <Collapsible.Root open={showAuditTrail}>
            <Collapsible.Content>
              <Box mt={2} ml={2}>
                {loadingAudit ? (
                  <VStack gap={2} align="stretch">
                    {[1, 2, 3].map((i) => (
                      <Skeleton key={i} height="24px" />
                    ))}
                  </VStack>
                ) : auditTrail && auditTrail.length > 0 ? (
                  <Timeline.Root size="sm" variant="outline">
                    {auditTrail.map((entry, i) => (
                      <Timeline.Item key={i}>
                        <Timeline.Connector>
                          <Timeline.Separator />
                          <Timeline.Indicator>
                            {entry.tool_used ? (
                              <LuWrench size={10} />
                            ) : entry.agent ? (
                              <LuBot size={10} />
                            ) : (
                              <LuClock size={10} />
                            )}
                          </Timeline.Indicator>
                        </Timeline.Connector>
                        <Timeline.Content>
                          <Timeline.Title>
                            <HStack gap={2}>
                              <Badge size="sm" variant="outline">
                                {entry.action}
                              </Badge>
                              {entry.agent && (
                                <Badge
                                  size="sm"
                                  colorPalette="blue"
                                  variant="subtle"
                                >
                                  {entry.agent}
                                </Badge>
                              )}
                            </HStack>
                          </Timeline.Title>
                          <Timeline.Description>
                            <HStack gap={2}>
                              <Text fontSize="xs" color="fg.subtle">
                                {new Date(entry.timestamp).toLocaleString()}
                              </Text>
                              {entry.tool_used && (
                                <Text fontSize="xs" color="fg.muted">
                                  Tool: {entry.tool_used}
                                </Text>
                              )}
                            </HStack>
                          </Timeline.Description>
                        </Timeline.Content>
                      </Timeline.Item>
                    ))}
                  </Timeline.Root>
                ) : (
                  <Text fontSize="sm" color="fg.muted">
                    No audit trail entries
                  </Text>
                )}
              </Box>
            </Collapsible.Content>
          </Collapsible.Root>
        </Box>
      </Card.Body>
    </Card.Root>
  );
}

export default function InvestigationPanel() {
  const [showCreate, setShowCreate] = useState(false);
  const [newInvestigation, setNewInvestigation] = useState({
    customer_id: "",
    reason: "",
    type: "comprehensive",
    priority: "normal",
  });
  const queryClient = useQueryClient();

  const { data: investigations, isLoading } = useQuery({
    queryKey: ["investigations"],
    queryFn: () => getInvestigations(),
  });

  const createMutation = useMutation({
    mutationFn: createInvestigation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investigations"] });
      setShowCreate(false);
      setNewInvestigation({
        customer_id: "",
        reason: "",
        type: "comprehensive",
        priority: "normal",
      });
    },
  });

  const startMutation = useMutation({
    mutationFn: startInvestigation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["investigations"] });
    },
  });

  const typeOptions = createListCollection({
    items: [
      { label: "Comprehensive", value: "comprehensive" },
      { label: "KYC Review", value: "kyc_review" },
      { label: "AML Investigation", value: "aml_investigation" },
      { label: "Fraud Investigation", value: "fraud_investigation" },
    ],
  });

  const priorityOptions = createListCollection({
    items: [
      { label: "Normal", value: "normal" },
      { label: "High", value: "high" },
      { label: "Urgent", value: "urgent" },
    ],
  });

  return (
    <Box>
      <HStack justify="space-between" mb={6}>
        <Heading size="lg">Investigations</Heading>
        <Button colorPalette="blue" onClick={() => setShowCreate(!showCreate)}>
          <LuPlus size={16} /> New Investigation
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
                <Text fontSize="sm" mb={1}>
                  Customer ID
                </Text>
                <Input
                  placeholder="e.g., CUST-003"
                  value={newInvestigation.customer_id}
                  onChange={(e) =>
                    setNewInvestigation({
                      ...newInvestigation,
                      customer_id: e.target.value,
                    })
                  }
                />
              </Box>
              <Box>
                <Text fontSize="sm" mb={1}>
                  Reason for Investigation
                </Text>
                <Input
                  placeholder="Describe the reason for this investigation"
                  value={newInvestigation.reason}
                  onChange={(e) =>
                    setNewInvestigation({
                      ...newInvestigation,
                      reason: e.target.value,
                    })
                  }
                />
              </Box>
              <HStack>
                <Box flex={1}>
                  <Text fontSize="sm" mb={1}>
                    Type
                  </Text>
                  <Select.Root
                    collection={typeOptions}
                    value={[newInvestigation.type]}
                    onValueChange={(e) =>
                      setNewInvestigation({
                        ...newInvestigation,
                        type: e.value[0],
                      })
                    }
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
                  <Text fontSize="sm" mb={1}>
                    Priority
                  </Text>
                  <Select.Root
                    collection={priorityOptions}
                    value={[newInvestigation.priority]}
                    onValueChange={(e) =>
                      setNewInvestigation({
                        ...newInvestigation,
                        priority: e.value[0],
                      })
                    }
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
                  disabled={
                    !newInvestigation.customer_id ||
                    !newInvestigation.reason ||
                    createMutation.isPending
                  }
                >
                  {createMutation.isPending ? <Spinner size="sm" /> : "Create"}
                </Button>
              </HStack>
            </VStack>
          </Card.Body>
        </Card.Root>
      )}

      {isLoading ? (
        <VStack gap={3} align="stretch">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} height="140px" borderRadius="md" />
          ))}
        </VStack>
      ) : investigations?.length === 0 ? (
        <Card.Root>
          <Card.Body py={10}>
            <EmptyState.Root>
              <EmptyState.Content>
                <EmptyState.Indicator>
                  <LuSearch />
                </EmptyState.Indicator>
                <EmptyState.Title>No investigations found</EmptyState.Title>
                <EmptyState.Description>
                  Create a new investigation to get started
                </EmptyState.Description>
              </EmptyState.Content>
            </EmptyState.Root>
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
  );
}
