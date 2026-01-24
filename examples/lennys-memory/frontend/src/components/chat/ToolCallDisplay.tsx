"use client";

import { Box, Flex, Text, Badge, Code, Stack } from "@chakra-ui/react";
import { useState } from "react";
import { LuChevronDown, LuChevronRight, LuWrench } from "react-icons/lu";
import type { ToolCall } from "@/lib/types";

interface ToolCallDisplayProps {
  toolCall: ToolCall;
}

export function ToolCallDisplay({ toolCall }: ToolCallDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const statusColor =
    toolCall.status === "success"
      ? "green"
      : toolCall.status === "error"
        ? "red"
        : "yellow";

  return (
    <Box
      borderWidth="1px"
      borderColor="border.subtle"
      borderRadius="md"
      overflow="hidden"
    >
      {/* Header */}
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
        <Text fontSize="sm" fontWeight="medium" flex="1" truncate>
          {toolCall.name}
        </Text>
        <Badge colorPalette={statusColor} size="sm">
          {toolCall.status}
        </Badge>
        {toolCall.duration_ms !== undefined && (
          <Text fontSize="xs" color="fg.muted" hideBelow="sm">
            {toolCall.duration_ms.toFixed(0)}ms
          </Text>
        )}
      </Flex>

      {/* Expandable content */}
      {isExpanded && (
        <Stack p={{ base: 2, md: 3 }} gap={{ base: 2, md: 3 }}>
          {/* Arguments */}
          <Box>
            <Text fontSize="xs" fontWeight="medium" color="fg.muted" mb="1">
              Arguments
            </Text>
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

          {/* Result */}
          {toolCall.result !== undefined && (
            <Box>
              <Text fontSize="xs" fontWeight="medium" color="fg.muted" mb="1">
                Result
              </Text>
              <Code
                display="block"
                whiteSpace="pre-wrap"
                p="2"
                borderRadius="md"
                fontSize="xs"
                bg="bg.subtle"
                maxH={{ base: "150px", md: "200px" }}
                overflowY="auto"
                overflowX="auto"
              >
                {typeof toolCall.result === "string"
                  ? toolCall.result
                  : JSON.stringify(toolCall.result, null, 2)}
              </Code>
            </Box>
          )}
        </Stack>
      )}
    </Box>
  );
}
