/**
 * Registry for mapping tool names to card types and data extractors.
 */

import type { ToolCall } from "@/lib/types";
import type {
  CardType,
  LocationData,
  PathNode,
  GraphNodeData,
  GraphRelationshipData,
  StatItem,
  ColumnDef,
  EntityData,
  EntityMention,
  RelatedEntity,
} from "./types";

/**
 * Determines which card type to render based on tool name and result structure
 */
export function getCardTypeForTool(
  toolName: string,
  result: unknown,
): CardType {
  const name = toolName.toLowerCase();

  // Location tools -> MapCard
  if (
    name.includes("location") ||
    name.includes("_near") ||
    name.includes("_path") ||
    name.includes("_clusters")
  ) {
    if (hasLocationData(result)) {
      return "map";
    }
  }

  // Entity context -> EntityCard (knowledge panel)
  if (name.includes("entity_context") || name.includes("get_entity")) {
    if (hasEntityData(result)) {
      return "entity";
    }
  }

  // Related entities -> GraphCard (shows relationships)
  if (name.includes("related_entities")) {
    return "graph";
  }

  // Memory graph search -> MemoryGraphCard (combined vector + graph visualization)
  if (name.includes("memory_graph_search")) {
    return "memory_graph";
  }

  // Stats tools -> StatsCard
  if (
    name.includes("get_stats") ||
    name.includes("top_entities") ||
    name.includes("memory_stats")
  ) {
    return "stats";
  }

  // Search results, lists, entity data -> DataCard
  if (
    name.includes("search") ||
    name.includes("list") ||
    name.includes("get_entity") ||
    name.includes("preferences") ||
    name.includes("similar") ||
    name.includes("speaker")
  ) {
    return "data";
  }

  // Default fallback
  return "raw";
}

/**
 * Type guard to check if result contains entity data
 */
function hasEntityData(result: unknown): boolean {
  if (!result || typeof result !== "object") return false;

  // Check for entity context format { entity: {...}, mentions: [...] }
  if ("entity" in result) {
    const entity = (result as { entity: unknown }).entity;
    return (
      entity !== null &&
      typeof entity === "object" &&
      "name" in (entity as Record<string, unknown>)
    );
  }

  // Check for direct entity format { name, type, ... }
  if ("name" in result && "type" in result) {
    return true;
  }

  return false;
}

/**
 * Type guard to check if result contains location data
 */
function hasLocationData(result: unknown): boolean {
  if (!result || typeof result !== "object") return false;

  // Check for array of locations
  if (Array.isArray(result)) {
    return (
      result.length > 0 &&
      result[0] &&
      typeof result[0] === "object" &&
      "latitude" in result[0] &&
      "longitude" in result[0]
    );
  }

  // Check for path result with nodes
  if (
    "nodes" in result &&
    Array.isArray((result as { nodes: unknown[] }).nodes)
  ) {
    const nodes = (result as { nodes: unknown[] }).nodes;
    return nodes.some(
      (n) =>
        n &&
        typeof n === "object" &&
        "latitude" in (n as Record<string, unknown>) &&
        "longitude" in (n as Record<string, unknown>),
    );
  }

  // Check for clusters result
  if (
    "clusters" in result &&
    Array.isArray((result as { clusters: unknown[] }).clusters)
  ) {
    return true;
  }

  return false;
}

/**
 * Extract location data from various tool result formats
 */
export function extractLocations(result: unknown): LocationData[] {
  if (!result) return [];

  // Direct array of locations
  if (Array.isArray(result)) {
    return result
      .filter(
        (item): item is Record<string, unknown> =>
          item &&
          typeof item === "object" &&
          "latitude" in item &&
          "longitude" in item,
      )
      .map((item) => ({
        id: String(item.id || Math.random()),
        name: String(item.name || "Unknown"),
        latitude: Number(item.latitude),
        longitude: Number(item.longitude),
        subtype: item.subtype as string | undefined,
        description: String(
          item.description || item.enriched_description || "",
        ),
        episodeCount: Array.isArray(item.conversations)
          ? item.conversations.length
          : (item.episode_count as number | undefined),
      }));
  }

  // Path result format
  if (typeof result === "object" && result !== null && "nodes" in result) {
    const pathResult = result as { nodes: unknown[] };
    return pathResult.nodes
      .filter((n): n is Record<string, unknown> => {
        if (n === null || n === undefined || typeof n !== "object")
          return false;
        const obj = n as Record<string, unknown>;
        return "latitude" in obj && "longitude" in obj;
      })
      .map((n) => ({
        id: String(n.id || Math.random()),
        name: String(n.name || n.id || "Unknown"),
        latitude: Number(n.latitude),
        longitude: Number(n.longitude),
        subtype: n.subtype as string | undefined,
      }));
  }

  // Clusters result format
  if (typeof result === "object" && result !== null && "clusters" in result) {
    const clustersResult = result as { clusters: unknown[] };
    const locations: LocationData[] = [];
    clustersResult.clusters.forEach((cluster) => {
      if (
        cluster &&
        typeof cluster === "object" &&
        "locations" in (cluster as Record<string, unknown>)
      ) {
        const clusterData = cluster as {
          locations: unknown[];
          country?: string;
        };
        const clusterLocs = clusterData.locations as Record<string, unknown>[];
        clusterLocs.forEach((loc) => {
          if ("latitude" in loc && "longitude" in loc) {
            locations.push({
              id: String(loc.id || Math.random()),
              name: String(loc.name || "Unknown"),
              latitude: Number(loc.latitude),
              longitude: Number(loc.longitude),
              subtype: (loc.subtype as string) || clusterData.country,
            });
          }
        });
      }
    });
    return locations;
  }

  return [];
}

/**
 * Extract path nodes for map visualization
 */
export function extractPathNodes(result: unknown): PathNode[] {
  if (!result || typeof result !== "object" || !("nodes" in result)) return [];

  const pathResult = result as { nodes: unknown[] };
  return pathResult.nodes.map((n) => {
    const node = n as Record<string, unknown>;
    return {
      id: String(node.id || Math.random()),
      name: String(node.name || node.id || "Unknown"),
      latitude: node.latitude as number | undefined,
      longitude: node.longitude as number | undefined,
    };
  });
}

/**
 * Extract graph data for visualization
 */
export function extractGraphData(result: unknown): {
  nodes: GraphNodeData[];
  relationships: GraphRelationshipData[];
} {
  if (!result || typeof result !== "object") {
    return { nodes: [], relationships: [] };
  }

  // Related entities format (array)
  if (Array.isArray(result)) {
    // Create nodes from related entities
    const nodes: GraphNodeData[] = result.map((entity, idx) => {
      const e = entity as Record<string, unknown>;
      return {
        id: String(e.id || e.name || idx),
        label: String(e.name || "Unknown"),
        type: String(e.type || "Entity"),
        properties: {
          coOccurrences: e.co_occurrences,
          subtype: e.subtype,
          description: e.description,
        },
      };
    });

    // Create relationships (all connected to a central node if there's more than one)
    const relationships: GraphRelationshipData[] = [];
    if (nodes.length > 1) {
      const centralNode = nodes[0];
      for (let i = 1; i < nodes.length; i++) {
        relationships.push({
          id: `rel-${i}`,
          from: centralNode.id,
          to: nodes[i].id,
          type: "RELATED_TO",
        });
      }
    }

    return { nodes, relationships };
  }

  // Entity context format (single entity with mentions)
  if ("entity" in result || "name" in result) {
    const entity =
      (result as { entity?: Record<string, unknown> }).entity ||
      (result as Record<string, unknown>);
    const mentions = (result as { mentions?: unknown[] }).mentions || [];

    const nodes: GraphNodeData[] = [
      {
        id: String(entity.id || entity.name),
        label: String(entity.name || "Unknown"),
        type: String(entity.type || "Entity"),
        properties: entity,
      },
    ];

    // Add mention nodes
    mentions.forEach((mention, idx) => {
      const m = mention as Record<string, unknown>;
      nodes.push({
        id: `mention-${idx}`,
        label: String(m.speaker || m.episode || `Mention ${idx + 1}`),
        type: "Mention",
        properties: m,
      });
    });

    // Create relationships from entity to mentions
    const relationships: GraphRelationshipData[] = mentions.map((_, idx) => ({
      id: `rel-mention-${idx}`,
      from: nodes[0].id,
      to: `mention-${idx}`,
      type: "MENTIONED_IN",
    }));

    return { nodes, relationships };
  }

  return { nodes: [], relationships: [] };
}

/**
 * Extract stats from tool results
 */
export function extractStats(toolName: string, result: unknown): StatItem[] {
  if (!result || typeof result !== "object") return [];

  const stats: StatItem[] = [];
  const name = toolName.toLowerCase();

  if (name.includes("get_stats") || name.includes("memory_stats")) {
    const r = result as Record<string, unknown>;
    if (r.total_episodes !== undefined) {
      stats.push({
        label: "Episodes",
        value: Number(r.total_episodes),
        colorPalette: "blue",
      });
    }
    if (r.total_speakers !== undefined) {
      stats.push({
        label: "Speakers",
        value: Number(r.total_speakers),
        colorPalette: "green",
      });
    }
    if (r.total_messages !== undefined) {
      stats.push({
        label: "Messages",
        value: Number(r.total_messages),
        colorPalette: "purple",
      });
    }
    if (r.total_entities !== undefined) {
      stats.push({
        label: "Entities",
        value: Number(r.total_entities),
        colorPalette: "orange",
      });
    }
    if (r.total_locations !== undefined) {
      stats.push({
        label: "Locations",
        value: Number(r.total_locations),
        colorPalette: "teal",
      });
    }
    if (r.total_preferences !== undefined) {
      stats.push({
        label: "Preferences",
        value: Number(r.total_preferences),
        colorPalette: "amber",
      });
    }
  }

  if (name.includes("top_entities") && Array.isArray(result)) {
    // Map entity types to color palettes matching EntityCard colors
    const typeColors: Record<string, string> = {
      PERSON: "pink",
      ORGANIZATION: "orange",
      LOCATION: "blue",
      EVENT: "purple",
      CONCEPT: "green",
      TOPIC: "green",
      OBJECT: "cyan",
    };
    const fallbackColors = [
      "blue",
      "green",
      "purple",
      "orange",
      "teal",
      "pink",
    ];

    result.slice(0, 6).forEach((entity, i) => {
      const e = entity as Record<string, unknown>;
      const entityType = String(e.type || "").toUpperCase();
      // Use type-specific color if available, otherwise cycle through fallback colors
      const colorPalette =
        typeColors[entityType] || fallbackColors[i % fallbackColors.length];

      stats.push({
        label: String(e.name || "Unknown"),
        value: Number(e.mentions || e.count || e.mention_count || 0),
        colorPalette,
      });
    });
  }

  return stats;
}

/**
 * Extract table columns and rows from search results
 */
export function extractTableData(
  toolName: string,
  result: unknown,
): {
  columns: ColumnDef[];
  rows: Record<string, unknown>[];
  title?: string;
} {
  if (!result || !Array.isArray(result)) {
    return { columns: [], rows: [] };
  }

  const name = toolName.toLowerCase();
  let columns: ColumnDef[] = [];
  let title: string | undefined;

  // Podcast search results (including search_episode which returns transcript segments)
  if (
    name.includes("search_podcast") ||
    name.includes("search_by_speaker") ||
    name.includes("search_episode")
  ) {
    title = "Podcast Matches";
    columns = [
      { key: "speaker", label: "Speaker", width: "20%" },
      { key: "content", label: "Content", width: "60%" },
      { key: "episode_guest", label: "Episode", width: "20%" },
    ];
  }
  // Episode list (but not search_episode which is handled above)
  else if (name.includes("list_episode") || name === "episode") {
    title = "Episodes";
    columns = [
      { key: "guest", label: "Guest", width: "50%" },
      { key: "session_id", label: "Episode ID", width: "30%" },
      { key: "message_count", label: "Messages", width: "20%" },
    ];
  }
  // Speaker list
  else if (name.includes("list_speaker") || name.includes("speaker")) {
    title = "Speakers";
    columns = [
      { key: "name", label: "Name", width: "40%" },
      { key: "role", label: "Role", width: "30%" },
      { key: "episode_count", label: "Episodes", width: "30%" },
    ];
  }
  // Entity search
  else if (name.includes("entities") || name.includes("entity")) {
    title = "Entities";
    columns = [
      { key: "name", label: "Name", width: "25%" },
      { key: "type", label: "Type", width: "15%" },
      { key: "subtype", label: "Subtype", width: "15%" },
      { key: "description", label: "Description", width: "45%" },
    ];
  }
  // Preferences
  else if (name.includes("preferences")) {
    title = "User Preferences";
    columns = [
      { key: "category", label: "Category", width: "25%" },
      { key: "preference", label: "Preference", width: "50%" },
      { key: "confidence", label: "Confidence", width: "25%" },
    ];
  }
  // Similar queries
  else if (name.includes("similar")) {
    title = "Similar Past Queries";
    columns = [
      { key: "task", label: "Query", width: "50%" },
      { key: "outcome", label: "Outcome", width: "35%" },
      { key: "similarity", label: "Match", width: "15%" },
    ];
  }
  // Auto-detect columns from first result
  else if (result.length > 0) {
    const firstRow = result[0] as Record<string, unknown>;
    columns = Object.keys(firstRow)
      .filter(
        (key) => !key.startsWith("_") && key !== "id" && key !== "embedding",
      )
      .slice(0, 4)
      .map((key) => ({
        key,
        label: key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase()),
      }));
  }

  return {
    columns,
    rows: result as Record<string, unknown>[],
    title,
  };
}

/**
 * Extract entity data from tool result
 */
export function extractEntityData(result: unknown): {
  entity: EntityData;
  mentions: EntityMention[];
  relatedEntities: RelatedEntity[];
} | null {
  if (!result || typeof result !== "object") return null;

  let entity: EntityData | null = null;
  let mentions: EntityMention[] = [];
  let relatedEntities: RelatedEntity[] = [];

  // Entity context format: { entity: {...}, mentions: [...] }
  if ("entity" in result) {
    const entityResult = result as {
      entity: Record<string, unknown>;
      mentions?: unknown[];
      related_entities?: unknown[];
    };

    const e = entityResult.entity;
    entity = {
      id: String(e.id || ""),
      name: String(e.name || "Unknown"),
      type: String(e.type || "UNKNOWN"),
      subtype: e.subtype as string | undefined,
      description: e.description as string | undefined,
      enriched_description: e.enriched_description as string | undefined,
      wikipedia_url: e.wikipedia_url as string | undefined,
      wikidata_id: e.wikidata_id as string | undefined,
      image_url: e.image_url as string | undefined,
      confidence: e.confidence as number | undefined,
    };

    // Extract mentions
    if (entityResult.mentions && Array.isArray(entityResult.mentions)) {
      mentions = entityResult.mentions.map((m) => {
        const mention = m as Record<string, unknown>;
        return {
          content: String(mention.content || ""),
          speaker: mention.speaker as string | undefined,
          episode: (mention.episode_guest ||
            mention.episode ||
            mention.session_id) as string | undefined,
          session_id: mention.session_id as string | undefined,
        };
      });
    }

    // Extract related entities
    if (
      entityResult.related_entities &&
      Array.isArray(entityResult.related_entities)
    ) {
      relatedEntities = entityResult.related_entities.map((r) => {
        const rel = r as Record<string, unknown>;
        return {
          id: String(rel.id || ""),
          name: String(rel.name || "Unknown"),
          type: String(rel.type || "UNKNOWN"),
          subtype: rel.subtype as string | undefined,
          co_occurrences: rel.co_occurrences as number | undefined,
        };
      });
    }
  }
  // Direct entity format: { name, type, ... }
  else if ("name" in result && "type" in result) {
    const e = result as Record<string, unknown>;
    entity = {
      id: String(e.id || ""),
      name: String(e.name || "Unknown"),
      type: String(e.type || "UNKNOWN"),
      subtype: e.subtype as string | undefined,
      description: e.description as string | undefined,
      enriched_description: e.enriched_description as string | undefined,
      wikipedia_url: e.wikipedia_url as string | undefined,
      wikidata_id: e.wikidata_id as string | undefined,
      image_url: e.image_url as string | undefined,
      confidence: e.confidence as number | undefined,
    };
  }

  if (!entity) return null;

  return { entity, mentions, relatedEntities };
}

/**
 * Get a friendly display title for a tool
 */
export function getToolDisplayTitle(toolName: string): string {
  const name = toolName
    .replace(/^tool_/, "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (l) => l.toUpperCase());

  return name;
}

/**
 * Memory graph node for visualization
 */
export interface MemoryGraphNode {
  id: string;
  label: string;
  type: string;
  properties?: Record<string, unknown>;
}

/**
 * Memory graph relationship for visualization
 */
export interface MemoryGraphRelationship {
  id: string;
  from: string;
  to: string;
  type: string;
}

/**
 * Memory graph search result summary
 */
export interface MemoryGraphSummary {
  messages_found: number;
  entities_found: number;
  relationships_found: number;
}

/**
 * Complete memory graph search result
 */
export interface MemoryGraphSearchResult {
  query: string;
  nodes: MemoryGraphNode[];
  relationships: MemoryGraphRelationship[];
  summary: MemoryGraphSummary;
  error?: string;
  message?: string;
}

/**
 * Extract memory graph data from tool result
 */
export function extractMemoryGraphData(
  result: unknown,
): MemoryGraphSearchResult | null {
  if (!result || typeof result !== "object") return null;

  const r = result as Record<string, unknown>;

  // Check for error response
  if (r.error) {
    return {
      query: String(r.query || ""),
      nodes: [],
      relationships: [],
      summary: {
        messages_found: 0,
        entities_found: 0,
        relationships_found: 0,
      },
      error: String(r.error),
    };
  }

  // Check for valid memory graph structure
  if (!("nodes" in r) || !Array.isArray(r.nodes)) return null;

  return {
    query: String(r.query || ""),
    nodes: (r.nodes as unknown[]).map((n) => {
      const node = n as Record<string, unknown>;
      return {
        id: String(node.id || ""),
        label: String(node.label || "Unknown"),
        type: String(node.type || "Entity"),
        properties: node.properties as Record<string, unknown> | undefined,
      };
    }),
    relationships: ((r.relationships as unknown[]) || []).map((rel) => {
      const relationship = rel as Record<string, unknown>;
      return {
        id: String(relationship.id || ""),
        from: String(relationship.from || ""),
        to: String(relationship.to || ""),
        type: String(relationship.type || "RELATED"),
      };
    }),
    summary: (r.summary as MemoryGraphSummary) || {
      messages_found: 0,
      entities_found: 0,
      relationships_found: 0,
    },
    message: r.message as string | undefined,
  };
}
