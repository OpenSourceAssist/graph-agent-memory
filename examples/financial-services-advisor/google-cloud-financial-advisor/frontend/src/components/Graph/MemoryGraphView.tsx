import { useEffect, useState, useCallback, useRef } from 'react'
import { Box, Heading, Text, Spinner, Flex, Badge, HStack } from '@chakra-ui/react'
import { InteractiveNvlWrapper } from '@neo4j-nvl/react'
import type { Node, Relationship } from '@neo4j-nvl/base'
import { LuNetwork, LuRefreshCw } from 'react-icons/lu'
import api from '../../lib/api'

const NODE_COLORS: Record<string, string> = {
  Customer: '#68BDF6',
  Organization: '#FB95AF',
  Transaction: '#FFD86E',
  Alert: '#FF6B6B',
  SanctionedEntity: '#E74C3C',
  PEP: '#9B59B6',
  Document: '#A5D6A7',
  Investigation: '#F39C12',
  Entity: '#DE9BF9',
  Person: '#68BDF6',
  PEPRelative: '#BB8FCE',
  SanctionAlias: '#E6B0AA',
}

function getNodeColor(labels: string[]): string {
  for (const label of labels) {
    if (NODE_COLORS[label]) return NODE_COLORS[label]
  }
  return '#95A5A6'
}

interface GraphData {
  nodes: Array<{
    id: string
    label: string
    labels: string[]
    properties: Record<string, unknown>
  }>
  relationships: Array<{
    id: string
    from: string
    to: string
    type: string
  }>
}

export default function MemoryGraphView() {
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const nvlRef = useRef<any>(null)

  const fetchGraph = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data } = await api.get('/graph/memory', { params: { limit: 500 } })
      setGraphData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load graph')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchGraph()
  }, [fetchGraph])

  const fetchNeighbors = useCallback(async (nodeId: string) => {
    try {
      const { data } = await api.get(`/graph/neighbors/${encodeURIComponent(nodeId)}`, {
        params: { depth: 1, limit: 20 },
      })
      if (data.nodes && graphData) {
        const existingIds = new Set(graphData.nodes.map(n => n.id))
        const newNodes = (data.nodes as any[])
          .filter((n: any) => !existingIds.has(n.id))
          .map((n: any) => ({
            id: n.id,
            label: n.label || n.id,
            labels: [n.type || 'Unknown'],
            properties: n,
          }))
        const newEdges = (data.edges || []).map((e: any, i: number) => ({
          id: `expanded-${nodeId}-${i}`,
          from: e.from || nodeId,
          to: e.to,
          type: e.relationship || 'RELATED',
        }))
        setGraphData(prev => prev ? {
          nodes: [...prev.nodes, ...newNodes],
          relationships: [...prev.relationships, ...newEdges],
        } : prev)
      }
    } catch {
      // Silently fail on neighbor expansion
    }
  }, [graphData])

  if (loading) {
    return (
      <Flex h="calc(100vh - 48px)" align="center" justify="center">
        <Spinner size="lg" />
        <Text ml={3}>Loading graph...</Text>
      </Flex>
    )
  }

  if (error) {
    return (
      <Flex h="calc(100vh - 48px)" align="center" justify="center" direction="column">
        <Text color="red.500">{error}</Text>
        <Text fontSize="sm" color="gray.500" mt={2}>Make sure sample data is loaded (make load-data)</Text>
      </Flex>
    )
  }

  if (!graphData || graphData.nodes.length === 0) {
    return (
      <Flex h="calc(100vh - 48px)" align="center" justify="center" direction="column">
        <LuNetwork size={48} color="gray" />
        <Text mt={4} color="gray.500">No graph data. Run "make load-data" first.</Text>
      </Flex>
    )
  }

  const nvlNodes: Node[] = graphData.nodes.map(n => ({
    id: n.id,
    caption: n.label || n.id,
    color: getNodeColor(n.labels || []),
    size: n.labels?.includes('Customer') ? 30 : 20,
  }))

  const nvlRels: Relationship[] = graphData.relationships
    .filter(r => r.from && r.to)
    .map(r => ({
      id: r.id,
      from: r.from,
      to: r.to,
      caption: r.type,
    }))

  return (
    <Box h="calc(100vh - 48px)">
      <Flex direction="column" h="full">
        <Flex justify="space-between" align="center" mb={2} px={2}>
          <HStack>
            <LuNetwork size={20} />
            <Heading size="md">Context Graph</Heading>
            <Badge colorPalette="blue">{graphData.nodes.length} nodes</Badge>
            <Badge colorPalette="gray">{graphData.relationships.length} relationships</Badge>
          </HStack>
          <HStack>
            <Text fontSize="xs" color="gray.500">Double-click a node to expand</Text>
            <Box cursor="pointer" onClick={fetchGraph} title="Refresh">
              <LuRefreshCw size={16} />
            </Box>
          </HStack>
        </Flex>

        <Flex mb={2} px={2} gap={2} flexWrap="wrap">
          {Object.entries(NODE_COLORS).slice(0, 8).map(([label, color]) => (
            <Badge key={label} size="sm" style={{ borderLeft: `3px solid ${color}` }} pl={2}>
              {label}
            </Badge>
          ))}
        </Flex>

        <Box flex={1} border="1px solid" borderColor="gray.200" borderRadius="md" overflow="hidden">
          <InteractiveNvlWrapper
            ref={nvlRef}
            nodes={nvlNodes}
            rels={nvlRels}
            nvlOptions={{
              layout: 'force-directed',
              relationshipThreshold: 0.55,
            }}
            nvlCallbacks={{
              onNodeDoubleClick: (node: Node) => {
                if (node.id) fetchNeighbors(node.id)
              },
            }}
          />
        </Box>
      </Flex>
    </Box>
  )
}
