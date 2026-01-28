# Restructure Documentation for Antora External Content Source

## Summary

This PR restructures the documentation to support Antora's external content source feature, enabling integration with Neo4j Labs Pages at `neo4j.com/labs/agent-memory/`.

## Changes

### New Files

- **`docs/antora.yml`** - Antora component descriptor with Labs theming attributes
- **`docs/modules/ROOT/nav.adoc`** - Navigation structure following Diataxis organization
- **`.github/workflows/trigger-labs-build.yml`** - GitHub Action to trigger Labs Pages rebuilds on docs changes
- **`docs/modules/ROOT/images/diagrams/excalidraw/memory-architecture.excalidraw`** - Memory architecture diagram with Neo4j Labs branding
- **`docs/modules/ROOT/images/diagrams/excalidraw/poleo-model.excalidraw`** - POLE+O entity model diagram

### Structural Changes

Migrated from flat documentation structure to Antora module format:

```
Before:                          After:
docs/                            docs/
├── index.adoc                   ├── antora.yml
├── tutorials/                   └── modules/ROOT/
├── how-to/                          ├── nav.adoc
├── reference/                       ├── pages/
└── explanation/                     │   ├── index.adoc
                                     │   ├── tutorials/
                                     │   ├── how-to/
                                     │   ├── reference/
                                     │   └── explanation/
                                     └── images/diagrams/
```

### Content Updates

- Added `:page-product: agent-memory` and `:page-pagination:` attributes to all 39 pages for Labs branding
- Removed 7 duplicate/orphaned files:
  - `configuration.adoc` (duplicate of `reference/configuration.adoc`)
  - `entity-extraction.adoc` (duplicate of `how-to/entity-extraction.adoc`)
  - `memory-types.adoc` (duplicate of `explanation/memory-types.adoc`)
  - `poleo-model.adoc` (duplicate of `explanation/poleo-model.adoc`)
  - `integrations.adoc` (duplicate of `how-to/integrations/index.adoc`)
  - `enrichment.adoc` (orphaned)
  - `product-improvements.adoc` (internal roadmap)

## Navigation Structure

The `nav.adoc` organizes content following Diataxis:

- **Tutorials** - Learning-oriented guides (first-agent-memory, conversation-memory, knowledge-graph)
- **How-To Guides** - Task-oriented guides including framework integrations (LangChain, LlamaIndex, PydanticAI, CrewAI, OpenAI Agents)
- **Reference** - Technical reference (configuration, CLI, API docs, schemas)
- **Concepts** - Explanatory content (memory types, POLE+O model, graph architecture)

## URL Structure

Final URLs on Labs Pages will be:
- `https://neo4j.com/labs/agent-memory/`
- `https://neo4j.com/labs/agent-memory/getting-started/`
- `https://neo4j.com/labs/agent-memory/tutorials/first-agent-memory/`
- `https://neo4j.com/labs/agent-memory/how-to/integrations/langchain/`
- `https://neo4j.com/labs/agent-memory/reference/configuration/`
- `https://neo4j.com/labs/agent-memory/explanation/memory-types/`

## Setup Required

After merging, the following setup is needed:

1. **Repository Secret**: Add `LABS_PAGES_TOKEN` with a PAT that has `repo` scope and dispatch permissions on `neo4j-contrib/labs-pages`

2. **Labs Pages Configuration**: Update the labs-pages Antora playbook to include this repository as an external content source:
   ```yaml
   content:
     sources:
       - url: https://github.com/neo4j-labs/agent-memory
         start_path: neo4j-agent-memory/docs
         branches: [main]
   ```

3. **Diagram Export**: Export Excalidraw diagrams to PNG/SVG for embedding in documentation

## Testing

- [ ] Verify Antora structure with local build: `npx antora <playbook>`
- [ ] Confirm all xref links resolve correctly
- [ ] Test Labs Pages integration in staging environment
- [ ] Verify GitHub Action triggers on docs changes

## Related

- Labs Pages repository: `neo4j-contrib/labs-pages`
- Antora documentation: https://docs.antora.org/
