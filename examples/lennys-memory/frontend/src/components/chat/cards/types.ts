/**
 * TypeScript interfaces for tool result card components.
 */

import type { ToolCall } from "@/lib/types";
import type { ReactNode } from "react";

/**
 * Card type enumeration for tool result visualization
 */
export type CardType =
  | "map"
  | "graph"
  | "data"
  | "stats"
  | "entity"
  | "memory_graph"
  | "raw";

/**
 * Base props shared by all card components
 */
export interface BaseCardProps {
  /** The tool call data including result */
  toolCall: ToolCall;
  /** Whether the card is in compact (inline) or expanded (fullscreen) mode */
  isExpanded?: boolean;
  /** Callback to request fullscreen expansion */
  onExpand?: () => void;
  /** Callback when fullscreen is closed */
  onCollapse?: () => void;
  /** Height of the card in compact mode */
  compactHeight?: number;
}

/**
 * Location data for MapCard
 */
export interface LocationData {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  subtype?: string;
  description?: string;
  episodeCount?: number;
}

/**
 * Path node for map path visualization
 */
export interface PathNode {
  id: string;
  name: string;
  latitude?: number;
  longitude?: number;
}

/**
 * Map card specific props
 */
export interface MapCardProps extends BaseCardProps {
  /** Locations to display on the map */
  locations: LocationData[];
  /** Optional center point override */
  center?: [number, number];
  /** Optional zoom level override */
  zoom?: number;
  /** Show path between locations */
  showPath?: boolean;
  /** Path nodes if showing path */
  pathNodes?: PathNode[];
}

/**
 * Graph node data for inline visualization
 */
export interface GraphNodeData {
  id: string;
  label: string;
  type: string;
  properties?: Record<string, unknown>;
}

/**
 * Graph relationship data
 */
export interface GraphRelationshipData {
  id: string;
  from: string;
  to: string;
  type: string;
}

/**
 * Graph card specific props
 */
export interface GraphCardProps extends BaseCardProps {
  /** Nodes to display in the graph */
  nodes: GraphNodeData[];
  /** Relationships between nodes */
  relationships: GraphRelationshipData[];
  /** Optional node to highlight/center */
  focusNodeId?: string;
}

/**
 * Column definition for DataCard table
 */
export interface ColumnDef {
  key: string;
  label: string;
  width?: string;
  render?: (value: unknown, row: Record<string, unknown>) => ReactNode;
}

/**
 * Data card props for table/list display
 */
export interface DataCardProps extends BaseCardProps {
  /** Column definitions for table view */
  columns: ColumnDef[];
  /** Row data */
  rows: Record<string, unknown>[];
  /** Optional title override */
  title?: string;
  /** Maximum rows to show in compact mode */
  compactRowLimit?: number;
}

/**
 * Individual stat item
 */
export interface StatItem {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: ReactNode;
  colorPalette?: string;
}

/**
 * Chart data point for sparklines
 */
export interface ChartDataPoint {
  label: string;
  value: number;
}

/**
 * Stats card props for metrics display
 */
export interface StatsCardProps extends BaseCardProps {
  /** Statistics to display */
  stats: StatItem[];
  /** Optional chart data for sparklines */
  chartData?: ChartDataPoint[];
}

/**
 * Tool name to card type mapping configuration
 */
export interface ToolCardMapping {
  cardType: CardType;
  title?: string;
  icon?: string;
}

/**
 * Entity data for EntityCard
 */
export interface EntityData {
  id: string;
  name: string;
  type: string;
  subtype?: string;
  description?: string;
  enriched_description?: string;
  wikipedia_url?: string;
  wikidata_id?: string;
  image_url?: string;
  confidence?: number;
}

/**
 * Entity mention from podcast
 */
export interface EntityMention {
  content: string;
  speaker?: string;
  episode?: string;
  session_id?: string;
}

/**
 * Related entity reference
 */
export interface RelatedEntity {
  id: string;
  name: string;
  type: string;
  subtype?: string;
  co_occurrences?: number;
}

/**
 * Entity card props for knowledge panel display
 */
export interface EntityCardProps extends BaseCardProps {
  /** The entity data */
  entity: EntityData;
  /** Podcast mentions of this entity */
  mentions?: EntityMention[];
  /** Related entities through co-occurrence */
  relatedEntities?: RelatedEntity[];
}
