"use client";

import { useState, useEffect } from "react";
import {
  Box,
  Button,
  Text,
  VStack,
  HStack,
  Badge,
  Portal,
  CloseButton,
  Flex,
  Separator,
} from "@chakra-ui/react";
import {
  DialogRoot,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogBody,
  DialogFooter,
  DialogCloseTrigger,
  DialogBackdrop,
  DialogPositioner,
} from "@chakra-ui/react";
import {
  LuBrain,
  LuMessageSquare,
  LuDatabase,
  LuSparkles,
  LuArrowRight,
} from "react-icons/lu";

const STORAGE_KEY = "lennys-memory-welcome-shown";

interface WelcomeModalProps {
  /** Callback when user starts using the app */
  onGetStarted?: () => void;
}

/**
 * Welcome modal for first-time users.
 * Explains the memory types and provides sample queries.
 */
export function WelcomeModal({ onGetStarted }: WelcomeModalProps) {
  const [isOpen, setIsOpen] = useState(false);

  // Check if user has seen the welcome modal
  useEffect(() => {
    const hasSeenWelcome = localStorage.getItem(STORAGE_KEY);
    if (!hasSeenWelcome) {
      // Small delay so the page renders first
      const timer = setTimeout(() => setIsOpen(true), 500);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleClose = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setIsOpen(false);
  };

  const handleGetStarted = () => {
    handleClose();
    onGetStarted?.();
  };

  return (
    <DialogRoot open={isOpen} onOpenChange={(e) => !e.open && handleClose()}>
      <Portal>
        <DialogBackdrop />
        <DialogPositioner>
          <DialogContent maxW={{ base: "95vw", sm: "500px" }}>
            <DialogHeader>
              <DialogTitle>
                <Flex align="center" gap={2}>
                  <Box color="brand.500">
                    <LuBrain size={24} />
                  </Box>
                  <Text fontFamily="heading">Welcome to Lenny's Memory</Text>
                </Flex>
              </DialogTitle>
              <DialogCloseTrigger asChild>
                <CloseButton size="sm" />
              </DialogCloseTrigger>
            </DialogHeader>

            <DialogBody>
              <VStack align="stretch" gap={4}>
                <Text color="fg.muted">
                  Explore Lenny's Podcast through the power of graph-based AI
                  memory. Ask questions about guests, topics, and insights from
                  hundreds of episodes.
                </Text>

                <Separator />

                {/* Memory Types */}
                <Text fontWeight="semibold" fontSize="sm">
                  How It Works
                </Text>

                <VStack align="stretch" gap={3}>
                  {/* Short-Term Memory */}
                  <HStack align="start" gap={3}>
                    <Box
                      p={2}
                      borderRadius="md"
                      bg="green.subtle"
                      color="green.fg"
                      flexShrink={0}
                    >
                      <LuMessageSquare size={16} />
                    </Box>
                    <Box>
                      <Text fontWeight="medium" fontSize="sm">
                        Short-Term Memory
                      </Text>
                      <Text fontSize="xs" color="fg.muted">
                        Conversation context that follows your chat
                      </Text>
                    </Box>
                  </HStack>

                  {/* Long-Term Memory */}
                  <HStack align="start" gap={3}>
                    <Box
                      p={2}
                      borderRadius="md"
                      bg="amber.subtle"
                      color="amber.fg"
                      flexShrink={0}
                    >
                      <LuDatabase size={16} />
                    </Box>
                    <Box>
                      <Text fontWeight="medium" fontSize="sm">
                        Long-Term Memory
                      </Text>
                      <Text fontSize="xs" color="fg.muted">
                        Knowledge graph of people, companies, and topics
                      </Text>
                    </Box>
                  </HStack>

                  {/* Reasoning Memory */}
                  <HStack align="start" gap={3}>
                    <Box
                      p={2}
                      borderRadius="md"
                      bg="purple.subtle"
                      color="purple.fg"
                      flexShrink={0}
                    >
                      <LuSparkles size={16} />
                    </Box>
                    <Box>
                      <Text fontWeight="medium" fontSize="sm">
                        Reasoning Memory
                      </Text>
                      <Text fontSize="xs" color="fg.muted">
                        Agent traces for learning and explainability
                      </Text>
                    </Box>
                  </HStack>
                </VStack>

                <Separator />

                {/* Sample Queries */}
                <Text fontWeight="semibold" fontSize="sm">
                  Try Asking
                </Text>

                <VStack align="stretch" gap={2}>
                  <SampleQuery>
                    Who has talked about product-market fit?
                  </SampleQuery>
                  <SampleQuery>
                    What companies are mentioned most often?
                  </SampleQuery>
                  <SampleQuery>
                    Find connections between Reid Hoffman and other guests
                  </SampleQuery>
                </VStack>
              </VStack>
            </DialogBody>

            <DialogFooter>
              <Button
                colorPalette="brand"
                size="lg"
                width="full"
                onClick={handleGetStarted}
              >
                Get Started
                <LuArrowRight />
              </Button>
            </DialogFooter>
          </DialogContent>
        </DialogPositioner>
      </Portal>
    </DialogRoot>
  );
}

/**
 * Sample query chip component
 */
function SampleQuery({ children }: { children: string }) {
  return (
    <Box
      px={3}
      py={2}
      bg="bg.muted"
      borderRadius="md"
      fontSize="sm"
      color="fg.muted"
      borderWidth="1px"
      borderColor="border.subtle"
    >
      "{children}"
    </Box>
  );
}

/**
 * Reset the welcome modal state (for testing)
 */
export function resetWelcomeModal() {
  localStorage.removeItem(STORAGE_KEY);
}
