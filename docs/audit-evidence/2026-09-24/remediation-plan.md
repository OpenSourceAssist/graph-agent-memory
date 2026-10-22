# Remediation plan for the 2026-09-24 branch review

This plan fixes every finding the review of branch `docs-review` confirmed (see `branch-review.md` and `findings.json` in this folder): 276 unique findings, of which 8 are blockers, 41 majors, 174 minors and 53 nits. It also fixes three SDK bugs that the review exposed. Nothing is deferred. A worker may decline a finding only if it shows evidence that the finding is wrong, and a reviewer then checks that decline.

## Decisions

- **Docs track the released packages.** The docs describe Python `neo4j-agent-memory` 0.6.0, `@neo4j-labs/agent-memory` 0.5.0 and `@neo4j-labs/nams-ai-provider` 0.3.0. Tutorials and recipes pin those releases, so every program is verified against the release from PyPI or npm, not against the editable checkout.
- **Fix the three exposed SDK bugs in `src/` for the next release,** each with tests and a `CHANGELOG.md` [Unreleased] entry. The bugs: GLiREL gets character offsets where it expects token indices; auto-extracted entities are stored without embeddings; and batch messages share one timestamp, so they read back in arbitrary order. Meanwhile the docs programs get workarounds so they pass on 0.6.0: explicit batch timestamps, entity checks that don't use entity vectors, and a relation path that works on 0.6.0 instead of GLiREL.
- **The NAMS first write creates its conversation first.** It calls `create_conversation`, uses the returned ID, and records that ID for the tutorial's scoped cleanup.
- **The MCP TypeScript lesson installs the published `@neo4j-labs/agent-memory@0.5.0`,** which a control run showed builds cleanly, and the checkout partial is updated to match.
- **CI builds the provider package for every example that depends on it,** now including `nextjs-memory-chat`, and the examples README gets the same build step.
- **Remove the `DOCUMENTATION_REMEDIATION_STATUS.md` links** from all 28 READMEs rather than creating that file. It was an audit-process artifact.
- **The team-memory `.mcp.json` uses `${VAR}` expansion** instead of literal secrets.
- **`make example-*` keeps Docker auto-start as the key-free local path.** It also exports `NEO4J_URI` and `NEO4J_USERNAME`, which fixes the `KeyError`, and every file that mentions it describes it the same way: the Makefile, `CLAUDE.md`, `AURA_SETUP.md` and `.env.example`.
- **`make docs-render-check` fails instead of skipping when Playwright is missing,** a new target installs Playwright, and plain `pytest` still skips cleanly.
- **Backend-scope partials must be true on every page that includes them.** Where one wording can't be, client-side-only pages get their own partial.
- **Kept compatibility anchors sit right before the section that now covers their content,** never after "See also". The roughly 60 fragments that no longer resolve are restored.
- **No commits.** Changes stay in the working tree until you ask for a commit.

## Waves

Work packages in the same wave run in parallel, and each owns a disjoint set of files. A worker records any change it needs in a file it doesn't own as a handoff.

1. **Wave 1: 28 area work packages** covering code, CI, tests, examples, diagrams and each docs area.
2. **Wave 2: two cross-cutting sweeps** that run after wave 1: backend-support labels, and small fixes that span two areas.
3. **Wave 3: anchor repair,** split by page directory, once page content has stopped changing.
4. **Handoffs:** one worker per owning area applies the changes that other workers handed off, contract-test updates included.
5. **Global gates, each with a fix loop:**
   - Python: `ruff format`/`check`, mypy, unit tests, `tests/examples`, `tests/docs` with and without Neo4j, and the integration tests.
   - Docs: `make docs`, `check_docs.py --build`, the rendered-site tests, diagram status, and a link and anchor check of the built site.
   - TypeScript: the SDK, the provider package, and every changed example.
6. **Re-verification:** every blocker and major is checked again against the finished tree.

After each work package finishes, a separate reviewer checks each finding against the source of truth and looks for new defects. A fixer then addresses what the reviewer found, for up to two rounds.

## Wave 1 work packages

### `ci-tooling`: CI workflows, Makefile, docs tooling scripts, UI assets, pyproject
9 findings (1 blocker, 2 major, 4 minor, 2 nit); owns 26 files.  
Findings: ex-python#1, ts-ex-b#0, py-examples#7, tooling-ci#0, tooling-ci#2, tooling-ci#4, tooling-ci#5, tooling-ci#9, x-diagrams#10

### `deploy`: Cloud Run and MCPB deployment assets
5 findings (4 minor, 1 nit); owns 7 files.  
Findings: deploy#0, deploy#1, deploy#4, deploy#5, deploy#7

### `diagrams`: Diagram scenes, exports, manifest
8 findings (6 minor, 2 nit); owns 106 files.  
Findings: x-diagrams#0, x-diagrams#2, x-diagrams#3, x-diagrams#4, x-diagrams#6, x-diagrams#7, x-diagrams#12, x-diagrams#13

### `docs-tests`: Docs and example test suites
15 findings (1 blocker, 2 major, 9 minor, 3 nit); owns 61 files.  
Findings: ex-python#0, deploy#3, docs-tests-a#0, docs-tests-a#1, docs-tests-b#3, docs-tests-b#5, docs-tests-b#6, docs-tests-b#7, docs-tests-b#8, docs-tests-b#9, docs-tests-b#10, docs-tests-b#12, gap1-bolt-programs-live#3, gap1-bolt-programs-live#4, gap1-bolt-programs-live#5

### `entry`: READMEs, CLAUDE.md, CONTRIBUTING, MAINTAINING, skills, index, getting started, SDK pages, nav
12 findings (10 minor, 2 nit); owns 15 files.  
Findings: tooling-ci#6, tooling-ci#8, entry#3, entry#4, entry#5, entry#6, entry#7, entry#8, entry#9, x-content-loss#7, x-style#10, gap2-gap2-install-commands-sweep#9

### `explanation`: Explanation pages, FAQ, glossary
10 findings (3 major, 5 minor, 2 nit); owns 17 files.  
Findings: explanation#0, explanation#1, explanation#2, explanation#3, explanation#4, explanation#5, explanation#6, explanation#7, explanation#8, explanation#9

### `howto-core-a`: How-to: entities, extraction, dedup, messages, preferences, reasoning, batch; core recipes
6 findings (1 blocker, 4 minor, 1 nit); owns 11 files.  
Findings: docs-examples-py#0, howto-core-a#1, howto-core-a#2, howto-core-a#5, howto-core-a#7, x-diagrams#9

### `howto-core-b`: How-to: v0.2 primitives, providers, migration, privacy
8 findings (7 minor, 1 nit); owns 13 files.  
Findings: howto-core-b#2, howto-core-b#4, howto-core-b#5, howto-core-b#6, howto-core-b#8, howto-core-b#9, howto-core-b#11, gap1-rendered-artifacts#10

### `howto-hosted`: How-to: NAMS, ontologies, context-graph MCP, team memory, how-to index
12 findings (2 major, 7 minor, 3 nit); owns 6 files.  
Findings: howto-core-a#6, howto-hosted#0, howto-hosted#1, howto-hosted#2, howto-hosted#3, howto-hosted#5, howto-hosted#6, howto-hosted#8, howto-hosted#9, howto-hosted#10, howto-hosted#11, integ-b#8

### `howto-ts`: TypeScript how-tos
9 findings (1 major, 7 minor, 1 nit); owns 12 files.  
Findings: howto-ts#0, howto-ts#1, howto-ts#2, howto-ts#3, howto-ts#4, howto-ts#7, gap1-rendered-artifacts#11, gap1-rendered-artifacts#12, gap2-gap2-ts-inline-snippet-typeche#0

### `integ-a`: Integration how-tos: AWS, Google, index; Strands tutorial
11 findings (1 blocker, 1 major, 7 minor, 2 nit); owns 12 files.  
Findings: integ-a#0, integ-a#1, integ-a#3, integ-a#4, integ-a#5, integ-a#8, integ-a#9, integ-a#10, integ-a#11, x-diagrams#8, gap1-bolt-programs-live#6

### `integ-b`: Integration how-tos: CrewAI, LangChain, LlamaIndex, Microsoft, OpenAI Agents, PydanticAI; Microsoft tutorial
12 findings (3 major, 7 minor, 2 nit); owns 13 files.  
Findings: tut-py#0, tut-py#2, tut-py#3, integ-b#0, integ-b#1, integ-b#2, integ-b#4, integ-b#5, integ-b#9, integ-b#10, x-content-loss#3, x-content-loss#4

### `partials`: Shared partials (except backend-* labels)
3 findings (3 minor); owns 24 files.  
Findings: tut-py#5, tut-ts#3, howto-core-a#4

### `provider-docs`: NAMS AI provider docs family
17 findings (1 major, 13 minor, 3 nit); owns 7 files.  
Findings: provider#0, provider#2, provider#3, provider#6, provider#7, provider#9, provider#10, provider#11, provider#12, provider#13, provider#14, x-style#4, x-style#7, gap1-rendered-artifacts#6, gap1-rendered-artifacts#7, gap1-rendered-artifacts#8, gap2-gap2-install-commands-sweep#5

### `py-examples`: Python examples and their READMEs
16 findings (1 major, 10 minor, 5 nit); owns 507 files.  
Findings: py-examples#0, py-examples#3, py-examples#4, py-examples#5, py-examples#6, py-examples#8, py-examples#9, py-examples#10, howto-hosted#4, ref-other#8, x-security#2, x-security#3, x-consistency#14, gap2-gap2-install-commands-sweep#6, gap2-gap2-install-commands-sweep#10, gap2-gap2-install-commands-sweep#11

### `py-lib`: Python SDK source, unit/integration tests, CHANGELOG
9 findings (4 major, 3 minor, 2 nit); owns 283 files.  
Findings: py-lib#0, py-lib#1, py-lib#2, py-lib#3, py-lib#4, py-lib#5, SDK-1, SDK-2, SDK-3

### `ref-api-a`: Python API reference: client, adapters, factory, LLM provider, long-term
8 findings (1 major, 6 minor, 1 nit); owns 9 files.  
Findings: ref-api-a#0, ref-api-a#1, ref-api-a#2, ref-api-a#4, ref-api-a#5, ref-api-a#6, gap1-rendered-artifacts#9, gap1-rendered-artifacts#13

### `ref-api-b`: Python API reference: short-term, reasoning
7 findings (1 major, 4 minor, 2 nit); owns 9 files.  
Findings: ref-api-b#0, ref-api-b#1, ref-api-b#2, ref-api-b#3, ref-api-b#4, ref-api-b#6, ref-api-b#7

### `ref-config`: Configuration, env vars, CLI, MCP tools, schema objects
5 findings (2 major, 2 minor, 1 nit); owns 10 files.  
Findings: ref-config#0, ref-config#2, ref-config#4, ref-config#6, gap2-gap2-install-commands-sweep#1

### `ref-extract-schema`: Extractor and schema reference
9 findings (1 major, 5 minor, 3 nit); owns 10 files.  
Findings: ref-extract-schema#0, ref-extract-schema#1, ref-extract-schema#2, ref-extract-schema#3, ref-extract-schema#4, ref-extract-schema#5, ref-extract-schema#7, ref-extract-schema#8, x-style#9

### `ref-other`: Reference: backends, REST, NAMS, ontology/skills API, auth, TypeScript API, deployment
11 findings (2 major, 8 minor, 1 nit); owns 11 files.  
Findings: ref-other#0, ref-other#1, ref-other#2, ref-other#3, ref-other#4, ref-other#5, ref-other#6, ref-other#7, x-style#8, gap2-gap2-python-api-binding-sweep#0, gap2-gap2-python-api-binding-sweep#1

### `ts-examples`: Other TypeScript examples and shared tutorial helpers
12 findings (5 major, 4 minor, 3 nit); owns 153 files.  
Findings: ts-ex-a#0, ts-ex-b#1, ts-ex-b#2, ts-ex-b#3, ts-ex-b#4, ts-ex-b#5, ts-ex-b#6, ts-ex-b#7, ts-ex-b#8, ts-ex-b#9, tut-ts#2, gap2-gap2-expected-output-vs-progra#2

### `ts-provider-ex`: nams-ai-provider example and provider package docs
6 findings (2 major, 2 minor, 2 nit); owns 45 files.  
Findings: ts-ex-a#1, ts-ex-a#2, ts-ex-a#4, ts-ex-a#5, gap2-gap2-install-commands-sweep#2, gap2-gap2-markdown-link-check#4

### `ts-sdk`: TypeScript SDK source, tests, CHANGELOG, README
6 findings (3 major, 2 minor, 1 nit); owns 77 files.  
Findings: ts-sdk#0, ts-sdk#1, ts-sdk#2, ts-sdk#3, x-consistency#8, x-consistency#13

### `tut-hosted`: Hosted Python tutorials and programs
7 findings (1 blocker, 4 minor, 2 nit); owns 10 files.  
Findings: docs-examples-py#1, tut-hosted-py#1, tut-hosted-py#2, tut-hosted-py#3, tut-hosted-py#5, tut-hosted-py#6, gap2-gap2-expected-output-vs-progra#6

### `tut-kg`: Knowledge-graph tutorial and program
2 findings (1 blocker, 1 minor); owns 2 files.  
Findings: tut-py#4, gap1-bolt-programs-live#2

### `tut-py`: Python Bolt/local tutorials and programs
2 findings (1 blocker, 1 minor); owns 12 files.  
Findings: docs-examples-py#2, gap1-bolt-programs-live#1

### `tut-ts`: TypeScript tutorials
3 findings (1 blocker, 2 minor); owns 5 files.  
Findings: tut-ts#0, tut-ts#4, tut-ts#5

## Wave 2 work packages

### `w2-cross`: Small fixes spanning two areas (Makefile/examples runtime, render-check, Vertex table, config names, rendering artifact, install pins)
10 findings (5 major, 5 minor); owns 25 files.  
Findings: py-examples#1, py-examples#2, tooling-ci#1, tut-py#1, howto-core-b#0, integ-a#2, ref-config#1, ref-config#5, gap1-rendered-artifacts#0, gap2-gap2-install-commands-sweep#8

### `w2-labels`: Backend-support labels and NotSupportedError wording across pages
8 findings (2 major, 6 minor); owns 14 files.  
Findings: howto-core-a#0, ref-api-a#3, ref-api-b#5, gap1-backend-support-labels#0, gap1-backend-support-labels#2, gap1-backend-support-labels#5, gap1-backend-support-labels#7, gap1-backend-support-labels#8

## Wave 3 work packages

### `w3-anchors-howto`: Anchor landing and restoration: how-to pages
11 findings (8 minor, 3 nit); owns 57 files.  
Findings: howto-core-a#8, integ-a#6, howto-ts#6, gap1-compat-anchor-landing#3, gap1-compat-anchor-landing#4, gap1-compat-anchor-landing#5, gap1-compat-anchor-landing#8, gap1-compat-anchor-landing#10, gap1-compat-anchor-landing#21, gap1-compat-anchor-landing#24, x-content-loss#6

### `w3-anchors-ref`: Anchor landing and restoration: reference pages
6 findings (6 minor); owns 49 files.  
Findings: ref-config#3, x-style#1, gap1-compat-anchor-landing#1, gap1-compat-anchor-landing#9, gap1-compat-anchor-landing#22, x-content-loss#6

### `w3-anchors-rest`: Anchor landing and restoration: tutorials, explanation, FAQ, glossary, entry pages
6 findings (4 minor, 2 nit); owns 39 files.  
Findings: entry#0, entry#1, x-content-loss#6, gap1-compat-anchor-landing#6, gap1-compat-anchor-landing#20, gap1-compat-anchor-landing#26

## Out of scope

- `npm ci` fails with ERESOLVE in `typescript/examples/strands`. It fails identically on `main`, so it predates this branch; it is noted for a separate fix.
- `ty` reports an unresolved `gliner` import only in this local environment. CI installs all extras, so it doesn't fail there.
