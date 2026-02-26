"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  Box,
  Container,
  Flex,
  Heading,
  Text,
  Input,
  Button,
  VStack,
  HStack,
  Card,
  Badge,
  Spinner,
  IconButton,
} from "@chakra-ui/react";
import { ChatInterface } from "@/components/ChatInterface";
import { PreferencePanel } from "@/components/PreferencePanel";
import { MemoryExplorer } from "@/components/MemoryExplorer";
import { checkHealth } from "@/lib/api";

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "memory" | "preferences">(
    "chat"
  );
  const [isConnected, setIsConnected] = useState(false);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    // Generate or retrieve session ID
    const stored = sessionStorage.getItem("shopping-session-id");
    if (stored) {
      setSessionId(stored);
    } else {
      const newId = `session-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
      sessionStorage.setItem("shopping-session-id", newId);
      setSessionId(newId);
    }

    // Check backend health
    checkHealth()
      .then((health) => {
        setIsConnected(health.status === "healthy");
      })
      .catch(() => {
        setIsConnected(false);
      })
      .finally(() => {
        setIsChecking(false);
      });
  }, []);

  return (
    <Box minH="100vh" bg="gray.50">
      {/* Header */}
      <Box bg="white" borderBottomWidth="1px" py={4}>
        <Container maxW="container.xl">
          <Flex justify="space-between" align="center">
            <HStack gap={4}>
              <Heading size="lg" color="teal.600">
                Smart Shopping Assistant
              </Heading>
              <Badge
                colorPalette={isConnected ? "green" : "red"}
                variant="subtle"
              >
                {isChecking
                  ? "Connecting..."
                  : isConnected
                    ? "Connected"
                    : "Disconnected"}
              </Badge>
            </HStack>

            <HStack gap={2}>
              <Button
                variant={activeTab === "chat" ? "solid" : "ghost"}
                colorPalette="teal"
                onClick={() => setActiveTab("chat")}
              >
                Chat
              </Button>
              <Button
                variant={activeTab === "memory" ? "solid" : "ghost"}
                colorPalette="teal"
                onClick={() => setActiveTab("memory")}
              >
                Memory Graph
              </Button>
              <Button
                variant={activeTab === "preferences" ? "solid" : "ghost"}
                colorPalette="teal"
                onClick={() => setActiveTab("preferences")}
              >
                Preferences
              </Button>
            </HStack>
          </Flex>
        </Container>
      </Box>

      {/* Main Content */}
      <Container maxW="container.xl" py={6}>
        {!isConnected && !isChecking && (
          <Card.Root mb={6} bg="red.50" borderColor="red.200">
            <Card.Body>
              <Text color="red.600">
                Unable to connect to the backend server. Make sure the server is
                running at http://localhost:8000
              </Text>
            </Card.Body>
          </Card.Root>
        )}

        {activeTab === "chat" && sessionId && (
          <ChatInterface sessionId={sessionId} />
        )}

        {activeTab === "memory" && sessionId && (
          <MemoryExplorer sessionId={sessionId} />
        )}

        {activeTab === "preferences" && sessionId && (
          <PreferencePanel sessionId={sessionId} />
        )}
      </Container>

      {/* Footer */}
      <Box
        position="fixed"
        bottom={0}
        left={0}
        right={0}
        bg="white"
        borderTopWidth="1px"
        py={2}
      >
        <Container maxW="container.xl">
          <Flex justify="space-between" align="center">
            <Text fontSize="sm" color="gray.500">
              Powered by Neo4j Agent Memory + Microsoft Agent Framework
            </Text>
            <Text fontSize="sm" color="gray.500">
              Session: {sessionId?.slice(0, 20)}...
            </Text>
          </Flex>
        </Container>
      </Box>
    </Box>
  );
}
