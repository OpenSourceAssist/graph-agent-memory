"use client";

import {
  Box,
  Code,
  Text,
  VStack,
  Portal,
  CloseButton,
  Flex,
} from "@chakra-ui/react";
import { DialogRoot, DialogContent, DialogHeader, DialogTitle, DialogBody, DialogCloseTrigger, DialogBackdrop, DialogPositioner } from "@chakra-ui/react";
import { BaseCard } from "./BaseCard";
import { LuCode } from "react-icons/lu";
import type { BaseCardProps } from "./types";
import { getToolDisplayTitle } from "./toolCardRegistry";

/**
 * RawJsonCard is the fallback card for tools without specific visualizations.
 * Displays the raw JSON result in a formatted code block.
 */
export function RawJsonCard({
  toolCall,
  isExpanded = false,
  onExpand,
  onCollapse,
  compactHeight = 200,
}: BaseCardProps) {
  // Format the result as pretty JSON
  const formattedResult = (() => {
    try {
      if (typeof toolCall.result === "string") {
        // Try to parse if it's a JSON string
        try {
          const parsed = JSON.parse(toolCall.result);
          return JSON.stringify(parsed, null, 2);
        } catch {
          return toolCall.result;
        }
      }
      return JSON.stringify(toolCall.result, null, 2);
    } catch {
      return String(toolCall.result);
    }
  })();

  const title = getToolDisplayTitle(toolCall.name);

  const jsonContent = (
    <Box height="100%" overflow="auto" p={2}>
      {toolCall.result === undefined ? (
        <VStack height="100%" justify="center">
          <Text fontSize="sm" color="fg.muted">
            No result data
          </Text>
        </VStack>
      ) : (
        <Code
          display="block"
          whiteSpace="pre-wrap"
          fontSize="xs"
          p={2}
          borderRadius="md"
          bg="bg.muted"
          overflowX="auto"
        >
          {formattedResult}
        </Code>
      )}
    </Box>
  );

  // Estimate content size for footer
  const resultSize = formattedResult.length;
  const footerText =
    resultSize > 1000
      ? `${Math.round(resultSize / 1000)}KB`
      : `${resultSize} chars`;

  // Fullscreen dialog
  if (isExpanded) {
    return (
      <DialogRoot open={true} size="cover" onOpenChange={() => onCollapse?.()}>
        <Portal>
          <DialogBackdrop />
          <DialogPositioner>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  <Flex align="center" gap={2}>
                    <LuCode />
                    {title}
                  </Flex>
                </DialogTitle>
                <DialogCloseTrigger asChild>
                  <CloseButton size="sm" />
                </DialogCloseTrigger>
              </DialogHeader>
              <DialogBody p={4} height="calc(100vh - 80px)" overflow="auto">
                {jsonContent}
              </DialogBody>
            </DialogContent>
          </DialogPositioner>
        </Portal>
      </DialogRoot>
    );
  }

  return (
    <BaseCard
      toolCall={toolCall}
      title={title}
      icon={<LuCode size={14} />}
      colorPalette="gray"
      isExpanded={isExpanded}
      onExpand={onExpand}
      onCollapse={onCollapse}
      compactHeight={compactHeight}
      footer={footerText}
    >
      {jsonContent}
    </BaseCard>
  );
}
