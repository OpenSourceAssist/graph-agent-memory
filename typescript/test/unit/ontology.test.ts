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

  it("import sends content/format and parses the draft + warnings", async () => {
    const t = mockTransport(() => ({
      ontology: DOC,
      warnings: [{ code: "unmapped", message: "no pole_type for :Widget", path: "Widget" }],
      detected_format: "arrows",
      suggested_name: "Legal",
    }));
    const o = new OntologyClient(t as never);
    const result = await o.import({ content: '{"nodes":[]}', format: "arrows" });
    expect(t.request.mock.calls[0]?.[0]).toBe("import_ontology");
    expect(t.request.mock.calls[0]?.[1].body).toMatchObject({ content: '{"nodes":[]}', format: "arrows" });
    expect(result.document?.entityTypes[0].label).toBe("Case");
    expect(result.detectedFormat).toBe("arrows");
    expect(result.suggestedName).toBe("Legal");
    expect(result.warnings[0].code).toBe("unmapped");
  });

  it("import requires content or url", async () => {
    const o = new OntologyClient(mockTransport(() => ({})) as never);
    await expect(o.import({})).rejects.toThrow(/content or url/);
  });

  it("diff passes from/to and maps revisions", async () => {
    const t = mockTransport(() => ({
      from_revision: 1,
      to_revision: 2,
      entity_types: { added: [{ label: "Widget" }], removed: [], renamed: [], modified: [] },
      relationships: { added: [], removed: [], renamed: [], modified: [] },
    }));
    const o = new OntologyClient(t as never);
    const d = await o.diff("ont_1", 1, 2);
    expect(t.request.mock.calls[0]?.[1]).toMatchObject({ id: "ont_1", from: 1, to: 2 });
    expect(d.fromRevision).toBe(1);
    expect(d.toRevision).toBe(2);
    expect((d.entityTypes.added as unknown[]).length).toBe(1);
  });

  it("migrate sends snake_case spec and maps the job", async () => {
    const t = mockTransport(() => ({
      id: "mig_1",
      ontology_id: "ont_1",
      status: "pending",
      total: 0,
      error_message: "",
    }));
    const o = new OntologyClient(t as never);
    const job = await o.migrate("ont_1", {
      fromVersionId: "ov_1",
      toVersionId: "ov_2",
      typeMappings: [{ from: "Widget", to: "Gadget" }],
      dryRun: true,
    });
    const body = t.request.mock.calls[0]?.[1].body as { spec: Record<string, unknown> };
    expect(body.spec).toMatchObject({
      from_version_id: "ov_1",
      to_version_id: "ov_2",
      type_mappings: [{ from: "Widget", to: "Gadget" }],
      dry_run: true,
    });
    expect(job.id).toBe("mig_1");
    expect(job.ontologyId).toBe("ont_1");
    expect(job.status).toBe("pending");
  });

  it("getMigration passes jobId and maps the job", async () => {
    const t = mockTransport(() => ({ id: "mig_1", status: "running", processed: 5, total: 10 }));
    const o = new OntologyClient(t as never);
    const job = await o.getMigration("mig_1");
    expect(t.request.mock.calls[0]?.[1]).toMatchObject({ jobId: "mig_1" });
    expect(job.processed).toBe(5);
    expect(job.total).toBe(10);
  });
});
