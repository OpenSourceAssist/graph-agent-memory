"use client";

import { Box, Flex, Text, Link, HStack, Separator } from "@chakra-ui/react";
import { Tooltip } from "@/components/ui/tooltip";
import {
  LuFlaskConical,
  LuGithub,
  LuMessageCircle,
  LuBookOpen,
} from "react-icons/lu";

/**
 * Footer component with Neo4j Labs branding and links.
 */
export function Footer() {
  return (
    <Box
      py={3}
      px={4}
      borderTopWidth="1px"
      borderColor="border.subtle"
      bg="bg.muted"
    >
      <Flex
        direction={{ base: "column", sm: "row" }}
        justify="space-between"
        align={{ base: "start", sm: "center" }}
        gap={2}
      >
        {/* Left: Labs badge and project info */}
        <Flex align="center" gap={2} fontSize="xs" color="fg.muted">
          <Box color="brand.500">
            <LuFlaskConical size={14} />
          </Box>
          <Text>
            Powered by{" "}
            <Link
              href="https://github.com/neo4j-labs/agent-memory"
              target="_blank"
              rel="noopener noreferrer"
              color="brand.fg"
              fontWeight="medium"
            >
              neo4j-agent-memory
            </Link>
          </Text>
          <Separator orientation="vertical" height="3" hideBelow="sm" />
          <Text hideBelow="sm">
            A{" "}
            <Link
              href="https://neo4j.com/labs/"
              target="_blank"
              rel="noopener noreferrer"
              color="brand.fg"
            >
              Neo4j Labs
            </Link>{" "}
            project
          </Text>
        </Flex>

        {/* Right: Links */}
        <HStack gap={4} fontSize="xs">
          <Tooltip content="GitHub" positioning={{ placement: "top" }}>
            <Link
              href="https://github.com/neo4j-labs/agent-memory"
              target="_blank"
              rel="noopener noreferrer"
              color="fg.muted"
              display="flex"
              alignItems="center"
              gap={1}
              _hover={{ color: "brand.fg" }}
              p={1}
            >
              <LuGithub size={14} />
              <Text hideBelow="sm">GitHub</Text>
            </Link>
          </Tooltip>
          <Tooltip content="Community Forum" positioning={{ placement: "top" }}>
            <Link
              href="https://community.neo4j.com"
              target="_blank"
              rel="noopener noreferrer"
              color="fg.muted"
              display="flex"
              alignItems="center"
              gap={1}
              _hover={{ color: "brand.fg" }}
              p={1}
            >
              <LuMessageCircle size={14} />
              <Text hideBelow="sm">Community</Text>
            </Link>
          </Tooltip>
          <Tooltip content="Documentation" positioning={{ placement: "top" }}>
            <Link
              href="https://github.com/neo4j-labs/agent-memory#readme"
              target="_blank"
              rel="noopener noreferrer"
              color="fg.muted"
              display="flex"
              alignItems="center"
              gap={1}
              _hover={{ color: "brand.fg" }}
              p={1}
            >
              <LuBookOpen size={14} />
              <Text hideBelow="sm">Docs</Text>
            </Link>
          </Tooltip>
        </HStack>
      </Flex>
    </Box>
  );
}
