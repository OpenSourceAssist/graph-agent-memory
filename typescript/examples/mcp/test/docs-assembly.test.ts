/** Compile the tutorial's complete standalone server, then inspect its real stdio tools. */
import { execFile } from "node:child_process";
import { mkdtemp, mkdir, readFile, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { expect, it } from "vitest";

const exec = promisify(execFile);
const sdkRoot = fileURLToPath(new URL("../../../", import.meta.url));

it("builds the authored MCP lesson and its custom-tool insertion at the documented path", async () => {
  const page = await readFile(new URL("../../../../docs/modules/ROOT/pages/tutorials/mcp-server-typescript.adoc", import.meta.url), "utf8");
  const blocks = [...page.matchAll(/\[source,(typescript|json)\]\n----\n([\s\S]*?)\n----/g)].map((match) => match[2]!);
  const source = blocks.find((block) => block.includes("async function main()"))!;
  const config = blocks.find((block) => block.includes('"compilerOptions"'))!;
  const custom = blocks.find((block) => block.includes('"memory_cypher"'))!;
  expect(source).toBeDefined();
  expect(config).toBeDefined();
  const directory = await mkdtemp(join(tmpdir(), "agent-memory-mcp-lesson-"));
  try {
    await mkdir(join(directory, "src"));
    await mkdir(join(directory, "node_modules", "@neo4j-labs"), { recursive: true });
    await symlink(sdkRoot, join(directory, "node_modules", "@neo4j-labs", "agent-memory"));
    await symlink(join(sdkRoot, "node_modules", "@modelcontextprotocol"), join(directory, "node_modules", "@modelcontextprotocol"));
    await symlink(join(sdkRoot, "node_modules", "@types"), join(directory, "node_modules", "@types"));
    await symlink(join(sdkRoot, "node_modules", "zod"), join(directory, "node_modules", "zod"));
    await writeFile(join(directory, "package.json"), JSON.stringify({ type: "module" }));
    await writeFile(join(directory, "tsconfig.json"), config);
    for (const withCustom of [false, true]) {
      const assembled = withCustom
        ? 'import { z } from "zod";\n' + source.replace("  const transport =", custom + "\n  const transport =")
        : source;
      await writeFile(join(directory, "src", "server.ts"), assembled);
      await exec(process.execPath, [join(sdkRoot, "node_modules", "typescript", "bin", "tsc"), "-p", join(directory, "tsconfig.json")]);
      expect(await readFile(join(directory, "dist", "server.js"), "utf8")).toContain("registerMemoryTools");
      const client = new Client({ name: "docs-check", version: "1.0.0" });
      const transport = new StdioClientTransport({
        command: process.execPath,
        args: [join(directory, "dist", "server.js")],
        env: { MEMORY_API_KEY: "nams_offline_docs" },
        stderr: "pipe",
      });
      try {
        await client.connect(transport);
        const { tools } = await client.listTools();
        expect(tools).toHaveLength(withCustom ? 13 : 12);
        expect(tools.some((tool) => /preference/.test(tool.name))).toBe(false);
      } finally { await client.close(); }
    }
  } finally { await rm(directory, { recursive: true, force: true }); }
}, 30_000);
