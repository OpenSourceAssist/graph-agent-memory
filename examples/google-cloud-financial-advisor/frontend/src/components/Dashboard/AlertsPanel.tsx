import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Box,
  Heading,
  Text,
  Card,
  Badge,
  VStack,
  HStack,
  Skeleton,
  Select,
  createListCollection,
  EmptyState,
} from "@chakra-ui/react";
import { useState } from "react";
import { LuTriangleAlert } from "react-icons/lu";
import { getAlerts, updateAlert, Alert } from "../../lib/api";

function SeverityBadge({ severity }: { severity: string }) {
  const colorMap: Record<string, string> = {
    LOW: "green",
    MEDIUM: "yellow",
    HIGH: "orange",
    CRITICAL: "red",
  };
  return (
    <Badge colorPalette={colorMap[severity] || "gray"} variant="solid">
      {severity}
    </Badge>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colorMap: Record<string, string> = {
    new: "blue",
    acknowledged: "purple",
    investigating: "orange",
    resolved: "green",
    false_positive: "gray",
  };
  return (
    <Badge colorPalette={colorMap[status] || "gray"} variant="outline">
      {status.replace("_", " ")}
    </Badge>
  );
}

function AlertCard({
  alert,
  onStatusChange,
}: {
  alert: Alert;
  onStatusChange: (id: string, status: string) => void;
}) {
  const statusOptions = createListCollection({
    items: [
      { label: "New", value: "new" },
      { label: "Acknowledged", value: "acknowledged" },
      { label: "Investigating", value: "investigating" },
      { label: "Resolved", value: "resolved" },
      { label: "False Positive", value: "false_positive" },
    ],
  });

  return (
    <Card.Root mb={3} _hover={{ shadow: "sm" }} transition="shadow 0.15s">
      <Card.Header py={3}>
        <HStack justify="space-between">
          <VStack align="start" gap={1}>
            <HStack>
              <SeverityBadge severity={alert.severity} />
              <Badge variant="outline">{alert.type}</Badge>
              <StatusBadge status={alert.status} />
            </HStack>
            <Heading size="sm">{alert.title}</Heading>
          </VStack>
          {alert.requires_sar && (
            <Badge colorPalette="red" variant="solid">
              SAR Required
            </Badge>
          )}
        </HStack>
      </Card.Header>
      <Card.Body pt={0}>
        <Text color="fg.muted" mb={3}>
          {alert.description}
        </Text>

        <Text fontSize="sm" color="fg.muted" mb={2}>
          Customer:{" "}
          <Text as="span" fontWeight="medium" color="fg">
            {alert.customer_name || alert.customer_id}
          </Text>
        </Text>

        {alert.evidence.length > 0 && (
          <Box mt={3} p={2} bg="bg.subtle" borderRadius="md">
            <Text fontSize="sm" fontWeight="medium" mb={1}>
              Evidence:
            </Text>
            <VStack align="start" gap={1}>
              {alert.evidence.slice(0, 3).map((ev, i) => (
                <Text key={i} fontSize="xs" color="fg.muted">
                  {ev}
                </Text>
              ))}
              {alert.evidence.length > 3 && (
                <Text fontSize="xs" color="fg.subtle">
                  +{alert.evidence.length - 3} more...
                </Text>
              )}
            </VStack>
          </Box>
        )}

        <HStack mt={4} justify="space-between">
          <Text fontSize="xs" color="fg.subtle">
            {new Date(alert.created_at).toLocaleString()}
          </Text>
          <Select.Root
            collection={statusOptions}
            size="sm"
            width="150px"
            value={[alert.status]}
            onValueChange={(e) => onStatusChange(alert.id, e.value[0])}
          >
            <Select.Trigger>
              <Select.ValueText placeholder="Change status" />
            </Select.Trigger>
            <Select.Content>
              {statusOptions.items.map((option) => (
                <Select.Item key={option.value} item={option}>
                  {option.label}
                </Select.Item>
              ))}
            </Select.Content>
          </Select.Root>
        </HStack>
      </Card.Body>
    </Card.Root>
  );
}

export default function AlertsPanel() {
  const [severityFilter, setSeverityFilter] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const queryClient = useQueryClient();

  const { data: alerts, isLoading } = useQuery({
    queryKey: ["alerts", severityFilter, statusFilter],
    queryFn: () =>
      getAlerts({ severity: severityFilter, status: statusFilter }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      updateAlert(id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      queryClient.invalidateQueries({ queryKey: ["alertSummary"] });
    },
  });

  const handleStatusChange = (id: string, status: string) => {
    updateMutation.mutate({ id, status });
  };

  const severityOptions = createListCollection({
    items: [
      { label: "All Severities", value: "" },
      { label: "Critical", value: "CRITICAL" },
      { label: "High", value: "HIGH" },
      { label: "Medium", value: "MEDIUM" },
      { label: "Low", value: "LOW" },
    ],
  });

  const statusOptions = createListCollection({
    items: [
      { label: "All Statuses", value: "" },
      { label: "New", value: "new" },
      { label: "Acknowledged", value: "acknowledged" },
      { label: "Investigating", value: "investigating" },
      { label: "Resolved", value: "resolved" },
    ],
  });

  return (
    <Box>
      <HStack justify="space-between" mb={6}>
        <Heading size="lg">Alerts</Heading>
        <HStack>
          <Select.Root
            collection={severityOptions}
            size="sm"
            width="150px"
            value={severityFilter ? [severityFilter] : []}
            onValueChange={(e) => setSeverityFilter(e.value[0] || undefined)}
          >
            <Select.Trigger>
              <Select.ValueText placeholder="Severity" />
            </Select.Trigger>
            <Select.Content>
              {severityOptions.items.map((option) => (
                <Select.Item key={option.value} item={option}>
                  {option.label}
                </Select.Item>
              ))}
            </Select.Content>
          </Select.Root>
          <Select.Root
            collection={statusOptions}
            size="sm"
            width="150px"
            value={statusFilter ? [statusFilter] : []}
            onValueChange={(e) => setStatusFilter(e.value[0] || undefined)}
          >
            <Select.Trigger>
              <Select.ValueText placeholder="Status" />
            </Select.Trigger>
            <Select.Content>
              {statusOptions.items.map((option) => (
                <Select.Item key={option.value} item={option}>
                  {option.label}
                </Select.Item>
              ))}
            </Select.Content>
          </Select.Root>
        </HStack>
      </HStack>

      {isLoading ? (
        <VStack gap={3} align="stretch">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} height="120px" borderRadius="md" />
          ))}
        </VStack>
      ) : alerts?.length === 0 ? (
        <Card.Root>
          <Card.Body py={10}>
            <EmptyState.Root>
              <EmptyState.Content>
                <EmptyState.Indicator>
                  <LuTriangleAlert />
                </EmptyState.Indicator>
                <EmptyState.Title>No alerts found</EmptyState.Title>
                <EmptyState.Description>
                  Adjust your filters or check back later
                </EmptyState.Description>
              </EmptyState.Content>
            </EmptyState.Root>
          </Card.Body>
        </Card.Root>
      ) : (
        alerts?.map((alert) => (
          <AlertCard
            key={alert.id}
            alert={alert}
            onStatusChange={handleStatusChange}
          />
        ))
      )}
    </Box>
  );
}
