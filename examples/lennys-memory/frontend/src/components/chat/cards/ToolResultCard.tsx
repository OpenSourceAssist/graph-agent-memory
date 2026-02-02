"use client";

import { useState, useMemo } from "react";
import type { ToolCall } from "@/lib/types";
import { MapCard } from "./MapCard";
import { GraphCard } from "./GraphCard";
import { DataCard } from "./DataCard";
import { StatsCard } from "./StatsCard";
import { EntityCard } from "./EntityCard";
import { RawJsonCard } from "./RawJsonCard";
import {
  getCardTypeForTool,
  extractLocations,
  extractPathNodes,
  extractGraphData,
  extractStats,
  extractTableData,
  extractEntityData,
} from "./toolCardRegistry";

interface ToolResultCardProps {
  toolCall: ToolCall;
}

/**
 * ToolResultCard is the smart selector that determines which card type
 * to render based on the tool name and result structure.
 *
 * Flow:
 * 1. Parse the result (may be JSON string from backend)
 * 2. Determine card type using getCardTypeForTool
 * 3. Extract relevant data using appropriate extractor
 * 4. Render the specific card component
 */
export function ToolResultCard({ toolCall }: ToolResultCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Parse the result (it may be a JSON string from the backend)
  const parsedResult = useMemo(() => {
    let result = toolCall.result;
    if (typeof result === "string") {
      try {
        result = JSON.parse(result);
      } catch {
        // Keep as string if not valid JSON
      }
    }
    return result;
  }, [toolCall.result]);

  // Determine card type
  const cardType = useMemo(() => {
    return getCardTypeForTool(toolCall.name, parsedResult);
  }, [toolCall.name, parsedResult]);

  const handleExpand = () => setIsExpanded(true);
  const handleCollapse = () => setIsExpanded(false);

  // If no result yet, return null (tool is still pending)
  if (toolCall.result === undefined) {
    return null;
  }

  // Render appropriate card based on type
  switch (cardType) {
    case "map": {
      const locations = extractLocations(parsedResult);
      const pathNodes = extractPathNodes(parsedResult);
      const showPath =
        toolCall.name.toLowerCase().includes("path") && pathNodes.length > 1;

      return (
        <MapCard
          toolCall={toolCall}
          locations={locations}
          showPath={showPath}
          pathNodes={pathNodes}
          isExpanded={isExpanded}
          onExpand={handleExpand}
          onCollapse={handleCollapse}
        />
      );
    }

    case "graph": {
      const { nodes, relationships } = extractGraphData(parsedResult);

      return (
        <GraphCard
          toolCall={toolCall}
          nodes={nodes}
          relationships={relationships}
          isExpanded={isExpanded}
          onExpand={handleExpand}
          onCollapse={handleCollapse}
        />
      );
    }

    case "stats": {
      const stats = extractStats(toolCall.name, parsedResult);

      return (
        <StatsCard
          toolCall={toolCall}
          stats={stats}
          isExpanded={isExpanded}
          onExpand={handleExpand}
          onCollapse={handleCollapse}
        />
      );
    }

    case "data": {
      const { columns, rows, title } = extractTableData(
        toolCall.name,
        parsedResult,
      );

      return (
        <DataCard
          toolCall={toolCall}
          columns={columns}
          rows={rows}
          title={title}
          isExpanded={isExpanded}
          onExpand={handleExpand}
          onCollapse={handleCollapse}
        />
      );
    }

    case "entity": {
      const entityData = extractEntityData(parsedResult);

      if (!entityData) {
        // Fall back to raw JSON if extraction fails
        return (
          <RawJsonCard
            toolCall={toolCall}
            isExpanded={isExpanded}
            onExpand={handleExpand}
            onCollapse={handleCollapse}
          />
        );
      }

      return (
        <EntityCard
          toolCall={toolCall}
          entity={entityData.entity}
          mentions={entityData.mentions}
          relatedEntities={entityData.relatedEntities}
          isExpanded={isExpanded}
          onExpand={handleExpand}
          onCollapse={handleCollapse}
        />
      );
    }

    default:
      return (
        <RawJsonCard
          toolCall={toolCall}
          isExpanded={isExpanded}
          onExpand={handleExpand}
          onCollapse={handleCollapse}
        />
      );
  }
}
