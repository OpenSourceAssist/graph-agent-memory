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
  /** Control expansion state externally */
  isExpanded?: boolean;
  /** Callback when expansion state changes */
  onToggle?: () => void;
  /** Show detailed arguments in expandable section (for debugging) */
  showArgsSection?: boolean;
}

/**
 * Format tool arguments for display in the header.
 * Shows key parameters in a compact format.
 */
function formatArgsPreview(args: Record<string, unknown> | undefined): string {
  if (!args || Object.keys(args).length === 0) {
    return "";
  }

  const parts: string[] = [];
  for (const [key, value] of Object.entries(args)) {
    if (value === undefined || value === null) continue;

    // Format the value based on type
    let formatted: string;
    if (typeof value === "string") {
      // Truncate long strings
      formatted =
        value.length > 30 ? `"${value.slice(0, 30)}..."` : `"${value}"`;
    } else if (typeof value === "number" || typeof value === "boolean") {
      formatted = String(value);
    } else if (Array.isArray(value)) {
      formatted = `[${value.length} items]`;
    } else {
      formatted = "{...}";
    }

    parts.push(`${key}=${formatted}`);
  }

  return parts.join(", ");
}

/**
 * ToolCallDisplay renders tool invocations in the chat interface.
 *
 * Features:
 * - Collapsible header with tool name, status, duration, and arguments preview
 * - Rich visualization cards for results (MapCard, GraphCard, DataCard, etc.)
 * - Pending state indicator while tool is executing
 * - Optional detailed arguments display for debugging
 * - Supports external control of expansion state
 */
export function ToolCallDisplay({
  toolCall,
  isExpanded: externalExpanded,
  onToggle,
  showArgsSection = false,
}: ToolCallDisplayProps) {
  // Use internal state if no external control provided
  const [internalExpanded, setInternalExpanded] = useState(false); // Default collapsed
  const [showArguments, setShowArguments] = useState(false);

  // Use external control if provided, otherwise use internal state
  const isExpanded =
    externalExpanded !== undefined ? externalExpanded : internalExpanded;
  const handleToggle =
    onToggle || (() => setInternalExpanded(!internalExpanded));

  const statusColor =
    toolCall.status === "success"
      ? "green"
      : toolCall.status === "error"
        ? "red"
        : "amber";

  const toolDisplayName = getToolDisplayTitle(toolCall.name);
  const argsPreview = formatArgsPreview(toolCall.args);

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
        onClick={handleToggle}
        _hover={{ bg: "bg.emphasized" }}
        _active={{ bg: "bg.subtle" }}
        flexWrap="wrap"
      >
        <Flex alignItems="center" gap="2" flex="1" minW="0">
          {isExpanded ? (
            <LuChevronDown size={14} />
          ) : (
            <LuChevronRight size={14} />
          )}
          <LuWrench size={14} style={{ flexShrink: 0 }} />
          <Text
            fontSize="sm"
            fontWeight="medium"
            truncate
            title={toolCall.name}
          >
            {toolDisplayName}
          </Text>
          {toolCall.status === "pending" && (
            <Spinner size="xs" color="amber.500" />
          )}
          <Badge colorPalette={statusColor} size="sm" flexShrink={0}>
            {toolCall.status}
          </Badge>
          {toolCall.duration_ms !== undefined && (
            <Text fontSize="xs" color="fg.muted" hideBelow="sm" flexShrink={0}>
              {toolCall.duration_ms.toFixed(0)}ms
            </Text>
          )}
        </Flex>

        {/* Arguments preview - shown in header when collapsed */}
        {argsPreview && (
          <Text
            fontSize="xs"
            color="fg.muted"
            fontFamily="mono"
            truncate
            maxW={{ base: "100%", md: "400px" }}
            title={argsPreview}
            mt={{ base: 1, md: 0 }}
            w={{ base: "100%", md: "auto" }}
            pl={{ base: 6, md: 0 }}
          >
            {argsPreview}
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

      {/* Arguments display - shown when expanded */}
      {isExpanded && toolCall.args && Object.keys(toolCall.args).length > 0 && (
        <Box
          px={{ base: 2, md: 3 }}
          py={2}
          bg="bg.subtle"
          borderBottomWidth="1px"
          borderColor="border.subtle"
        >
          <Text fontSize="xs" fontWeight="medium" color="fg.muted" mb={1}>
            Arguments
          </Text>
          <Code
            display="block"
            whiteSpace="pre-wrap"
            p="2"
            borderRadius="md"
            fontSize="xs"
            bg="bg.muted"
            overflowX="auto"
          >
            {JSON.stringify(toolCall.args, null, 2)}
          </Code>
        </Box>
      )}

      {/* Result card - only show when we have a result */}
      {isExpanded && toolCall.result !== undefined && (
        <Box p={{ base: 2, md: 3 }}>
          <ToolResultCard toolCall={toolCall} />
        </Box>
      )}

      {/* Optional detailed arguments section (for additional debugging) */}
      {isExpanded && showArgsSection && (
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
                {showArguments ? "Hide" : "Show"} Raw Arguments
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
