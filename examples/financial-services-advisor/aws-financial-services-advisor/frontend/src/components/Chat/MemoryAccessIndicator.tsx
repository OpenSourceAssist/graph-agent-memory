import { Box, Flex, Text, Badge } from '@chakra-ui/react'
import { motion } from 'framer-motion'
import { LuDatabase, LuSearch, LuSave } from 'react-icons/lu'

interface MemoryAccessIndicatorProps {
  operation: string
  tool: string
  query?: string
}

export default function MemoryAccessIndicator({ operation, tool, query }: MemoryAccessIndicatorProps) {
  const isSearch = operation === 'search'
  const color = isSearch ? 'blue' : 'green'
  const Icon = isSearch ? LuSearch : LuSave

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
    >
      <Flex
        align="center"
        gap={1.5}
        p={1.5}
        borderRadius="md"
        border="1px solid"
        borderColor={`${color}.200`}
        bg={`${color}.50`}
        fontSize="xs"
      >
        <LuDatabase size={12} />
        <Icon size={10} />
        <Badge size="sm" colorPalette={color}>{operation}</Badge>
        <Text fontFamily="mono" color={`${color}.700`}>{tool}</Text>
        {query && <Text color="gray.500" truncate maxW="150px">{query}</Text>}
      </Flex>
    </motion.div>
  )
}
