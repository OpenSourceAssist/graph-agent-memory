import { useQuery } from "@tanstack/react-query";
import {
  Box,
  Heading,
  Text,
  SimpleGrid,
  Card,
  Badge,
  HStack,
  Skeleton,
  Table,
  Stat,
} from "@chakra-ui/react";
import {
  LuTriangleAlert,
  LuCircleAlert,
  LuUsers,
  LuShieldAlert,
} from "react-icons/lu";
import { getCustomers, getAlertSummary, Customer } from "../../lib/api";

function RiskBadge({ level }: { level: string }) {
  const colorMap: Record<string, string> = {
    LOW: "green",
    MEDIUM: "yellow",
    HIGH: "orange",
    CRITICAL: "red",
  };
  return (
    <Badge colorPalette={colorMap[level] || "gray"} variant="solid">
      {level}
    </Badge>
  );
}

function StatSkeleton() {
  return (
    <Card.Root>
      <Card.Body>
        <Skeleton height="16px" width="80px" mb={2} />
        <Skeleton height="36px" width="60px" />
      </Card.Body>
    </Card.Root>
  );
}

export default function CustomerDashboard() {
  const { data: customers, isLoading: loadingCustomers } = useQuery({
    queryKey: ["customers"],
    queryFn: getCustomers,
  });

  const { data: alertSummary, isLoading: loadingAlerts } = useQuery({
    queryKey: ["alertSummary"],
    queryFn: getAlertSummary,
  });

  return (
    <Box>
      <Heading size="lg" mb={6}>
        Dashboard
      </Heading>

      {/* Alert Summary Stats */}
      <SimpleGrid columns={{ base: 2, md: 4 }} gap={4} mb={8}>
        {loadingAlerts ? (
          <>
            <StatSkeleton />
            <StatSkeleton />
            <StatSkeleton />
            <StatSkeleton />
          </>
        ) : (
          <>
            <Card.Root>
              <Card.Body>
                <Stat.Root>
                  <Stat.Label>
                    <HStack gap={1}>
                      <LuTriangleAlert size={14} />
                      <Text>Total Alerts</Text>
                    </HStack>
                  </Stat.Label>
                  <Stat.ValueText>{alertSummary?.total || 0}</Stat.ValueText>
                </Stat.Root>
              </Card.Body>
            </Card.Root>

            <Card.Root>
              <Card.Body>
                <Stat.Root>
                  <Stat.Label>
                    <HStack gap={1} color="red.500">
                      <LuShieldAlert size={14} />
                      <Text>Critical</Text>
                    </HStack>
                  </Stat.Label>
                  <Stat.ValueText color="red.500">
                    {alertSummary?.critical_unresolved || 0}
                  </Stat.ValueText>
                </Stat.Root>
              </Card.Body>
            </Card.Root>

            <Card.Root>
              <Card.Body>
                <Stat.Root>
                  <Stat.Label>
                    <HStack gap={1} color="orange.500">
                      <LuCircleAlert size={14} />
                      <Text>High Priority</Text>
                    </HStack>
                  </Stat.Label>
                  <Stat.ValueText color="orange.500">
                    {alertSummary?.high_unresolved || 0}
                  </Stat.ValueText>
                </Stat.Root>
              </Card.Body>
            </Card.Root>

            <Card.Root>
              <Card.Body>
                <Stat.Root>
                  <Stat.Label>
                    <HStack gap={1}>
                      <LuUsers size={14} />
                      <Text>Customers</Text>
                    </HStack>
                  </Stat.Label>
                  <Stat.ValueText>{customers?.length || 0}</Stat.ValueText>
                </Stat.Root>
              </Card.Body>
            </Card.Root>
          </>
        )}
      </SimpleGrid>

      {/* Customer List */}
      <Card.Root>
        <Card.Header>
          <Heading size="md">Customers</Heading>
        </Card.Header>
        <Card.Body>
          {loadingCustomers ? (
            <Box>
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} height="40px" mb={2} />
              ))}
            </Box>
          ) : (
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
                  <Table.Row key={customer.id} _hover={{ bg: "bg.subtle" }}>
                    <Table.Cell fontFamily="mono" fontSize="sm">
                      {customer.id}
                    </Table.Cell>
                    <Table.Cell fontWeight="medium">{customer.name}</Table.Cell>
                    <Table.Cell>
                      <Badge variant="outline">{customer.type}</Badge>
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
          )}
        </Card.Body>
      </Card.Root>
    </Box>
  );
}
