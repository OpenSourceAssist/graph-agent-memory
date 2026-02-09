"use client";

import { createSystem, defaultConfig, defineConfig } from "@chakra-ui/react";

/**
 * Neo4j Labs Theme for Lenny's Memory
 *
 * Brand Colors:
 * - Labs Purple: #6366F1 (primary accent)
 * - Neo4j Teal: #009999 (secondary/links)
 *
 * Status Colors:
 * - Experimental: #F59E0B (amber)
 * - Beta: #6366F1 (purple)
 * - Success: #10B981 (green)
 * - Error: #EF4444 (red)
 *
 * Graph Node Colors (from Neo4j brand):
 * - Person: #DA7194 (pink)
 * - Organization: #F79767 (orange)
 * - Location: #68BDF6 (blue)
 * - Topic: #A4DD00 (lime green)
 * - Event: #C990C0 (purple)
 * - Default: #A5ABB6 (gray)
 */

const config = defineConfig({
  theme: {
    tokens: {
      colors: {
        // Neo4j Labs Purple (primary brand color)
        brand: {
          50: { value: "#EEF2FF" },
          100: { value: "#E0E7FF" },
          200: { value: "#C7D2FE" },
          300: { value: "#A5B4FC" },
          400: { value: "#818CF8" },
          500: { value: "#6366F1" }, // Labs Purple
          600: { value: "#4F46E5" }, // Labs Purple Dark
          700: { value: "#4338CA" },
          800: { value: "#3730A3" },
          900: { value: "#312E81" },
          950: { value: "#1E1B4B" },
        },
        // Neo4j Teal (secondary color)
        teal: {
          50: { value: "#E6F7F7" },
          100: { value: "#CCEFEF" },
          200: { value: "#99DFDF" },
          300: { value: "#66CFCF" },
          400: { value: "#33BFBF" },
          500: { value: "#009999" }, // Neo4j Teal
          600: { value: "#007A7A" },
          700: { value: "#005C5C" },
          800: { value: "#003D3D" },
          900: { value: "#001F1F" },
          950: { value: "#001010" },
        },
        // Status colors
        amber: {
          50: { value: "#FFFBEB" },
          100: { value: "#FEF3C7" },
          200: { value: "#FDE68A" },
          300: { value: "#FCD34D" },
          400: { value: "#FBBF24" },
          500: { value: "#F59E0B" }, // Experimental
          600: { value: "#D97706" },
          700: { value: "#B45309" },
          800: { value: "#92400E" },
          900: { value: "#78350F" },
          950: { value: "#451A03" },
        },
        // Graph visualization node colors
        node: {
          person: { value: "#DA7194" },
          organization: { value: "#F79767" },
          location: { value: "#68BDF6" },
          topic: { value: "#A4DD00" },
          event: { value: "#C990C0" },
          default: { value: "#A5ABB6" },
        },
      },
      fonts: {
        heading: {
          value:
            "var(--font-syne), 'Syne', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        },
        body: {
          value:
            "var(--font-public-sans), 'Public Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        },
        mono: {
          value:
            "var(--font-jetbrains-mono), 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace",
        },
      },
    },
    semanticTokens: {
      colors: {
        // Brand semantic tokens
        brand: {
          solid: { value: "{colors.brand.500}" },
          contrast: { value: "white" },
          fg: {
            value: {
              _light: "{colors.brand.600}",
              _dark: "{colors.brand.400}",
            },
          },
          muted: {
            value: {
              _light: "{colors.brand.100}",
              _dark: "{colors.brand.900}",
            },
          },
          subtle: {
            value: { _light: "{colors.brand.50}", _dark: "{colors.brand.950}" },
          },
          emphasized: {
            value: {
              _light: "{colors.brand.200}",
              _dark: "{colors.brand.800}",
            },
          },
          focusRing: { value: "{colors.brand.500}" },
        },
        // Teal semantic tokens
        teal: {
          solid: { value: "{colors.teal.500}" },
          contrast: { value: "white" },
          fg: {
            value: { _light: "{colors.teal.600}", _dark: "{colors.teal.400}" },
          },
          muted: {
            value: { _light: "{colors.teal.100}", _dark: "{colors.teal.900}" },
          },
          subtle: {
            value: { _light: "{colors.teal.50}", _dark: "{colors.teal.950}" },
          },
          emphasized: {
            value: { _light: "{colors.teal.200}", _dark: "{colors.teal.800}" },
          },
          focusRing: { value: "{colors.teal.500}" },
        },
        // Amber semantic tokens (for experimental/warning states)
        amber: {
          solid: { value: "{colors.amber.500}" },
          contrast: { value: "white" },
          fg: {
            value: {
              _light: "{colors.amber.600}",
              _dark: "{colors.amber.400}",
            },
          },
          muted: {
            value: {
              _light: "{colors.amber.100}",
              _dark: "{colors.amber.900}",
            },
          },
          subtle: {
            value: { _light: "{colors.amber.50}", _dark: "{colors.amber.950}" },
          },
          emphasized: {
            value: {
              _light: "{colors.amber.200}",
              _dark: "{colors.amber.800}",
            },
          },
          focusRing: { value: "{colors.amber.500}" },
        },
      },
    },
  },
});

export const neo4jLabsSystem = createSystem(defaultConfig, config);

/**
 * Graph node colors for visualization components
 * Use these when rendering Neo4j NVL graphs or custom visualizations
 */
export const nodeColors = {
  Person: "#DA7194",
  Organization: "#F79767",
  Location: "#68BDF6",
  Topic: "#A4DD00",
  Concept: "#A4DD00",
  Event: "#C990C0",
  Episode: "#C990C0",
  Message: "#A5ABB6",
  Preference: "#F59E0B",
  default: "#A5ABB6",
} as const;

/**
 * Status badge colors for Labs project lifecycle
 */
export const statusColors = {
  experimental: "#F59E0B", // Amber
  beta: "#6366F1", // Labs Purple
  stable: "#10B981", // Green
  deprecated: "#EF4444", // Red
  graduated: "#009999", // Neo4j Teal
} as const;

/**
 * Memory type colors for visualization
 */
export const memoryTypeColors = {
  shortTerm: {
    stroke: "#2F9E44",
    fill: "#B2F2BB",
  },
  longTerm: {
    stroke: "#F79767",
    fill: "#FFEC99",
  },
  reasoning: {
    stroke: "#C990C0",
    fill: "#D0BFFF",
  },
} as const;
