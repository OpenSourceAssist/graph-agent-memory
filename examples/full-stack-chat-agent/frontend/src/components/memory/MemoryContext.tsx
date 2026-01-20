"use client";

import { Box, Stack, Text, Badge, Flex, Heading } from "@chakra-ui/react";
import { useEffect, useState } from "react";
import {
  LuBrain,
  LuHeart,
  LuUser,
  LuBuilding,
  LuMapPin,
  LuMessageSquare,
} from "react-icons/lu";
import { api } from "@/lib/api";
import type { MemoryContext as MemoryContextType } from "@/lib/types";

interface MemoryContextPanelProps {
  threadId: string | null;
  isVisible: boolean;
}

const entityTypeIcons: Record<string, React.ReactNode> = {
  PERSON: <LuUser size={12} />,
  ORGANIZATION: <LuBuilding size={12} />,
  LOCATION: <LuMapPin size={12} />,
};

export function MemoryContextPanel({
  threadId,
  isVisible,
}: MemoryContextPanelProps) {
  const [context, setContext] = useState<MemoryContextType | null>(null);
  const [isLoading, setIsLoading] = useState(false);

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

  return (
    <Box
      w="280px"
      borderLeftWidth="1px"
      borderColor="border.subtle"
      bg="bg.panel"
      p="4"
      overflowY="auto"
    >
      <Stack gap="6">
        {/* Header */}
        <Flex alignItems="center" gap="2">
          <LuBrain size={20} />
          <Heading size="sm">Memory Context</Heading>
        </Flex>

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
      </Stack>
    </Box>
  );
}
