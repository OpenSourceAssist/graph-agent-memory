"use client";

import {
  Box,
  SimpleGrid,
  VStack,
  Text,
  Badge,
  Portal,
  CloseButton,
  Flex,
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
import { BaseCard } from "./BaseCard";
import { LuChartBar } from "react-icons/lu";
import type { StatsCardProps, StatItem } from "./types";

/**
 * Individual stat box component
 */
function StatBox({ stat }: { stat: StatItem }) {
  const colorPalette = stat.colorPalette || "gray";

  return (
    <Box
      p={3}
      borderRadius="md"
      bg={`${colorPalette}.subtle`}
      borderWidth="1px"
      borderColor={`${colorPalette}.muted`}
    >
      <Text
        fontSize={{ base: "xl", md: "2xl" }}
        fontWeight="bold"
        color={`${colorPalette}.fg`}
      >
        {typeof stat.value === "number"
          ? stat.value.toLocaleString()
          : stat.value}
      </Text>
      <Text fontSize="xs" color="fg.muted" mt={1} lineClamp={2}>
        {stat.label}
      </Text>
      {stat.change !== undefined && (
        <Badge
          size="sm"
          colorPalette={stat.change >= 0 ? "green" : "red"}
          mt={1}
        >
          {stat.change >= 0 ? "+" : ""}
          {stat.change}%
        </Badge>
      )}
      {stat.changeLabel && (
        <Text fontSize="xs" color="fg.muted">
          {stat.changeLabel}
        </Text>
      )}
    </Box>
  );
}

/**
 * StatsCard displays key metrics in a grid layout.
 * Features:
 * - Responsive grid (2 columns mobile, 3 desktop)
 * - Color-coded by metric type
 * - Numeric formatting with locale support
 * - Optional change indicators
 */
export function StatsCard({
  toolCall,
  stats,
  isExpanded = false,
  onExpand,
  onCollapse,
  compactHeight = 200,
}: StatsCardProps) {
  const displayStats = isExpanded ? stats : stats.slice(0, 6);

  const statsContent = (
    <Box height="100%" p={3} overflow="auto">
      {stats.length === 0 ? (
        <VStack height="100%" justify="center">
          <Text fontSize="sm" color="fg.muted">
            No statistics available
          </Text>
        </VStack>
      ) : (
        <SimpleGrid columns={{ base: 2, sm: 3 }} gap={3}>
          {displayStats.map((stat, idx) => (
            <StatBox key={idx} stat={stat} />
          ))}
        </SimpleGrid>
      )}
    </Box>
  );

  // Footer summary
  const footerText = `${stats.length} metric${stats.length !== 1 ? "s" : ""}`;

  // Fullscreen dialog
  if (isExpanded) {
    return (
      <DialogRoot open={true} size="lg" onOpenChange={() => onCollapse?.()}>
        <Portal>
          <DialogBackdrop />
          <DialogPositioner>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>
                  <Flex align="center" gap={2}>
                    <LuChartBar />
                    Statistics
                  </Flex>
                </DialogTitle>
                <DialogCloseTrigger asChild>
                  <CloseButton size="sm" />
                </DialogCloseTrigger>
              </DialogHeader>
              <DialogBody p={4}>{statsContent}</DialogBody>
            </DialogContent>
          </DialogPositioner>
        </Portal>
      </DialogRoot>
    );
  }

  return (
    <BaseCard
      toolCall={toolCall}
      title="Statistics"
      icon={<LuChartBar size={14} />}
      colorPalette="amber"
      isExpanded={isExpanded}
      onExpand={onExpand}
      onCollapse={onCollapse}
      compactHeight={compactHeight}
      footer={footerText}
    >
      {statsContent}
    </BaseCard>
  );
}
