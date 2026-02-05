import { useState, useEffect, useRef } from 'react'
import {
  Box,
  Card,
  Flex,
  Heading,
  Text,
  Button,
  Spinner,
  Badge,
  Input,
  SimpleGrid,
  Stat,
} from '@chakra-ui/react'
import { LuRefreshCw, LuZoomIn, LuZoomOut, LuMaximize } from 'react-icons/lu'
import { Network, DataSet } from 'vis-network/standalone'
import { getCustomerNetwork, getGraphStats, type NetworkData } from '../../lib/api'

interface NetworkViewerProps {
  customerId: string | null
}

const nodeColors: Record<string, string> = {
  Customer: '#4299E1',
  Organization: '#48BB78',
  Transaction: '#ECC94B',
  Alert: '#F56565',
  Account: '#9F7AEA',
  Address: '#ED8936',
  Document: '#38B2AC',
}

export function NetworkViewer({ customerId }: NetworkViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<Network | null>(null)
  const [loading, setLoading] = useState(false)
  const [networkData, setNetworkData] = useState<NetworkData | null>(null)
  const [stats, setStats] = useState<{
    nodes: { total: number; by_label: Record<string, number> }
    relationships: { total: number; by_type: Record<string, number> }
  } | null>(null)
  const [inputCustomerId, setInputCustomerId] = useState(customerId || '')
  const [depth, setDepth] = useState(2)

  useEffect(() => {
    loadStats()
  }, [])

  useEffect(() => {
    if (customerId) {
      setInputCustomerId(customerId)
      loadNetwork(customerId)
    }
  }, [customerId])

  useEffect(() => {
    if (networkData && containerRef.current) {
      renderNetwork()
    }
  }, [networkData])

  const loadStats = async () => {
    try {
      const data = await getGraphStats()
      setStats(data)
    } catch (error) {
      console.error('Failed to load graph stats:', error)
    }
  }

  const loadNetwork = async (custId: string) => {
    try {
      setLoading(true)
      const data = await getCustomerNetwork(custId, depth)
      setNetworkData(data)
    } catch (error) {
      console.error('Failed to load network:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    if (inputCustomerId.trim()) {
      loadNetwork(inputCustomerId.trim())
    }
  }

  const renderNetwork = () => {
    if (!containerRef.current || !networkData) return

    // Clean up previous network
    if (networkRef.current) {
      networkRef.current.destroy()
    }

    // Create nodes dataset
    const nodes = new DataSet(
      networkData.nodes.map((node) => ({
        id: node.id,
        label: node.name || node.id,
        color: nodeColors[node.labels[0]] || '#718096',
        shape: node.isSource ? 'star' : 'dot',
        size: node.isSource ? 30 : 20,
        title: `${node.labels.join(', ')}\n${JSON.stringify(node.properties, null, 2)}`,
      }))
    )

    // Create edges dataset
    const edges = new DataSet(
      networkData.edges.map((edge, index) => ({
        id: index,
        from: edge.source,
        to: edge.target,
        label: edge.type,
        arrows: 'to',
        font: { size: 10 },
      }))
    )

    // Network options
    const options = {
      nodes: {
        font: { size: 12, color: '#333' },
        borderWidth: 2,
      },
      edges: {
        color: { color: '#999', highlight: '#333' },
        smooth: { type: 'continuous' },
      },
      physics: {
        stabilization: { iterations: 100 },
        barnesHut: {
          gravitationalConstant: -2000,
          springLength: 150,
        },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
      },
    }

    networkRef.current = new Network(
      containerRef.current,
      { nodes, edges },
      options
    )
  }

  const handleZoomIn = () => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale()
      networkRef.current.moveTo({ scale: scale * 1.3 })
    }
  }

  const handleZoomOut = () => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale()
      networkRef.current.moveTo({ scale: scale / 1.3 })
    }
  }

  const handleFit = () => {
    if (networkRef.current) {
      networkRef.current.fit()
    }
  }

  return (
    <Box>
      {/* Stats */}
      {stats && (
        <SimpleGrid columns={{ base: 2, md: 4 }} gap={4} mb={4}>
          <Card.Root>
            <Card.Body>
              <Stat.Root>
                <Stat.Label>Total Nodes</Stat.Label>
                <Stat.ValueText>{stats.nodes.total}</Stat.ValueText>
              </Stat.Root>
            </Card.Body>
          </Card.Root>
          <Card.Root>
            <Card.Body>
              <Stat.Root>
                <Stat.Label>Relationships</Stat.Label>
                <Stat.ValueText>{stats.relationships.total}</Stat.ValueText>
              </Stat.Root>
            </Card.Body>
          </Card.Root>
          <Card.Root>
            <Card.Body>
              <Stat.Root>
                <Stat.Label>Customers</Stat.Label>
                <Stat.ValueText>{stats.nodes.by_label.Customer || 0}</Stat.ValueText>
              </Stat.Root>
            </Card.Body>
          </Card.Root>
          <Card.Root>
            <Card.Body>
              <Stat.Root>
                <Stat.Label>Organizations</Stat.Label>
                <Stat.ValueText>{stats.nodes.by_label.Organization || 0}</Stat.ValueText>
              </Stat.Root>
            </Card.Body>
          </Card.Root>
        </SimpleGrid>
      )}

      {/* Search and Controls */}
      <Card.Root mb={4}>
        <Card.Body>
          <Flex justify="space-between" align="center" mb={4}>
            <Heading size="md">Relationship Network</Heading>
            <Flex gap={2}>
              <Button size="sm" variant="outline" onClick={handleZoomIn}>
                <LuZoomIn />
              </Button>
              <Button size="sm" variant="outline" onClick={handleZoomOut}>
                <LuZoomOut />
              </Button>
              <Button size="sm" variant="outline" onClick={handleFit}>
                <LuMaximize />
              </Button>
            </Flex>
          </Flex>

          <Flex gap={2} mb={4}>
            <Input
              placeholder="Enter customer ID..."
              value={inputCustomerId}
              onChange={(e) => setInputCustomerId(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <Button onClick={handleSearch} colorPalette="blue">
              Load Network
            </Button>
            <Button
              variant="outline"
              onClick={() => inputCustomerId && loadNetwork(inputCustomerId)}
            >
              <LuRefreshCw />
            </Button>
          </Flex>

          {/* Legend */}
          <Flex gap={2} flexWrap="wrap">
            {Object.entries(nodeColors).map(([label, color]) => (
              <Badge
                key={label}
                style={{ backgroundColor: color, color: 'white' }}
              >
                {label}
              </Badge>
            ))}
          </Flex>
        </Card.Body>
      </Card.Root>

      {/* Network Visualization */}
      <Card.Root>
        <Card.Body p={0}>
          {loading ? (
            <Flex justify="center" align="center" h={500}>
              <Spinner size="lg" />
            </Flex>
          ) : networkData ? (
            <>
              <Box p={2} borderBottom="1px" borderColor="border.muted">
                <Text fontSize="sm" color="fg.muted">
                  Showing {networkData.nodes.length} nodes and{' '}
                  {networkData.edges.length} relationships
                </Text>
              </Box>
              <Box ref={containerRef} h={500} />
            </>
          ) : (
            <Flex justify="center" align="center" h={500}>
              <Text color="fg.muted">
                Enter a customer ID to visualize their relationship network
              </Text>
            </Flex>
          )}
        </Card.Body>
      </Card.Root>
    </Box>
  )
}
