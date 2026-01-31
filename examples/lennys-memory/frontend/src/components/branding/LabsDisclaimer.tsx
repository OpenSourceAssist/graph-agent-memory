"use client";

import { Box, Text, Link, Flex, Badge } from "@chakra-ui/react";
import {
  LuFlaskConical,
  LuMessageCircle,
  LuExternalLink,
} from "react-icons/lu";

interface LabsDisclaimerProps {
  /** Compact mode for footer placement */
  compact?: boolean;
}

/**
 * Labs disclaimer component following Neo4j Labs brand guidelines.
 * Required on all Labs projects to clarify support model.
 */
export function LabsDisclaimer({ compact = false }: LabsDisclaimerProps) {
  if (compact) {
    return (
      <Flex
        px={3}
        py={2}
        bg="brand.subtle"
        borderRadius="md"
        align="center"
        gap={2}
        fontSize="xs"
        color="fg.muted"
      >
        <LuFlaskConical size={12} />
        <Text>
          <Link
            href="https://neo4j.com/labs/"
            target="_blank"
            rel="noopener noreferrer"
            color="brand.fg"
            fontWeight="medium"
          >
            Neo4j Labs
          </Link>{" "}
          project · Community supported
        </Text>
      </Flex>
    );
  }

  return (
    <Box
      p={4}
      bg="brand.subtle"
      borderRadius="lg"
      borderWidth="1px"
      borderColor="brand.muted"
    >
      <Flex align="center" gap={2} mb={2}>
        <Box color="brand.fg">
          <LuFlaskConical size={18} />
        </Box>
        <Text fontWeight="semibold" color="brand.fg" fontSize="sm">
          Neo4j Labs Project
        </Text>
        <Badge size="sm" colorPalette="brand">
          Beta
        </Badge>
      </Flex>
      <Text fontSize="sm" color="fg.muted" lineHeight="tall">
        This project is part of{" "}
        <Link
          href="https://neo4j.com/labs/"
          target="_blank"
          rel="noopener noreferrer"
          color="brand.fg"
          fontWeight="medium"
        >
          Neo4j Labs
        </Link>{" "}
        and is actively maintained, but not officially supported. There are no
        SLAs or guarantees around backwards compatibility and deprecation.
      </Text>
      <Flex mt={3} gap={4} fontSize="xs">
        <Link
          href="https://community.neo4j.com"
          target="_blank"
          rel="noopener noreferrer"
          color="brand.fg"
          display="flex"
          alignItems="center"
          gap={1}
        >
          <LuMessageCircle size={12} />
          Community Forum
        </Link>
        <Link
          href="https://github.com/neo4j-labs/agent-memory"
          target="_blank"
          rel="noopener noreferrer"
          color="brand.fg"
          display="flex"
          alignItems="center"
          gap={1}
        >
          <LuExternalLink size={12} />
          GitHub
        </Link>
      </Flex>
    </Box>
  );
}
