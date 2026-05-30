/**
 * E2E ontology lifecycle against the hosted service (staging).
 *
 * Skips unless MEMORY_API_KEY is set. Mutates workspace-global active-ontology
 * state, so it snapshots and restores the active version, and deletes the
 * test clone afterward.
 */

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { MemoryClient } from "../../src/client.js";

const API_KEY = (process.env.MEMORY_API_KEY ?? "").trim();
const ENDPOINT = process.env.MEMORY_ENDPOINT ?? "https://memory.neo4jlabs.com/v1";
const WORKSPACE_ID = (process.env.MEMORY_WORKSPACE_ID ?? "").trim() || undefined;
const describeOrSkip = API_KEY.length > 0 ? describe : describe.skip;

const TEMPLATE = "conservation";
const CLONE_NAME = `${TEMPLATE}-clone`;

describeOrSkip("ontology lifecycle (hosted)", () => {
  let client: MemoryClient;
  let priorVersionId: string | undefined;

  beforeAll(async () => {
    client = new MemoryClient({ endpoint: ENDPOINT, apiKey: API_KEY, workspaceId: WORKSPACE_ID });
    const before = await client.ontology.getActive();
    priorVersionId = before.versionId;
    // Clean any leftover clone from a prior run.
    for (const s of await client.ontology.list()) {
      if (s.name === CLONE_NAME && !s.isSystem) await client.ontology.delete(s.id);
    }
  });

  afterAll(async () => {
    for (const s of await client.ontology.list()) {
      if (s.name === CLONE_NAME && !s.isSystem) await client.ontology.delete(s.id);
    }
    if (priorVersionId) await client.ontology.activate(priorVersionId);
  });

  it("lists system templates", async () => {
    const names = (await client.ontology.list()).map((o) => o.name);
    expect(names).toContain(TEMPLATE);
    expect(names).toContain("nams-default");
  });

  it("clone → update (preserves schema) → activate → getActive", async () => {
    const v = await client.ontology.clone(TEMPLATE);
    expect(v.revision).toBe(1);
    const typeCount = v.document?.entityTypes.length ?? 0;
    expect(typeCount).toBeGreaterThan(0);

    const v2 = await client.ontology.update({
      id: v.ontologyId,
      schema: v.document!,
      validationMode: "strict",
    });
    expect(v2.revision).toBe(2);
    expect(v2.document?.entityTypes.length).toBe(typeCount); // schema preserved

    await client.ontology.activate(v2.id);
    const active = await client.ontology.getActive();
    expect(active.document.domain.id).toBe(CLONE_NAME);
    expect(active.validationMode).toBe("strict");
    expect(active.revision).toBe(2);
  });
});
