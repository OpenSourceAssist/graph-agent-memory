"use client";

import { Stack } from "@chakra-ui/react";
import { Message } from "./Message";
import type { Message as MessageType } from "@/lib/types";

interface MessageListProps {
  messages: MessageType[];
}

export function MessageList({ messages }: MessageListProps) {
  return (
    <Stack
      gap={{ base: 3, md: 4 }}
      maxW="4xl"
      mx="auto"
      px={{ base: 1, md: 0 }}
    >
      {messages.map((message) => (
        <Message key={message.id} message={message} />
      ))}
    </Stack>
  );
}
