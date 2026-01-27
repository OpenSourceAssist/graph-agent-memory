"use client";

import { useState, useEffect } from "react";
import {
  Box,
  VStack,
  HStack,
  Heading,
  Text,
  Card,
  Badge,
  Button,
  Spinner,
  SimpleGrid,
} from "@chakra-ui/react";
import { getPreferences } from "@/lib/api";

interface Preference {
  id: string;
  category: string;
  preference: string;
  context?: string;
  confidence?: number;
}

interface PreferencePanelProps {
  sessionId: string;
}

const categoryColors: Record<string, string> = {
  brand: "purple",
  category: "blue",
  style: "green",
  price: "orange",
  size: "pink",
  color: "cyan",
};

export function PreferencePanel({ sessionId }: PreferencePanelProps) {
  const [preferences, setPreferences] = useState<Preference[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadPreferences = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getPreferences(sessionId);
      setPreferences(data.preferences);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load preferences");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPreferences();
  }, [sessionId]);

  // Group preferences by category
  const groupedPreferences = preferences.reduce(
    (acc, pref) => {
      if (!acc[pref.category]) {
        acc[pref.category] = [];
      }
      acc[pref.category].push(pref);
      return acc;
    },
    {} as Record<string, Preference[]>
  );

  return (
    <Box>
      <HStack justify="space-between" mb={6}>
        <Heading size="lg">Learned Preferences</Heading>
        <Button
          size="sm"
          variant="outline"
          onClick={loadPreferences}
          disabled={isLoading}
        >
          Refresh
        </Button>
      </HStack>

      {isLoading ? (
        <Box textAlign="center" py={10}>
          <Spinner size="lg" color="teal.500" />
          <Text mt={4} color="gray.500">
            Loading preferences...
          </Text>
        </Box>
      ) : error ? (
        <Card.Root bg="red.50">
          <Card.Body>
            <Text color="red.600">{error}</Text>
          </Card.Body>
        </Card.Root>
      ) : preferences.length === 0 ? (
        <Card.Root>
          <Card.Body textAlign="center" py={10}>
            <Text color="gray.500" mb={4}>
              No preferences learned yet.
            </Text>
            <Text color="gray.400" fontSize="sm">
              Start chatting with the assistant and express your preferences.
              For example, say "I prefer Nike brand" or "My budget is under
              $150".
            </Text>
          </Card.Body>
        </Card.Root>
      ) : (
        <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={6}>
          {Object.entries(groupedPreferences).map(([category, prefs]) => (
            <Card.Root key={category}>
              <Card.Header>
                <HStack>
                  <Badge
                    colorPalette={categoryColors[category.toLowerCase()] || "gray"}
                    size="lg"
                  >
                    {category}
                  </Badge>
                  <Text color="gray.500" fontSize="sm">
                    ({prefs.length})
                  </Text>
                </HStack>
              </Card.Header>
              <Card.Body>
                <VStack align="stretch" gap={3}>
                  {prefs.map((pref) => (
                    <Box
                      key={pref.id}
                      p={3}
                      bg="gray.50"
                      borderRadius="md"
                      borderLeftWidth="3px"
                      borderLeftColor={`${categoryColors[category.toLowerCase()] || "gray"}.400`}
                    >
                      <Text fontWeight="medium">{pref.preference}</Text>
                      {pref.context && (
                        <Text fontSize="sm" color="gray.500" mt={1}>
                          Context: {pref.context}
                        </Text>
                      )}
                      {pref.confidence !== undefined && (
                        <HStack mt={2}>
                          <Text fontSize="xs" color="gray.400">
                            Confidence:
                          </Text>
                          <Box
                            flex={1}
                            h="4px"
                            bg="gray.200"
                            borderRadius="full"
                          >
                            <Box
                              h="100%"
                              w={`${pref.confidence * 100}%`}
                              bg={`${categoryColors[category.toLowerCase()] || "gray"}.400`}
                              borderRadius="full"
                            />
                          </Box>
                          <Text fontSize="xs" color="gray.400">
                            {Math.round(pref.confidence * 100)}%
                          </Text>
                        </HStack>
                      )}
                    </Box>
                  ))}
                </VStack>
              </Card.Body>
            </Card.Root>
          ))}
        </SimpleGrid>
      )}

      {/* Explanation */}
      <Card.Root mt={6} bg="teal.50">
        <Card.Body>
          <Heading size="sm" color="teal.700" mb={2}>
            How Preferences Work
          </Heading>
          <Text color="teal.600" fontSize="sm">
            The assistant automatically learns your preferences from
            conversation. When you mention brands you like, budget constraints,
            style preferences, or size requirements, these are stored in
            long-term memory and used to personalize future recommendations.
          </Text>
        </Card.Body>
      </Card.Root>
    </Box>
  );
}
