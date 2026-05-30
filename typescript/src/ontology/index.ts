/**
 * NAMS ontology surface — typed, versioned, validated domain schemas
 * extending POLE+O. Mirrors the Python `client.ontology` accessor.
 *
 * The ontology endpoints are a snake_case sub-API verified empirically against
 * staging (absent from the OpenAPI spec). The `RestTransport` routes for these
 * (`*_ontology`) send bodies verbatim via the `snakeBody` flag.
 *
 *   GET    /ontologies                        → list (summaries)
 *   GET    /ontologies/{id}                    → { record, versions[] }
 *   GET    /ontologies/active                  → { ontology, version }
 *   POST   /ontologies/{name}/clone            → version
 *   POST   /ontologies        { ontology, validation_mode? }       → version
 *   PUT    /ontologies/{id}    { ontology, validation_mode? }       → new revision
 *   POST   /ontologies/active { version_id }                       → version
 *   DELETE /ontologies/{id}                    → 204
 */

import { NotSupportedError } from "../errors.js";
import type { Transport } from "../transport/index.js";

export interface PropertyDef {
  name: string;
  type: string; // string | datetime | date | float | integer
  required?: boolean;
  unique?: boolean;
  enum?: string[];
}

export interface EntityTypeDef {
  label: string;
  poleType: string; // PERSON | ORGANIZATION | LOCATION | EVENT | OBJECT
  subtype?: string;
  color?: string;
  icon?: string;
  properties: PropertyDef[];
}

export interface RelationshipDef {
  type: string;
  source: string;
  target: string;
}

export interface DomainInfo {
  id: string;
  name: string;
  description?: string;
  tagline?: string;
  emoji?: string;
}

export interface OntologyDocument {
  domain: DomainInfo;
  entityTypes: EntityTypeDef[];
  relationships: RelationshipDef[];
}

export interface OntologySummary {
  id: string;
  name: string;
  displayName?: string;
  description?: string;
  emoji?: string;
  tagline?: string;
  isSystem: boolean;
  currentRevision?: number;
  isActive: boolean;
}

export interface OntologyVersion {
  id: string;
  ontologyId: string;
  revision: number;
  validationMode: string; // permissive | strict
  document?: OntologyDocument;
  schemaHash?: string;
  createdAt?: string;
  message?: string;
}

export interface OntologyRecord {
  id: string;
  name: string;
  description?: string;
  workspaceId?: string;
  isSystem: boolean;
  createdAt?: string;
}

export interface Ontology {
  record: OntologyRecord;
  versions: OntologyVersion[];
}

export interface ActiveOntology {
  document: OntologyDocument;
  validationMode?: string;
  revision?: number;
  ontologyId?: string;
  versionId?: string;
}

export interface CreateOntologyOptions {
  /** Identity comes from `schema.domain`; `name` is accepted for symmetry. */
  name: string;
  schema: OntologyDocument;
  validationMode?: string;
}

export interface UpdateOntologyOptions {
  id: string;
  schema: OntologyDocument;
  validationMode?: string;
}

// ---- snake_case wire shapes (responses are snake_case) ----------------------

interface WireProperty {
  name: string;
  type: string;
  required?: boolean;
  unique?: boolean;
  enum?: string[] | null;
}
interface WireEntityType {
  label: string;
  pole_type: string;
  subtype?: string;
  color?: string;
  icon?: string;
  properties?: WireProperty[] | null;
}
interface WireRelationship {
  type: string;
  source: string;
  target: string;
}
interface WireDocument {
  domain: DomainInfo;
  entity_types?: WireEntityType[] | null;
  relationships?: WireRelationship[] | null;
}
interface WireVersion {
  id: string;
  ontology_id: string;
  revision: number;
  validation_mode: string;
  schema_json?: string | null;
  schema_hash?: string;
  created_at?: string;
  message?: string;
}
interface WireSummary {
  id: string;
  name: string;
  display_name?: string;
  description?: string;
  emoji?: string;
  tagline?: string;
  is_system?: boolean;
  current_revision?: number;
  is_active?: boolean;
}
interface WireRecord {
  id: string;
  name: string;
  description?: string;
  workspace_id?: string;
  is_system?: boolean;
  created_at?: string;
}

function toDocument(raw: WireDocument | null | undefined): OntologyDocument | undefined {
  if (!raw || typeof raw !== "object" || !raw.domain) return undefined;
  return {
    domain: raw.domain,
    entityTypes: (raw.entity_types ?? []).map((e) => ({
      label: e.label,
      poleType: e.pole_type,
      subtype: e.subtype,
      color: e.color,
      icon: e.icon,
      properties: (e.properties ?? []).map((p) => ({
        name: p.name,
        type: p.type,
        required: p.required,
        unique: p.unique,
        enum: p.enum ?? undefined,
      })),
    })),
    relationships: raw.relationships ?? [],
  };
}

function toDocumentFromJson(schemaJson: string | null | undefined): OntologyDocument | undefined {
  if (schemaJson == null) return undefined;
  try {
    return toDocument(JSON.parse(schemaJson) as WireDocument);
  } catch {
    return undefined;
  }
}

function toVersion(raw: WireVersion): OntologyVersion {
  return {
    id: raw.id,
    ontologyId: raw.ontology_id,
    revision: raw.revision,
    validationMode: raw.validation_mode,
    document: toDocumentFromJson(raw.schema_json),
    schemaHash: raw.schema_hash,
    createdAt: raw.created_at,
    message: raw.message,
  };
}

function toSummary(raw: WireSummary): OntologySummary {
  return {
    id: raw.id,
    name: raw.name,
    displayName: raw.display_name,
    description: raw.description,
    emoji: raw.emoji,
    tagline: raw.tagline,
    isSystem: raw.is_system ?? false,
    currentRevision: raw.current_revision,
    isActive: raw.is_active ?? false,
  };
}

function docToWire(doc: OntologyDocument): WireDocument {
  return {
    domain: doc.domain,
    entity_types: doc.entityTypes.map((e) => ({
      label: e.label,
      pole_type: e.poleType,
      subtype: e.subtype,
      color: e.color,
      icon: e.icon,
      properties: (e.properties ?? []).map((p) => ({
        name: p.name,
        type: p.type,
        required: p.required,
        unique: p.unique,
        enum: p.enum,
      })),
    })),
    relationships: doc.relationships,
  };
}

export class OntologyClient {
  constructor(private readonly transport: Transport) {}

  async list(): Promise<OntologySummary[]> {
    const raw = await this.transport.request<{ ontologies?: WireSummary[] }>(
      "list_ontologies",
      {},
    );
    return (raw.ontologies ?? []).map(toSummary);
  }

  async get(id: string): Promise<Ontology> {
    const raw = await this.transport.request<{ record: WireRecord; versions?: WireVersion[] }>(
      "get_ontology",
      { id },
    );
    const r = raw.record ?? ({} as WireRecord);
    return {
      record: {
        id: r.id,
        name: r.name,
        description: r.description,
        workspaceId: r.workspace_id,
        isSystem: r.is_system ?? false,
        createdAt: r.created_at,
      },
      versions: (raw.versions ?? []).map(toVersion),
    };
  }

  async getActive(): Promise<ActiveOntology> {
    const raw = await this.transport.request<{ ontology?: WireDocument }>(
      "get_active_ontology",
      {},
    );
    const document = toDocument(raw.ontology);
    if (!document) {
      throw new NotSupportedError("No active ontology bound for this workspace.");
    }
    const active: ActiveOntology = { document };
    // Compose version metadata via a second lookup (the active response carries
    // no version metadata).
    const summaries = await this.list();
    const match =
      summaries.find((s) => s.isActive) ??
      summaries.find((s) => s.name === document.domain.id);
    if (match) {
      active.ontologyId = match.id;
      const detail = await this.get(match.id);
      const current = currentVersion(detail, match.currentRevision);
      if (current) {
        active.validationMode = current.validationMode;
        active.revision = current.revision;
        active.versionId = current.id;
      }
    }
    return active;
  }

  async clone(templateName: string): Promise<OntologyVersion> {
    const raw = await this.transport.request<WireVersion>("clone_ontology", { name: templateName });
    return toVersion(raw);
  }

  async create(options: CreateOntologyOptions): Promise<OntologyVersion> {
    const body: Record<string, unknown> = { ontology: docToWire(options.schema) };
    if (options.validationMode !== undefined) body.validation_mode = options.validationMode;
    const raw = await this.transport.request<WireVersion>("create_ontology", { body });
    return toVersion(raw);
  }

  async update(options: UpdateOntologyOptions): Promise<OntologyVersion> {
    const body: Record<string, unknown> = { ontology: docToWire(options.schema) };
    if (options.validationMode !== undefined) body.validation_mode = options.validationMode;
    const raw = await this.transport.request<WireVersion>("update_ontology", {
      id: options.id,
      body,
    });
    return toVersion(raw);
  }

  async activate(versionId: string): Promise<OntologyVersion> {
    const raw = await this.transport.request<WireVersion>("activate_ontology", {
      body: { version_id: versionId },
    });
    return toVersion(raw);
  }

  async delete(id: string): Promise<void> {
    await this.transport.request("delete_ontology", { id });
  }
}

function currentVersion(ontology: Ontology, revision?: number): OntologyVersion | undefined {
  if (ontology.versions.length === 0) return undefined;
  if (revision !== undefined) {
    const exact = ontology.versions.find((v) => v.revision === revision);
    if (exact) return exact;
  }
  return ontology.versions.reduce((a, b) => (b.revision > a.revision ? b : a));
}
