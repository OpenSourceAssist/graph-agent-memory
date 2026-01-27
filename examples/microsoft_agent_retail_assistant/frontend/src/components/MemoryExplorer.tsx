"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Card,
  Badge,
  Button,
  Input,
  Spinner,
  SimpleGrid,
  Tabs,
} from "@chakra-ui/react";
import { getMemoryContext, getMemoryGraph, type GraphData } from "@/lib/api";

interface MemoryExplorerProps {
  sessionId: string;
}

export function MemoryExplorer({ sessionId }: MemoryExplorerProps) {
  const [activeTab, setActiveTab] = useState("context");
  const [context, setContext] = useState<{
    short_term: Array<{
      id: string;
      role: string;
      content: string;
      timestamp?: string;
    }>;
    long_term: {
      entities: Array<{
        id: string;
        name: string;
        type: string;
        description?: string;
      }>;
      preferences: Array<{
        id: string;
        category: string;
        preference: string;
      }>;
    };
    reasoning: Array<{
      id: string;
      task: string;
      outcome: string;
      steps: number;
    }>;
  } | null>(null);
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [query, setQuery] = useState("");

  const loadContext = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getMemoryContext(sessionId, query || undefined);
      setContext(data);
    } catch (error) {
      console.error("Failed to load context:", error);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, query]);

  const loadGraph = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getMemoryGraph(sessionId);
      setGraphData(data);
    } catch (error) {
      console.error("Failed to load graph:", error);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    if (activeTab === "context") {
      loadContext();
    } else {
      loadGraph();
    }
  }, [activeTab, loadContext, loadGraph]);

  return (
    <Box>
      <HStack justify="space-between" mb={6}>
        <Heading size="lg">Memory Explorer</Heading>
        <HStack>
          <Input
            placeholder="Search query..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            width="200px"
            size="sm"
          />
          <Button
            size="sm"
            colorPalette="teal"
            onClick={activeTab === "context" ? loadContext : loadGraph}
            disabled={isLoading}
          >
            Refresh
          </Button>
        </HStack>
      </HStack>

      <Tabs.Root
        value={activeTab}
        onValueChange={(e) => setActiveTab(e.value)}
        mb={6}
      >
        <Tabs.List>
          <Tabs.Trigger value="context">Memory Context</Tabs.Trigger>
          <Tabs.Trigger value="graph">Knowledge Graph</Tabs.Trigger>
        </Tabs.List>
      </Tabs.Root>

      {isLoading ? (
        <Box textAlign="center" py={10}>
          <Spinner size="lg" color="teal.500" />
          <Text mt={4} color="gray.500">
            Loading memory data...
          </Text>
        </Box>
      ) : activeTab === "context" ? (
        <ContextView context={context} />
      ) : (
        <GraphView data={graphData} />
      )}
    </Box>
  );
}

function ContextView({
  context,
}: {
  context: {
    short_term: Array<{
      id: string;
      role: string;
      content: string;
      timestamp?: string;
    }>;
    long_term: {
      entities: Array<{
        id: string;
        name: string;
        type: string;
        description?: string;
      }>;
      preferences: Array<{
        id: string;
        category: string;
        preference: string;
      }>;
    };
    reasoning: Array<{
      id: string;
      task: string;
      outcome: string;
      steps: number;
    }>;
  } | null;
}) {
  if (!context) {
    return (
      <Card.Root>
        <Card.Body>
          <Text color="gray.500">No memory context available</Text>
        </Card.Body>
      </Card.Root>
    );
  }

  return (
    <SimpleGrid columns={{ base: 1, lg: 3 }} gap={6}>
      {/* Short-term Memory */}
      <Card.Root borderTopWidth="4px" borderTopColor="green.400">
        <Card.Header>
          <HStack>
            <Badge colorPalette="green" size="lg">
              Short-term
            </Badge>
            <Text color="gray.500" fontSize="sm">
              ({context.short_term.length} messages)
            </Text>
          </HStack>
        </Card.Header>
        <Card.Body maxH="400px" overflowY="auto">
          <VStack align="stretch" gap={2}>
            {context.short_term.length === 0 ? (
              <Text color="gray.400" fontSize="sm">
                No recent messages
              </Text>
            ) : (
              context.short_term.map((msg) => (
                <Box
                  key={msg.id}
                  p={2}
                  bg="gray.50"
                  borderRadius="md"
                  borderLeftWidth="3px"
                  borderLeftColor={
                    msg.role === "user" ? "blue.400" : "green.400"
                  }
                >
                  <Badge size="sm" colorPalette={msg.role === "user" ? "blue" : "green"}>
                    {msg.role}
                  </Badge>
                  <Text fontSize="sm" mt={1} noOfLines={3}>
                    {msg.content}
                  </Text>
                </Box>
              ))
            )}
          </VStack>
        </Card.Body>
      </Card.Root>

      {/* Long-term Memory */}
      <Card.Root borderTopWidth="4px" borderTopColor="orange.400">
        <Card.Header>
          <HStack>
            <Badge colorPalette="orange" size="lg">
              Long-term
            </Badge>
            <Text color="gray.500" fontSize="sm">
              ({context.long_term.entities.length} entities,{" "}
              {context.long_term.preferences.length} preferences)
            </Text>
          </HStack>
        </Card.Header>
        <Card.Body maxH="400px" overflowY="auto">
          <VStack align="stretch" gap={4}>
            {/* Entities */}
            <Box>
              <Text fontWeight="medium" mb={2}>
                Entities
              </Text>
              <VStack align="stretch" gap={1}>
                {context.long_term.entities.length === 0 ? (
                  <Text color="gray.400" fontSize="sm">
                    No entities yet
                  </Text>
                ) : (
                  context.long_term.entities.slice(0, 10).map((entity) => (
                    <HStack key={entity.id} p={1} bg="gray.50" borderRadius="sm">
                      <Badge size="sm">{entity.type}</Badge>
                      <Text fontSize="sm">{entity.name}</Text>
                    </HStack>
                  ))
                )}
              </VStack>
            </Box>

            {/* Preferences */}
            <Box>
              <Text fontWeight="medium" mb={2}>
                Preferences
              </Text>
              <VStack align="stretch" gap={1}>
                {context.long_term.preferences.length === 0 ? (
                  <Text color="gray.400" fontSize="sm">
                    No preferences yet
                  </Text>
                ) : (
                  context.long_term.preferences.map((pref) => (
                    <HStack key={pref.id} p={1} bg="gray.50" borderRadius="sm">
                      <Badge size="sm" colorPalette="purple">
                        {pref.category}
                      </Badge>
                      <Text fontSize="sm">{pref.preference}</Text>
                    </HStack>
                  ))
                )}
              </VStack>
            </Box>
          </VStack>
        </Card.Body>
      </Card.Root>

      {/* Reasoning Memory */}
      <Card.Root borderTopWidth="4px" borderTopColor="purple.400">
        <Card.Header>
          <HStack>
            <Badge colorPalette="purple" size="lg">
              Reasoning
            </Badge>
            <Text color="gray.500" fontSize="sm">
              ({context.reasoning.length} traces)
            </Text>
          </HStack>
        </Card.Header>
        <Card.Body maxH="400px" overflowY="auto">
          <VStack align="stretch" gap={2}>
            {context.reasoning.length === 0 ? (
              <Text color="gray.400" fontSize="sm">
                No reasoning traces yet
              </Text>
            ) : (
              context.reasoning.map((trace) => (
                <Box
                  key={trace.id}
                  p={2}
                  bg="gray.50"
                  borderRadius="md"
                  borderLeftWidth="3px"
                  borderLeftColor="purple.400"
                >
                  <Text fontSize="sm" fontWeight="medium" noOfLines={2}>
                    {trace.task}
                  </Text>
                  <HStack mt={1}>
                    <Badge
                      size="sm"
                      colorPalette={trace.outcome === "success" ? "green" : "red"}
                    >
                      {trace.outcome}
                    </Badge>
                    <Text fontSize="xs" color="gray.500">
                      {trace.steps} steps
                    </Text>
                  </HStack>
                </Box>
              ))
            )}
          </VStack>
        </Card.Body>
      </Card.Root>
    </SimpleGrid>
  );
}

function GraphView({ data }: { data: GraphData | null }) {
  const containerRef = useRef<HTMLDivElement>(null);

  if (!data || (data.nodes.length === 0 && data.edges.length === 0)) {
    return (
      <Card.Root>
        <Card.Body textAlign="center" py={10}>
          <Text color="gray.500" mb={4}>
            No graph data available yet.
          </Text>
          <Text color="gray.400" fontSize="sm">
            Start a conversation to see entities and their relationships
            visualized here.
          </Text>
        </Card.Body>
      </Card.Root>
    );
  }

  // Simple list-based visualization (force-graph would require dynamic import)
  const nodeTypes = [...new Set(data.nodes.map((n) => n.type))];
  const typeColors: Record<string, string> = {
    Entity: "teal",
    Product: "blue",
    Category: "green",
    Brand: "purple",
    Preference: "orange",
    Message: "gray",
  };

  return (
    <VStack align="stretch" gap={6}>
      {/* Stats */}
      <HStack gap={4}>
        <Card.Root flex={1}>
          <Card.Body>
            <Text fontSize="2xl" fontWeight="bold" color="teal.500">
              {data.nodes.length}
            </Text>
            <Text color="gray.500">Nodes</Text>
          </Card.Body>
        </Card.Root>
        <Card.Root flex={1}>
          <Card.Body>
            <Text fontSize="2xl" fontWeight="bold" color="purple.500">
              {data.edges.length}
            </Text>
            <Text color="gray.500">Relationships</Text>
          </Card.Body>
        </Card.Root>
        <Card.Root flex={1}>
          <Card.Body>
            <Text fontSize="2xl" fontWeight="bold" color="blue.500">
              {nodeTypes.length}
            </Text>
            <Text color="gray.500">Node Types</Text>
          </Card.Body>
        </Card.Root>
      </HStack>

      {/* Nodes by type */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4}>
        {nodeTypes.map((type) => {
          const nodesOfType = data.nodes.filter((n) => n.type === type);
          return (
            <Card.Root key={type}>
              <Card.Header>
                <HStack>
                  <Badge colorPalette={typeColors[type] || "gray"}>
                    {type}
                  </Badge>
                  <Text color="gray.500" fontSize="sm">
                    ({nodesOfType.length})
                  </Text>
                </HStack>
              </Card.Header>
              <Card.Body maxH="200px" overflowY="auto">
                <VStack align="stretch" gap={1}>
                  {nodesOfType.slice(0, 10).map((node) => (
                    <Text key={node.id} fontSize="sm" noOfLines={1}>
                      {node.label}
                    </Text>
                  ))}
                  {nodesOfType.length > 10 && (
                    <Text fontSize="sm" color="gray.400">
                      +{nodesOfType.length - 10} more
                    </Text>
                  )}
                </VStack>
              </Card.Body>
            </Card.Root>
          );
        })}
      </SimpleGrid>

      {/* Relationships */}
      <Card.Root>
        <Card.Header>
          <Heading size="sm">Relationships</Heading>
        </Card.Header>
        <Card.Body maxH="300px" overflowY="auto">
          <VStack align="stretch" gap={2}>
            {data.edges.slice(0, 20).map((edge) => {
              const sourceNode = data.nodes.find((n) => n.id === edge.source);
              const targetNode = data.nodes.find((n) => n.id === edge.target);
              return (
                <HStack key={edge.id} p={2} bg="gray.50" borderRadius="md">
                  <Text fontSize="sm" fontWeight="medium">
                    {sourceNode?.label || edge.source}
                  </Text>
                  <Badge colorPalette="purple" size="sm">
                    {edge.type}
                  </Badge>
                  <Text fontSize="sm" fontWeight="medium">
                    {targetNode?.label || edge.target}
                  </Text>
                </HStack>
              );
            })}
            {data.edges.length > 20 && (
              <Text fontSize="sm" color="gray.400" textAlign="center">
                +{data.edges.length - 20} more relationships
              </Text>
            )}
          </VStack>
        </Card.Body>
      </Card.Root>

      {/* Info box */}
      <Card.Root bg="teal.50">
        <Card.Body>
          <Heading size="sm" color="teal.700" mb={2}>
            About the Memory Graph
          </Heading>
          <Text color="teal.600" fontSize="sm">
            This graph shows entities extracted from your conversation, their
            types (products, brands, categories), and how they relate to each
            other. The assistant uses this graph to provide contextual
            recommendations and understand relationships between products.
          </Text>
        </Card.Body>
      </Card.Root>
    </VStack>
  );
}
