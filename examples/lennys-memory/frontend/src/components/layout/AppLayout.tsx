"use client";

import {
  Box,
  Flex,
  Stack,
  IconButton,
  Text,
  Button,
  HStack,
  Drawer,
  Portal,
  CloseButton,
  Menu,
  useBreakpointValue,
} from "@chakra-ui/react";
import {
  LuPanelLeftClose,
  LuPanelLeft,
  LuMapPin,
  LuMenu,
  LuEllipsisVertical,
} from "react-icons/lu";
import { HiOutlineShare } from "react-icons/hi";
import { useState } from "react";
import { Sidebar } from "./Sidebar";
import MemoryGraphView from "@/components/memory/MemoryGraphView";
import MemoryMapView from "@/components/memory/MemoryMapView";
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [graphViewOpen, setGraphViewOpen] = useState(false);
  const [mapViewOpen, setMapViewOpen] = useState(false);

  // Detect mobile viewport
  const isMobile = useBreakpointValue({ base: true, md: false });

  return (
    <Flex h="100vh" overflow="hidden" bg="bg.canvas">
      {/* Desktop Sidebar */}
      {sidebarOpen && !isMobile && (
        <Box
          w="280px"
          borderRightWidth="1px"
          borderColor="border.subtle"
          bg="bg.panel"
          flexShrink={0}
          hideBelow="md"
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

      {/* Mobile Drawer Sidebar */}
      <Drawer.Root
        open={mobileMenuOpen}
        onOpenChange={(e) => setMobileMenuOpen(e.open)}
        placement="start"
      >
        <Portal>
          <Drawer.Backdrop />
          <Drawer.Positioner>
            <Drawer.Content maxW="280px">
              <Drawer.CloseTrigger
                asChild
                position="absolute"
                top="3"
                right="3"
              >
                <CloseButton size="sm" />
              </Drawer.CloseTrigger>
              <Sidebar
                threads={threads}
                activeThreadId={activeThreadId}
                onSelectThread={(id) => {
                  onSelectThread(id);
                  setMobileMenuOpen(false);
                }}
                onCreateThread={() => {
                  onCreateThread();
                  setMobileMenuOpen(false);
                }}
                onDeleteThread={onDeleteThread}
                memoryEnabled={memoryEnabled}
                onToggleMemory={onToggleMemory}
              />
            </Drawer.Content>
          </Drawer.Positioner>
        </Portal>
      </Drawer.Root>

      {/* Main content */}
      <Stack flex="1" gap="0" overflow="hidden">
        {/* Header */}
        <Flex
          h="14"
          px={{ base: 2, md: 4 }}
          alignItems="center"
          justifyContent="space-between"
          borderBottomWidth="1px"
          borderColor="border.subtle"
          bg="bg.panel"
        >
          <Flex alignItems="center">
            {/* Mobile hamburger menu */}
            <IconButton
              aria-label="Open menu"
              variant="ghost"
              size="sm"
              hideFrom="md"
              onClick={() => setMobileMenuOpen(true)}
            >
              <LuMenu />
            </IconButton>

            {/* Desktop sidebar toggle */}
            <IconButton
              aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
              variant="ghost"
              size="sm"
              hideBelow="md"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              {sidebarOpen ? <LuPanelLeftClose /> : <LuPanelLeft />}
            </IconButton>

            <Text
              ml={{ base: 2, md: 3 }}
              fontWeight="medium"
              color="fg.default"
              fontSize={{ base: "sm", md: "md" }}
            >
              <Text as="span" hideBelow="sm">
                Lenny's Podcast Explorer
              </Text>
              <Text as="span" hideFrom="sm">
                Lenny's Podcast
              </Text>
            </Text>
          </Flex>

          {/* Desktop action buttons */}
          <HStack gap={2} hideBelow="sm">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setMapViewOpen(true)}
            >
              <LuMapPin />
              <Text ml="2">View Map</Text>
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setGraphViewOpen(true)}
            >
              <HiOutlineShare />
              <Text ml="2">View Graph</Text>
            </Button>
          </HStack>

          {/* Mobile action menu */}
          <Menu.Root>
            <Menu.Trigger asChild>
              <IconButton
                aria-label="More options"
                variant="ghost"
                size="sm"
                hideFrom="sm"
              >
                <LuEllipsisVertical />
              </IconButton>
            </Menu.Trigger>
            <Portal>
              <Menu.Positioner>
                <Menu.Content>
                  <Menu.Item value="map" onClick={() => setMapViewOpen(true)}>
                    <LuMapPin />
                    <Text ml="2">View Map</Text>
                  </Menu.Item>
                  <Menu.Item
                    value="graph"
                    onClick={() => setGraphViewOpen(true)}
                  >
                    <HiOutlineShare />
                    <Text ml="2">View Graph</Text>
                  </Menu.Item>
                </Menu.Content>
              </Menu.Positioner>
            </Portal>
          </Menu.Root>
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

      {/* Memory Map View Modal */}
      <MemoryMapView
        isOpen={mapViewOpen}
        onClose={() => setMapViewOpen(false)}
        threadId={activeThreadId || undefined}
      />
    </Flex>
  );
}
