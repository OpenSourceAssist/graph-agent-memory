/**
 * Unit tests — OntologyClient (TS mirror of the Python ontology surface).
 * Verified contract shapes; transport mocked.
 */

import { describe, it, expect, vi } from "vitest";
import { OntologyClient } from "../../src/ontology/index.js";

const DOC = {
  domain: { id: "legal-clone", name: "Legal (clone)" },
  entity_types: [
    {
      label: "Case",
      pole_type: "EVENT",
      subtype: "CASE",
      properties: [
        { name: "docket", type: "string", unique: true, required: true },
        { name: "status", type: "string", enum: ["open", "closed"] },
      ],
    },
  ],
  relationships: [{ type: "FILED_BY", source: "Case", target: "Person" }],
};

function version(revision = 1, mode = "permissive") {
  return {
    id: `ov_${revision}`,
    ontology_id: "ont_1",
    revision,
    validation_mode: mode,
    schema_json: JSON.stringify(DOC),
    schema_hash: "abc",
  };
}

function mockTransport(handler: (method: string, params: Record<string, unknown>) => unknown) {
  return { request: vi.fn(async (m: string, p: Record<string, unknown>) => handler(m, p)) };
}

describe("OntologyClient", () => {
  it("list parses summaries", async () => {
    const t = mockTransport(() => ({
      ontologies: [
        { id: "ont_1", name: "legal-clone", current_revision: 2, is_active: true, is_system: false },
      ],
    }));
    const o = new OntologyClient(t as never);
    const [s] = await o.list();
    expect(s.name).toBe("legal-clone");
    expect(s.currentRevision).toBe(2);
    expect(s.isActive).toBe(true);
  });

  it("get parses record + versions and decodes schema_json", async () => {
    const t = mockTransport(() => ({
      record: { id: "ont_1", name: "legal-clone" },
      versions: [version(1)],
    }));
    const o = new OntologyClient(t as never);
    const result = await o.get("ont_1");
    expect(result.record.id).toBe("ont_1");
    expect(result.versions[0].document?.entityTypes[0].label).toBe("Case");
    expect(result.versions[0].document?.entityTypes[0].properties[0].unique).toBe(true);
  });

  it("getActive composes validationMode via second lookup", async () => {
    const t = mockTransport((method) => {
      if (method === "get_active_ontology") return { ontology: DOC, version: null };
      if (method === "list_ontologies")
        return {
          ontologies: [
            { id: "ont_1", name: "legal-clone", current_revision: 2, is_active: true },
          ],
        };
      if (method === "get_ontology")
        return { record: { id: "ont_1", name: "legal-clone" }, versions: [version(1), version(2, "strict")] };
      return {};
    });
    const o = new OntologyClient(t as never);
    const active = await o.getActive();
    expect(active.document.domain.id).toBe("legal-clone");
    expect(active.validationMode).toBe("strict");
    expect(active.revision).toBe(2);
    expect(active.versionId).toBe("ov_2");
  });

  it("create sends snake_case body wrapped under ontology", async () => {
    const t = mockTransport(() => version(1));
    const o = new OntologyClient(t as never);
    await o.create({
      name: "legal-clone",
      schema: {
        domain: { id: "legal-clone", name: "Legal" },
        entityTypes: [{ label: "Case", poleType: "EVENT", properties: [] }],
        relationships: [],
      },
      validationMode: "strict",
    });
    const body = t.request.mock.calls[0]?.[1].body as Record<string, unknown>;
    expect(body).toHaveProperty("ontology");
    const onto = body.ontology as { entity_types: unknown[] };
    expect(onto.entity_types).toBeDefined(); // snake_case preserved
    expect(body.validation_mode).toBe("strict");
  });

  it("activate posts version_id", async () => {
    const t = mockTransport(() => version(2, "strict"));
    const o = new OntologyClient(t as never);
    await o.activate("ov_2");
    expect(t.request.mock.calls[0]?.[1]).toMatchObject({ body: { version_id: "ov_2" } });
  });
});
