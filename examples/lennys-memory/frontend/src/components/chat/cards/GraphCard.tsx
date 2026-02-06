"use client";

import { useState, useMemo } from "react";
import {
  Box,
  VStack,
  Text,
  Spinner,
  Portal,
  CloseButton,
  Flex,
  HStack,
  Badge,
} from "@chakra-ui/react";
import {
  DialogRoot,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogBody,
  DialogCloseTrigger,
  DialogBackdrop,
  DialogPositioner,
} from "@chakra-ui/react";
import dynamic from "next/dynamic";
import { BaseCard } from "./BaseCard";
import { LuNetwork } from "react-icons/lu";
import type { GraphCardProps, GraphNodeData } from "./types";

// Entity type colors - handles both uppercase and capitalized types
const graphNodeColors: Record<string, string> = {
  // Entity types - both cases for flexibility
  Person: "#DA7194",
  PERSON: "#DA7194",
  Organization: "#F79767",
  ORGANIZATION: "#F79767",
  Location: "#68BDF6",
  LOCATION: "#68BDF6",
  Topic: "#A4DD00",
  TOPIC: "#A4DD00",
  Concept: "#A4DD00",
  CONCEPT: "#A4DD00",
  Event: "#C990C0",
  EVENT: "#C990C0",
  Object: "#57C7E3",
  OBJECT: "#57C7E3",
  Episode: "#C990C0",
  EPISODE: "#C990C0",
  Preference: "#F59E0B",
  PREFERENCE: "#F59E0B",
  // Entity as fallback for untyped entities
  Entity: "#8B5CF6",
  ENTITY: "#8B5CF6",
  // Default - purple instead of gray
  default: "#8B5CF6",
};

// Get color for a node type with fallback
function getNodeColor(type: string): string {
  return (
    graphNodeColors[type] ||
    graphNodeColors[type.toUpperCase()] ||
    graphNodeColors[
      type.charAt(0).toUpperCase() + type.slice(1).toLowerCase()
    ] ||
    graphNodeColors.default
  );
}

// Define types for NVL
interface NvlNode {
  id: string;
  caption?: string;
  size?: number;
  color?: string;
  selected?: boolean;
}

interface NvlRelationship {
  id: string;
  from: string;
  to: string;
  caption?: string;
}

// Dynamically import NVL to avoid SSR issues
const InteractiveNvlWrapper = dynamic(
  () => import("@neo4j-nvl/react").then((mod) => mod.InteractiveNvlWrapper),
  {
    ssr: false,
    loading: () => (
      <VStack height="100%" justifyContent="center" gap={4}>
        <Spinner size="md" color="brand.500" />
        <Text color="fg.muted" fontSize="sm">
          Loading graph...
        </Text>
      </VStack>
    ),
  },
);

/**
 * GraphCard displays a knowledge graph visualization.
 * Features:
 * - Inline compact view (180-250px height)
 * - Node colors by entity type
 * - D3 force layout
 * - Expand to fullscreen for interaction
 */
export function GraphCard({
  toolCall,
  nodes,
  relationships,
  focusNodeId,
  isExpanded = false,
  onExpand,
  onCollapse,
  compactHeight = 220,
}: GraphCardProps) {
  const [selectedNode, setSelectedNode] = useState<GraphNodeData | null>(null);

  // Convert to NVL format with label fallbacks and focus node highlighting
  const nvlNodes: NvlNode[] = useMemo(() => {
    return nodes.map((node) => {
      const isFocus = node.id === focusNodeId;
      // Calculate size: focus node is 1.5x larger
      const baseSize = isExpanded ? 22 : 16;
      const focusSize = isExpanded ? 35 : 25;

      return {
        id: node.id,
        // Ensure caption always has a value for label visibility
        caption: node.label || node.id || "Unknown",
        size: isFocus ? focusSize : baseSize,
        color: getNodeColor(node.type),
        selected: isFocus,
      };
    });
  }, [nodes, focusNodeId, isExpanded]);

  const nvlRels: NvlRelationship[] = useMemo(() => {
    return relationships.map((rel) => ({
      id: rel.id,
      from: rel.from,
      to: rel.to,
      caption: rel.type,
    }));
  }, [relationships]);

  // Get unique node types for legend
  const nodeTypes = useMemo(() => {
    const types = new Set(nodes.map((n) => n.type));
    return Array.from(types);
  }, [nodes]);

  const graphContent = (height: string) => (
    <Box height={height} width="100%" bg="white" position="relative">
      {nodes.length === 0 ? (
        <VStack height="100%" justify="center">
          <Text fontSize="sm" color="fg.muted">
            No graph data available
          </Text>
        </VStack>
      ) : (
        <>
          <InteractiveNvlWrapper
            nodes={nvlNodes}
            rels={nvlRels}
            mouseEventCallbacks={{
              onNodeClick: (node: NvlNode) => {
                const original = nodes.find((n) => n.id === node.id);
                if (original) setSelectedNode(original);
              },
              onPan: isExpanded,
              onZoom: isExpanded,
              onDrag: isExpanded,
            }}
            nvlOptions={{
              layout: "d3Force",
              initialZoom: isExpanded ? 1 : 0.8,
              disableWebGL: false,
            }}
          />
          {/* Legend - shown in both compact and expanded modes */}
          {nodeTypes.length > 0 && (
            <Box
              position="absolute"
              bottom={isExpanded ? 4 : 2}
              left={isExpanded ? 4 : 2}
              bg="whiteAlpha.900"
              p={isExpanded ? 2 : 1.5}
              borderRadius="md"
              borderWidth="1px"
              borderColor="border.subtle"
              maxW={isExpanded ? "200px" : "160px"}
              boxShadow="sm"
            >
              {isExpanded && (
                <Text fontSize="xs" fontWeight="medium" mb={1}>
                  Node Types
                </Text>
              )}
              <Flex wrap="wrap" gap={1}>
                {/* Show all types in expanded, limit to 4 in compact */}
                {nodeTypes.slice(0, isExpanded ? undefined : 4).map((type) => (
                  <HStack key={type} gap={1}>
                    <Box
                      w={isExpanded ? 3 : 2.5}
                      h={isExpanded ? 3 : 2.5}
                      borderRadius="full"
                      bg={getNodeColor(type)}
                      flexShrink={0}
                    />
                    <Text fontSize="xs">{type}</Text>
                  </HStack>
                ))}
                {!isExpanded && nodeTypes.length > 4 && (
                  <Text fontSize="xs" color="fg.muted">
                    +{nodeTypes.length - 4}
                  </Text>
                )}
              </Flex>
            </Box>
          )}
          {/* Selected node info - only in expanded mode */}
          {isExpanded && selectedNode && (
            <Box
              position="absolute"
              top={4}
              right={4}
              bg="white"
              p={3}
              borderRadius="md"
              borderWidth="1px"
              borderColor="border.subtle"
              maxW="250px"
            >
              <Text fontSize="sm" fontWeight="bold">
                {selectedNode.label}
              </Text>
              <Badge size="sm" colorPalette="brand" mt={1}>
                {selectedNode.type}
              </Badge>
              {selectedNode.properties && (
                <Box mt={2}>
                  {Object.entries(selectedNode.properties)
                    .filter(([, v]) => v !== undefined && v !== null)
                    .slice(0, 3)
                    .map(([key, value]) => (
                      <Text key={key} fontSize="xs" color="fg.muted">
                        <Text as="span" fontWeight="medium">
                          {key}:
                        </Text>{" "}
                        {String(value).slice(0, 50)}
                        {String(value).length > 50 ? "..." : ""}
                      </Text>
                    ))}
                </Box>
              )}
            </Box>
          )}
        </>
      )}
    </Box>
  );

  // Footer summary
  const footerText = `${nodes.length} node${nodes.length !== 1 ? "s" : ""} · ${relationships.length} relationship${relationships.length !== 1 ? "s" : ""}`;

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
                    <LuNetwork />
                    Related Entities ({nodes.length})
                  </Flex>
                </DialogTitle>
                <DialogCloseTrigger asChild>
                  <CloseButton size="sm" />
                </DialogCloseTrigger>
              </DialogHeader>
              <DialogBody p={0} height="calc(100vh - 80px)">
                {graphContent("100%")}
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
      title={`Related (${nodes.length})`}
      icon={<LuNetwork size={14} />}
      colorPalette="purple"
      isExpanded={isExpanded}
      onExpand={onExpand}
      onCollapse={onCollapse}
      compactHeight={compactHeight}
      footer={footerText}
    >
      {graphContent(`${compactHeight}px`)}
    </BaseCard>
  );
}
