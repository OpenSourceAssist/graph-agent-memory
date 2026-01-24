"use client";

import {
  Box,
  Flex,
  Textarea,
  IconButton,
  HStack,
  Text,
} from "@chakra-ui/react";
import { useState, KeyboardEvent } from "react";
import { LuSend, LuLoader } from "react-icons/lu";

interface PromptInputProps {
  onSend: (content: string) => void;
  isLoading?: boolean;
  placeholder?: string;
}

export function PromptInput({
  onSend,
  isLoading = false,
  placeholder = "Type a message...",
}: PromptInputProps) {
  const [value, setValue] = useState("");

  const handleSend = () => {
    if (value.trim() && !isLoading) {
      onSend(value.trim());
      setValue("");
      // Reset textarea height
      const textarea = document.querySelector(
        'textarea[name="prompt"]',
      ) as HTMLTextAreaElement;
      if (textarea) {
        textarea.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Box maxW="4xl" mx="auto" w="full">
      <Flex
        bg="bg.muted"
        borderRadius={{ base: "xl", md: "2xl" }}
        border="1px solid"
        borderColor="border.subtle"
        px={{ base: 3, md: 4 }}
        py={{ base: 2, md: 3 }}
        alignItems="flex-end"
        gap={{ base: 2, md: 3 }}
        _focusWithin={{
          borderColor: "blue.500",
          boxShadow: "0 0 0 1px var(--chakra-colors-blue-500)",
        }}
        transition="all 0.2s"
      >
        <Textarea
          name="prompt"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isLoading}
          rows={1}
          resize="none"
          minH={{ base: "40px", md: "44px" }}
          maxH="200px"
          py={{ base: 2, md: 2 }}
          px="0"
          border="none"
          outline="none"
          bg="transparent"
          fontSize={{ base: "sm", md: "md" }}
          _focus={{
            outline: "none",
            boxShadow: "none",
          }}
          css={{
            overflow: "hidden",
            resize: "none",
            "&::-webkit-scrollbar": {
              display: "none",
            },
          }}
          onInput={(e) => {
            const target = e.target as HTMLTextAreaElement;
            target.style.height = "auto";
            target.style.height = `${Math.min(target.scrollHeight, 200)}px`;
          }}
        />
        <HStack gap={1} flexShrink={0}>
          <IconButton
            aria-label="Send message"
            onClick={handleSend}
            disabled={!value.trim() || isLoading}
            colorPalette="blue"
            borderRadius="full"
            size={{ base: "sm", md: "md" }}
            minW={{ base: "36px", md: "40px" }}
            minH={{ base: "36px", md: "40px" }}
          >
            {isLoading ? <LuLoader className="animate-spin" /> : <LuSend />}
          </IconButton>
        </HStack>
      </Flex>
      <Text
        fontSize="xs"
        color="fg.muted"
        textAlign="center"
        mt="2"
        hideBelow="sm"
      >
        Press Enter to send, Shift+Enter for new line
      </Text>
    </Box>
  );
}
