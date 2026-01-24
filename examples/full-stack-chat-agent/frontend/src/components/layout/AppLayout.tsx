"use client";

import { Box, Flex, Stack, IconButton, Text, Button } from "@chakra-ui/react";
import { LuPanelLeftClose, LuPanelLeft } from "react-icons/lu";
import { HiOutlineShare } from "react-icons/hi";
import { useState } from "react";
import { Sidebar } from "./Sidebar";
import MemoryGraphView from "@/components/memory/MemoryGraphView";
import type { Thread } from "@/lib/types";

interface AppLayoutProps {
  children: React.ReactNode;
  threads: Thread[];
  activeThreadId: string | null;
  onSelectThread: (id: string) => void;
  onCreateThread: () => void;
  onDeleteThread: (id: string) => void;
  memoryEnabled: boolean;
  onToggleMemory: (enabled: boolean) => void;
}

export function AppLayout({
  children,
  threads,
  activeThreadId,
  onSelectThread,
  onCreateThread,
  onDeleteThread,
  memoryEnabled,
  onToggleMemory,
}: AppLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [graphViewOpen, setGraphViewOpen] = useState(false);

  return (
    <Flex h="100vh" overflow="hidden" bg="bg.canvas">
      {/* Sidebar */}
      {sidebarOpen && (
        <Box
          w="280px"
          borderRightWidth="1px"
          borderColor="border.subtle"
          bg="bg.panel"
          flexShrink={0}
        >
          <Sidebar
            threads={threads}
            activeThreadId={activeThreadId}
            onSelectThread={onSelectThread}
            onCreateThread={onCreateThread}
            onDeleteThread={onDeleteThread}
            memoryEnabled={memoryEnabled}
            onToggleMemory={onToggleMemory}
          />
        </Box>
      )}

      {/* Main content */}
      <Stack flex="1" gap="0" overflow="hidden">
        {/* Header */}
        <Flex
          h="14"
          px="4"
          alignItems="center"
          justifyContent="space-between"
          borderBottomWidth="1px"
          borderColor="border.subtle"
          bg="bg.panel"
        >
          <Flex alignItems="center">
            <IconButton
              aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
              variant="ghost"
              size="sm"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              {sidebarOpen ? <LuPanelLeftClose /> : <LuPanelLeft />}
            </IconButton>
            <Text ml="3" fontWeight="medium" color="fg.default">
              News Research Assistant
            </Text>
          </Flex>

          <Button
            size="sm"
            variant="outline"
            onClick={() => setGraphViewOpen(true)}
          >
            <HiOutlineShare />
            <Text ml="2">View Memory Graph</Text>
          </Button>
        </Flex>

        {/* Content area */}
        <Box flex="1" overflow="hidden">
          {children}
        </Box>
      </Stack>

      {/* Memory Graph View Modal */}
      <MemoryGraphView
        isOpen={graphViewOpen}
        onClose={() => setGraphViewOpen(false)}
        threadId={activeThreadId || undefined}
      />
    </Flex>
  );
}
