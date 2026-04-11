import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Box, Flex } from "@chakra-ui/react";
import Sidebar from "./components/Dashboard/Sidebar";
import CustomerDashboard from "./components/Dashboard/CustomerDashboard";
import ChatInterface from "./components/Chat/ChatInterface";
import InvestigationPanel from "./components/Investigation/InvestigationPanel";
import AlertsPanel from "./components/Dashboard/AlertsPanel";

function App() {
  return (
    <Router>
      <Flex minH="100vh">
        <Sidebar />
        <Box flex="1" bg="bg.subtle" p={6} overflowY="auto">
          <Routes>
            <Route path="/" element={<CustomerDashboard />} />
            <Route path="/chat" element={<ChatInterface />} />
            <Route path="/customers" element={<CustomerDashboard />} />
            <Route path="/investigations" element={<InvestigationPanel />} />
            <Route path="/alerts" element={<AlertsPanel />} />
          </Routes>
        </Box>
      </Flex>
    </Router>
  );
}

export default App;
