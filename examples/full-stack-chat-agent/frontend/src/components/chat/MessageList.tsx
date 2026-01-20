"use client";

import { Stack } from "@chakra-ui/react";
import { Message } from "./Message";
import type { Message as MessageType } from "@/lib/types";

interface MessageListProps {
  messages: MessageType[];
}

export function MessageList({ messages }: MessageListProps) {
  return (
    <Stack gap="4" maxW="4xl" mx="auto">
      {messages.map((message) => (
        <Message key={message.id} message={message} />
      ))}
    </Stack>
  );
}
