"use client";

import { ChakraProvider } from "@chakra-ui/react";
import { ThemeProvider } from "next-themes";
import { neo4jLabsSystem } from "@/theme";

export function Provider({ children }: { children: React.ReactNode }) {
  return (
    <ChakraProvider value={neo4jLabsSystem}>
      <ThemeProvider attribute="class" disableTransitionOnChange>
        {children}
      </ThemeProvider>
    </ChakraProvider>
  );
}
