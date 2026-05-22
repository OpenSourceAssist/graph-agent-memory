# Examples

Runnable examples demonstrating each integration shipped with
`@neo4j-labs/agent-memory`. Each example is a self-contained Node.js
script you can clone, install, and run against the hosted Neo4j Agent
Memory Service.

## Prerequisites

- Node.js 20+
- A `MEMORY_API_KEY` from [memory.neo4jlabs.com](https://memory.neo4jlabs.com)

## The examples

| Folder | What it shows |
|---|---|
| [`vercel-ai/`](./vercel-ai) | Memory-augmented chat using the Vercel AI SDK middleware |
| [`mcp/`](./mcp) | Registering the 12 memory tools with an MCP server |
| [`langchain/`](./langchain) | Chat history + entity retriever shapes for LangChain JS |
| [`mastra/`](./mastra) | Wrapping the client as a Mastra-compatible memory provider |
| [`strands/`](./strands) | AWS Strands agent with session persistence, three-tier context, and reasoning capture |

## Running an example

```bash
cd vercel-ai
cp .env.example .env       # then edit .env with your MEMORY_API_KEY
npm install
npm start
```

Each example's own README has the full step-by-step.

## Notes

- These examples use `"@neo4j-labs/agent-memory": "file:../.."` to
  depend on the in-tree SDK during development — so contributors can
  iterate on both without an npm publish round-trip. When using one of
  these examples as a template for your own project, replace the
  `file:` path with a published version:
  ```
  "@neo4j-labs/agent-memory": "^0.3.0"
  ```
- Each example is **type-checked in CI** by the `type-check-examples`
  matrix in `.github/workflows/ci-typescript.yml` — drift between an
  example and the SDK's public API fails the PR that introduces it.
  Runtime execution (`npm start`) still needs API keys you provide
  locally.
