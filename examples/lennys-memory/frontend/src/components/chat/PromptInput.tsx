"use client";

import { Box, Flex, Textarea, IconButton } from "@chakra-ui/react";
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
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Flex gap="2" alignItems="flex-end">
      <Box flex="1" position="relative">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isLoading}
          rows={1}
          resize="none"
          minH="44px"
          maxH="200px"
          py="3"
          pr="12"
          borderRadius="xl"
          bg="bg.subtle"
          _focus={{
            bg: "bg.panel",
            borderColor: "border.emphasized",
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
      </Box>
      <IconButton
        aria-label="Send message"
        onClick={handleSend}
        disabled={!value.trim() || isLoading}
        colorPalette="blue"
        borderRadius="full"
        size="md"
      >
        {isLoading ? <LuLoader className="animate-spin" /> : <LuSend />}
      </IconButton>
    </Flex>
  );
}
