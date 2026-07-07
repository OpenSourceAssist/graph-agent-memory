import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  // ESM-only: the @neo4j-labs/agent-memory peer is ESM-only (no `require`
  // export condition), so a CJS build of this package cannot work at runtime.
  format: ['esm'],
  dts: true,
  sourcemap: true,
  clean: true,
  treeshake: true,
  // Peer dependencies (including the optional @ai-sdk/mcp) are externalized
  // automatically by tsup — no explicit list needed.
});
