import { Box, VStack, Text, Icon, Flex } from '@chakra-ui/react'
import { Link, useLocation } from 'react-router-dom'
import {
  FiHome,
  FiMessageSquare,
  FiUsers,
  FiAlertTriangle,
  FiSearch,
  FiFileText,
} from 'react-icons/fi'

interface NavItemProps {
  icon: React.ElementType
  label: string
  to: string
  isActive?: boolean
}

function NavItem({ icon, label, to, isActive }: NavItemProps) {
  return (
    <Link to={to} style={{ width: '100%' }}>
      <Flex
        align="center"
        p={3}
        borderRadius="md"
        cursor="pointer"
        bg={isActive ? 'teal.500' : 'transparent'}
        color={isActive ? 'white' : 'gray.600'}
        _hover={{ bg: isActive ? 'teal.600' : 'gray.100' }}
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
    { icon: FiMessageSquare, label: 'AI Advisor', to: '/chat' },
    { icon: FiUsers, label: 'Customers', to: '/customers' },
    { icon: FiSearch, label: 'Investigations', to: '/investigations' },
    { icon: FiAlertTriangle, label: 'Alerts', to: '/alerts' },
    { icon: FiFileText, label: 'Reports', to: '/reports' },
  ]

  return (
    <Box
      w="250px"
      bg="white"
      borderRight="1px"
      borderColor="gray.200"
      h="100vh"
      position="sticky"
      top={0}
    >
      {/* Logo */}
      <Flex align="center" p={4} borderBottom="1px" borderColor="gray.200">
        <Box
          w={10}
          h={10}
          borderRadius="lg"
          bg="teal.500"
          display="flex"
          alignItems="center"
          justifyContent="center"
          mr={3}
        >
          <Text color="white" fontWeight="bold" fontSize="lg">
            FS
          </Text>
        </Box>
        <Box>
          <Text fontWeight="bold" fontSize="sm" color="gray.800">
            Financial Services
          </Text>
          <Text fontSize="xs" color="gray.500">
            Compliance Advisor
          </Text>
        </Box>
      </Flex>

      {/* Navigation */}
      <VStack align="stretch" p={4} gap={1}>
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
      <Box position="absolute" bottom={0} left={0} right={0} p={4} borderTop="1px" borderColor="gray.200">
        <Text fontSize="xs" color="gray.500" textAlign="center">
          Powered by Neo4j + AWS
        </Text>
      </Box>
    </Box>
  )
}
