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
import { DialogRoot, DialogContent, DialogHeader, DialogTitle, DialogBody, DialogCloseTrigger, DialogBackdrop, DialogPositioner } from "@chakra-ui/react";
import dynamic from "next/dynamic";
import { BaseCard } from "./BaseCard";
import { LuNetwork } from "react-icons/lu";
import type { GraphCardProps, GraphNodeData } from "./types";
import { nodeColors } from "@/theme";

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
  }
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

  // Convert to NVL format
  const nvlNodes: NvlNode[] = useMemo(() => {
    return nodes.map((node) => ({
      id: node.id,
      caption: node.label,
      size: isExpanded ? 20 : 15,
      color: nodeColors[node.type as keyof typeof nodeColors] || nodeColors.default,
      selected: node.id === focusNodeId,
    }));
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
          {/* Legend - only in expanded mode */}
          {isExpanded && nodeTypes.length > 0 && (
            <Box
              position="absolute"
              bottom={4}
              left={4}
              bg="white"
              p={2}
              borderRadius="md"
              borderWidth="1px"
              borderColor="border.subtle"
              maxW="200px"
            >
              <Text fontSize="xs" fontWeight="medium" mb={1}>
                Node Types
              </Text>
              <Flex wrap="wrap" gap={1}>
                {nodeTypes.map((type) => (
                  <HStack key={type} gap={1}>
                    <Box
                      w={3}
                      h={3}
                      borderRadius="full"
                      bg={nodeColors[type as keyof typeof nodeColors] || nodeColors.default}
                    />
                    <Text fontSize="xs">{type}</Text>
                  </HStack>
                ))}
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
