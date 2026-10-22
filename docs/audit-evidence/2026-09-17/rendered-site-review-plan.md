# Rendered site review: findings and improvement plan

**Date:** 2026-09-17
**Branch reviewed:** `docs-review` at the state committed as `d3db0ff` (the served build was made from that working tree just before the commit; the later merge from `main` at `73ef201` changed no docs)
**Status:** plan only. No file under `docs/modules/ROOT/` was changed for this review.

## How the review was done

The Claude in Chrome extension was not connected, so the site was rendered headlessly with Playwright's Chromium against the local static server (`http://localhost:8080/agent-memory/`). Every one of the 115 published pages was captured at 1280px (full page) and 390px (first viewport, plus the viewport around the first image), every content image was cropped at its rendered size (27 crops on 24 pages), and the 24 diagram pages were rendered again with the browser set to prefer a dark colour scheme. A script also recorded per-page facts: image natural and rendered size, alt text and captions, horizontal overflow, table widths, code-block overflow, heading text, admonition and word counts, console and HTTP errors, breadcrumbs and sidebar state. Four Sonnet reviewers read the screenshots by quadrant (entry, tutorials and explanation; how-to; reference; diagrams and dark mode), and the orchestrator spot-checked the strongest claims against the served HTML and the `docs-review` source. Artifacts: `scratchpad/render/report.json`, `scratchpad/render/shots/`, `scratchpad/render/render.mjs` (session scratchpad, not in the repository).

Caveat on two reviewer remarks that are discounted below: the checkout had been switched to `gliner-2.5` while the reviewers ran, so their comments about "two Excalidraw source trees" and stray `.bak` or `poleo-model2.png` files describe that branch's old layout. `docs-review` already consolidated scenes under `docs/assets/diagrams/excalidraw/` and deleted those files.

## Verdict

The site is mechanically healthy. Across 115 pages there are no broken images, no console or HTTP errors, no horizontal scroll at desktop width, no upscaled images, alt text on every image, correct breadcrumbs and sidebar highlighting everywhere, and the four entry pages carry the Labs disclaimer after the intro rather than as the first thing on the page. Mobile rendering is clean except for wide tables on four reference pages.

The problems are editorial and visual rather than structural, and most are cheap: one diagram that is unreadable, a leftover migration section published on ten reference pages, a duplicated table of contents on every TypeScript how-to, a raw identifier used as a page title, inconsistent headings and closing sections across the how-to family, and a diagram estate that mixes three visual styles and captions 5 images out of 27.

## What renders well and should be kept

- The landing page: a one-screen "Choose your starting path" table, a code sample, a captioned diagram, and the disclaimer in second position.
- Tutorial pages share one skeleton (intro, prerequisites, numbered steps mirrored in the right rail, verification, cleanup table, next steps) and every step ends with visible output.
- The Python integration how-tos share a tight skeleton with matching backend-scope admonitions that let a reader triage applicability at a glance.
- The schema diagrams that embed real names (`message-chain.svg`, `entity-dedup-flow.svg`, `reasoning-trace-graph.svg`, `mcp-server-architecture.png`) are accurate against the source and legible at both widths.
- The MCP tools page's diagram matches the page's tool counts exactly, and the deployment split reads as two distinct, correctly named pages.
- Long code listings collapse behind "View all" controls, so even the densest pages do not blow out the layout.

## Findings

Severity: **high** means a reader is misled or cannot use the page as intended; **medium** means it visibly degrades trust or navigation; **low** is polish.

### A. Diagrams

| # | Severity | Page(s) | What the render shows | Fix |
|---|---|---|---|---|
| A1 | high | `tutorials/index` | `tutorial-routes.svg` is authored 4,536px wide and lands at 648×197, a 0.14 scale; labels render around 3px and are unreadable at both widths. This is the visual meant to help a first-time visitor pick a route. | Redraw as three stacked single-lane diagrams (one per route) or one vertical diagram, canvas no wider than about 1,400px, or replace with the route table the page already has. |
| A2 | high | `how-to/audit-reasoning` | Both diagrams are the same generic four-box prose flow used on other pages; neither draws a `:TOUCHED` edge, `HAS_STEP` or `INITIATED_BY`, which is the page's subject. | Replace both with one graph fragment `(:ReasoningTrace)-[:HAS_STEP]->(:ReasoningStep)-[:TOUCHED]->(:Entity)` in the style of `reasoning-trace-graph.svg`. |
| A3 | medium | `explanation/backends`, `explanation/multi-agent-sharing` | Canvases about three times the column width; effective label size 7.5 to 8.5px on desktop, lanes about 170px wide on a phone. Legible on desktop, borderline on mobile. | Recompose for the 648px column: larger fonts, fewer words per box, stack the lanes vertically or make the lanes the mobile breakpoint. |
| A4 | medium | corpus | Three visual languages coexist: hand-drawn (`poleo-model.png`, `memory-architecture.png`), clean flowchart (the majority), and a dashed-lane style (`backends`, `multi-agent-sharing`, `aws-strands` figure 1). `explanation/graph-architecture` and `explanation/memory-types` draw the same three-layer concept in two styles on adjacent pages. | Choose the clean flowchart style as the house style, record it in `MAINTAINING.md`, and re-export the hand-drawn and dashed-lane scenes to match. |
| A5 | medium | corpus | Captions: 5 of 27 images have an AsciiDoc figure caption; the rest rely on alt text and titles baked into the artwork, which are not selectable, indexed or announced as captions. | Adopt `.Figure` captions on every diagram (a `.Title` line before `image::`), numbered per page, and put the in-image title on the caption instead. |
| A6 | medium | `how-to/integrations/aws-strands` | Figure 1 shows a KYC, AML, relationship and compliance agent architecture unrelated to the page's session-manager and memory-store content; the body has to disclaim that the integration does not create those agents. | Replace with a diagram of what the page actually wires (`NeoSessionManager`, `NeoMemoryStore`, Bedrock embeddings, Neo4j), or move figure 1 to the financial-advisor example's README. |
| A7 | low | 13 pages | 13 diagrams are still PNG while SVG exports of the same scenes exist and are tracked in the manifest. | Switch the `image::` macros to the SVG exports and drop the PNGs from the manifest. |
| A8 | low | `explanation/extraction-pipeline`, `how-to/entity-extraction` | The same diagram is embedded as a PNG on one page and a differently styled SVG on the other, with different alt text. | Reference one export from both pages. |
| A9 | low | `how-to/multi-tenancy`, `how-to/preferences` | The `:User` node is purple on one diagram and green on the other; both colours already mean something else in the palette. | Pick one colour for `:User` (a neutral grey is safest) and record it in the palette rule. |
| A10 | low | `explanation/context-tiers` | The newest explanation page describes a three-stage compression model with no diagram, the only concept page without one. | Add a simple funnel diagram: recent messages, observations, reflections. |
| A11 | low | `how-to/integrations/microsoft-agent` | The TfL Explorer app screenshot is shrunk to 540px, so its UI text is illegible. | Keep it but caption it as a screenshot and rely on the existing click-to-open behaviour, or crop to the relevant panel. |
| A12 | low | corpus | Every image already opens full size on click (`link=self`), but nothing tells the reader. Widths are set three ways (`100%`, `540`, `600`). | Standardise on `width=100%` for diagrams designed for the column and add "Click to open full size" to captions of the few wide ones. |
| A13 | info | corpus | The UI ignores the browser's dark-scheme preference, so the opaque white backgrounds baked into every export are invisible today. If the UI ever gains a dark theme, all 27 exports need re-exporting with a dark-safe background. | Note in `MAINTAINING.md`; no change now. |

### B. Published scaffolding and titles

| # | Severity | Page(s) | What the render shows | Fix |
|---|---|---|---|---|
| B1 | high | 10 reference pages (`reference/api/factory`, `llm-provider`, `long-term`, `memory-client`, `reasoning`, `short-term`; `reference/configuration`, `environment-variables`, `extractors`, `schemas`) | Each ends with a real H2 "Earlier section links" that appears in the right rail, followed by anchor clusters and the boilerplate sentence "The earlier sections have been consolidated into the current contracts." It reads as an editorial note that got published. | Remove the heading and sentence. Keep the old ids by placing each `anchor:` immediately before the section that now covers it, or use Antora page aliases for whole-page moves. Add a check to `check_docs.py` that fails on a heading containing "Earlier section". |
| B2 | high | `reference/api/factory` and every surface that names it | The page title is `from_provider factory reference`: the raw identifier appears unformatted in the tab title, breadcrumb, sidebar, pagination and Open Graph metadata. | Retitle to "Provider factory reference" and name `from_provider` in code font in the first sentence. Update nav and index text so `tests/docs/test_nav_labels.py` stays green. |
| B3 | high | 11 pages under `how-to/typescript/` plus one other page that sets `:toc:` | The pages declare `:toc:` or `:toc: left`, so Asciidoctor emits an inline "Table of Contents" that duplicates the right-rail Contents panel. No Python page does this. | Delete the `:toc:` and `:toc: left` attributes; keep `:toclevels:`. |

### C. Headings, labels and link text

| # | Severity | Page(s) | What the render shows | Fix |
|---|---|---|---|---|
| C1 | medium | `how-to/integrations/index` | Seven Title Case headings ("Available Integrations", "Choosing a Framework", "Common Patterns", "Three-Layer Memory", "Semantic Search", "Entity Extraction", "Integration Guides") under a sentence-case H1. | Sentence-case all seven; add `anchor:` ids if any are linked. |
| C2 | medium | `how-to/audit-reasoning`, `buffered-writes`, `consolidation`, `evaluation`, `privacy-and-audit` | Closing heading is "See Also" in Title Case. | Rename to "See also" (see E1). |
| C3 | medium | `sdks/typescript` (4), `how-to/typescript/integrations-overview` (3), `edge-runtime`, `vercel-ai`, `reference/typescript-api` | Ten link labels still carry a "How-to:" prefix that the page titles no longer have, and one says "use LangChain JS" where the title says "Integrate with LangChain JS". | Replace the labels with the page titles or a lowercase mid-sentence phrase. |
| C4 | low | `how-to/typescript/strands`, `how-to/bring-your-own-model`, `faq` | "Quick Start", "B. Explicit Provider instance", "What are NAMS Agent Skills? (Preview)". | Sentence-case ("Quick start", "Explicit provider instance"); "Agent Skills" is a product name and stays. |
| C5 | low | `how-to/integrations/index` | The same target gets three labels: the table says "Google Cloud", the guide list says "Google Cloud Integration", the page is "Use Vertex AI embeddings with Neo4j"; likewise for Strands. | One label per target, reused in the table, the list and the sidebar. |
| C6 | low | `how-to/typescript/mcp` | Sidebar label "MCP Tools" differs from the H1 "Use the MCP tools" and is the only allowlisted mismatch. | Now that the Python page is labelled "Self-hosted Python MCP reference", rename the sidebar entry to "Use the MCP tools" and remove the allowlist entry. |

### D. Reference tables and page length

| # | Severity | Page(s) | What the render shows | Fix |
|---|---|---|---|---|
| D1 | high | `reference/deploy-an-application` | The options table puts 60 to 100 word paragraphs with inline code into every cell of a five-column grid; it overflows on a phone (572px in a 356px column). | Convert to one definition block per deployment option: a heading plus a short fact list, the pattern `backend-capabilities` uses for prose comparisons. |
| D2 | high | `reference/backend-capabilities` | The page's central eight-column matrix overflows on a phone with no scroll affordance; the reference index tells readers to start here. | Split into one table per data type with at most four columns, or transpose so backends are rows, and give the wrapper horizontal scroll with a visible hint. |
| D3 | medium | `reference/schema-objects` | The Name column is too narrow, so identifiers wrap mid-word (`conversatio` / `n_id`, `reasoning_t` / `race_id`) in all four tables. | Set explicit `cols` widths favouring the Name column, or merge Label and Property, so every identifier fits on one line. |
| D4 | medium | `reference/rest-api` | Four seven-column endpoint tables with per-language method names (including Go and C#, which this repository does not ship) overflow on a phone. | Split per language or move the per-language accessor columns into a collapsible block; add a one-line note that Go and C# clients live outside this repository. |
| D5 | medium | `reference/api/long-term` (28,311px), `reference/extractors` (28,279px), `reference/configuration` (21,899px), `reference/api/reasoning` (19,617px), `reference/api/short-term` (15,798px), `reference/schemas` (15,491px), `reference/typescript-api` (14,482px), `faq` (12,877px) | Twenty to thirty screens of scroll each. The right rail helps, but the rail for the longest pages is itself a wall. | Split by cohesive subsystem (for example deduplication, provenance and geospatial out of `long-term`; builder and streaming out of `extractors`; per-settings-class pages out of `configuration`), keeping old anchors via aliases. Add a short jump list under each remaining page's intro. Group the FAQ under six or seven headings. |
| D6 | low | `reference/api/*` | Seven sibling pages do not share one template: four open with an "Overview" H2, three do not; `adapters` closes with "Related" while the others use "See also". | One template: intro, Overview, sections in a fixed order, "See also" last. |
| D7 | low | `reference/index` | The 17-item "Configuration, service and SDK contracts" list is in neither alphabetical nor sidebar order. | Regroup under three subheadings (configuration and CLI, hosted service, extraction and schema) in sidebar order. |
| D8 | low | `reference/environment-variables` | Only three real variable tables; eleven subsections are prose pointing at the configuration page, which undercuts the page's own purpose. | Either restore a compact variable table per subsection or retitle the page as an environment-variable guide and say so in the intro. |

### E. How-to family consistency

| # | Severity | Page(s) | What the render shows | Fix |
|---|---|---|---|---|
| E1 | medium | corpus | Closing cross-reference sections use six headings: "See also" (36), "Next steps" (7), "Related tasks" (6), "Related" (6), "Related documentation" (4), "Where to go next" (2); about 30 how-tos have none. On `how-to/typescript/nextjs-memory-chat` the block is not the last section. | Standardise: how-to and reference pages end with "See also"; tutorials end with "Next steps". Move the Next.js block last. Add a `check_docs.py` rule for the allowed closing headings. |
| E2 | medium | `how-to/entities`, `messages`, `preferences`, `reasoning-traces`, `deduplication`, `create-context-graph-mcp` | No backend-scope partial, while the rest of the family opens with one under the intro. | Include the matching `backend-*.adoc` partial in the same position. |
| E3 | medium | `how-to/deduplication` | No goal or prerequisites section; opens with tutorial scaffolding (`mkdir`, venv, "Save as" listings, collapsible helpers) and has no closing section. | Rewrite to the how-to contract: goal, prerequisites pointing at the tutorial setup partial, the three numbered steps, verification, "See also". Move the environment scaffolding behind the shared partial. |
| E4 | medium | `how-to/index` | "Memory and deployment tasks" flattens 22 bare titles into one list while the sidebar groups them into six categories. | Mirror the six sidebar groups with a one-line description per page. |
| E5 | low | `explanation/index` | 84 words: a bare list with no guidance on which concept page to read first. | One line per page plus a suggested reading order for newcomers. |
| E6 | low | `configuration` (legacy stub) | The sidebar shows no active entry because the page is not in nav; expected for a forwarding page, but disorienting. | Accept as is, or add a one-line "You followed an old link" note above the redirect text. |

### F. Tooling

| # | Severity | Scope | Gap | Fix |
|---|---|---|---|---|
| F1 | medium | `scripts/check_docs.py`, CI | Nothing checks the rendered site for the defect classes found here: inline TOC duplication, images rendered below 0.45 of natural width, mobile horizontal overflow, Title Case headings, leftover scaffolding headings. | Promote the session's `render.mjs` into `scripts/render_docs.mjs` (Playwright is already a dependency under `docs/diagrams/`), have it write `report.json`, and add a pytest in `tests/docs/` that asserts those thresholds against a fresh build. Run it in `make docs-lint`. |

## Plan

Work happens on `docs-review`. Each phase is one pull request; tasks list the owning files so they can be parallelised the same way as the previous implementation run.

### Phase A. Quick wins (one PR, all S effort)

Status: 7 of 8 tasks done (A1-A5, A7, A8); A6 failed (harness StructuredOutput error on every attempt, no changes made, needs a human/rerun) — see docs/audit-evidence/2026-09-17/implementation-report-rendered.md sections 2 and 3.

| ID | Task | Files | Acceptance |
|---|---|---|---|
| A-1 | Remove inline TOC attributes | 11 `how-to/typescript/*.adoc`, plus the one other page with `:toc:` | No article contains an element with `id="toc"` in the fresh build |
| A-2 | Sentence-case headings | `how-to/integrations/index.adoc` (7), the five "See Also" pages, `how-to/typescript/strands.adoc`, `how-to/bring-your-own-model.adoc` | The heading-case check in the render report returns zero non-proper-noun hits |
| A-3 | Replace "How-to:" link labels | `sdks/typescript.adoc`, `how-to/typescript/integrations-overview.adoc`, `edge-runtime.adoc`, `vercel-ai.adoc`, `reference/typescript-api.adoc` | `git grep 'How-to:' docs/modules/ROOT/pages` is empty |
| A-4 | Retitle the factory reference | `reference/api/factory.adoc`, `nav.adoc`, `reference/index.adoc` | Title, breadcrumb and sidebar read "Provider factory reference"; `test_nav_labels.py` passes |
| A-5 | Standardise closing sections | every page with a closing block; `nextjs-memory-chat.adoc` | Only "See also" (how-to, reference) and "Next steps" (tutorials) remain, always last |
| A-6 | Add backend-scope partials | the six core how-tos in E2 | Every how-to opens with a scope partial |
| A-7 | Index descriptions | `how-to/index.adoc`, `explanation/index.adoc` | Each index groups pages as the sidebar does, one line per page |
| A-8 | One label per integration target | `how-to/integrations/index.adoc`; `nav.adoc` and the allowlist for the MCP how-to | Table, list and sidebar agree; the allowlist entry is gone |

### Phase B. Published scaffolding and reference tables (one PR, M effort)

Status: all 8 tasks done, with one objection (B-8's "Configuration and CLI" ordering diverges from `nav.adoc` for `deployment`/`deploy-an-application`) — see docs/audit-evidence/2026-09-17/implementation-report-rendered.md sections 2 and 3.

| ID | Task | Files | Acceptance |
|---|---|---|---|
| B-1 | Remove "Earlier section links" sections | the ten reference pages; `scripts/check_docs.py` | No page has the heading; every old anchor id still resolves (compare against the 2026-09-13 anchor inventory); the new check fails on regressions |
| B-2 | Deploy-an-application options as definition blocks | `reference/deploy-an-application.adoc` | No table wider than the phone column; content unchanged |
| B-3 | Backend capability matrix mobile-safe | `reference/backend-capabilities.adoc` | No horizontal overflow at 390px; every cell's fact preserved |
| B-4 | Schema-objects column widths | `reference/schema-objects.adoc` | No identifier wraps mid-word at 1280px |
| B-5 | REST endpoint tables | `reference/rest-api.adoc` | No overflow at 390px; a note explains the Go and C# columns |
| B-6 | Rewrite the deduplication how-to to the contract | `how-to/deduplication.adoc`, shared setup partial | Goal, prerequisites, steps, verification, "See also"; snippet tests pass |
| B-7 | API page template | `reference/api/*.adoc` | Seven pages share section order; `adapters` ends with "See also" |
| B-8 | Reference index grouping | `reference/index.adoc` | Three topical subgroups in sidebar order |

### Phase C. Diagrams (one PR, M to L effort)

Status: all 9 tasks plus the manifest reconcile (CM) done, with objections: C-5 left two different three-layer diagrams unmerged, C-7 left 2 of 13 PNGs on disk (README.md-blocked), and the area review flagged 3 remaining font-family house-style violations plus a content mismatch in the redrawn tutorial-routes diagram and an unwired extraction-pipeline scene — see docs/audit-evidence/2026-09-17/implementation-report-rendered.md sections 2 and 3.

| ID | Task | Files | Acceptance |
|---|---|---|---|
| C-1 | Redraw the tutorial routes | `docs/assets/diagrams/excalidraw/tutorial-routes.excalidraw`, export, manifest, `tutorials/index.adoc` | Smallest label at least 10px when rendered in the 648px column; legible at 390px |
| C-2 | Replace the audit-reasoning diagrams | new scene, exports, manifest, `how-to/audit-reasoning.adoc` | One diagram showing `HAS_STEP` and `TOUCHED` with real labels; the redundant second image removed |
| C-3 | Recompose backends and multi-agent diagrams | the two scenes, exports, manifest | Smallest label at least 9px in the column; lanes readable at 390px |
| C-4 | Replace the Strands figure 1 | scene, export, manifest, `how-to/integrations/aws-strands.adoc` | The diagram shows the components the page wires; the disclaimer sentence becomes unnecessary |
| C-5 | Unify the house style | `poleo-model`, `memory-architecture` scenes and the dashed-lane scenes; `MAINTAINING.md` | All diagrams share one style; `graph-architecture` and `memory-types` use one three-layer diagram |
| C-6 | Captions everywhere | every `image::` in pages | Every diagram has a `.Figure N.` caption; in-image titles removed or matched |
| C-7 | PNG to SVG swap | the 13 pages in A7; manifest | Only SVG exports referenced; PNG outputs removed from the manifest and disk for 11 of the 13 diagrams. `mcp-server-architecture.png` and `the-three-layer-memory-architecture.png` stay on disk and in the manifest because `README.md` (outside this task's files) still hard-references them by filename; repointing `README.md` and deleting those two PNGs is a follow-up task that owns `README.md`. |
| C-8 | Small fixes | `:User` colour (A9), extraction-pipeline duplicate (A8), context-tiers funnel (A10), TfL screenshot caption (A11), width convention (A12) | As described |
| C-9 | Record the rules | `docs/MAINTAINING.md` | Canvas width cap, minimum effective font size, caption convention, palette entry for `:User`, dark-theme note |

### Phase D. Structure (one PR per split, L effort)

Status: all 4 tasks done, with objections: D-1 split only its four named pages (four other reference pages still exceed the height guidance and need a follow-up split task) and D-4 added a working rendered-site check but did not wire it into CI or `docs-lint` — see docs/audit-evidence/2026-09-17/implementation-report-rendered.md sections 2 and 3.

| ID | Task | Files | Acceptance |
|---|---|---|---|
| D-1 | Split the longest reference pages | `reference/api/long-term.adoc`, `reference/extractors.adoc`, `reference/configuration.adoc`, `reference/api/reasoning.adoc`; `nav.adoc`; index; aliases | No reference page taller than about 12,000px at 1280px among D-1's four owned pages (confirmed: `long-term.adoc` 2,374px, `extractors.adoc` 4,677px, `configuration.adoc` 4,347px, `reasoning.adoc` 2,325px); every old anchor resolves through an alias. `reference/api/short-term.adoc`, `reference/schemas.adoc`, `reference/typescript-api.adoc` and `reference/mcp-tools.adoc` also exceed the threshold but are out of scope for D-1 and need their own split task. |
| D-2 | Group the FAQ | `faq.adoc` | Six or seven headings; each question reachable from the right rail |
| D-3 | Environment-variables page purpose | `reference/environment-variables.adoc` | Either tables per subsection or an explicit guide framing |
| D-4 | Rendered-site check in CI | `scripts/render_docs.mjs`, `tests/docs/test_rendered_site.py`, `Makefile`, `.github/workflows/ci-python.yml` | `make docs-lint` fails on inline TOC, downscale below 0.45, mobile overflow, Title Case headings and scaffolding headings (done: `docs-lint` now depends on `docs-render-check`). Wiring the same check into `.github/workflows/ci-python.yml` is a separate follow-up owned by whoever can edit CI workflow files. |

## Verification for every phase

1. `python3 scripts/check_docs.py --build --report <path>` renders with zero errors.
2. `uv run --no-sync pytest tests/docs -q --ignore=tests/docs/test_tutorial_examples.py --ignore=tests/docs/test_howto_examples.py` passes.
3. Re-run the render script and confirm the counts move: inline TOC pages 12 to 0, downscaled images 5 to 0, mobile-overflow pages 4 to 0, uncaptioned images 22 to 0, Title Case headings to 0, "Earlier section" headings 10 to 0.
4. Open the affected pages at 1280px and 390px and look at each changed diagram at full size.
