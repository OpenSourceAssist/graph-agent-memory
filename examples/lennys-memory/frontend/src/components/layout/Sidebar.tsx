"use client";

import {
  Box,
  Stack,
  Text,
  Button,
  IconButton,
  Flex,
  Heading,
} from "@chakra-ui/react";
import { LuPlus, LuTrash2, LuMessageSquare, LuBrain } from "react-icons/lu";
import type { Thread } from "@/lib/types";

interface SidebarProps {
  threads: Thread[];
  activeThreadId: string | null;
  onSelectThread: (id: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (id: string) => void;
  memoryEnabled: boolean;
  onToggleMemory: (enabled: boolean) => void;
}

export function Sidebar({
  threads,
  activeThreadId,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
  memoryEnabled,
  onToggleMemory,
}: SidebarProps) {
  return (
    <Stack h="full" p="4" gap="4">
      {/* Header */}
      <Flex alignItems="center" gap="2">
        <LuMessageSquare size={20} />
        <Heading size="sm" fontWeight="semibold">
          Conversations
        </Heading>
      </Flex>

      {/* New conversation button */}
      <Button
        w="full"
        size="sm"
        variant="outline"
        onClick={() => onCreateThread()}
      >
        <LuPlus />
        New Conversation
      </Button>

      {/* Memory toggle */}
      <Flex
        alignItems="center"
        gap="2"
        px="3"
        py="2"
        bg={memoryEnabled ? "green.subtle" : "bg.muted"}
        borderRadius="md"
        cursor="pointer"
        onClick={() => onToggleMemory(!memoryEnabled)}
      >
        <LuBrain size={16} />
        <Text fontSize="sm" flex="1">
          Memory
        </Text>
        <Box
          w="8"
          h="4"
          bg={memoryEnabled ? "green.solid" : "gray.300"}
          borderRadius="full"
          position="relative"
          transition="background 0.2s"
        >
          <Box
            position="absolute"
            top="2px"
            left={memoryEnabled ? "18px" : "2px"}
            w="3"
            h="3"
            bg="white"
            borderRadius="full"
            transition="left 0.2s"
          />
        </Box>
      </Flex>

      {/* Thread list */}
      <Stack flex="1" gap="1" overflowY="auto">
        {threads.length === 0 ? (
          <Text fontSize="sm" color="fg.muted" textAlign="center" py="8">
            No conversations yet
          </Text>
        ) : (
          threads.map((thread) => (
            <Flex
              key={thread.id}
              px="3"
              py="2"
              bg={
                activeThreadId === thread.id ? "bg.emphasized" : "transparent"
              }
              borderRadius="md"
              cursor="pointer"
              _hover={{ bg: "bg.muted" }}
              onClick={() => onSelectThread(thread.id)}
              alignItems="center"
              gap="2"
            >
              <Text
                flex="1"
                fontSize="sm"
                truncate
                color={activeThreadId === thread.id ? "fg.default" : "fg.muted"}
              >
                {thread.title}
              </Text>
              <IconButton
                aria-label="Delete thread"
                variant="ghost"
                size="xs"
                onClick={(e) => {
                  e.stopPropagation();
                  onDeleteThread(thread.id);
                }}
                opacity={0}
                _groupHover={{ opacity: 1 }}
              >
                <LuTrash2 size={14} />
              </IconButton>
            </Flex>
          ))
        )}
      </Stack>
    </Stack>
  );
}
