"use client";

import { Box, Card, Flex, IconButton, Text, Badge } from "@chakra-ui/react";
import { LuExpand, LuMinimize2 } from "react-icons/lu";
import type { ToolCall } from "@/lib/types";
import type { ReactNode } from "react";

interface BaseCardWrapperProps {
  /** The tool call data */
  toolCall: ToolCall;
  /** Whether the card is in expanded (fullscreen) mode */
  isExpanded?: boolean;
  /** Callback to request fullscreen expansion */
  onExpand?: () => void;
  /** Callback when fullscreen is closed */
  onCollapse?: () => void;
  /** Height of the card in compact mode */
  compactHeight?: number;
  /** Card title */
  title: string;
  /** Optional icon to display */
  icon?: ReactNode;
  /** Color palette for the card accent */
  colorPalette?: string;
  /** Card content */
  children: ReactNode;
  /** Optional footer content (e.g., count summary) */
  footer?: ReactNode;
}

/**
 * BaseCard provides a consistent wrapper for all tool result card types.
 * Features:
 * - Header with title, status badge, and expand button
 * - Configurable height for compact mode
 * - Footer for summary information
 */
export function BaseCard({
  toolCall,
  isExpanded = false,
  onExpand,
  onCollapse,
  compactHeight = 250,
  title,
  icon,
  colorPalette = "brand",
  children,
  footer,
}: BaseCardWrapperProps) {
  const statusColor =
    toolCall.status === "success"
      ? "green"
      : toolCall.status === "error"
        ? "red"
        : "amber";

  return (
    <Card.Root
      size="sm"
      variant="outline"
      overflow="hidden"
      height={isExpanded ? "100%" : "auto"}
      borderColor="border.subtle"
      borderLeftWidth="3px"
      borderLeftColor={`${colorPalette}.500`}
    >
      {/* Header */}
      <Card.Header py={2} px={3} bg="bg.muted">
        <Flex justify="space-between" align="center">
          <Flex align="center" gap={2} minW={0} flex={1}>
            {icon && (
              <Box color={`${colorPalette}.fg`} flexShrink={0}>
                {icon}
              </Box>
            )}
            <Text fontSize="sm" fontWeight="medium" truncate title={title}>
              {title}
            </Text>
            <Badge size="sm" colorPalette={statusColor} flexShrink={0}>
              {toolCall.status}
            </Badge>
            {toolCall.duration_ms !== undefined && (
              <Text
                fontSize="xs"
                color="fg.muted"
                flexShrink={0}
                hideBelow="sm"
              >
                {toolCall.duration_ms.toFixed(0)}ms
              </Text>
            )}
          </Flex>
          <IconButton
            aria-label={isExpanded ? "Minimize" : "Expand to fullscreen"}
            size={{ base: "sm", md: "xs" }}
            variant="ghost"
            onClick={isExpanded ? onCollapse : onExpand}
            flexShrink={0}
            minW={{ base: "32px", md: "auto" }}
            minH={{ base: "32px", md: "auto" }}
            _focusVisible={{
              outline: "2px solid",
              outlineColor: "brand.500",
              outlineOffset: "2px",
            }}
          >
            {isExpanded ? <LuMinimize2 /> : <LuExpand />}
          </IconButton>
        </Flex>
      </Card.Header>

      {/* Content */}
      <Card.Body
        p={0}
        height={isExpanded ? "100%" : `${compactHeight}px`}
        overflow="hidden"
      >
        {children}
      </Card.Body>

      {/* Optional Footer */}
      {footer && !isExpanded && (
        <Card.Footer py={2} px={3} bg="bg.muted" borderTopWidth="1px">
          <Text fontSize="xs" color="fg.muted">
            {footer}
          </Text>
        </Card.Footer>
      )}
    </Card.Root>
  );
}
