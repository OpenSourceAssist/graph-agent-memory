# Remediation status for the 2026-09-24 branch review

Status of every finding in `branch-review.md`, applied to the working tree of `docs-review` (uncommitted), following `remediation-plan.md`.

## Outcome

- **Implementation (33 work packages, 3 waves plus a handoff wave):** 261 fixed, 14 partially fixed and then completed in later rounds, 5 completed through handoffs, and 1 declined with evidence, which a reviewer accepted.
- **Cross-area handoffs:** 98 requests. 50 applied, 21 adapted, 23 already done, 4 rejected with reasons.
- **Final independent check of all 52 blockers and majors, including the three SDK fixes:** 49 resolved on the first pass. The other 3 were partially resolved: `ref-api-b#0` (one remaining page), `ts-sdk#1` (unreleased TypeDoc labelling) and `gap1-bolt-programs-live#2` (the temperature limit on GPT-5-family models). All three were fixed in the final round.
- **Regression sweep of the remediation diff:** 17 confirmed and 2 refuted. All confirmed regressions were fixed in the final round (listed below).
- **Final gates, all green:**
  - Python: `ruff format --check` and `ruff check` over the CI paths, `mypy --strict`, `ty`, and 1,872 unit tests.
  - `tests/examples`: 918 passed. The only failures come from a local, untracked `examples/ontology-extraction/__pycache__` leftover that is not part of the branch.
  - `tests/docs`: 1,064 passed. The three failures that were already failing on `main` now pass.
  - Neo4j integration tests: 537 passed.
  - `make test-docs-integration` (new, and run in CI): 22 passed. It runs the tutorial and how-to programs against Neo4j.
  - Docs: `make docs` with 0 warnings, `check_docs.py --build` with 0 errors over 145 pages, the diagram manifest status is clean, and the rendered-site checks pass under Playwright.
  - TypeScript: the SDK (293 unit and 96 integration tests), the provider package (136 tests, pack), and nine of ten examples (`tsc`, tests and build). `npm ci` in `strands` fails with ERESOLVE, as it does on `main`.
  - CI YAML and Makefile references are consistent.

## SDK changes (next release, `CHANGELOG.md` [Unreleased])

- GLiREL relation extraction now receives token indices and string head and tail texts (SDK-1).
- Auto-extracted entities are embedded when an embedder is configured, so `search_entities` finds them (SDK-2). The regression sweep caught an issue in this fix: `generate_embedding=False` must still prevent embedder calls. That is now restored.
- `add_messages_batch` gives untimed messages strictly increasing timestamps, and readback breaks ties in chain order (SDK-3). The head test in the tie query is anchored on the bound node; before that change, `migrate_message_links` was quadratic.
- Behavioural change: `ontology.get_active()` reports the bound revision. It is marked BREAKING in both changelogs, and the TypeScript TSDoc labels it as unreleased.

The docs programs keep working on the released 0.6.0, which doesn't have these fixes. They use explicit batch timestamps, a graph read instead of entity vector search, and an LLM relation stage in place of GLiREL.

## Regressions found and fixed after the per-package reviews

- [minor] `src/neo4j_agent_memory/memory/short_term.py:1325`: generate_embedding(s)=False no longer prevents embedder calls, and an embedder error now surfaces after the message is committed
- [nit] `CHANGELOG.md:23`: "Message timestamps never sort before the conversation's current last message" overstates what the code does
- [nit] `CHANGELOG.md:12`: Breaking changes are filed under Changed with no BREAKING marker, unlike the TS changelog
- [minor] `typescript/packages/packages:1`: Stray self-referential symlink left in the working tree (untracked, not gitignored)
- [minor] `typescript/examples/nextjs-memory-chat/README.md:26`: Rewritten description of the provider's retrieval drops the reasoning-step source
- [nit] `examples/lennys-memory/Makefile:161`: `make mcp-server` no longer works against the example's own local Neo4j without an explicit export
- [nit] `deploy/mcpb/README.md:27`: New pack command writes the bundle to an un-ignored path at the repository root
- [minor] `tests/docs/utils/extract_code.py:97`: New CodeSnippet.parse() only parses (PyCF_ONLY_AST), so the docs syntax check stopped catching compile-phase SyntaxErrors that HEAD caught
- [minor] `scripts/check_docs.py:379`: New section-id compatibility guard (docs_section_ids.json) is wired only into check_docs.main(), so no CI job can ever fail on it
- [major] `docs/modules/ROOT/examples/knowledge_graph.py:80`: Knowledge-graph ingest now needs a chat model that accepts temperature=0; gpt-5-family models fail on 0.6.0
- [minor] `docs/modules/ROOT/pages/how-to/integrations/microsoft-agent.adoc:205`: New GDS fallback table misdescribes community detection: the 0.6.0 fallback query fails and returns one community
- [minor] `docs/modules/ROOT/pages/tutorials/knowledge-graph.adoc:49`: Rewritten Aura setup partial contradicts the unchanged 'no database fallback' manifest rows on three tutorials
- [major] `docs/modules/ROOT/pages/how-to/integrations/aws-hybrid-memory.adoc:94`: New how-to text says clear_session removes reasoning traces, contradicting the corrected reference
- [minor] `docs/modules/ROOT/pages/reference/backend-capabilities.adoc:45`: List of NAMS preference/fact calls that raise TypeError leaves out get_facts_about
- [major] `README.md:115`: Rewritten, 0.6.0-pinned uvx MCP commands leave out the httpx fix that sdks/python.adoc now requires, so the server crashes on Bolt connect
- [minor] `README.md:276`: New text names the Streamable HTTP endpoint as /mcp/, but the server serves /mcp and redirects /mcp/
- [minor] `README.md:277`: The replacement HTTP command binds an unauthenticated memory server to all interfaces without a caveat

## Items still open for a maintainer

- `npm ci` in `typescript/examples/strands` fails with ERESOLVE (openai ^7 against the Strands SDK peer range openai ^6). It fails the same way on `main`, so it predates this branch and was not in scope.
- CLAUDE.md says an in-tree TCK suite (`typescript/test/tck/`) runs in TypeScript CI on every PR, but `ci-typescript.yml` does not run it. The TypeScript gate flagged this while running.
- Antora does not clean `docs/build/site` between runs, so deleted attachments can linger in a local build. Use `npm run clean` (or delete `docs/build`) before the rendered checks.

## Per-finding status

Each row gives the finding id, its severity, the status reported by the work package, and the verdict of the final package review. Blockers and majors also show the final independent check. "(new issue)" rows are defects that reviewers found in a fix, which were fixed in the same package.

### ci-tooling (wave 1, 2 review round(s))

- `ts-ex-b#0` [blocker] fixed · review: resolved · final check: resolved: CI builds vercel-ai-provider only for nams-ai-provider, but nextjs-memory-chat now depends on it too
- `tooling-ci#0` [major] fixed · review: resolved · final check: resolved: Keyboard users can't reach the new tutorial copy button: its container stays display:none unless hovered
- `tooling-ci#2` [major] fixed · review: resolved · final check: resolved: Documented `export_diagrams.mjs --all` writes 23 untracked PNGs that check_manifest rejects as orphans
- `ex-python#1` [minor] fixed · review: resolved: New pytest.mark.rendered used but not registered in pyproject.toml, causing a warning on every run
- `py-examples#7` [minor] fixed · review: resolved: `make help` describes docs-lint as 'Watch for changes and rebuild'
- `tooling-ci#4` [minor] fixed · review: resolved: New tests/docs/test_nav_labels.py is not run by any CI job
- `tooling-ci#5` [minor] fixed · review: resolved: Image alt-quoting check flags valid named attributes whose quoted value has a comma
- `tooling-ci#9` [nit] fixed · review: resolved: Comment says nine of ten examples ship a vitest suite; all ten do
- `x-diagrams#10` [nit] fixed · review: resolved: add-refs still inserts PNG embeds without a caption, against the new SVG policy

### deploy (wave 1, 1 review round(s))

- `deploy#0` [minor] fixed · review: resolved: MCPB manifest fails the official validator; Quick Start's extension env setup cannot work
- `deploy#1` [minor] fixed · review: resolved: Documented endpoint `/mcp/` is a 307 redirect to an absolute http:// `/mcp` URL
- `deploy#4` [minor] fixed · review: resolved: Local smoke test runs `fastmcp` on the host but the install step was removed
- `deploy#5` [minor] fixed · review: resolved: env.yaml.example contradicts the branch's new image config (OpenAI extraction, unused VERTEX_AI_LOCATION)
- `deploy#7` [nit] fixed · review: resolved: Review-process narration left in the user-facing deployment README

### diagrams (wave 1, 2 review round(s))

- `x-diagrams#0` [minor] fixed · review: —: Published POLE+O diagram shows five subtypes the SDK rejects
- `x-diagrams#2` [minor] handed_off · review: resolved: Modes diagram says NAMS retrieves and persists automatically in every mode, contradicting tools/hooks
- `x-diagrams#3` [minor] fixed · review: —: Manifest statuses inverted: stale PNGs recorded as clean, fresh SVGs as unresolved
- `x-diagrams#4` [minor] fixed · review: —: memory-architecture.svg referring_pages omits memory-types.adoc, which now embeds it
- `x-diagrams#6` [minor] fixed · review: —: Migration record points to a scene that does not exist
- `x-diagrams#7` [minor] fixed · review: —: diagram-descriptions.md disagrees with the manifest and with the diagrams' own text
- `x-diagrams#12` [nit] fixed · review: —: Re-authored diagrams break house style: roughness 0 and labels well under 20px
- `x-diagrams#13` [nit] fixed · review: —: three-extraction-approaches.svg is a byte-identical copy of extraction-pipeline.svg

### docs-tests (wave 1, 3 review round(s))

- `ex-python#0` [blocker] fixed · review: — · final check: resolved: ruff format --check fails on 3 branch-touched test files, breaking CI's format-check step
- `gap1-bolt-programs-live#3` [major] partially_fixed · review: not_resolved · final check: resolved: No test or CI job runs the Bolt docs programs against Neo4j; mocked suite passes while live runs fail
- `gap1-bolt-programs-live#5` [major] fixed · review: — · final check: resolved: test_howto_examples.py tests the old how-to code, not the core_memory_recipes.py/extraction_recipes.py tags now shown
- `deploy#3` [minor] fixed · review: —: Test fakes vertexai availability but never asserts the Dockerfile installs an extra providing it
- `docs-tests-a#0` [minor] fixed · review: —: 'stops before reasoning' assertion is vacuous: nams_quickstart.exercise never calls reasoning
- `docs-tests-b#3` [minor] fixed · review: —: Import checker counts names imported only under TYPE_CHECKING as declared, so it certifies imports that fail at runtime
- `docs-tests-b#5` [minor] fixed · review: —: Obsolete is_signature_doc skip hides 141 blocks that all compile, including real programs, from syntax and drift checks
- `docs-tests-b#6` [minor] fixed · review: —: test_perturbed_label_is_caught tests Python's assert, not the alignment check
- `docs-tests-b#7` [minor] fixed · review: —: test_complete_async_helper_keeps_future_import_at_module_level compiles a literal and exercises no project code
- `docs-tests-b#8` [minor] fixed · review: —: Trace-outcome assertions pass vacuously when a recipe records no trace
- `docs-tests-b#9` [minor] handed_off · review: —: 'make test-docs' fails in the documented dev environment: this module needs agent-framework-openai, which no extra installs
- `gap1-bolt-programs-live#4` [minor] fixed · review: —: test_tutorial_examples.py still tests the old tutorial code, which the rewritten pages no longer show
- `docs-tests-a#1` [nit] fixed · review: —: Skills seed runs only against permissive fakes; its SDK calls are never checked against real NAMS signatures
- `docs-tests-b#10` [nit] fixed · review: —: Stale ALLOWED_DIVERGENCE entry exempts how-to/integrations/index.adoc from drift detection
- `docs-tests-b#12` [nit] fixed · review: —: Stale comments and docstrings still describe the removed async wrapper and allowed_missing allowlist

### entry (wave 1, 3 review round(s))

- `tooling-ci#6` [minor] fixed · review: resolved: Excalidraw skill tells authors to embed PNG exports with no caption, against MAINTAINING's SVG/caption rule
- `entry#3` [minor] fixed · review: resolved: CLAUDE.md still names the Excalidraw directory this branch moved away
- `entry#4` [minor] fixed · review: resolved: CLAUDE.md CI section misses the new docs triggers and still says the TCK runs on every PR
- `entry#5` [minor] fixed · review: resolved: CONTRIBUTING still lists two published packages and omits the nams-ai-provider release flow
- `entry#6` [minor] fixed · review: resolved: README Development section still cds into nonexistent agent-memory/neo4j-agent-memory
- `entry#7` [minor] fixed · review: resolved: README says 'All nine TypeScript examples' (there are ten) and misstates Python dependency files
- `entry#8` [minor] fixed · review: resolved: Edited README MCP command still uses deprecated `--transport sse` for 'network deployment'
- `entry#9` [minor] fixed · review: resolved: Aura quickstarts now tell readers to set ANTHROPIC_API_KEY but hard-code a retired Claude 3.5 model
- `x-content-loss#7` [minor] fixed · review: resolved: Python extras table removed; several extras ([opentelemetry], [fuzzy], [cli] install) now undocumented
- `gap2-gap2-install-commands-sweep#9` [minor] fixed · review: resolved: README uvx MCP commands are unpinned although the same README says its instructions use ==0.6.0
- `tooling-ci#8` [nit] fixed · review: resolved: Skill says `npm run serve` previews the existing build, but the script rebuilds first
- `x-style#10` [nit] handed_off · review: decline_ok: Nav drops the '(Preview)' label from the Agent Skills entries but keeps it elsewhere

### explanation (wave 1, 1 review round(s))

- `explanation#0` [major] fixed · review: resolved · final check: resolved: multi_tenant=True claim is backwards: scoping works without it and unscoped writes then raise
- `explanation#1` [major] fixed · review: resolved · final check: resolved: POLE+O subtype catalog removed; the page it defers to has no subtype list
- `explanation#2` [major] fixed · review: resolved · final check: resolved: FAQ 'Which Neo4j versions are supported?' points to pages that state no version
- `explanation#3` [minor] fixed · review: resolved: extra_forbidden FAQ dropped the fix and hints it may not be released
- `explanation#4` [minor] fixed · review: resolved: `write_mode="buffered"` placed on MemorySettings; it belongs on MemorySettings.memory
- `explanation#5` [minor] fixed · review: resolved: Says Strands and Mastra merge tiers into one block and replay recent messages; they do not
- `explanation#6` [minor] fixed · review: resolved: Observations/reflections called hosted-TS-only, but the Python MCP server has its own three-tier view
- `explanation#7` [minor] fixed · review: resolved: Tells readers to compare against a 'version banner' the docs site does not have
- `explanation#8` [nit] fixed · review: resolved: llm=None check attributed to _resolve_providers; it lives in _validate_llm_consistency
- `explanation#9` [nit] fixed · review: resolved: Reasoning 'observation' described as a tool call's result; it is a ReasoningStep field

### howto-core-a (wave 1, 2 review round(s))

- `docs-examples-py#0` [blocker] fixed · review: resolved · final check: resolved: messages recipe asserts an order the SDK doesn't guarantee, and fails in about 40% of runs
- `howto-core-a#1` [minor] fixed · review: resolved: Merge claim that every copied edge carries the source id and migrated_from is wrong for most types
- `howto-core-a#2` [minor] fixed · review: resolved: find_potential_duplicates confidence is always 0.0 on Bolt, and each pair is returned twice
- `x-diagrams#9` [minor] fixed · review: resolved: Reasoning-trace caption promises touched entities that the diagram does not draw
- `howto-core-a#5` [minor] fixed · review: resolved: Catalog example's "Avoid duplicates" filter never matches GLiNER output types
- `howto-core-a#7` [nit] fixed · review: resolved: Chunk intro refers to a `deduplicate` keyword "shown below" that the code block doesn't use

### howto-core-b (wave 1, 3 review round(s))

- `howto-core-b#2` [minor] fixed · review: resolved: Retained anchors for the old dry-run and call sections point to the wrong sections
- `howto-core-b#4` [minor] fixed · review: resolved: The note that adoption writes no embeddings was removed
- `howto-core-b#5` [minor] fixed · review: resolved: The page is still the UserMemory reference target, but the user API and :User schema were removed
- `howto-core-b#6` [minor] fixed · review: resolved: Claims Bring your own model has runnable embedding-instance code, but that page shows only llm=
- `howto-core-b#8` [minor] fixed · review: resolved: How-tos describe a 'checked-out source' SDK, not the published 0.6.0 package
- `howto-core-b#9` [minor] fixed · review: resolved: New Prerequisites omit the cli and mcp extras that the MCP CLI sections need
- `gap1-rendered-artifacts#10` [minor] fixed · review: resolved: `Thought: ` / `Action: ` / `Observation: ` show literal backticks (trailing space inside code)
- `howto-core-b#11` [nit] fixed · review: resolved: Changed xref link texts use stale or inconsistent titles for their target pages

### howto-hosted (wave 1, 1 review round(s))

- `howto-hosted#0` [major] fixed · review: resolved · final check: resolved: Claude Code .mcp.json snippet puts literal Aura password and OpenAI key in the committed project file
- `howto-hosted#1` [major] fixed · review: resolved · final check: resolved: Index says multi-tenancy scopes entities to users; the target page and scope reference say it does not
- `howto-core-a#6` [minor] fixed · review: resolved: How-to index says the dedup page reviews a flagged SAME_AS pair; the recipe merges a manual pair
- `howto-hosted#2` [minor] fixed · review: resolved: Two index blurbs describe the opposite of what their target pages do (TypeScript MCP, hybrid provider)
- `howto-hosted#3` [minor] fixed · review: resolved: Several index blurbs overclaim relative to the rewritten pages (offline, ontology effect, migration effort, audit)
- `howto-hosted#5` [minor] fixed · review: resolved: use-nams dropped the NAMS span/observability details and the runnable-example links; no other page has them
- `howto-hosted#6` [minor] fixed · review: resolved: Retained old anchors land on unrelated sections; stacked [#id] lines are silently overridden
- `integ-b#8` [minor] fixed · review: resolved: New index entry says Microsoft wiring uses `ChatAgent`, which the page and framework no longer have
- `howto-hosted#8` [minor] fixed · review: resolved: Cursor prose refers to ${VAR} expansion that the included cursor template does not use
- `howto-hosted#9` [nit] fixed · review: resolved: Appendix cross-reference <<_list_the_catalog>> points to the wrong section for the get_active note
- `howto-hosted#10` [nit] fixed · review: resolved: "the installation and connection check below" links to another page
- `howto-hosted#11` [nit] fixed · review: resolved: Seed step says it creates a conversation but omits that it also writes two entities to the shared workspace

### howto-ts (wave 1, 2 review round(s))

- `howto-ts#0` [major] fixed · review: resolved · final check: resolved: Next.js guide pairs persistInteractions:false with an assistant-only write pattern, so user turns are lost
- `howto-ts#1` [minor] fixed · review: resolved: MCP verify step runs `npm run lint`, but the mcp example has no lint script
- `howto-ts#2` [minor] fixed · review: resolved: Mastra follow-up snippet stores only the assistant reply in the new thread and drops the user turn
- `howto-ts#3` [minor] fixed · review: resolved: Overview calls neo4j-agent-memory 'the self-hosted package' and sends hosted Python users elsewhere
- `howto-ts#4` [minor] fixed · review: resolved: Overview names the NAMS provider's four modes differently from the mode-selection page
- `gap1-rendered-artifacts#11` [minor] fixed · review: resolved: `TypeError`s merges two identifiers into one code span with a literal backtick
- `gap1-rendered-artifacts#12` [minor] fixed · review: resolved: `boolean \| ExtractionConfig` shows a literal backslash (escape only needed in tables)
- `gap2-gap2-ts-inline-snippet-typeche#0` [minor] fixed · review: resolved: Manual-wiring Strands block fails strict tsc: Neo4jConversationManager is not a ConversationManager
- `howto-ts#7` [nit] fixed · review: resolved: New streaming snippet defaults to gpt-4o-mini while the rest of the page uses gpt-5-mini

### integ-a (wave 1, 3 review round(s))

- `integ-a#0` [blocker] fixed · review: resolved · final check: resolved: Cloud embeddings recipe raises TypeError for both Bedrock and Vertex before any database write
- `integ-a#3` [major] fixed · review: resolved · final check: resolved: Strands page dropped context_graph_tools, retrieval_config and constructor reference; no other page has them
- `integ-a#1` [minor] fixed · review: resolved: 'Deployment reference' link points to the docs-site publication page, not app deployment
- `integ-a#4` [minor] fixed · review: resolved: Hybrid 'explicit route' verification cannot fail; search errors are swallowed
- `gap1-bolt-programs-live#6` [minor] fixed · review: resolved: hybrid recipe passes session_id to search_memory, but results include other sessions relabelled as this one
- `integ-a#5` [minor] fixed · review: resolved: Index rows describe Google Cloud and Hybrid pages contrary to their rewritten content
- `integ-a#8` [minor] fixed · review: resolved: Strands how-to reuses the tutorial's program and session file but omits its inspect/recovery path
- `integ-a#9` [minor] fixed · review: resolved: ADK recipe iterates event.content.parts without guarding for None
- `x-diagrams#8` [minor] fixed · review: resolved: Strands caption says embeddings feed all three surfaces; diagram says two
- `integ-a#10` [nit] fixed · review: resolved: Credential setup is instructed after the block that already runs aws sts get-caller-identity
- `integ-a#11` [nit] fixed · review: resolved: Retained hybrid anchors land on text that no longer mentions their topic

### integ-b (wave 1, 3 review round(s))

- `integ-b#0` [major] fixed · review: resolved · final check: resolved: LangChain @tool snippet has no docstring, so LangChain raises ValueError when the tool is defined
- `integ-b#1` [major] fixed · review: resolved · final check: resolved: Says Microsoft create_memory_tools returns plain definitions to translate, but it returns FunctionTool objects
- `integ-b#2` [major] fixed · review: resolved · final check: resolved: Rewrites dropped adapter API detail that no other docs page now covers
- `tut-py#0` [minor] fixed · review: resolved: Preview note calls Microsoft Agent Framework 'pre-1.0' while the page pins the 1.x GA line
- `tut-py#2` [minor] fixed · review: resolved: Shared model-selection partial asks for Chat Completions support, but this lesson uses the Responses API
- `tut-py#3` [minor] fixed · review: resolved: Missing OPENAI_MODEL is only detected after the preference has been written
- `integ-b#4` [minor] fixed · review: resolved: execute_memory_tool is named without its import path, and the package root does not export it
- `integ-b#5` [minor] partially_fixed · review: resolved: Overstates what the OpenAI Agents recipe does, and nothing tests the Agents SDK path
- `x-content-loss#3` [minor] fixed · review: resolved: LangChain middleware/retriever options and NAMS session_id requirement no longer documented anywhere
- `x-content-loss#4` [minor] fixed · review: resolved: nams_memory_tools() (the PydanticAI hosted tool set) dropped from all docs
- `integ-b#9` [nit] fixed · review: resolved: get_conversation readback is shown without await
- `integ-b#10` [nit] fixed · review: resolved: Screenshot is captioned as a TfL Explorer example application that doesn't exist in the repo

### partials (wave 1, 1 review round(s))

- `howto-core-a#4` [minor] fixed · review: resolved: Setup partial on how-to pages tells readers to run a file manifest and offline assembly checks that aren't there
- `tut-py#5` [minor] fixed · review: resolved: Equivalents table pairs add_messages_batch with bulkAddMessages; the Python counterpart is bulk_add_messages
- `tut-ts#3` [minor] partially_fixed · review: resolved: Pages say Node.js 22 or later, but every command uses `--env-file-if-exists` (Node 22.9+)

### provider-docs (wave 1, 3 review round(s))

- `provider#0` [major] fixed · review: — · final check: resolved: Docs imply omitting conversationId starts a new conversation; it silently reuses the user's latest
- `provider#2` [minor] handed_off · review: not_resolved: Tools-mode expected output: wrong line order, missing final-step lines and turn-2 fallback line
- `provider#3` [minor] fixed · review: —: Hooks-mode expected output shows 3/3/2/2 saved turns; one tool call per turn saves 4
- `provider#6` [minor] fixed · review: —: How-to prerequisites omit OPENAI_API_KEY, which all four programs need by default
- `provider#7` [minor] fixed · review: —: 'Save as provider-mode.ts' has no matching run step; run instructions assume the repo checkout and src/
- `provider#9` [minor] fixed · review: —: query_memory limit documented as 1–20 without noting that results are capped at 12
- `provider#10` [minor] fixed · review: —: baseProvider typed as `(modelId) => LanguageModel`; a string model id is not accepted
- `provider#11` [minor] fixed · review: —: loadSession documented as 'Never throws', but it throws when no userId is available
- `provider#12` [minor] fixed · review: —: Reference claims 'every export' but omits exported types, including tool result shapes
- `provider#13` [minor] fixed · review: —: Explanation says assistant text is skipped only for tool-call-only steps; any step with an app tool call is skipped
- `gap1-rendered-artifacts#6` [minor] fixed · review: —: Nested backticks in the store_memory input schema break the schema rendering
- `gap1-rendered-artifacts#7` [minor] fixed · review: —: `=>`/`->` inside inline code render as ⇒/→, corrupting TS signatures and Cypher patterns
- `gap1-rendered-artifacts#8` [minor] fixed · review: —: Spread example `{ ...tools }` renders as `{ …tools }` (ellipsis character)
- `gap2-gap2-install-commands-sweep#5` [minor] fixed · review: —: Tools-mode page documents toolsWithMcp but its install command omits the optional @ai-sdk/mcp peer
- `provider#14` [nit] fixed · review: —: Turn-4 card redaction is credited to PreMemoryWrite; UserPromptSubmit already redacted the saved prompt
- `x-style#4` [nit] fixed · review: —: Mode how-tos don't end with verification: long reference sections follow 'Run and verify'
- `x-style#7` [nit] fixed · review: —: 'Choose a NAMS AI provider mode' is a comparison and reference page filed as a how-to

### py-examples (wave 1, 2 review round(s))

- `py-examples#0` [major] fixed · review: — · final check: resolved: 29 example READMEs link to DOCUMENTATION_REMEDIATION_STATUS.md, which does not exist
- `py-examples#5` [minor] fixed · review: —: BaseContextProvider ImportError troubleshooting lost its fix and now points at a missing file
- `py-examples#3` [minor] fixed · review: —: README says the eval runner ignores NEO4J_DATABASE, but main.py reads it
- `py-examples#4` [minor] fixed · review: —: Lenny's README says the backend reads NEO4J_DATABASE; the backend has no such setting
- `py-examples#6` [minor] fixed · review: —: Contributor guidance no longer asks for a 'verified against' footer, but the registry test requires one
- `py-examples#8` [minor] fixed · review: —: FSA GETTING_STARTED Node floors contradict the Node 22.13+/24 floor the branch set in the READMEs
- `howto-hosted#4` [minor] fixed · review: —: Included doctor.py and seed_workspace.py still assert '47' hosted tools and a 'Platinum-tier' Cypher feature
- `ref-other#8` [minor] fixed · review: —: README links to nams-mcp for 'the 47-tool surface', but this branch removed that count
- `x-consistency#14` [nit] fixed · review: —: Examples index still states '47 scope-gated tools', a count the hosted MCP reference now declines to give
- `x-security#3` [minor] fixed · review: —: Claude Desktop MCP snippet still passes --password password with no URI after the Aura migration
- `gap2-gap2-install-commands-sweep#6` [minor] fixed · review: —: Installing glirel alone (without loguru) makes --relations silently skip
- `gap2-gap2-install-commands-sweep#10` [minor] fixed · review: resolved: Strands READMEs still install from git@main 'until released', though 0.6.0 on PyPI ships the classes
- `py-examples#9` [nit] fixed · review: —: Expected output drops the 'Done. Inspect …' prefix that main.py still prints
- `py-examples#10` [nit] fixed · review: —: 'through a example architecture' (should be 'an example')
- `x-security#2` [nit] partially_fixed · review: —: README puts literal OpenAI and Aura credentials in a repo-root .cursor/mcp.json that git does not ignore
- `gap2-gap2-install-commands-sweep#11` [nit] fixed · review: —: no_llm README install is unpinned while its main.py (shown on the docs page) was changed to ==0.6.0

### py-lib (wave 1, 3 review round(s))

- `py-lib#0` [major] fixed · review: — · final check: resolved: Only live check of the rewritten get_active() is now skipped in every CI run
- `SDK-3` [major] fixed · review: — · final check: resolved: add_messages_batch gives every message the same timestamp, so conversation readback order is arbitrary
- `py-lib#2` [nit] fixed · review: —: The 'appends serialize' claim does not cover add_messages_batch, which can still fork the chain
- `SDK-2` [major] fixed · review: — · final check: resolved: Entities created by auto-extraction are stored without embeddings, so search_entities never finds them
- `SDK-1` [major] fixed · review: — · final check: resolved: GLiRELExtractor passes character offsets where GLiREL expects token indices; head/tail text can come back as token lists
- `py-lib#1` [minor] fixed · review: —: Forked-chain test builds a fork races never produce; migrate 'repair' leaves the fork edge
- `py-lib#3` [minor] fixed · review: —: ORDER BY on GET_LAST_MESSAGE makes the tail lookup scan every message in the conversation
- `py-lib#5` [nit] fixed · review: —: Python accepts a non-string version.schema_json; TypeScript rejects it
- `py-lib#4` [minor] fixed · review: —: Branch changes shipped behaviour in src but leaves CHANGELOG [Unreleased] empty

### ref-api-a (wave 1, 2 review round(s))

- `ref-api-a#0` [major] fixed · review: — · final check: resolved: get_facts_about described as matching subject or object; it matches subject only
- `ref-api-a#1` [minor] fixed · review: —: search_entities prose claims a subtype control that does not exist (also NAMS table 'Bolt subtypes')
- `ref-api-a#2` [minor] fixed · review: —: NAMS table omits that get_entity_relationships takes an id and returns a different shape
- `ref-api-a#4` [minor] fixed · review: —: Escaped `\{...}` renders with a literal backslash in the built page
- `ref-api-a#5` [minor] fixed · review: —: Overview promises an extra-to-adapter mapping that the 'Adapter availability' section lacks
- `gap1-rendered-artifacts#9` [minor] fixed · review: —: `<<graph>>` points at a bare anchor with no title and renders as the link text "[graph]"
- `gap1-rendered-artifacts#13` [minor] partially_fixed · review: —: New model-field tables publish a Description column that is empty in every row
- `ref-api-a#6` [nit] fixed · review: —: query.cypher shown with a 'parameters' argument; the real parameter is 'params'

### ref-api-b (wave 1, 2 review round(s))

- `ref-api-b#0` [major] fixed · review: — · final check: partially_resolved: clear_session is documented as deleting a session's traces, but the SDK never creates the link it follows
- `ref-api-b#1` [minor] fixed · review: —: NAMS create_conversation looks like session_id is optional, but calling it without one raises TypeError
- `ref-api-b#2` [minor] fixed · review: —: delete_message raises a Neo4j error for stored messages; it does not return False
- `ref-api-b#4` [minor] fixed · review: —: The steps page says "Bolt only" though NAMS implements add_step, record_tool_call and link_trace_to_message
- `ref-api-b#6` [minor] fixed · review: —: search_steps note implies steps have no embeddings unless complete_trace generates them
- `ref-api-b#3` [nit] fixed · review: —: The hub says the hosted lifecycle limits are "below", but they are on a subpage
- `ref-api-b#7` [nit] fixed · review: —: Internal page named as a code literal instead of an xref

### ref-config (wave 1, 3 review round(s))

- `ref-config#0` [major] fixed · review: resolved · final check: resolved: conversation_ttl_days row names a nonexistent `older_than_days` argument (actual: `ttl_days`)
- `ref-config#2` [major] fixed · review: resolved · final check: resolved: NAM_MEMORY__CONVERSATION_TTL_DAYS / AUDIT_READ rows repeat the wrong `older_than_days` and `audit_reads` names
- `ref-config#4` [minor] fixed · review: resolved: `<<integration-limits>>` renders with raw link text "[integration-limits]"
- `gap2-gap2-install-commands-sweep#1` [minor] fixed · review: resolved: CLI page installs only [cli], but its YAML schema commands need PyYAML, which no extra provides
- `ref-config#6` [nit] fixed · review: resolved: Hub page still says field tables are "below" after they moved to subpages; "in this checkout" wording

### ref-extract-schema (wave 1, 1 review round(s))

- `ref-extract-schema#0` [major] fixed · review: resolved · final check: resolved: DEFAULT_GLIREL_MODEL documented as jackboyla/glirel_base; the source default is jackboyla/glirel-large-v0
- `ref-extract-schema#1` [minor] fixed · review: resolved: Says the 4000/200 chunk defaults change when token chunking is selected; the constructor keeps them
- `ref-extract-schema#2` [minor] fixed · review: resolved: GLiREL install note omits spaCy and en_core_web_sm, which GLiRELExtractor needs for tokenization
- `ref-extract-schema#3` [minor] fixed · review: resolved: with_llm_fallback is called a fallback, but build() runs the LLM on every extraction
- `ref-extract-schema#4` [minor] fixed · review: resolved: DomainSchema example calls GLiNEREntityExtractor without importing it
- `ref-extract-schema#5` [minor] fixed · review: resolved: SchemaManager(client.graph) goes through the deprecated graph proxy; load_schema emits a DeprecationWarning
- `ref-extract-schema#7` [nit] fixed · review: resolved: Sphinx roles (:meth:, :class:) copied from docstrings render literally in AsciiDoc
- `ref-extract-schema#8` [nit] fixed · review: resolved: Docstring bullet lists are flattened into single table cells
- `x-style#9` [nit] partially_fixed · review: resolved: schemas-custom reference keeps how-to material and unlabeled partial snippets

### ref-other (wave 1, 3 review round(s))

- `ref-other#0` [major] fixed · review: — · final check: resolved: Embedded Python SDK credentials named as NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD; MemorySettings ignores them
- `ref-other#1` [major] fixed · review: — · final check: resolved: Active-binding caveat covers Python 0.6.0 only; released TS 0.5.0 has the same latest-revision bug
- `ref-other#2` [minor] fixed · review: —: getActive/activate rows contradict the revised ontology-api page and the HEAD TS source
- `ref-other#3` [minor] fixed · review: —: Language-neutral limits page says 'the SDK retries' and raises RateLimitError; TS does neither
- `ref-other#4` [minor] fixed · review: —: 'Capability matrix' links point to backends.adoc section that is no longer a matrix
- `ref-other#5` [minor] fixed · review: —: waitForExtraction prose says search limit is always at least 10; an explicit smaller limit wins
- `ref-other#6` [minor] fixed · review: —: Self-hosted MCP server options list Bolt as the only backend; server also runs against NAMS
- `ref-other#7` [minor] fixed · review: —: Skills page still fixes the MCP surface at '13 tools' after nams-mcp dropped fixed counts
- `gap2-gap2-python-api-binding-sweep#0` [minor] partially_fixed · review: —: Docs call Python get_active() unreliable, but this branch's SDK source fixes it
- `gap2-gap2-python-api-binding-sweep#1` [minor] fixed · review: —: Capabilities page implies add_relationship stores attributes; the Bolt write drops them
- `x-style#8` [nit] fixed · review: —: Reference pages contain editorial notes about their own former layout, and tutorial narrative

### ts-examples (wave 1, 2 review round(s))

- `ts-ex-a#0` [major] fixed · review: resolved · final check: resolved: Extraction wait treats only per-message status "done" as finished, so "completed" times out every cleanup
- `ts-ex-b#1` [major] fixed · review: resolved · final check: resolved: Relative links to the Python gallery and the CI workflow now resolve outside the repository
- `ts-ex-b#2` [major] fixed · review: resolved · final check: resolved: 'Running an example' walkthrough for nextjs-memory-chat omits the provider build and fails
- `ts-ex-b#3` [major] fixed · review: resolved · final check: resolved: README still says the model gets the rail's three tiers and the recent history, but the provider injects neither
- `tut-ts#2` [major] fixed · review: resolved · final check: resolved: MCP docs-assembly test builds from the SDK's own node_modules, not the lesson's install
- `ts-ex-b#4` [minor] fixed · review: resolved: README says the suite checks the abort and error settle paths, but no test covers either
- `ts-ex-b#5` [minor] fixed · review: resolved: The streaming-persistence section misdescribes both the Cloudflare pattern and `persistInteractions: false`
- `ts-ex-b#6` [minor] fixed · review: resolved: 'Build the shared packages' section makes two wrong claims: a shared tsconfig and that everything runs on current source
- `gap2-gap2-expected-output-vs-progra#2` [minor] fixed · review: resolved: LangChain example: first turn shows injected memory the program no longer produces
- `ts-ex-b#7` [nit] fixed · review: resolved: Test comment says memory is appended as a second text part; the provider prepends it as the first
- `ts-ex-b#8` [nit] fixed · review: resolved: 'Graph, not buffer' bullet describes a readback that the run does not end with
- `ts-ex-b#9` [nit] fixed · review: resolved: Garbled sentence in the fake's header comment

### ts-provider-ex (wave 1, 1 review round(s))

- `ts-ex-a#1` [major] fixed · review: resolved · final check: resolved: Hooks-mode test passes even when the deny hook and the retry hook are disabled
- `gap2-gap2-install-commands-sweep#2` [major] fixed · review: resolved · final check: resolved: Provider README says it is version 0.2.0 with Node >=20; the package is 0.3.0 with Node >=22
- `ts-ex-a#2` [minor] fixed · review: resolved: Entry-point check `file://${argv[1]}` silently does nothing when the path has spaces or other encoded characters
- `ts-ex-a#4` [minor] fixed · review: resolved: Hooks-mode README and header comment get the turn count and hook firing wrong
- `ts-ex-a#5` [nit] fixed · review: resolved: Test header and README still say the doc pages do not exist yet ("another worker")
- `gap2-gap2-markdown-link-check#4` [nit] fixed · review: resolved: README names ../vercel-ai/test/docs-hosted-stub.js; the file on disk is .ts

### ts-sdk (wave 1, 2 review round(s))

- `ts-sdk#0` [major] fixed · review: resolved · final check: resolved: E2E cleanup expects NotFoundError, but the REST transport throws TransportError(404)
- `ts-sdk#1` [major] partially_fixed · review: resolved · final check: partially_resolved: Unreleased getActive() change and new ActiveOntology.schemaHash are not in the CHANGELOG
- `ts-sdk#2` [major] fixed · review: resolved · final check: resolved: README tutorial links now point to raw .adoc source whose Antora includes don't resolve
- `ts-sdk#3` [minor] fixed · review: resolved: Edge-runtime sentence was left ungrammatical by a partial edit
- `x-consistency#8` [minor] partially_fixed · review: resolved: New text calls the Python SDK Experimental, but its package metadata says Beta
- `x-consistency#13` [nit] fixed · review: resolved: npm install commands are unpinned, against the pin rule MAINTAINING.md adds

### tut-hosted (wave 1, 2 review round(s))

- `docs-examples-py#1` [blocker] fixed · review: resolved · final check: resolved: Hosted first write uses a fixed display name as the conversation ID, contradicting the NAMS docs
- `tut-hosted-py#2` [minor] fixed · review: resolved: Step 3's first-write record is never recorded in the ledger or cleaned up
- `tut-hosted-py#1` [minor] fixed · review: resolved: inspect-file handoff summary omits the ontology's previous active version needed to restore the binding
- `tut-hosted-py#3` [minor] fixed · review: resolved: Page says Use NAMS documents context, graph expansion and Cypher, but it covers none of them
- `tut-hosted-py#5` [minor] fixed · review: resolved: After publish detects changed provenance, the page doesn't say to rerun inspect
- `tut-hosted-py#6` [nit] fixed · review: resolved: The nams_first_write.py listing has no '.Save as' title, contrary to MAINTAINING.md
- `gap2-gap2-expected-output-vs-progra#6` [nit] fixed · review: resolved: Skills download 'Expected' leaves out the attestation reminder printed before the listing

### tut-kg (wave 1, 1 review round(s))

- `gap1-bolt-programs-live#2` [blocker] fixed · review: resolved · final check: partially_resolved: Knowledge-graph tutorial ingest fails: documented install cannot load GLiREL, and working GLiREL finds no relations
- `tut-py#4` [minor] fixed · review: resolved: GLiREL xref lands on a legacy anchor on the index page, not on the explanation it promises

### tut-py (wave 1, 1 review round(s))

- `gap1-bolt-programs-live#1` [blocker] fixed · review: resolved · final check: resolved: Anthropic tutorial always stops at 'No entity candidates': extracted entities are stored without embeddings
- `docs-examples-py#2` [minor] fixed · review: resolved: Comment says 'seed' runs without the openai package, but seed makes OpenAI embedding calls

### tut-ts (wave 1, 2 review round(s))

- `tut-ts#0` [blocker] fixed · review: resolved · final check: resolved: MCP lesson's documented install makes `npm run build` fail with a type error (two zod copies)
- `tut-ts#4` [minor] fixed · review: resolved: Lessons send readers to the API reference for reasoning cleanup limits, but it doesn't cover them
- `tut-ts#5` [minor] fixed · review: resolved: Recall step says to expect output the program never prints (the retrieved memory)

### w2-cross (wave 2, 1 review round(s))

- `py-examples#1` [major] fixed · review: resolved · final check: resolved: make example-no-llm / example-eval-harness / examples now crash with KeyError on a clean checkout
- `tooling-ci#1` [major] fixed · review: resolved · final check: resolved: make docs-lint skips all rendered-layout checks after the documented setup; the skip hint names the wrong install
- `howto-core-b#0` [major] partially_fixed · review: resolved · final check: resolved: Newly published eval-harness docstring tells NAMS users to run the preference dimension, which is unsupported
- `integ-a#2` [major] fixed · review: resolved · final check: resolved: Vertex AI model table removed, but inbound 'model table' link still targets it (circular)
- `ref-config#1` [major] fixed · review: resolved · final check: resolved: audit_read row points to nonexistent `consolidation.audit_reads(...)`; the method is `record_read_audit`
- `py-examples#2` [minor] fixed · review: resolved: Makefile, CLAUDE.md and examples/.env.example still describe Docker auto-start; READMEs now say Aura
- `tut-py#1` [minor] partially_fixed · review: resolved: Docs say the Aura helper has 'no fallback database', but aura_config() defaults to 'neo4j'
- `ref-config#5` [minor] fixed · review: resolved: CLI `--profile` row says extended = 16 tools, but on NAMS the server registers 20
- `gap1-rendered-artifacts#0` [minor] partially_fixed · review: resolved: `createNamsProvider`'s breaks the code span and turns the whole next sentence into monospace
- `gap2-gap2-install-commands-sweep#8` [minor] fixed · review: resolved: TypeScript API reference installs @neo4j-labs/agent-memory without the required exact version

### w2-labels (wave 2, 2 review round(s))

- `howto-core-a#0` [major] fixed · review: resolved · final check: resolved: Reasoning page newly labeled bolt-only ("raises NotSupportedError"), but NAMS implements these calls
- `gap1-backend-support-labels#0` [major] handed_off · review: resolved · final check: resolved: Bolt-only label says every API raises NotSupportedError on NAMS; many labelled calls do not
- `ref-api-a#3` [minor] fixed · review: resolved: Says unsupported calls raise NotSupportedError; bolt-only long_term methods raise AttributeError on NAMS
- `ref-api-b#5` [minor] fixed · review: resolved: On NAMS, only get_tool_stats raises NotSupportedError; the other tool-stat methods raise AttributeError
- `gap1-backend-support-labels#2` [minor] fixed · review: resolved: Messages page newly labelled 'Available on NAMS: Yes' but its procedure and table fail on NAMS
- `gap1-backend-support-labels#5` [minor] fixed · review: resolved: include_long_term now says 'facts and preferences'; long-term context has entities, not facts
- `gap1-backend-support-labels#7` [minor] fixed · review: resolved: Preferences row says NAMS methods raise NotSupportedError; documented call forms raise TypeError
- `gap1-backend-support-labels#8` [minor] fixed · review: resolved: NOTE blames 'the hosted Python bridge' for dropping touched_entities; REST client drops it too

### w3-anchors-howto (wave 3, 1 review round(s))

- `integ-a#6` [minor] fixed · review: resolved: Integrations index drops eleven former section ids, against the preserve-anchors rule
- `gap1-compat-anchor-landing#3` [minor] fixed · review: resolved: _next_steps and _env_var_reference render in Prerequisites; the intended later anchors are dropped
- `gap1-compat-anchor-landing#4` [minor] declined · review: decline_ok: Old migration steps land on See also, Prerequisites and connection setup
- `gap1-compat-anchor-landing#5` [minor] fixed · review: resolved: Python page-level ids land on the TypeScript section, and TypeScript subsection ids land on Python steps
- `gap1-compat-anchor-landing#8` [minor] fixed · review: resolved: Old 'Step 2: seed...' id lands in Step 3 (wire the editors), off by one
- `gap1-compat-anchor-landing#10` [minor] fixed · review: resolved: Old section ids are stacked after See also although matching procedure steps exist
- `gap1-compat-anchor-landing#21` [minor] fixed · review: resolved: Bedrock troubleshooting and model-choice ids land in 'Run and verify'
- `x-content-loss#6` [minor] partially_fixed · review: resolved: About 60 section fragments from before the branch no longer resolve, contrary to 4052e1b's 'every section id was preserved' claim
- `howto-core-a#8` [nit] fixed · review: resolved: Redundant legacy anchors duplicate section auto-ids, so the sections render as _prerequisites_2 and _see_also_2
- `howto-ts#6` [nit] fixed · review: resolved: Restructure keeps four old section anchors but drops the four TypeScript ones (and nextjs `_compatibility`)
- `gap1-compat-anchor-landing#24` [nit] fixed · review: resolved: Persist and GLiREL ids open on the next section, not on their own content

### w3-anchors-ref (wave 3, 1 review round(s))

- `ref-config#3` [minor] fixed · review: resolved: Compatibility anchors for old Embedding/LLM sections forward to the wrong subpage bullets
- `x-style#1` [minor] fixed · review: resolved: Old GLiRELExtractor anchors _constructor_5/_example_5 now forward to the builder page
- `gap1-compat-anchor-landing#1` [minor] fixed · review: resolved: Old Schema Configuration ids land on Extraction configuration, not Graph schema configuration
- `gap1-compat-anchor-landing#9` [minor] fixed · review: resolved: get_context Example/Parameters ids land on See also and the Methods heading
- `gap1-compat-anchor-landing#22` [minor] fixed · review: resolved: 'Schema Best Practices' id lands on the Entity type mapping table
- `x-content-loss#6` [minor] partially_fixed · review: resolved: About 60 section fragments from before the branch no longer resolve, contrary to 4052e1b's 'every section id was preserved' claim

### w3-anchors-rest (wave 3, 1 review round(s))

- `entry#0` [minor] fixed · review: resolved: Retained 'Demos' anchors on index use wrong ids; the real former ids are still lost
- `x-content-loss#6` [minor] fixed · review: resolved: About 60 section fragments from before the branch no longer resolve, contrary to 4052e1b's 'every section id was preserved' claim
- `gap1-compat-anchor-landing#6` [minor] fixed · review: resolved: '2. Install the SDK' and Bolt 'Prerequisites' ids land on the See also list
- `gap1-compat-anchor-landing#20` [minor] fixed · review: resolved: TS tutorial ids meant for Next steps sit above the cleanup-result partial
- `entry#1` [nit] fixed · review: resolved: Former 'Next steps' / 'Where to go next' section ids dropped on getting-started and both SDK pages
- `gap1-compat-anchor-landing#26` [nit] fixed · review: resolved: Stacked [#id] block lines: only the last survives; earlier ones are dead, duplicated ids

