"use client";

import {
  Box,
  Stack,
  Text,
  Badge,
  Flex,
  Heading,
  Accordion,
  Span,
  Drawer,
  Portal,
  IconButton,
  useBreakpointValue,
} from "@chakra-ui/react";
import { useEffect, useState } from "react";
import {
  LuBrain,
  LuHeart,
  LuUser,
  LuBuilding,
  LuMapPin,
  LuMessageSquare,
  LuWrench,
  LuBot,
  LuSearch,
  LuGlobe,
  LuSettings,
  LuX,
} from "react-icons/lu";
import { api } from "@/lib/api";
import type { MemoryContext as MemoryContextType } from "@/lib/types";

// Agent tools configuration - matches the backend tools
const AGENT_TOOLS = {
  podcast: [
    {
      name: "search_podcast",
      description: "Search podcast transcripts for topics",
    },
    {
      name: "search_by_speaker",
      description: "Find what a specific speaker said",
    },
    { name: "search_episode", description: "Search within a specific episode" },
    { name: "list_episodes", description: "Get list of all podcast episodes" },
    { name: "list_speakers", description: "Get list of all speakers" },
    { name: "get_stats", description: "Get podcast data statistics" },
  ],
  entities: [
    {
      name: "search_entities",
      description: "Search for people, companies, topics",
    },
    {
      name: "get_entity_context",
      description: "Get detailed entity info with Wikipedia",
    },
    {
      name: "find_related_entities",
      description: "Find co-occurring entities",
    },
    { name: "get_top_entities", description: "Get most mentioned entities" },
  ],
  locations: [
    {
      name: "search_locations",
      description: "Search for locations in podcasts",
    },
    { name: "find_locations_near", description: "Find nearby locations" },
    {
      name: "get_episode_locations",
      description: "Get locations for an episode",
    },
    {
      name: "find_location_path",
      description: "Find path between locations in graph",
    },
    { name: "get_location_clusters", description: "Analyze location clusters" },
    {
      name: "calculate_distances",
      description: "Calculate distances between locations",
    },
  ],
  memory: [
    {
      name: "get_user_preferences",
      description: "Get stored user preferences",
    },
    {
      name: "find_similar_queries",
      description: "Find similar past interactions",
    },
  ],
};

interface MemoryContextPanelProps {
  threadId: string | null;
  isVisible: boolean;
  onClose?: () => void;
}

const entityTypeIcons: Record<string, React.ReactNode> = {
  PERSON: <LuUser size={12} />,
  ORGANIZATION: <LuBuilding size={12} />,
  LOCATION: <LuMapPin size={12} />,
};

export function MemoryContextPanel({
  threadId,
  isVisible,
  onClose,
}: MemoryContextPanelProps) {
  const [context, setContext] = useState<MemoryContextType | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Detect mobile viewport
  const isMobile = useBreakpointValue({ base: true, lg: false });

  useEffect(() => {
    if (!isVisible) return;

    const fetchContext = async () => {
      setIsLoading(true);
      try {
        const data = await api.memory.getContext(threadId || undefined);
        setContext(data);
      } catch {
        // Ignore errors, just don't show context
      } finally {
        setIsLoading(false);
      }
    };

    fetchContext();
  }, [threadId, isVisible]);

  if (!isVisible) return null;

  // Content to render (shared between mobile and desktop)
  const renderContent = () => (
    <Stack gap="6">
      {isLoading ? (
        <Text fontSize="sm" color="fg.muted">
          Loading...
        </Text>
      ) : !context ? (
        <Text fontSize="sm" color="fg.muted">
          No memory context available
        </Text>
      ) : (
        <>
          {/* Preferences */}
          {context.preferences.length > 0 && (
            <Stack gap="2">
              <Flex alignItems="center" gap="2">
                <LuHeart size={14} />
                <Text fontSize="sm" fontWeight="medium">
                  Preferences
                </Text>
              </Flex>
              <Stack gap="1">
                {context.preferences.slice(0, 5).map((pref) => (
                  <Box
                    key={pref.id}
                    p="2"
                    bg="bg.muted"
                    borderRadius="md"
                    fontSize="xs"
                  >
                    <Badge size="sm" mb="1">
                      {pref.category}
                    </Badge>
                    <Text>{pref.preference}</Text>
                  </Box>
                ))}
              </Stack>
            </Stack>
          )}

          {/* Entities */}
          {context.entities.length > 0 && (
            <Stack gap="2">
              <Text fontSize="sm" fontWeight="medium">
                Known Entities
              </Text>
              <Flex flexWrap="wrap" gap="1">
                {context.entities.slice(0, 10).map((entity) => (
                  <Badge
                    key={entity.id}
                    size="sm"
                    variant="subtle"
                    display="flex"
                    alignItems="center"
                    gap="1"
                  >
                    {entityTypeIcons[entity.type] || null}
                    {entity.name}
                  </Badge>
                ))}
              </Flex>
            </Stack>
          )}

          {/* Recent Messages (Episodic Memory) */}
          {context.recent_messages && context.recent_messages.length > 0 && (
            <Stack gap="2">
              <Flex alignItems="center" gap="2">
                <LuMessageSquare size={14} />
                <Text fontSize="sm" fontWeight="medium">
                  Recent Messages
                </Text>
              </Flex>
              <Stack gap="1">
                {context.recent_messages.slice(0, 5).map((msg) => (
                  <Box
                    key={msg.id}
                    p="2"
                    bg="bg.muted"
                    borderRadius="md"
                    fontSize="xs"
                  >
                    <Badge
                      size="sm"
                      mb="1"
                      colorPalette={msg.role === "user" ? "blue" : "green"}
                    >
                      {msg.role}
                    </Badge>
                    <Text>{msg.content}</Text>
                  </Box>
                ))}
              </Stack>
            </Stack>
          )}

          {/* Empty state */}
          {context.preferences.length === 0 &&
            context.entities.length === 0 &&
            (!context.recent_messages ||
              context.recent_messages.length === 0) && (
              <Text fontSize="sm" color="fg.muted" textAlign="center">
                No memories stored yet. Start chatting to build context!
              </Text>
            )}
        </>
      )}

      {/* Agent Context Accordion */}
      <Stack gap="2">
        <Flex alignItems="center" gap="2">
          <LuBot size={14} />
          <Text fontSize="sm" fontWeight="medium">
            Agent Configuration
          </Text>
        </Flex>

        <Accordion.Root collapsible size="sm">
          {/* Available Tools */}
          <Accordion.Item value="tools">
            <Accordion.ItemTrigger>
              <Flex flex="1" alignItems="center" gap="2">
                <LuWrench size={12} />
                <Span fontSize="xs">Available Tools</Span>
                <Badge size="sm" ml="auto">
                  {Object.values(AGENT_TOOLS).flat().length}
                </Badge>
              </Flex>
              <Accordion.ItemIndicator />
            </Accordion.ItemTrigger>
            <Accordion.ItemContent>
              <Stack gap="3" py="2">
                {/* Podcast Tools */}
                <Box>
                  <Flex alignItems="center" gap="1" mb="1">
                    <LuSearch size={10} />
                    <Text fontSize="xs" fontWeight="medium" color="fg.muted">
                      Podcast Search
                    </Text>
                  </Flex>
                  <Stack gap="0.5">
                    {AGENT_TOOLS.podcast.map((tool) => (
                      <Text
                        key={tool.name}
                        fontSize="xs"
                        color="fg.muted"
                        pl="3"
                      >
                        • {tool.description}
                      </Text>
                    ))}
                  </Stack>
                </Box>

                {/* Entity Tools */}
                <Box>
                  <Flex alignItems="center" gap="1" mb="1">
                    <LuUser size={10} />
                    <Text fontSize="xs" fontWeight="medium" color="fg.muted">
                      Entity Queries
                    </Text>
                  </Flex>
                  <Stack gap="0.5">
                    {AGENT_TOOLS.entities.map((tool) => (
                      <Text
                        key={tool.name}
                        fontSize="xs"
                        color="fg.muted"
                        pl="3"
                      >
                        • {tool.description}
                      </Text>
                    ))}
                  </Stack>
                </Box>

                {/* Location Tools */}
                <Box>
                  <Flex alignItems="center" gap="1" mb="1">
                    <LuGlobe size={10} />
                    <Text fontSize="xs" fontWeight="medium" color="fg.muted">
                      Location Analysis
                    </Text>
                  </Flex>
                  <Stack gap="0.5">
                    {AGENT_TOOLS.locations.map((tool) => (
                      <Text
                        key={tool.name}
                        fontSize="xs"
                        color="fg.muted"
                        pl="3"
                      >
                        • {tool.description}
                      </Text>
                    ))}
                  </Stack>
                </Box>

                {/* Memory Tools */}
                <Box>
                  <Flex alignItems="center" gap="1" mb="1">
                    <LuBrain size={10} />
                    <Text fontSize="xs" fontWeight="medium" color="fg.muted">
                      Memory & Preferences
                    </Text>
                  </Flex>
                  <Stack gap="0.5">
                    {AGENT_TOOLS.memory.map((tool) => (
                      <Text
                        key={tool.name}
                        fontSize="xs"
                        color="fg.muted"
                        pl="3"
                      >
                        • {tool.description}
                      </Text>
                    ))}
                  </Stack>
                </Box>
              </Stack>
            </Accordion.ItemContent>
          </Accordion.Item>

          {/* Agent Capabilities */}
          <Accordion.Item value="capabilities">
            <Accordion.ItemTrigger>
              <Flex flex="1" alignItems="center" gap="2">
                <LuSettings size={12} />
                <Span fontSize="xs">Agent Capabilities</Span>
              </Flex>
              <Accordion.ItemIndicator />
            </Accordion.ItemTrigger>
            <Accordion.ItemContent>
              <Stack gap="2" py="2">
                <Box p="2" bg="green.subtle" borderRadius="md">
                  <Text fontSize="xs" fontWeight="medium" color="green.700">
                    Multi-step Reasoning
                  </Text>
                  <Text fontSize="xs" color="green.600">
                    Plans and executes complex queries step by step
                  </Text>
                </Box>
                <Box p="2" bg="blue.subtle" borderRadius="md">
                  <Text fontSize="xs" fontWeight="medium" color="blue.700">
                    Conversation Memory
                  </Text>
                  <Text fontSize="xs" color="blue.600">
                    Maintains context across messages in the thread
                  </Text>
                </Box>
                <Box p="2" bg="purple.subtle" borderRadius="md">
                  <Text fontSize="xs" fontWeight="medium" color="purple.700">
                    Preference Learning
                  </Text>
                  <Text fontSize="xs" color="purple.600">
                    Adapts responses based on your stored preferences
                  </Text>
                </Box>
                <Box p="2" bg="orange.subtle" borderRadius="md">
                  <Text fontSize="xs" fontWeight="medium" color="orange.700">
                    Knowledge Graph
                  </Text>
                  <Text fontSize="xs" color="orange.600">
                    Queries entities and relationships in Neo4j
                  </Text>
                </Box>
              </Stack>
            </Accordion.ItemContent>
          </Accordion.Item>
        </Accordion.Root>
      </Stack>
    </Stack>
  );

  // Mobile: Bottom sheet drawer
  if (isMobile) {
    return (
      <Drawer.Root
        open={isVisible}
        onOpenChange={(e) => !e.open && onClose?.()}
        placement="bottom"
      >
        <Portal>
          <Drawer.Backdrop />
          <Drawer.Positioner>
            <Drawer.Content borderTopRadius="xl" maxH="70vh">
              <Drawer.Header borderBottomWidth="1px" py="3">
                <Flex
                  alignItems="center"
                  justifyContent="space-between"
                  w="full"
                >
                  <Flex alignItems="center" gap="2">
                    <LuBrain size={20} />
                    <Heading size="sm">Memory Context</Heading>
                  </Flex>
                  <IconButton
                    aria-label="Close"
                    variant="ghost"
                    size="sm"
                    onClick={() => onClose?.()}
                  >
                    <LuX />
                  </IconButton>
                </Flex>
              </Drawer.Header>
              <Drawer.Body overflowY="auto" py="4">
                {renderContent()}
              </Drawer.Body>
            </Drawer.Content>
          </Drawer.Positioner>
        </Portal>
      </Drawer.Root>
    );
  }

  // Desktop: Side panel
  return (
    <Box
      w="280px"
      borderLeftWidth="1px"
      borderColor="border.subtle"
      bg="bg.panel"
      p="4"
      overflowY="auto"
      hideBelow="lg"
    >
      {/* Header */}
      <Flex alignItems="center" gap="2" mb="6">
        <LuBrain size={20} />
        <Heading size="sm">Memory Context</Heading>
      </Flex>
      {renderContent()}
    </Box>
  );
}
