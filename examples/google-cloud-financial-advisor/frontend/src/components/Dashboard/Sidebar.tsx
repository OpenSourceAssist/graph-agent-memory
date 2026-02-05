import { Link, useLocation } from 'react-router-dom'
import { Box, VStack, Text, Icon, Flex } from '@chakra-ui/react'
import {
  FiHome,
  FiMessageSquare,
  FiUsers,
  FiSearch,
  FiAlertTriangle,
} from 'react-icons/fi'

interface NavItemProps {
  icon: React.ElementType
  label: string
  to: string
  isActive: boolean
}

function NavItem({ icon, label, to, isActive }: NavItemProps) {
  return (
    <Link to={to} style={{ width: '100%' }}>
      <Flex
        align="center"
        px={4}
        py={3}
        borderRadius="md"
        bg={isActive ? 'blue.50' : 'transparent'}
        color={isActive ? 'blue.600' : 'gray.600'}
        _hover={{ bg: isActive ? 'blue.50' : 'gray.100' }}
        transition="all 0.2s"
      >
        <Icon as={icon} boxSize={5} mr={3} />
        <Text fontWeight={isActive ? 'semibold' : 'medium'}>{label}</Text>
      </Flex>
    </Link>
  )
}

export default function Sidebar() {
  const location = useLocation()

  const navItems = [
    { icon: FiHome, label: 'Dashboard', to: '/' },
    { icon: FiMessageSquare, label: 'Chat', to: '/chat' },
    { icon: FiUsers, label: 'Customers', to: '/customers' },
    { icon: FiSearch, label: 'Investigations', to: '/investigations' },
    { icon: FiAlertTriangle, label: 'Alerts', to: '/alerts' },
  ]

  return (
    <Box
      w="250px"
      minH="100vh"
      bg="white"
      borderRight="1px"
      borderColor="gray.200"
      py={6}
    >
      {/* Logo */}
      <Box px={6} mb={8}>
        <Text fontSize="lg" fontWeight="bold" color="blue.600">
          Financial Advisor
        </Text>
        <Text fontSize="xs" color="gray.500">
          Powered by Google ADK + Neo4j
        </Text>
      </Box>

      {/* Navigation */}
      <VStack gap={1} px={3} align="stretch">
        {navItems.map((item) => (
          <NavItem
            key={item.to}
            icon={item.icon}
            label={item.label}
            to={item.to}
            isActive={location.pathname === item.to}
          />
        ))}
      </VStack>

      {/* Footer */}
      <Box position="absolute" bottom={6} px={6}>
        <Text fontSize="xs" color="gray.400">
          v0.1.0 - Demo
        </Text>
      </Box>
    </Box>
  )
}
