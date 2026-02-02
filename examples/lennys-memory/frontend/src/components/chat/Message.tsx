"use client";

import { Box, Flex, Text, Stack, Button } from "@chakra-ui/react";
import { useState, useCallback } from "react";
import { LuUser, LuBot, LuChevronDown, LuChevronUp } from "react-icons/lu";
import ReactMarkdown from "react-markdown";
import { ToolCallDisplay } from "./ToolCallDisplay";
import type { Message as MessageType } from "@/lib/types";

interface MessageProps {
  message: MessageType;
}

export function Message({ message }: MessageProps) {
  const isUser = message.role === "user";
  const hasToolCalls = message.toolCalls && message.toolCalls.length > 0;

  // Track expansion state for each tool call
  const [expandedTools, setExpandedTools] = useState<Record<string, boolean>>(
    {},
  );

  // Check if all tools are expanded
  const allExpanded = hasToolCalls
    ? message.toolCalls!.every((tc) => expandedTools[tc.id] === true)
    : false;

  // Check if any tools are expanded
  const anyExpanded = hasToolCalls
    ? message.toolCalls!.some((tc) => expandedTools[tc.id] === true)
    : false;

  // Toggle a single tool's expansion
  const toggleTool = useCallback((toolId: string) => {
    setExpandedTools((prev) => ({
      ...prev,
      [toolId]: !prev[toolId],
    }));
  }, []);

  // Toggle all tools
  const toggleAll = useCallback(() => {
    if (!message.toolCalls) return;

    const newState: Record<string, boolean> = {};
    const shouldExpand = !allExpanded;

    for (const tc of message.toolCalls) {
      newState[tc.id] = shouldExpand;
    }

    setExpandedTools(newState);
  }, [message.toolCalls, allExpanded]);

  return (
    <Flex
      gap={{ base: 2, md: 3 }}
      alignItems="flex-start"
      p={{ base: 2, md: 3 }}
      mx={{ base: -2, md: -3 }}
      borderRadius="lg"
      transition="background 0.15s"
      _hover={{ bg: "bg.subtle" }}
    >
      {/* Avatar */}
      <Flex
        w={{ base: 7, md: 8 }}
        h={{ base: 7, md: 8 }}
        borderRadius="full"
        bg={isUser ? "blue.subtle" : "green.subtle"}
        alignItems="center"
        justifyContent="center"
        flexShrink={0}
        role="img"
        aria-label={isUser ? "User avatar" : "Assistant avatar"}
      >
        {isUser ? <LuUser size={16} /> : <LuBot size={16} />}
      </Flex>

      {/* Content */}
      <Stack gap={{ base: 1.5, md: 2 }} flex="1" minW="0">
        <Text fontSize="sm" fontWeight="medium" color="fg.muted">
          {isUser ? "You" : "Assistant"}
        </Text>

        {/* Message content */}
        {message.content && (
          <Box
            className="prose prose-sm"
            css={{
              "& p": { margin: 0 },
              "& p + p": { marginTop: "0.5em" },
              "& ul, & ol": { paddingLeft: "1.5em", margin: "0.5em 0" },
              "& code": {
                backgroundColor: "var(--chakra-colors-bg-muted)",
                padding: "0.1em 0.3em",
                borderRadius: "0.25em",
                fontSize: "0.9em",
              },
              "& pre": {
                backgroundColor: "var(--chakra-colors-bg-muted)",
                padding: "0.75em",
                borderRadius: "0.5em",
                overflow: "auto",
              },
              "& pre code": {
                background: "none",
                padding: 0,
              },
            }}
          >
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </Box>
        )}

        {/* Tool calls */}
        {hasToolCalls && (
          <Stack gap={{ base: 1.5, md: 2 }}>
            {/* Global expand/collapse toggle */}
            {message.toolCalls!.length > 1 && (
              <Flex justify="flex-end">
                <Button
                  size="xs"
                  variant="ghost"
                  onClick={toggleAll}
                  color="fg.muted"
                  _hover={{ color: "fg", bg: "bg.subtle" }}
                >
                  {allExpanded ? (
                    <>
                      <LuChevronUp size={14} />
                      Collapse All ({message.toolCalls!.length})
                    </>
                  ) : (
                    <>
                      <LuChevronDown size={14} />
                      {anyExpanded ? "Expand All" : "Expand All"} (
                      {message.toolCalls!.length})
                    </>
                  )}
                </Button>
              </Flex>
            )}

            {message.toolCalls!.map((toolCall) => (
              <ToolCallDisplay
                key={toolCall.id}
                toolCall={toolCall}
                isExpanded={expandedTools[toolCall.id] ?? false}
                onToggle={() => toggleTool(toolCall.id)}
              />
            ))}
          </Stack>
        )}
      </Stack>
    </Flex>
  );
}
