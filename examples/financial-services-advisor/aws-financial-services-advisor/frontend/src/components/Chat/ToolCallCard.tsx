import { Box, Flex, Text, Badge } from '@chakra-ui/react'
import { motion } from 'framer-motion'
import { LuWrench, LuCheck, LuLoader } from 'react-icons/lu'

interface ToolCallCardProps {
  tool: string
  args: Record<string, unknown>
  result?: string
  color?: string
}

export const agentColorMap: Record<string, string> = {
  supervisor: 'blue',
  kyc: 'teal',
  kyc_agent: 'teal',
  aml: 'orange',
  aml_agent: 'orange',
  relationship: 'purple',
  relationship_agent: 'purple',
  compliance: 'red',
  compliance_agent: 'red',
}

function formatValue(value: unknown): string {
  if (typeof value === 'string') return value.length > 40 ? value.slice(0, 40) + '...' : value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return JSON.stringify(value).slice(0, 40)
}

export default function ToolCallCard({ tool, args, result, color = 'gray' }: ToolCallCardProps) {
  const argEntries = Object.entries(args).slice(0, 3)

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2 }}
    >
      <Box
        p={2}
        borderRadius="md"
        border="1px solid"
        borderColor={`${color}.200`}
        bg={`${color}.50`}
        fontSize="xs"
      >
        <Flex align="center" gap={1} mb={1}>
          {result ? (
            <LuCheck size={12} color="green" />
          ) : (
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
              <LuLoader size={12} />
            </motion.div>
          )}
          <Text fontFamily="mono" fontWeight="semibold">{tool}</Text>
        </Flex>

        {argEntries.length > 0 && (
          <Flex gap={1} flexWrap="wrap" mb={result ? 1 : 0}>
            {argEntries.map(([key, val]) => (
              <Badge key={key} size="sm" variant="outline" fontFamily="mono">
                {key}={formatValue(val)}
              </Badge>
            ))}
          </Flex>
        )}

        {result && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
            <Text color="green.600" fontSize="xs" lineClamp={2}>
              {result.slice(0, 120)}{result.length > 120 ? '...' : ''}
            </Text>
          </motion.div>
        )}
      </Box>
    </motion.div>
  )
}
