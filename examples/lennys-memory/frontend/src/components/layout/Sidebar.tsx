"use client";

import {
  Box,
  Stack,
  Text,
  Button,
  IconButton,
  Flex,
  Heading,
  Link,
  Separator,
} from "@chakra-ui/react";
import {
  LuPlus,
  LuTrash2,
  LuMessageSquare,
  LuBrain,
  LuGithub,
  LuExternalLink,
  LuDatabase,
} from "react-icons/lu";
import type { Thread } from "@/lib/types";

interface SidebarProps {
  threads: Thread[];
  activeThreadId: string | null;
  onSelectThread: (id: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (id: string) => void;
  memoryEnabled: boolean;
  onToggleMemory: (enabled: boolean) => void;
  onThreadSelect?: () => void; // Called after selecting a thread (for mobile drawer close)
}

export function Sidebar({
  threads,
  activeThreadId,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
  memoryEnabled,
  onToggleMemory,
  onThreadSelect,
}: SidebarProps) {
  const handleSelectThread = (id: string) => {
    onSelectThread(id);
    onThreadSelect?.();
  };

  const handleCreateThread = () => {
    onCreateThread();
    onThreadSelect?.();
  };

  return (
    <Stack h="full" p={{ base: 3, md: 4 }} gap={{ base: 3, md: 4 }}>
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
        onClick={handleCreateThread}
        minH={{ base: "44px", md: "auto" }}
      >
        <LuPlus />
        New Conversation
      </Button>

      {/* Memory toggle */}
      <Flex
        alignItems="center"
        gap="2"
        px="3"
        py={{ base: 3, md: 2 }}
        minH={{ base: "44px", md: "auto" }}
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
              py={{ base: 3, md: 2 }}
              minH={{ base: "44px", md: "auto" }}
              bg={
                activeThreadId === thread.id ? "bg.emphasized" : "transparent"
              }
              borderRadius="md"
              cursor="pointer"
              _hover={{ bg: "bg.muted" }}
              _active={{ bg: "bg.emphasized" }}
              onClick={() => handleSelectThread(thread.id)}
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

      {/* Branding footer */}
      <Stack gap={{ base: 2, md: 3 }} pt="2">
        <Separator />

        {/* Powered by section */}
        <Stack gap={{ base: 1.5, md: 2 }}>
          <Text fontSize="xs" color="fg.muted" fontWeight="medium">
            Powered by
          </Text>

          <Link
            href="https://github.com/neo4j-labs/agent-memory"
            target="_blank"
            rel="noopener noreferrer"
            _hover={{ textDecoration: "none" }}
          >
            <Flex
              px="3"
              py={{ base: 2.5, md: 2 }}
              minH={{ base: "44px", md: "auto" }}
              bg="blue.subtle"
              borderRadius="md"
              alignItems="center"
              gap="2"
              _hover={{ bg: "blue.100" }}
              _active={{ bg: "blue.200" }}
              transition="background 0.2s"
            >
              <LuDatabase size={16} color="var(--chakra-colors-blue-600)" />
              <Text fontSize="sm" fontWeight="medium" color="blue.700" flex="1">
                @neo4j-labs/agent-memory
              </Text>
              <LuExternalLink size={12} color="var(--chakra-colors-blue-500)" />
            </Flex>
          </Link>

          <Flex gap="2">
            <Link
              href="https://neo4j.com"
              target="_blank"
              rel="noopener noreferrer"
              flex="1"
              _hover={{ textDecoration: "none" }}
            >
              <Flex
                px="2"
                py={{ base: 2, md: 1.5 }}
                minH={{ base: "40px", md: "auto" }}
                bg="bg.muted"
                borderRadius="md"
                alignItems="center"
                justifyContent="center"
                gap="1"
                _hover={{ bg: "bg.emphasized" }}
                _active={{ bg: "bg.subtle" }}
                transition="background 0.2s"
              >
                <Text fontSize="xs" color="fg.muted">
                  Neo4j
                </Text>
              </Flex>
            </Link>

            <Link
              href="https://www.lennysnewsletter.com/podcast"
              target="_blank"
              rel="noopener noreferrer"
              flex="1"
              _hover={{ textDecoration: "none" }}
            >
              <Flex
                px="2"
                py={{ base: 2, md: 1.5 }}
                minH={{ base: "40px", md: "auto" }}
                bg="bg.muted"
                borderRadius="md"
                alignItems="center"
                justifyContent="center"
                gap="1"
                _hover={{ bg: "bg.emphasized" }}
                _active={{ bg: "bg.subtle" }}
                transition="background 0.2s"
              >
                <Text fontSize="xs" color="fg.muted">
                  Lenny's Podcast
                </Text>
              </Flex>
            </Link>
          </Flex>
        </Stack>

        {/* GitHub link */}
        <Link
          href="https://github.com/neo4j-labs/agent-memory/tree/main/neo4j-agent-memory/examples/lennys-memory"
          target="_blank"
          rel="noopener noreferrer"
          _hover={{ textDecoration: "none" }}
        >
          <Flex
            px="3"
            py={{ base: 2.5, md: 2 }}
            minH={{ base: "44px", md: "auto" }}
            bg="bg.muted"
            borderRadius="md"
            alignItems="center"
            gap="2"
            _hover={{ bg: "bg.emphasized" }}
            _active={{ bg: "bg.subtle" }}
            transition="background 0.2s"
          >
            <LuGithub size={16} />
            <Text fontSize="xs" color="fg.muted" flex="1">
              View source on GitHub
            </Text>
            <LuExternalLink size={12} />
          </Flex>
        </Link>
      </Stack>
    </Stack>
  );
}
