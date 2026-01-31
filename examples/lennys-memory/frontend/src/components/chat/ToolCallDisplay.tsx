"use client";

import {
  Box,
  Flex,
  Text,
  Badge,
  Code,
  Spinner,
  Collapsible,
} from "@chakra-ui/react";
import { useState } from "react";
import { LuChevronDown, LuChevronRight, LuWrench } from "react-icons/lu";
import type { ToolCall } from "@/lib/types";
import { ToolResultCard } from "./cards";
import { getToolDisplayTitle } from "./cards/toolCardRegistry";

interface ToolCallDisplayProps {
  toolCall: ToolCall;
  /** Show detailed arguments (for debugging) */
  showArgs?: boolean;
}

/**
 * ToolCallDisplay renders tool invocations in the chat interface.
 *
 * Features:
 * - Collapsible header with tool name, status, and duration
 * - Rich visualization cards for results (MapCard, GraphCard, DataCard, etc.)
 * - Pending state indicator while tool is executing
 * - Optional arguments display for debugging
 */
export function ToolCallDisplay({
  toolCall,
  showArgs = false,
}: ToolCallDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(true); // Default to expanded to show cards
  const [showArguments, setShowArguments] = useState(false);

  const statusColor =
    toolCall.status === "success"
      ? "green"
      : toolCall.status === "error"
        ? "red"
        : "amber";

  const toolDisplayName = getToolDisplayTitle(toolCall.name);

  return (
    <Box
      borderWidth="1px"
      borderColor="border.subtle"
      borderRadius="md"
      overflow="hidden"
    >
      {/* Header - clickable to toggle visibility */}
      <Flex
        px={{ base: 2, md: 3 }}
        py={{ base: 2.5, md: 2 }}
        minH={{ base: "44px", md: "auto" }}
        bg="bg.muted"
        alignItems="center"
        gap="2"
        cursor="pointer"
        onClick={() => setIsExpanded(!isExpanded)}
        _hover={{ bg: "bg.emphasized" }}
        _active={{ bg: "bg.subtle" }}
      >
        {isExpanded ? (
          <LuChevronDown size={14} />
        ) : (
          <LuChevronRight size={14} />
        )}
        <LuWrench size={14} />
        <Text
          fontSize="sm"
          fontWeight="medium"
          flex="1"
          truncate
          title={toolCall.name}
        >
          {toolDisplayName}
        </Text>
        {toolCall.status === "pending" && (
          <Spinner size="xs" color="amber.500" />
        )}
        <Badge colorPalette={statusColor} size="sm">
          {toolCall.status}
        </Badge>
        {toolCall.duration_ms !== undefined && (
          <Text fontSize="xs" color="fg.muted" hideBelow="sm">
            {toolCall.duration_ms.toFixed(0)}ms
          </Text>
        )}
      </Flex>

      {/* Pending state message */}
      {isExpanded && toolCall.status === "pending" && (
        <Box p={3} bg="amber.subtle">
          <Flex align="center" gap={2}>
            <Spinner size="sm" color="amber.600" />
            <Text fontSize="sm" color="amber.fg">
              Executing {toolDisplayName}...
            </Text>
          </Flex>
        </Box>
      )}

      {/* Result card - only show when we have a result */}
      {isExpanded && toolCall.result !== undefined && (
        <Box p={{ base: 2, md: 3 }}>
          <ToolResultCard toolCall={toolCall} />
        </Box>
      )}

      {/* Optional arguments display (for debugging) */}
      {isExpanded && showArgs && (
        <Collapsible.Root
          open={showArguments}
          onOpenChange={(e) => setShowArguments(e.open)}
        >
          <Collapsible.Trigger asChild>
            <Flex
              px={3}
              py={2}
              cursor="pointer"
              borderTopWidth="1px"
              borderColor="border.subtle"
              _hover={{ bg: "bg.subtle" }}
            >
              <Text fontSize="xs" color="fg.muted">
                {showArguments ? "Hide" : "Show"} Arguments
              </Text>
            </Flex>
          </Collapsible.Trigger>
          <Collapsible.Content>
            <Box px={3} pb={3}>
              <Code
                display="block"
                whiteSpace="pre-wrap"
                p="2"
                borderRadius="md"
                fontSize="xs"
                bg="bg.subtle"
                overflowX="auto"
              >
                {JSON.stringify(toolCall.args, null, 2)}
              </Code>
            </Box>
          </Collapsible.Content>
        </Collapsible.Root>
      )}
    </Box>
  );
}
