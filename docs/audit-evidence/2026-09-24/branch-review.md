# Branch review: docs-review (2026-09-24)

Branch `docs-review` at `e2bcb93`, compared with main at merge-base `ec9fc65` (main as of 2026-09-22). The branch has 19 commits touching 685 files (+68,516 / −33,324), mostly documentation.

## Verdict

The branch is not ready to merge. It breaks CI in two places: ruff format --check fails on three new docs test modules, and the TypeScript type-check-examples leg for nextjs-memory-chat never builds the nams-ai-provider package it now depends on. Beyond CI, at least six published docs programs fail when a reader runs them live: the core_memory_recipes messages order, the NAMS first write, the cloud embeddings recipe, the Anthropic tutorial, the knowledge-graph GLiREL install and the TypeScript MCP lesson build. The mocked docs tests are built so they cannot catch these failures. There is also a cluster of major accuracy problems. Some API names and behaviour don't match 0.6.0 (ttl_days, record_read_audit, get_facts_about, the multi_tenant semantics, the GLiREL default model). Content was lost with no new home. Twenty-nine READMEs link to a nonexistent DOCUMENTATION_REMEDIATION_STATUS.md. And one guide tells readers to put literal secrets in a committed .mcp.json. Fix the must-fix list and add at least one live smoke run of the Bolt docs programs before merging. The many minor anchor-landing and rendering issues can follow in a sweep.

**Unique confirmed findings:** 276 after merging duplicates (365 raw): 8 blockers, 41 majors, 174 minors, 53 nits. **Must fix before merge:** 49. Reviewers refuted 13 of their own reports; 3 stayed uncertain (listed in the appendix).

## How the review ran

A workflow of 161 agents ran in several stages:

- **Executors.** Four agents ran the real checks: `make check`, the unit tests, `tests/examples`, and `tests/docs`; the Neo4j integration and docs tests on testcontainers; `make docs` plus the checkers, the rendered-site tests and an independent link and image check of the built site; and the TypeScript SDK, the provider package, all ten examples, and a TypeDoc regeneration diffed against the committed output.
- **Area reviewers.** 32 reviewers covered the diff by area: code, examples, CI and tooling, docs tests, each docs quadrant, and cross-cutting sweeps for content loss and anchors, diagrams, security, consistency, and style.
- **Verification.** A skeptic re-checked each area's findings. Every surviving blocker or major then got a second, independent check that had to reproduce it by running code.
- **Gap rounds.** Two completeness-critic rounds added nine gap reviewers: anchor landing, rendered artifacts, backend labels, live runs of the Bolt docs programs, inline TypeScript type-checks, a sweep of Python API bindings, expected output, install commands, and Markdown links.
- **Synthesis.** A final agent merged duplicates and ranked the findings.

I spot-checked every blocker by hand: I re-ran ruff, reproduced the embedder `TypeError`, read the CI matrix and the batch-insert Cypher, and read each reproduction transcript.

Side effect: the TypeScript executor's `npm install` changed one line of `typescript/examples/nams-ai-provider/package-lock.json`. I restored it with `git restore`. There is also an untracked, gitignored leftover, `examples/ontology-extraction/__pycache__`, from an older checkout. It makes four `tests/examples/test_examples_registry.py` cases fail locally; it is not part of the branch.

## Themes

- The published docs programs do not run as written against a real backend: order assertions on tied timestamps, a made-up NAMS conversation ID, a legacy embedder that MemorySettings rejects, entities stored without embeddings, an uninstallable GLiREL stack, a zod version clash and an undocumented LangChain tool (docs-examples-py#0, docs-examples-py#1, integ-a#0, gap1-bolt-programs-live#1, gap1-bolt-programs-live#2, tut-ts#0, integ-b#0).
- The tests that should protect those programs cannot fail: they are mocked or pointed at old page code, they install from the wrong node_modules, they check canned mock text or they make vacuous all() checks, so CI passes while live runs fail (gap1-bolt-programs-live#3, gap1-bolt-programs-live#4, gap1-bolt-programs-live#5, tut-ts#2, ts-ex-a#1, docs-tests-a#0, docs-tests-b#8, docs-tests-b#6, py-lib#0).
- CI and tooling do not do what they claim: ruff format fails on three new test files, the nextjs example's new provider dependency is never built in CI or in the README recipe, test_nav_labels.py is never run, the rendered checks skip because 'make docs-install' does not install Playwright, and the diagram exporter writes PNGs that the orphan check then rejects (ex-python#0, ts-ex-b#0, ts-ex-b#2, tooling-ci#4, tooling-ci#1, tooling-ci#2, ex-python#1).
- Rewrites cut content that now appears on no other page, and some pages that remain point readers to places that do not have it: the Vertex model table, the Strands, Microsoft, LangChain and PydanticAI adapter APIs, the POLE+O subtype lists, the Neo4j version floor, the extras table and the NAMS telemetry (integ-a#2, integ-a#3, integ-b#2, explanation#1, explanation#2, x-content-loss#3, x-content-loss#4, x-content-loss#5, x-content-loss#7, howto-core-b#5).
- Several API and behaviour claims disagree with the 0.6.0 / 0.5.0 source, often copied from stale docstrings: wrong argument and method names, wrong defaults, wrong env var names and inverted multi-tenant semantics (ref-config#0, ref-config#1, ref-config#2, ref-api-a#0, ref-api-b#0, ref-extract-schema#0, ref-other#0, explanation#0, explanation#4, integ-b#1, provider#0, ts-ex-b#3, howto-ts#0).
- Backend-availability banners and NotSupportedError statements are too blunt. Pages whose calls work on NAMS are labelled bolt-only, a page that fails on NAMS is labelled 'both', and the 'raises NotSupportedError' wording ignores the AttributeError and TypeError paths (gap1-backend-support-labels#0, howto-core-a#0, gap1-backend-support-labels#2, ref-api-b#4, ref-api-a#3, ref-api-b#5, gap1-backend-support-labels#7).
- Audit and process artifacts leaked into user-facing text: about 29 READMEs link to a nonexistent DOCUMENTATION_REMEDIATION_STATUS.md, and 'this source review' / 'another worker' wording, a wrong provider version and repo-checkout hedging appear throughout (py-examples#0, py-examples#5, gap2-gap2-install-commands-sweep#2, ts-ex-a#5, deploy#7, explanation#7, howto-core-b#8, x-style#8).
- Page restructuring kept anchors but put many of them in the wrong place: about 60 old fragments no longer resolve, and many kept ids land after 'See also' or on unrelated sections. Separately, the rewritten team-memory guide tells readers to put literal Aura and OpenAI secrets in a committed .mcp.json (x-content-loss#6, gap1-compat-anchor-landing#0, gap1-compat-anchor-landing#10, entry#0, howto-hosted#6, howto-hosted#0, x-security#2).

## Blockers (8)

### ex-python#0 — ruff format --check fails on 3 branch-touched test files, breaking CI's format-check step
**blocker** · lint · `tests/docs/test_rendered_site.py:21` · **must fix**

`make format-check` (== `uv run ruff format --check src tests examples docs/modules/ROOT/examples`, the exact command ci-python.yml's 'Run ruff format check' step runs) reports 'Would reformat' for three files this branch added/modified: tests/docs/test_docs_checker.py, tests/docs/test_nav_labels.py, and tests/docs/test_rendered_site.py. All three were committed un-formatted (long lines that ruff format wraps, e.g. multi-argument function signatures and long assert messages left on one line). This will fail the ci-python.yml format-check job on this branch's PR.

**Evidence.** Command: `make format-check` → 'Would reformat: tests/docs/test_docs_checker.py' / 'Would reformat: tests/docs/test_nav_labels.py' / 'Would reformat: tests/docs/test_rendered_site.py' / '3 files would be reformatted, 562 files already formatted' / 'make: *** [format-check] Error 1'. Confirmed all three are branch-touched via `git log --oneline ec9fc65..HEAD -- tests/docs/test_docs_checker.py tests/docs/test_nav_labels.py tests/docs/test_rendered_site.py` (non-empty). CI step: .github/workflows/ci-python.yml:80 `run: uv run ruff format --check src tests examples docs/modules/ROOT/examples`.

**Fix.** Run `uv run ruff format tests/docs/test_docs_checker.py tests/docs/test_nav_labels.py tests/docs/test_rendered_site.py` and commit the reformatted files.

**Independent reproduction.** From the repo root:
1. `uv run ruff --version` printed `ruff 0.14.14`. uv.lock pins `name = "ruff" version = "0.14.14"`.
2. `uv run ruff format --check src tests examples docs/modules/ROOT/examples` printed 'Would reformat: tests/docs/test_docs_checker.py', 'Would reformat: tests/docs/test_nav_labels.py', 'Would reformat: tests/docs/test_rendered_site.py' and '3 files would be reformatted, 562 files already formatted', then exited with EXIT=1.
3. `git cat-file -e ec9fc65:tests/docs/<f>.py` failed for all three files, so they are absent on main and new on this branch.
4. `uv run ruff format --diff tests/docs/test_rendered_site.py` shows that PRODUCT_ALLOWLIST at line 23 would be reflowed from packed multi-item lines to one item per line. That is a real formatting difference, not a trivial one.
5. `git status --short tests/docs` shows no uncommitted changes, so what I checked is the committed HEAD content.
6. In .github/workflows/ci-python.yml, `tests/**` appears in both the push and pull_request `paths` filters. The lint job has no `if:` condition, and line 80 is `run: uv run ruff format --check src tests examples docs/modules/ROOT/examples`.

**Orchestrator spot-check.** Re-ran `uv run ruff format --check tests/docs`: 3 files would be reformatted (test_docs_checker.py, test_nav_labels.py, test_rendered_site.py). CI runs this command at ci-python.yml:80.

Also reported as: docs-tests-b#0 (`tests/docs/test_nav_labels.py:130`)

### ts-ex-b#0 — CI builds vercel-ai-provider only for nams-ai-provider, but nextjs-memory-chat now depends on it too
**blocker** · ci · `.github/workflows/ci-typescript.yml:128` · **must fix**

This branch adds `@neo4j-labs/nams-ai-provider: file:../../packages/vercel-ai-provider` to nextjs-memory-chat and imports `createNamsProvider` from it in lib/handlers.ts. The provider's dist/ is gitignored and nothing builds it on a fresh checkout. The step that runs `npm ci && npm run build` in typescript/packages/vercel-ai-provider only runs when `matrix.example == 'nams-ai-provider'`. In the `Example (nextjs-memory-chat, Node 24)` leg, the package therefore has no dist/index.d.ts, no dist/index.js and no node_modules. `tsc --noEmit` then cannot resolve the module, and `npm test` and `npm run build` fail. `make ts-test-examples` (Makefile:835-848) also never builds the provider, so the local mirror fails the same way.

**Evidence.** .github/workflows/ci-typescript.yml:127-128: `- name: 'Build vercel-ai-provider package (populates dist for nams-ai-provider example)'` / `if: matrix.example == 'nams-ai-provider'`. The matrix at :95 includes `- nextjs-memory-chat`. typescript/examples/nextjs-memory-chat/package.json:24: `"@neo4j-labs/nams-ai-provider": "file:../../packages/vercel-ai-provider"`. typescript/examples/nextjs-memory-chat/lib/handlers.ts:12: `import { createNamsProvider } from "@neo4j-labs/nams-ai-provider";`. typescript/packages/vercel-ai-provider/.gitignore:5 `dist/`, and `git ls-files typescript/packages/vercel-ai-provider/dist` returns nothing. The provider package.json has `"types": "./dist/index.d.ts"`. Makefile:836 builds only `$(TS_DIR)`.

**Fix.** Change the condition to `if: matrix.example == 'nams-ai-provider' || matrix.example == 'nextjs-memory-chat'`, or derive it from whether the example's package.json references packages/vercel-ai-provider. Add the same provider build to `make ts-test-examples`.

**Independent reproduction.** S=<scratchpad>/review/ciproof; git archive HEAD typescript | tar -x -C $S
ls $S/typescript/packages/vercel-ai-provider  -> no dist/, no node_modules
cd $S/typescript && npm ci && npm run build  -> sdk-build-exit=0
cd examples/nextjs-memory-chat && npm ci  -> EUSAGE lockfile out of sync (Invalid: @emnapi/wasi-threads@1.2.1; Node 25/npm 11.6.2 locally), so I used npm install instead
ls -la node_modules/@neo4j-labs/  -> nams-ai-provider -> ../../../../packages/vercel-ai-provider (no dist)
npx tsc --noEmit  -> exit 2:
  lib/handlers.ts(12,36): error TS2307: Cannot find module '@neo4j-labs/nams-ai-provider' or its corresponding type declarations.
  lib/memory.ts(15,33): error TS2307: Cannot find module '@neo4j-labs/nams-ai-provider' ...
npm test  -> exit 1: FAIL test/routes.test.ts  Error: Failed to resolve entry for package "@neo4j-labs/nams-ai-provider".
Control: cd packages/vercel-ai-provider && npm ci && npm run build (exit 0); back in the example, npx tsc --noEmit -> no errors; npm test -> Test Files 1 passed, Tests 15 passed.
Makefile:835-848 ts-test-examples runs `cd $(TS_DIR) && npm ci && npm run build` and never builds packages/vercel-ai-provider.

**Orchestrator spot-check.** Confirmed: e2bcb93 adds `@neo4j-labs/nams-ai-provider: file:../../packages/vercel-ai-provider` to nextjs-memory-chat/package.json, and lib/handlers.ts imports it. ci-typescript.yml:128 builds the provider only `if: matrix.example == 'nams-ai-provider'`.

Also reported as: x-consistency#0 (`.github/workflows/ci-typescript.yml:128`)

### docs-examples-py#0 — messages recipe asserts an order the SDK doesn't guarantee, and fails in about 40% of runs
**blocker** · correctness · `docs/modules/ROOT/examples/core_memory_recipes.py:32` · **must fix**

add_messages_batch writes both messages in one Cypher statement. Neither message gets a timestamp, so CREATE_MESSAGES_BATCH gives both the same datetime(). get_conversation then sorts only by `ORDER BY m.timestamp ASC`, so which of the two tied messages comes first is not defined. Readback often comes back reversed, and the assertion `[m.id for m in conversation.messages] == [m.id for m in stored]` fails. how-to/messages.adoc:55 tells readers 'The ID assertion checks order and persistence'. So `python core_memory_recipes.py messages` crashes with AssertionError for readers following the page. The released python-v0.6.0 has the same batch-timestamp query, so the recipe fails against the PyPI package too. The mocked docs tests (tests/docs/test_core_python_tutorials.py) never run this against Neo4j, so they pass.

**Evidence.** core_memory_recipes.py:18-32 `stored = await client.short_term.add_messages_batch(session, [...])` ... `assert [m.id for m in conversation.messages] == [m.id for m in stored]`. Source: src/neo4j_agent_memory/memory/short_term.py:442 `timestamp = msg_dict.get("timestamp")` (None when omitted); graph/queries.py:109 `timestamp: CASE WHEN msg.timestamp IS NOT NULL THEN datetime(msg.timestamp) ELSE datetime() END`; graph/queries.py:169-173 GET_CONVERSATION_MESSAGES `ORDER BY m.timestamp ASC`. Ran against neo4j:5.26-community (testcontainer) with the recipe's own messages() function: probe readback `[('assistant','f5b92c05', 14:59:10.352000), ('user','5648aefd', 14:59:10.352000)]` vs stored `[('user','5648aefd'), ('assistant','f5b92c05')]`. With 10 fresh-client runs of core_memory_recipes.messages the result was `pass 6 fail 4`, and an earlier harness run failed 3/3.

**Fix.** Don't assert order the SDK doesn't guarantee. Either give each batch dict an explicit, increasing ISO `timestamp`, or add the two messages with sequential add_message calls, or compare ID sets and check the roles separately. Update the 'checks order' sentence in how-to/messages.adoc to match. A separate follow-up: fix add_messages_batch in the SDK so each message gets a distinct, increasing timestamp.

**Independent reproduction.** Wrote scratchpad/review/probe_msgs.py. It stubs the core_memory_settings and aura_connection imports, imports docs/modules/ROOT/examples/core_memory_recipes.py, starts testcontainers Neo4jContainer("neo4j:5.26-community"), and runs `await r.messages(client, uuid4().hex[:8])` N times, each time with a fresh MemoryClient(backend="bolt", llm=None, extraction none, resolution none, 8-dim stub embedder).

`uv run python probe_msgs.py`, N=10: "pass 1 fail 9", every failure an AssertionError.
Re-run with full tracebacks, N=4: "pass 0 fail 4", each traceback showing `File ".../docs/modules/ROOT/examples/core_memory_recipes.py", line 32, in messages`.
`git show python-v0.6.0:src/neo4j_agent_memory/graph/queries.py | grep -n "ELSE datetime() END"` gives 99: `timestamp: CASE WHEN msg.timestamp IS NOT NULL THEN datetime(msg.timestamp) ELSE datetime() END,`, so the released package behaves the same way.
`git show ec9fc65:docs/modules/ROOT/examples/core_memory_recipes.py` gives "exists on disk, but not in 'ec9fc65'", so the file is new on this branch.

**Orchestrator spot-check.** Confirmed by reading the code. CREATE_MESSAGES_BATCH sets `timestamp: ... ELSE datetime()`, and Cypher evaluates `datetime()` once per statement, so every message in a batch gets the same timestamp. GET_CONVERSATION_MESSAGES then orders by `m.timestamp ASC` with no tiebreak, so the recipe's order assertion is racy.

Also reported as: gap1-bolt-programs-live#0 (`docs/modules/ROOT/examples/core_memory_recipes.py:32`)

### docs-examples-py#1 — Hosted first write uses a fixed display name as the conversation ID, contradicting the NAMS docs
**blocker** · api-contract · `docs/modules/ROOT/examples/nams_first_write.py:11` · **must fix**

The program sends add_message to a hard-coded conversation ID, 'docs-nams-first-write', without calling create_conversation first. On NAMS the SDK posts to /conversations/{id}/messages. Conversation IDs are assigned by the server (create_conversation sends only userId/metadata), and other pages on this branch tell readers to call create_conversation first and never use a display name as the session ID. Two outcomes are possible: (a) the write targets a conversation that doesn't exist, so the tutorial's first step fails; or (b) the service creates it on the fly, which gives every reader the same fixed-ID conversation in their workspace. In case (b), `conversation.messages[-1]` can come from an earlier run, and nothing checks the returned message ID. Either way the record is never put in the ledger. nams_quickstart's cleanup only deletes the ledgered conversation, so this write is never cleaned up. That contradicts the page's promise ('We will retain the IDs returned by NAMS and use them for scoped cleanup') and its later guidance to keep state until every created resource has a disposition.

**Evidence.** nams_first_write.py:11-14 `session_id = "docs-nams-first-write"` / `await client.short_term.add_message(session_id, "user", "Hello, NAMS!")` / `last = conversation.messages[-1]`. Contradicted by docs/modules/ROOT/pages/reference/api/short-term.adoc:24 'On NAMS, call `create_conversation` first and use its returned ID.'; how-to/migrate-to-nams.adoc:72 'Persist the ID returned by `create_conversation`; do not continue using its display name as the message session ID.'; how-to/use-nams.adoc:115 'A conversation's display name and a user ID are not substitutes for its returned ID.'; src/neo4j_agent_memory/nams/short_term.py:465-476 (create_conversation body is only `{userId, metadata}`) and :292-298 (add_message posts to `/conversations/{conv}/messages` with no creation). `grep -rn docs-nams-first-write docs tests` finds no cleanup or test beyond the include at pages/tutorials/nams-quickstart.adoc:72.

**Fix.** Call `conversation = await client.short_term.create_conversation(name)` and use `str(conversation.id)` for add_message and get_conversation. Check the stored message by the returned ID rather than messages[-1]. Then either add the conversation to the ledger or give explicit instructions to delete it, so the lesson's cleanup covers every resource it creates.

**Independent reproduction.** 1) `git show ec9fc65:docs/modules/ROOT/examples/nams_first_write.py` -> "fatal: path ... exists on disk, but not in 'ec9fc65'". `git log ec9fc65..HEAD -- <file>` -> d3db0ff. The branch added the file.
2) scratchpad/review/trace_first_write.py: sets MEMORY_API_KEY=nams_fake, monkeypatches neo4j_agent_memory.nams.transport.HttpTransport.request to print each request, then runs the example with runpy. Output:
   REQUEST GET /conversations None            (connect probe)
   REQUEST POST /conversations/docs-nams-first-write/messages {'content': 'Hello, NAMS!', 'role': 'user'}
   No create_conversation request (POST /conversations) is ever sent. (It then raised a pydantic UUID error because my fake response used id 'm1'. That is irrelevant, but it shows the Message.id field must be a UUID.)
3) Code trace: nams/short_term.py:211-231 `_resolve_conversation_id` returns the raw string unchanged. :292-299 add_message POSTs to /conversations/{conv}/messages. :459-481 create_conversation body is only {userId, metadata}, so conversation IDs come from the server.
4) Repo evidence of live NAMS behaviour: tests/integration/nams/test_smoke.py:11-15 and tests/integration/nams/conftest.py:264-265 ("NAMS (unlike bolt) does **not** auto-create conversations on the first `add_message`").
5) `grep -rn "docs-nams-first-write\|nams_first_write" docs/modules docs/extensions tests examples` -> only the example file and tutorials/nams-quickstart.adoc:72,77. Nothing tests it or cleans it up.

**Orchestrator spot-check.** Evidence checked, with a caveat: nobody ran this against live NAMS. The failure is inferred from the repo's own NAMS contract (tests/integration/nams/test_smoke.py:11-15, "NAMS requires explicit conversation creation") and from a mocked 404. Either way the script contradicts four other pages on this branch.

Also reported as: tut-hosted-py#0 (`docs/modules/ROOT/examples/nams_first_write.py:11`), gap2-gap2-expected-output-vs-progra#1 (`docs/modules/ROOT/examples/nams_first_write.py:12`)

### tut-ts#0 — MCP lesson's documented install makes `npm run build` fail with a type error (two zod copies)
**blocker** · reader-flow · `docs/modules/ROOT/pages/tutorials/mcp-server-typescript.adoc:62` · **must fix**

The lesson installs the SDK with `npm install ../typescript`, which creates a symlink. The SDK's `mcp/register` then resolves `zod` from `typescript/node_modules` (4.6.1 from the lockfile), while the reader's `McpServer` resolves the newer `zod@^4` that npm installs in `my-memory-mcp/node_modules` (4.6.5 today). tsc rejects `registerMemoryTools(server, …)` with TS2345, so `npm run build` exits 2. Step 4 tells the reader to run that build before pointing Desktop at `dist/server.js`. tsc still emits `dist/`, and the server does start: tools/list and zod validation work. But a reader following the page sees the build fail and stops. The build passes only when both zod versions match exactly (confirmed by installing zod@4.6.1). It also conflicts with the checkout partial's line 3-4 statement that 'application code instead installs the published `@neo4j-labs/agent-memory@0.5.0` package from npm'. `my-memory-mcp` is exactly that kind of standalone application project.

**Evidence.** Offending text at mcp-server-typescript.adoc:62: `npm install ../typescript @modelcontextprotocol/sdk@^1.30 zod@^4`. mcp-server-typescript.adoc:258 then says: "Run `npm run build` first so `dist/server.js` exists."

Reproduction in the scratchpad: npm init, the documented installs, the three copied helpers, the page's server.ts / tsconfig.json / package fields, then `npm run build`. Output:
`src/server.ts(21,41): error TS2345: Argument of type 'McpServer' is not assignable to parameter of type 'RegisterToolCapable'. ... Type 'MemoryToolShape' is missing the following properties from type 'ZodType<any, any, any>': _type, _output, _input, _def, and 34 more.` exit=2.

`npm ls zod` shows `zod@4.6.5` (the reader's) and `@neo4j-labs/agent-memory -> ../typescript` using `zod@4.6.1`. After `npm install zod@4.6.1`, `npm run build` exits 0.

Source of truth: typescript/src/mcp/register.ts:53 `import { z } from "zod";` and typescript/node_modules/zod/package.json `"version": "4.6.1"`.

**Fix.** In the standalone `my-memory-mcp` project, install the published release: `npm install @neo4j-labs/agent-memory@0.5.0 @modelcontextprotocol/sdk@^1.30 zod@^4`. npm then dedupes zod and the MCP SDK. The copied helpers only need the public API. If the source build is kept on purpose, pin `zod` to the exact version in typescript/package-lock.json, or compile with `--noEmitOnError false` and state that TS2345 is expected. Either way, make the checkout partial's npm sentence agree with whichever path is chosen.

**Independent reproduction.** Scratch dir: review/v1. The `typescript` symlink points to the repo's typescript/ folder, and typescript/dist/index.js already exists.

Commands, in my-memory-mcp:
1. `npm init -y`
2. `npm install ../typescript @modelcontextprotocol/sdk@^1.30 zod@^4`
3. `npm install --save-dev typescript@^5.9 tsx@^4 @types/node@^22`
4. Copy tutorial-{state,cleanup,mcp}.ts into src/.
5. Take server.ts from adoc lines 145-195 and tsconfig.json from adoc lines 95-106. Merge the package fields (type module, engines, start/build scripts) into package.json.

`npm run build` prints `src/server.ts(21,41): error TS2345: Argument of type 'McpServer' is not assignable to parameter of type 'RegisterToolCapable'.` It exits 2 (v1exit=2), and dist/ is still emitted.

`npm ls zod` output:
- `@modelcontextprotocol/sdk@1.30.1` → `zod@4.6.5 deduped`
- `@neo4j-labs/agent-memory@0.5.0 -> .../typescript` → `zod@4.6.1`
- top level: `zod@4.6.5`

Control run (review/v2): the same project with the dependencies replaced by `npm install @neo4j-labs/agent-memory@0.5.0 @modelcontextprotocol/sdk@^1.30 zod@^4`. `npm run build` exits 0 (v2exit=0), and zod resolves to a single 4.6.5.

Origin of the change: `git show ec9fc65:docs/modules/ROOT/pages/tutorials/mcp-server-typescript.adoc` line 44 is `npm install @neo4j-labs/agent-memory @modelcontextprotocol/sdk zod`. `git log -S'npm install ../typescript @modelcontextprotocol' ec9fc65..HEAD` returns 8fc3ead "docs: align guides and examples with current SDK behavior".

**Orchestrator spot-check.** Evidence checked (reproduction transcript). The regression came in with 8fc3ead, which changed the install to `npm install ../typescript`. A control run with `@neo4j-labs/agent-memory@0.5.0` from npm builds cleanly.

### integ-a#0 — Cloud embeddings recipe raises TypeError for both Bedrock and Vertex before any database write
**blocker** · code-wont-run · `docs/modules/ROOT/examples/integrations/cloud_embeddings_recipe.py:41` · **must fix**

`main()` calls `settings(embedding=embedder)` with a legacy `BedrockEmbedder` or `VertexAIEmbedder`. `MemorySettings._resolve_providers` only accepts an EmbeddingConfig, a provider string, or an `EmbeddingProvider` protocol instance. The old embedders expose `embed(text)`, `embed_batch` and a `_model` attribute but have no `model` or `embed_one`, so construction raises TypeError. As a result, both `python integrations/cloud_embeddings_recipe.py bedrock` (aws-bedrock-embeddings.adoc:83) and `... vertex` (google-cloud.adoc:94) print the vector check and then crash. Neither page's 'Expected ... then stored-message verification' step can succeed. aws-bedrock-embeddings.adoc:107 also says 'The recipe's shared setup accepts the explicit embedder object', which is false. The offline contract test (tests/docs/test_python_integration_contracts.py:257-283) only exercises `build_embedder` and `verify_vectors`. It never passes the embedder through `common.settings` or `main()`, so it passes (32 passed) while the program cannot run.

**Evidence.** Command: NEO4J_URI=… NEO4J_USERNAME=n NEO4J_PASSWORD=p AWS_REGION=us-east-1 GOOGLE_CLOUD_PROJECT=p GOOGLE_CLOUD_LOCATION=us-central1 uv run python -c "...common.settings(embedding=cloud.build_embedder(p))" -> 'bedrock ERR TypeError MemorySettings.embedding must be EmbeddingConfig, a provider string, or an EmbeddingProvider instance; got BedrockEmbedder.' and 'vertex ERR TypeError ... got VertexAIEmbedder.' Source of truth: src/neo4j_agent_memory/config/settings.py:720-730 (isinstance check against llm.protocol.EmbeddingProvider, which requires model/dimensions/embed/embed_one per src/neo4j_agent_memory/llm/protocol.py:157-197). Other docs show the correct pattern: reference/api/adapters.adoc:226 ('construct VertexAIEmbedder(...) directly and pass it as embedder= to MemoryClient') and configure-embedding-provider.adoc:110-121 (BedrockEmbeddingProvider).

**Fix.** Pass an `EmbeddingProvider` instead. For example, `settings(embedding=from_provider('bedrock/amazon.titan-embed-text-v2:0', kind='embedding', aws_region=os.environ['AWS_REGION']))` and `settings(embedding='vertex_ai/gemini-embedding-001')` both construct (Bedrock gives 1024 dims, Vertex 768). Alternatively, pass the legacy embedder with `MemoryClient(settings(embedding=<matching provider>), embedder=embedder)`. Fix the Bedrock page:107 sentence to match, and add a contract test that calls `common.settings(embedding=cloud.build_embedder(p))` or `cloud.main` with a stubbed client.

**Independent reproduction.** From docs/modules/ROOT/examples/integrations, with dummy env vars (NEO4J_URI=bolt://localhost:1 NEO4J_USERNAME=n NEO4J_PASSWORD=p AWS_REGION=us-east-1 GOOGLE_CLOUD_PROJECT=p GOOGLE_CLOUD_LOCATION=us-central1):
uv run --project <repo> python -c "import common, cloud_embeddings_recipe as cloud; for each p in bedrock/vertex: e=cloud.build_embedder(p); print(type(e).__name__, hasattr(e,'model'), hasattr(e,'embed_one')); common.settings(embedding=e)"
Output:
bedrock BedrockEmbedder False False
bedrock ERR TypeError MemorySettings.embedding must be EmbeddingConfig, a provider string, or an EmbeddingProvider instance; got BedrockEmbedder.
vertex VertexAIEmbedder True False
vertex ERR TypeError MemorySettings.embedding must be EmbeddingConfig, a provider string, or an EmbeddingProvider instance; got VertexAIEmbedder.
The raising branch is in src/neo4j_agent_memory/config/settings.py: `if not isinstance(self.embedding, _EP): raise TypeError(...)`. `git show ec9fc65:docs/modules/ROOT/examples/integrations/cloud_embeddings_recipe.py` gives "exists on disk, but not in 'ec9fc65'", so this branch added the file. grep shows the pages that include it and give the run commands: aws-bedrock-embeddings.adoc:62/83/107 and google-cloud.adoc:65/94.

**Orchestrator spot-check.** Reproduced: `settings(embedding=VertexAIEmbedder(...))` raises `TypeError: MemorySettings.embedding must be EmbeddingConfig, a provider string, or an EmbeddingProvider instance; got VertexAIEmbedder.`

Also reported as: gap2-gap2-expected-output-vs-progra#0 (`docs/modules/ROOT/examples/integrations/cloud_embeddings_recipe.py:41`)

### gap1-bolt-programs-live#1 — Anthropic tutorial always stops at 'No entity candidates': extracted entities are stored without embeddings
**blocker** · correctness · `docs/modules/ROOT/examples/anthropic_local_memory.py:37` · **must fix**

The program stores a message with `extract_entities=True`, then calls `client.long_term.search_entities("Maya Chen", limit=5)` and raises if nothing comes back. search_entities is a pure vector search. The auto-extraction path in short_term writes every extracted entity with `embedding: None`, so the search can never match them. The tutorial therefore fails at step 5 however well the Anthropic model extracts. Step 6's check also fails: it expects `the returned entity vectors have 384 dimensions`, but the query returns no rows.

**Evidence.** Offending: anthropic_local_memory.py:37-41 `entities = await client.long_term.search_entities("Maya Chen", limit=5)` / `if not entities: raise RuntimeError("No entity candidates returned; ...")`; tutorials/anthropic-and-local-embeddings.adoc:127 `One or more Entity candidate: lines, then Verified: context assembly returned text` and :146 `Expected: the returned entity vectors have 384 dimensions`. Source of truth: src/neo4j_agent_memory/memory/short_term.py:1376 `"embedding": None,` in _extract_and_link_entities; long_term.py:1150-1153 search_entities embeds the query and runs SEARCH_ENTITIES_BY_EMBEDDING. Live run, 5 times, against a neo4j:5.26 testcontainer: the real BAAI/bge-small-en-v1.5 embedder, with AnthropicProvider.complete_structured patched to return Maya Chen/Northstar Robotics/Denver. Output: `Verified message readback; session=anthropic-tutorial-3591e6c3` then `RuntimeError: No entity candidates returned; inspect extraction before continuing` (FAKE structured calls: 1). The DB then held `{'n': 'Maya Chen', 't': 'PERSON', 'noemb': True, 'dim': 0}` for all three entities, and `MATCH (entity:Entity) WHERE entity.embedding IS NOT NULL RETURN count(*)` returned `0`.

**Fix.** Verify extraction with an exact lookup instead of vector search. For example, query `MATCH (m:Message {id:$id})-[:MENTIONS]->(e:Entity) RETURN e.name, e.type` through client.query.cypher, or call get_entity_by_name. Rewrite the step-6 Cypher and its expectation to check message and index dimensions rather than entity embeddings. Alternatively, fix the SDK so it embeds extracted entities, and pin the docs to the release that includes that fix.

**Independent reproduction.** 1) Code trace: `grep -rn UPDATE_ENTITY_EMBEDDING src/neo4j_agent_memory` returns only its definition at queries.py:287, never a use. At short_term.py:757-759, add_message's 'auto' mode calls `_extract_and_link_entities`, which runs build_create_entity_query with `embedding: None`.
2) Live run: scratchpad/review/verify_anthropic.py ran against a neo4j:5.26 testcontainer. It used MemoryClient(settings, embedder=tests.conftest.MockEmbedder(), extractor=FakeExtractor) where the extractor returns Maya Chen/PERSON, Northstar Robotics/ORGANIZATION and Denver/LOCATION. It then called add_message(..., extract_entities=True) followed by search_entities("Maya Chen", limit=5). Output:
readback ok: True
search_entities -> []
search_entities threshold=0 -> []
entities: [{'n': 'Maya Chen', 'noemb': True}, {'n': 'Northstar Robotics', 'noemb': True}, {'n': 'Denver', 'noemb': True}]
mentions: [{'c': 3}]
The entities are stored and MENTIONS-linked but have no embedding, so even threshold=0 finds nothing. The tutorial program would raise at line 39.
3) Regression check: `git show ec9fc65:docs/modules/ROOT/pages/tutorials/anthropic-and-local-embeddings.adoc` lines 108-114 show the old snippet only printing `Found {len(entities)} entities`, with no raise. The file anthropic_local_memory.py does not exist at ec9fc65; commits 8fc3ead and 881c337 on this branch added it.

**Orchestrator spot-check.** Evidence checked. The root cause is in the SDK: the auto-extraction path writes entities with `embedding: None` (short_term.py:1376), and UPDATE_ENTITY_EMBEDDING has no caller. The new tutorial asserts on a vector search that cannot match those entities. Fix either the SDK or the tutorial's check.

### gap1-bolt-programs-live#2 — Knowledge-graph tutorial ingest fails: documented install cannot load GLiREL, and working GLiREL finds no relations
**blocker** · correctness · `docs/modules/ROOT/pages/tutorials/knowledge-graph.adoc:33` · **must fix**

The documented install pulls huggingface-hub 1.33.0 and transformers 5.16.1. With those, glirel 1.2.1 cannot load its model, so `python knowledge_graph.py ingest` fails on the first document. With huggingface-hub<1 plus protobuf, the model loads. Even then, GLiRELExtractor returns zero relations at the program's threshold of 0.5, so ingest stops with `No resolved relationships were stored` after both documents have been written. The cause is that `_entities_to_glirel_format` passes character offsets where GLiREL expects token indices. At threshold 0.1 the SDK instead crashes with a pydantic ValidationError, because head_text comes back as a token list. A reader following the page cannot reach `Verified: extraction produced storable relationships` or the later inspect/answer steps. The storage, inspect and answer code itself is correct: with a deterministic extractor supplying the same entities and relations, 5/5 runs printed `Verified: 2 source documents and 4 relationships read back`.

**Evidence.** Offending: knowledge-graph.adoc:33 `python -m pip install 'neo4j-agent-memory[openai,gliner,spacy]==0.6.0' glirel 'loguru>=0.7,<1'`; :131 `Expected: ... followed by Verified: extraction produced storable relationships`; knowledge_graph.py:55 `GLiRELExtractor(relation_types=SCHEMA.relation_types, threshold=0.5)`. Command: `uv pip install --dry-run 'neo4j-agent-memory[openai,gliner,spacy]==0.6.0' glirel 'loguru>=0.7,<1'` resolves `huggingface-hub==1.33.0, transformers==5.16.1, glirel==1.2.1, gliner==0.2.29`. In a venv installed exactly that way from PyPI, plus `python -m spacy download en_core_web_sm`, `python knowledge_graph.py ingest` fails with `RuntimeError: Could not load GLiREL model 'jackboyla/glirel-large-v0': GLiREL._from_pretrained() missing 2 required keyword-only arguments: 'proxies' and 'resume_download'`. With huggingface-hub 0.36.2 + protobuf the log shows `leadership.txt: stored 4 mentions, 0 relationships; skipped 0`, `partnership.txt: stored 4 mentions, 0 relationships; skipped 0`, `RuntimeError: No resolved relationships were stored; inspect extraction output`. The GLiRELExtractor probe at threshold 0.5 and 0.3 returned `[]`; at 0.1 it raised `ValidationError: 2 validation errors for ExtractedRelation source Input should be a valid string [input_value=['Maya', 'Chen', 'is', 'C...'Northstar', 'Robotics']`. SDK source: src/neo4j_agent_memory/extraction/gliner_extractor.py:989-993 (character positions used as GLiREL spans) and :1030-1041.

**Fix.** Don't publish this lesson on GLiREL until the SDK's GLiREL span conversion is fixed and released. For now, use a relation source that works (for example the LLM extractor, which the page already requires an OpenAI key for), or build relations from the GLiNER entities explicitly. If GLiREL stays, pin 'huggingface-hub<1' and protobuf and verify that a real run stores at least one relationship before publishing.

**Independent reproduction.** Scratch dir: /private/tmp/claude-502/-Users-lyonwj-github-neo4j-labs-agent-memory/66a2977c-9670-4b56-8270-fc84ea0f1100/scratchpad/review/indep2

1. `uv pip compile req.in --python 3.12` (req.in = the adoc:33 requirement set) resolved to: gliner==0.2.29, glirel==1.2.1, huggingface-hub==1.33.0, neo4j-agent-memory==0.6.0, torch==2.14.0, transformers==5.16.1.

2. `uv venv venv && uv pip install -r req.in`, then `venv/bin/python -c "from neo4j_agent_memory.extraction.gliner_extractor import GLiRELExtractor; GLiRELExtractor().model"` printed:
   RuntimeError Could not load GLiREL model 'jackboyla/glirel-large-v0': GLiREL._from_pretrained() missing 2 required keyword-only arguments: 'proxies' and 'resume_download'

3. Built venv2 from req.in plus 'huggingface-hub<1', protobuf and en_core_web_sm 3.8.0. Resolved to hf-hub 0.36.2 and transformers 4.57.6. Ran probe.py, which imports the tutorial's knowledge_graph.py with a stubbed core_memory_settings and calls kg.extractor().extract() on each document:
   leadership.txt [('Maya Chen','PERSON',0,9),('Northstar Robotics','ORGANIZATION',20,38),('Northstar Robotics','ORGANIZATION',40,58),('Denver','LOCATION',65,71)] relations: []
   partnership.txt [...4 entities...] relations: []
   glirel fmt: [[0, 9, 'PERSON', 'Maya Chen'], [20, 38, ...], [40, 58, ...], [65, 71, ...]] ntokens 14
   threshold 0.3 -> []
   threshold 0.1 -> ValidationError 2 validation errors for ExtractedRelation source Input should be a valid string [input_value=['Maya', 'Chen', 'is', 'C...'Northstar', 'Robotics'], input_type=list]

4. knowledge_graph.py:126-127 raises RuntimeError("No resolved relationships were stored; inspect extraction output") when total == 0.

5. `git cat-file -e ec9fc65:docs/modules/ROOT/examples/knowledge_graph.py` shows the file did not exist there, so it is new on this branch. The old page's install line was `pip install neo4j-agent-memory[all] python-dotenv`.

I did not run it against a live Neo4j/Aura database. The failure happens during extraction, before any storage path that needs one.

**Orchestrator spot-check.** Evidence checked. There are two causes. First, the documented install resolves huggingface-hub 1.x, and GLiREL 1.2.1 cannot load a model with it. Second, an SDK bug that predates this branch: `_entities_to_glirel_format` passes character offsets where GLiREL expects token indices, so it finds zero relations. The tutorial is new on this branch and exposes both.

Also reported as: gap2-gap2-install-commands-sweep#0 (`docs/modules/ROOT/pages/tutorials/knowledge-graph.adoc:33`)

## Majors (41)

### explanation#0 — multi_tenant=True claim is backwards: scoping works without it and unscoped writes then raise
**major** · behaviour-claim · `docs/modules/ROOT/pages/explanation/operational-primitives.adoc:21` · **must fix**

The page says multi-tenant scoping needs `multi_tenant=True` plus `user_identifier=`, and that unscoped calls then keep working exactly as before. The source does the opposite on both counts. `user_identifier` links the conversation or preference to a `:User` whether or not the flag is set. The flag only makes the enforced write paths (add_message, add_messages_batch, add_preference, start_trace) raise ValueError when `user_identifier` is left out. A reader who turns the flag on expecting unscoped code to keep running will see existing writes fail. The how-to has it right: 'memory.multi_tenant=True requires it on specific write paths'.

**Evidence.** operational-primitives.adoc:21-23: "Multi-tenant scoping requires `MemorySettings.memory.multi_tenant=True` plus a `user_identifier=` kwarg on the specific call; unscoped calls keep working exactly as before."
Source: src/neo4j_agent_memory/config/settings.py:340-346, multi_tenant description: "When True, APIs that accept ``user_identifier=`` raise a ValueError if the kwarg is omitted."; src/neo4j_agent_memory/memory/short_term.py:350-357 _enforce_multi_tenant raises ValueError.
Command: `ShortTermMemory(client=None, multi_tenant=True).add_message('s','user','hi',extract_entities=False,generate_embedding=False)` gives `ValueError MemorySettings.memory.multi_tenant=True but no user_identifier was supplied.`
how-to/multi-tenancy.adoc:46: "`memory.multi_tenant=True` requires it on specific write paths but does not make all reads user-scoped."

**Fix.** Rewrite the bullet: `user_identifier=` on the supported write methods associates records with a `:User` whether or not the flag is set. Setting `MemorySettings.memory.multi_tenant=True` makes those write paths raise ValueError when `user_identifier` is omitted, so it is a guard against accidental unscoped writes. It is not what turns scoping on.

**Independent reproduction.** I wrote scratchpad/mt.py. It builds ShortTermMemory on a MagicMock client (execute_write/execute_read as AsyncMock), spies on _link_user_to_conversation, and calls add_message('s','user','hi', extract_entities=False, generate_embedding=False, user_identifier=uid) for each combination of flag and uid.

Command: `uv run python .../scratchpad/mt.py`

Output:
- flag=False uid=None: ok, user links=[]
- flag=False uid=alice: ok, user links=['alice']   (user scoping works with no flag)
- flag=True uid=None: ValueError MemorySettings.memory.multi_tenant=True but no user_identifier was supplied. Pass user_identifier= to scope this write.
- flag=True uid=alice: ok, user links=['alice']

Supporting checks:
- `git log ec9fc65..HEAD -- docs/.../operational-primitives.adoc` returns d3db0ff, and `git show ec9fc65:<path>` returns "exists on disk, but not in 'ec9fc65'", so this branch introduced the text.
- `sed -n 40,50p docs/modules/ROOT/pages/how-to/multi-tenancy.adoc` shows line 46 stating the correct behaviour.

### explanation#1 — POLE+O subtype catalog removed; the page it defers to has no subtype list
**major** · lost-content · `docs/modules/ROOT/pages/explanation/poleo-model.adoc:36` · **must fix**

The branch cut the per-type subtype lists (PERSON: INDIVIDUAL, ALIAS, ...) from this page and now says the schema reference owns them. reference/schemas.adoc is an index of GLiNER domain schemas. No docs page now lists the valid POLE+O subtypes. This matters on Bolt: for a POLE+O type, a subtype outside the known list is silently left off the node's labels. A reader can no longer find out which subtypes produce labels such as `:Vehicle`.

**Evidence.** poleo-model.adoc:36: "The xref:reference/schemas.adoc[schema reference] owns the complete supported type and subtype lists." (also line 99: "Domain schemas and subtype catalog").
`grep -rn "SUSPECT\|WITNESS\|COORDINATES\|LANDMARK\|PHONE\|NONPROFIT\|EDUCATIONAL" docs/modules/ROOT/pages` returns no matches. The old page (git show ec9fc65:.../poleo-model.adoc lines 32-226) had `=== PERSON` ... `=== ORGANIZATION` subtype sections.
Source: src/neo4j_agent_memory/schema/models.py:372-430 defines the subtype lists. src/neo4j_agent_memory/graph/query_builder.py:194-201: "For POLE+O types, only allow known subtypes" (invalid subtype gets no label).

**Fix.** Add the POLE+O subtype table, taken from schema/models.py, to a reference page (for example reference/schema-objects.adoc or reference/schemas-custom.adoc). Point this page and its See-also entry at that section, and say that an unknown subtype on a POLE+O type gets no label.

**Independent reproduction.** 1) sed -n 25,45p docs/modules/ROOT/pages/explanation/poleo-model.adoc: line 36 defers the "complete supported type and subtype lists" to xref:reference/schemas.adoc. The See also section links "Domain schemas and subtype catalog".
2) grep -rln "SUSPECT\|WITNESS\|COORDINATES\|LANDMARK\|NONPROFIT\|INDIVIDUAL\|VEHICLE" docs/modules/ROOT/pages docs/modules/ROOT/partials returned 6 files. A per-file grep showed only single examples (extractors.adoc:62, mcp-tools.adoc:132, long-term-entities.adoc:46/206, long-term.adoc:20/23, schemas-custom.adoc:90). No file has a catalog, and schemas.adoc and schema-objects.adoc have none.
3) git show ec9fc65:docs/modules/ROOT/pages/explanation/poleo-model.adoc | grep -n "=== \|SUSPECT" returned "34:=== PERSON", "51:|`SUSPECT`", "70:=== OBJECT", "119:=== LOCATION", "157:=== EVENT" and "194:=== ORGANIZATION". git grep -ln SUSPECT ec9fc65 -- docs/modules matches only that file.
4) uv run python -c "from neo4j_agent_memory.graph.query_builder import validate_subtype, VALID_SUBTYPES; print(VALID_SUBTYPES); print(validate_subtype('OBJECT','VEHICLE'), validate_subtype('ORGANIZATION','RESTAURANT'), validate_subtype('LOCATION','LANDMARK'))" printed the full set (OBJECT includes PRODUCT; LOCATION includes FACILITY, GEOGRAPHIC and GEOPOLITICAL; EVENT includes DATE and TIME; ORGANIZATION includes GROUP), then "Vehicle None Landmark". An unknown subtype on a POLE+O type gets no label (query_builder.py:194-201).
5) grep -rln SUSPECT docs/build/site found no matches in the existing built site.

Also reported as: x-content-loss#2 (`docs/modules/ROOT/pages/explanation/poleo-model.adoc:36`)

### explanation#2 — FAQ 'Which Neo4j versions are supported?' points to pages that state no version
**major** · lost-content · `docs/modules/ROOT/pages/faq.adoc:51` · **must fix**

The old answer gave the requirement: Neo4j 5.x, with 5.11+ recommended for vector indexes. The new answer sends readers to 'database prerequisites' in Getting started and 'vector-index requirements' in the Configuration reference. Neither page, nor any other docs page, states a Neo4j server version. The Bolt backend depends on `db.index.vector.queryNodes`, so the version still matters to self-hosted users, and the question now goes unanswered.

**Evidence.** faq.adoc:51: "For Bolt, use the database prerequisites in xref:getting-started.adoc[Getting started] and the vector-index requirements in xref:reference/configuration.adoc[Configuration]."
Old (git show ec9fc65:docs/modules/ROOT/pages/faq.adoc:77): "Neo4j 5.x is supported, with **5.11+ recommended** for vector index support".
`grep -rn -i "5\.11\|Neo4j 5\.\|server version" docs/modules/ROOT/pages` finds only faq.adoc:51, how-to/adopt-existing-graph.adoc:23 ("Neo4j 5.x") and a schema-objects note. Neither getting-started.adoc nor reference/configuration*.adoc mentions a Neo4j version.
src/neo4j_agent_memory/graph/queries.py:177: `CALL db.index.vector.queryNodes('message_embedding_idx', ...)`.

**Fix.** Put the concrete requirement back in the answer (Neo4j 5.x with vector-index support, 5.11+, or Aura), or add it to the Getting started prerequisites and link that anchor.

**Independent reproduction.** 1) sed -n 47,51p docs/modules/ROOT/pages/faq.adoc prints: "For Bolt, use the database prerequisites in xref:getting-started.adoc[Getting started] and the vector-index requirements in xref:reference/configuration.adoc[Configuration]. ..."
2) grep -rn -i -E "5\.11|neo4j 5|5\.x|2025\.|server version|vector index|prerequisit" over getting-started.adoc, reference/configuration*.adoc and partials/ finds only getting-started.adoc:68 "anchor:_2_install_the_sdk[]anchor:_prerequisites[]" (an empty anchor under "== See also"), a Vertex AI output_dimensionality row in configuration-providers.adoc:33, and an Aura cleanup partial line. None of these states a server version or a vector-index requirement.
3) sed -n 20,110p getting-started.adoc: the "Python with Neo4j Aura" section links to tutorials and states no Neo4j version or vector-index requirement.
4) grep -n -i -E "neo4j (5|20)|version|vector" reference/configuration.adoc returns no matches. The same grep for "vector.index|queryNodes|server version|neo4j version" over tutorials/first-agent-memory.adoc and sdks/python.adoc also returns nothing.
5) grep -rn -i -E "Neo4j (5|20[0-9]{2})|5\.1[0-9]|APOC" over docs pages and partials returns only how-to/adopt-existing-graph.adoc:23 "* A running Neo4j 5.x ...".
6) git show ec9fc65:docs/modules/ROOT/pages/faq.adoc lines 75-77: "Neo4j 5.x is supported, with **5.11+ recommended** for vector index support (used for semantic search)."
7) grep -rn queryNodes src/neo4j_agent_memory | wc -l gives 14, so the Bolt backend depends on server vector search.
8) docs/build/site/agent-memory/faq.html contains the question, so the dead-end answer is in the built site.

Also reported as: x-consistency#10 (`README-pypi.md:158`)

### gap1-backend-support-labels#0 — Bolt-only label says every API raises NotSupportedError on NAMS; many labelled calls do not
**major** · backend-label · `docs/modules/ROOT/partials/backend-bolt-only.adoc:3` · **must fix**

The partial tells readers that the page's APIs raise `NotSupportedError` on NAMS. This branch adds the label to 14 more pages (reasoning-traces, entity-extraction, entity-extraction-batch, entity-extraction-schemas, configure-llm-provider, configure-embedding-provider, bring-your-own-model, migrate-to-providers, running-without-an-llm, migrate-embedding-model, batch-processing, preferences, privacy-and-audit, create-context-graph-mcp). For many of the calls on those pages the claim is false. Standalone extractors (`extraction_recipes.py`) never touch a backend. On NAMS, `MemorySettings.embedding`/`extraction` are accepted with a UserWarning and then ignored. Methods missing from the NAMS classes raise `AttributeError`, for example `add_messages_batch`, `link_entity_to_message`, `find_potential_duplicates`, `get_preferences_by_category` and `reasoning.on_tool_call_recorded`. The documented positional calls `get_preferences_for(user)` and `supersede_preference(old, new)` raise `TypeError`. `record_tool_call(touched_entities=...)` succeeds and drops the argument. A reader who catches `NotSupportedError` to detect a missing feature will get `AttributeError`, `TypeError` or silent success instead.

**Evidence.** Offending: docs/modules/ROOT/partials/backend-bolt-only.adoc:3 "The APIs on this page are *bolt-only* — calling them against the hosted NAMS backend raises `NotSupportedError`."
Source: src/neo4j_agent_memory/__init__.py:678-712 `_warn_inactive_layers_on_nams` only warns ("NAMS backend ignores client-side memory layers"); src/neo4j_agent_memory/nams/reasoning.py:206-234 record_tool_call builds the body without touched_entities. Probe on a NAMS MemoryClient with a fake transport (scratchpad review/nams_probe.py):
"ERR c.short_term.add_messages_batch('s', []): AttributeError: 'NamsShortTermMemory' object has no attribute 'add_messages_batch'"
"ERR c.reasoning.on_tool_call_recorded: AttributeError: 'NamsReasoningMemory' object has no attribute 'on_tool_call_recorded'"
"ERR c.long_term.get_preferences_for('sara-demo'): TypeError: NamsLongTermMemory.get_preferences_for() takes 1 positional argument but 2 were given"
"ERR c.long_term.supersede_preference('a','b'): TypeError: ... takes 2 positional arguments but 3 were given"
"OK c.reasoning.record_tool_call(..., touched_entities=[]): ToolCall"
Settings probe (review/nams_settings.py): "connected OK; warnings: ['NAMS backend ignores client-side memory layers: embedding (server-managed), extraction (server-managed)...']"

**Fix.** Reword the partial to say the procedure needs Bolt and is not available on NAMS, without promising one exception type. For example: "On NAMS these operations are unavailable: depending on the call they raise NotSupportedError or AttributeError, or are ignored." Alternatively, add a separate 'client-side only' partial for the extraction and provider-configuration pages, which never call a backend.

**Independent reproduction.** 1) Which pages newly include the partial: for each page under docs/modules/ROOT/pages that includes backend-bolt-only, test `git show ec9fc65:<page> | grep -q backend-bolt-only`. It prints 14 NEW pages: configure-llm-provider, privacy-and-audit, create-context-graph-mcp, migrate-to-providers, reasoning-traces, migrate-embedding-model, entity-extraction-batch, entity-extraction, running-without-an-llm, batch-processing, configure-embedding-provider, bring-your-own-model, preferences, entity-extraction-schemas.
2) Class introspection with `uv run python` (inspect on the NAMS classes):
- NamsShortTermMemory: add_messages_batch MISSING
- NamsLongTermMemory: find_potential_duplicates MISSING, link_entity_to_message MISSING, get_preferences_by_category MISSING
- `get_preferences_for (self, **kwargs)`; `supersede_preference (self, preference_id, **kwargs)`
- NamsReasoningMemory: on_tool_call_recorded MISSING
- No class defines __getattr__.
- NAMS classes do have add_preference, search_preferences, start_trace, add_step, complete_trace and get_session_traces.
3) Probe on a NAMS MemoryClient with a fake transport (scratchpad review/nams_probe.py):
- `type(c.short_term).__name__` returns 'NamsShortTermMemory'
- `c.short_term.add_messages_batch('s', [])` raises AttributeError
- `c.long_term.find_potential_duplicates()` raises AttributeError
- `c.long_term.get_preferences_for('u')` raises TypeError: "takes 1 positional argument but 2 were given"
- `c.reasoning.on_tool_call_recorded` raises AttributeError
- `c.users` and `c.consolidation` return `_NamsUnsupported` sentinels (these do raise NotSupportedError when used)
4) `grep -rn NotSupportedError src/neo4j_agent_memory`: raised only in core/_unsupported.py:48, __init__.py:1037/1119/1178/1457, nams/reasoning.py:246/254/332/343, and the bolt-side stubs in memory/long_term.py:1922/1935 and memory/short_term.py:589/602.
5) docs/modules/ROOT/pages/how-to/configure-embedding-provider.adoc:9 includes the partial, while line 19 of the same page says that on NAMS "embedding runs server-side".

Also reported as: howto-core-a#3 (`docs/modules/ROOT/pages/how-to/entity-extraction.adoc:7`)

### gap1-bolt-programs-live#3 — No test or CI job runs the Bolt docs programs against Neo4j; mocked suite passes while live runs fail
**major** · test-coverage · `tests/docs/test_core_python_tutorials.py:379` · **must fix**

test_core_python_tutorials.py is fully mocked by design: create_autospec clients, canned query rows, a fake extractor. It never calls core_memory_recipes.messages, anthropic_local_memory, mcp_local_tutorial, integrations/hybrid_recipe, or a real GLiNER/GLiREL pipeline. It also enshrines the install that fails: the knowledge-graph parameter asserts extras {openai,gliner,spacy} plus glirel and loguru, and that exact install cannot load GLiREL (see the knowledge-graph finding). test_document_relations_use_exact_endpoints_and_record_provenance feeds hand-built relations that the real GLiREL path never produces. On the CI side, docs-tests has no services block, integration-test runs only tests/integration, and example-tests runs only tests/examples. None of them executes docs/modules/ROOT/examples/* against Neo4j, so the three live failures above ship with every job green.

**Evidence.** `uv run pytest tests/docs/test_core_python_tutorials.py -q` gives `105 passed in 0.54s` (also 105 passed in a dev-only venv without openai/gliner/spacy). Live runs of the same programs: messages 8/9 AssertionError, anthropic 5/5 RuntimeError, knowledge_graph ingest 5/5 failure. test_core_python_tutorials.py:379 `("knowledge-graph", {"openai", "gliner", "spacy"}, "knowledge_graph.py")` and :428-431 `assert "glirel" in requirements` / loguru specifier. .github/workflows/ci-python.yml:647-705 docs-tests job has no `services:`; :242 `uv run --no-sync pytest tests/integration`; :442 `uv run pytest tests/examples`. The only Neo4j-backed docs tests are behind `make test-docs-integration` (Makefile:365-367), which runs the stale test_tutorial_examples.py/test_howto_examples.py and is not wired into CI.

**Fix.** Add a Neo4j-backed docs job, for example in example-tests, which already has a neo4j:5.26 service. It should import each maintained program with aura_connection pointed at the service and run every recipe command and tutorial phase with a local embedder and a stub chat client. Run it several times, or add explicit ordering checks, so the flake is caught.

**Independent reproduction.** 1) Run the mocked suite:
`uv run pytest tests/docs/test_core_python_tutorials.py -q`
Output: `105 passed in 0.55s`

2) Run it live. The script is at /private/tmp/claude-502/-Users-lyonwj-github-neo4j-labs-agent-memory/66a2977c-9670-4b56-8270-fc84ea0f1100/scratchpad/review/live_messages.py. It starts `Neo4jContainer("neo4j:5.26-community")` with testcontainers and builds a MemoryClient with the same settings as core_memory_settings.py (llm=None, extraction none, resolution none), except that it uses a deterministic 8-dim fake embedder. It then calls `core_memory_recipes.messages(client, uuid4().hex[:8])` 10 times.
Output: `FAIL AssertionError AssertionError()` x9, then `ok 1 fail 9`.

3) CI and Makefile wiring:
- `grep -n "pytest\|services:" .github/workflows/ci-python.yml`
  - docs-tests (lines 647-705) has no services block.
  - integration-test runs only `tests/docs/test_python_integration_contracts.py` (line 221), which is mocked, plus `tests/integration` (line 242).
  - example-tests runs only `tests/examples` (line 442).
- `grep -rn "core_memory_recipes" tests .github` finds only the mocked test_core_python_tutorials.py (lines 32, 136, 560).
- Makefile: `test-docs` ignores the two Neo4j-backed docs test files (lines 345-346). `test-docs-integration` (lines 365-367) is not referenced in .github.

### gap1-bolt-programs-live#5 — test_howto_examples.py tests the old how-to code, not the core_memory_recipes.py/extraction_recipes.py tags now shown
**major** · test-coverage · `tests/docs/test_howto_examples.py:18` · **must fix**

The rewritten how-to pages contain no inline Python calls; each one includes a tag of core_memory_recipes.py or extraction_recipes.py. The test classes still say `Test examples from how-to/<page>.adoc` and exercise the old code. TestMessagesHowTo (line 18) uses `search_messages(session_id=..., metadata_filters=...)` and portfolio metadata; the page now shows add_messages_batch, get_conversation, get_conversation_summary and a database-wide search, and warns that the session_id filter is not applied. TestEntitiesHowTo (line 109) uses iPhone/AAPL `SECURITY` add_entity and search_entities; the page now shows add_relationship, add_fact, query.cypher and get_facts_about. TestPreferencesHowTo (line 176) uses search_preferences; the page now shows get_preferences_for and supersede_preference and calls search_preferences a broader, non-user-scoped query. TestReasoningTracesHowTo (line 220) covers a success-path lifecycle and list_traces; the page now shows the failure path with TraceOutcome and get_trace_with_steps. TestEntityExtractionHowTo (line 310) covers add_message auto-extraction; the page now shows a DB-free GLiNER extract. TestDeduplicationHowTo (line 354) adds Apple Inc twice and searches; the page now shows LongTermMemory.merge_duplicate_entities. So the tagged recipes, including the flaky messages one, have no Neo4j-backed test.

**Evidence.** `grep -o 'client\.[a-z_]*\.[a-z_]*('` finds no inline calls in HEAD messages/entities/preferences/reasoning-traces/deduplication.adoc. The old pages had, for example, 8x search_messages, 13x add_entity, 14x search_preferences and 5x review_duplicate. HEAD messages.adoc:41 `include::example$core_memory_recipes.py[tag=messages]`, entities.adoc:41, preferences.adoc:43, reasoning-traces.adoc:43, deduplication.adoc:39, entity-extraction.adoc:41 `include::example$extraction_recipes.py[tags=extract]`. Old-page strings such as `portfolio` (3x in the old messages.adoc) and `AAPL`/`SECURITY` (3x/5x in the old entities.adoc) are absent at HEAD. test_howto_examples.py:19 `"""Test examples from how-to/messages.adoc."""`, :97-101 `search_messages(... session_id=session_id, metadata_filters={"topic": "trading"} ...)`. Live run of both files: `3 failed, 24 passed` (the 3 known pre-existing failures).

**Fix.** Replace these classes with fixture-backed tests that call core_memory_recipes.messages/entities/preferences/reasoning/deduplication/audit and extraction_recipes functions directly, repeating the ordering-sensitive ones. Or delete them and update the `make test-docs-integration` description.

**Independent reproduction.** 1) `git diff --quiet ec9fc65..HEAD -- tests/docs/test_howto_examples.py && echo UNCHANGED` printed UNCHANGED.
2) For each of messages, entities, preferences, reasoning-traces, deduplication and entity-extraction.adoc, `grep -c 'client\.[a-z_]*\.[a-z_]*('` returned 0. The only includes are core_memory_recipes.py[tag=messages|entities|preferences|reasoning|deduplication] and extraction_recipes.py[tags=extract].
3) `sed -n 95,103p tests/docs/test_howto_examples.py` shows the search_messages(session_id=..., metadata_filters={"topic": "trading"}) call. messages.adoc:61 says the session_id filter is never applied, and core_memory_recipes.py:16-47 has none of that code.
4) `git grep -n 'core_memory_recipes\|extraction_recipes' HEAD -- . ':!docs/audit-evidence'` found only docs pages, partials and tests/docs/test_core_python_tutorials.py. No integration test runs `python core_memory_recipes.py <cmd>`.
5) `uv run pytest tests/docs/test_core_python_tutorials.py -q -k 'core_memory_recipes or recipe or howto'` gave 39 passed. All of these are offline: AST binding, mocked reasoning(), the Cypher regex and tag existence. The fixture at :34-49 uses a fake neo4j+s URI.
6) `git grep test_howto HEAD -- .github` found nothing. Makefile:345-346 excludes the file from the default docs run, and Makefile:367 runs it only under `make test-docs-integration`.
I did not re-run test_howto_examples.py against testcontainers Neo4j; the reviewer's live result was 3 failed, 24 passed, and the 3 failures are the known pre-existing ones.

### gap2-gap2-install-commands-sweep#2 — Provider README says it is version 0.2.0 with Node >=20; the package is 0.3.0 with Node >=22
**major** · version-claim · `typescript/packages/vercel-ai-provider/README.md:62` · **must fix**

This branch added setup text to the published package README that names the wrong version and the wrong engine floor. It also says in a reviewer's voice that "this source review does not verify npm publication", although 0.3.0 is on npm. Readers of the npm page get a stale version and a Node floor that npm's engine check contradicts. The install command below it is unpinned, so it installs 0.3.0, not 0.2.0.

**Evidence.** typescript/packages/vercel-ai-provider/README.md:59-63: "The commands below name the package, but this source review does not verify npm publication ... The provider manifest is version 0.2.0 and declares Node >=20; its core SDK peer currently requires Node >=22".
Source: typescript/packages/vercel-ai-provider/package.json: "version": "0.3.0", "engines": { "node": ">=22" }. `npm view @neo4j-labs/nams-ai-provider@0.3.0 engines` gives { node: '>=22' }, and `npm view @neo4j-labs/nams-ai-provider versions` includes "0.3.0".

**Fix.** Replace lines 59-64 with: requires Node.js 22+; install `npm install @neo4j-labs/nams-ai-provider@0.3.0 @neo4j-labs/agent-memory@0.5.0 ai@^7 zod@^4` (the command the docs pages use); peers are ai ^7, zod ^3.25.76 || ^4.1.8, @neo4j-labs/agent-memory ~0.4.0 || ~0.5.0.

**Independent reproduction.** 1) sed -n 50,75p typescript/packages/vercel-ai-provider/README.md shows lines 59-64: "...this source review does not verify npm publication or deployed-service behavior... The provider manifest is version 0.2.0 and declares Node >=20; its core SDK peer currently requires Node >=22..."
2) grep on typescript/packages/vercel-ai-provider/package.json: 3: "version": "0.3.0", 25-26: "engines": { "node": ">=22" }. git show ec9fc65:typescript/packages/vercel-ai-provider/package.json gives the same values: "version": "0.3.0", "node": ">=22".
3) git diff ec9fc65..HEAD -- that README shows these lines as additions ('+'). git log ec9fc65..HEAD names 8fc3ead ("docs: align guides and examples with current SDK behavior") as the commit that touched the file.
4) npm view @neo4j-labs/nams-ai-provider versions engines version peerDependencies gives versions [0.1.0, 0.2.0, 0.2.1, 0.3.0], engines {node: '>=22'}, version 0.3.0, peers ai ^7.0.0, zod ^3.25.76 || ^4.1.8, @ai-sdk/mcp ^2.0.0, @neo4j-labs/agent-memory ~0.4.0 || ~0.5.0. The peer list includes @ai-sdk/mcp ^2.0.0, which the suggested fix leaves out.

Also reported as: ts-ex-a#3 (`typescript/packages/vercel-ai-provider/README.md:62`), ts-ex-a#6 (`typescript/packages/vercel-ai-provider/README.md:59`)

### howto-core-a#0 — Reasoning page newly labeled bolt-only ("raises NotSupportedError"), but NAMS implements these calls
**major** · backend-claim · `docs/modules/ROOT/pages/how-to/reasoning-traces.adoc:7` · **must fix**

This branch added the bolt-only banner to the reasoning-traces page. The banner says the APIs on the page raise NotSupportedError against NAMS. The Python NAMS backend does implement start_trace, add_step, record_tool_call, complete_trace, get_trace_with_steps and get_session_traces. It adapts them to conversation-level steps and tool calls, with the trace lifecycle built client-side. Only search_steps, get_similar_traces and list_traces raise. The banner therefore contradicts the source, the backend capabilities reference and the reasoning API reference. The actual limits on NAMS are different: complete_trace is kept only in memory, and TraceOutcome and error are not sent. A NAMS reader is told the whole feature is unavailable, and the real limits go unmentioned.

**Evidence.** Offending: docs/modules/ROOT/pages/how-to/reasoning-traces.adoc:7 `include::partial$backend-bolt-only.adoc[]` -> docs/modules/ROOT/partials/backend-bolt-only.adoc:3 "*Available on NAMS: No.* The APIs on this page are *bolt-only* — calling them against the hosted NAMS backend raises `NotSupportedError`." (At ec9fc65 the page had no backend partial: `git show ec9fc65:.../reasoning-traces.adoc | grep partial$backend` -> empty.)
Source of truth: src/neo4j_agent_memory/nams/reasoning.py:165 `async def start_trace(...)`, :190 `add_step` (POST /v1/reasoning/steps), :206 `record_tool_call` (POST /v1/reasoning/tool-calls), :236 `complete_trace`, :281 `get_trace_with_steps`, :307 `get_session_traces`; none of these raise. Only :245 search_steps, :253 get_similar_traces and :331 list_traces raise NotSupportedError.
Other pages: docs/modules/ROOT/pages/reference/backend-capabilities.adoc:50-52 "Python with NAMS:: Python accessors adapt supported service records; check each accessor's contract"; docs/modules/ROOT/pages/reference/api/reasoning.adoc:6 "NAMS stores conversation-level steps and tool calls and synthesizes the trace lifecycle locally."

**Fix.** Replace the bolt-only banner with backend-both, or with a page-specific note: the recipe is Bolt-only because it relies on persisted TraceOutcome/success, while NAMS supports the step and tool-call calls with a synthetic trace lifecycle. Point to reference/api/reasoning-search-stats.adoc for the NAMS lifecycle table.

**Independent reproduction.** I wrote a fake HttpTransport that answers POST /reasoning/steps, POST /reasoning/tool-calls and GET /reasoning/trace/{id}, then ran the recipe's calls against NamsReasoningMemory with it. The script is at /private/tmp/claude-502/-Users-lyonwj-github-neo4j-labs-agent-memory/66a2977c-9670-4b56-8270-fc84ea0f1100/scratchpad/review/nams_reason.py and was run with `uv run python <that path>` from the repo root.

Run 1, the recipe exactly as documented (outcome=TraceOutcome(success=False, ...)):
  start_trace OK / add_step OK / record_tool_call OK ToolCallStatus.ERROR, request body {'toolName': 'lookup_product', 'input': '{"sku": "x"}', 'stepId': ..., 'status': ERROR, 'durationMs': 0} (the `error` kwarg is not sent) / complete_trace OK
  get_trace_with_steps -> pydantic_core.ValidationError: 1 validation error for ReasoningTrace outcome: Input should be a valid string [input_type=TraceOutcome] (raised from nams/reasoning.py:291)
  No NotSupportedError was raised.

Run 2, with outcome="boom", success=False:
  get_trace_with_steps OK; success=False steps=1 tcs=[1] [[ToolCallStatus.ERROR]]
  search_steps -> NotSupportedError; get_similar_traces -> NotSupportedError; list_traces -> NotSupportedError; get_tool_stats -> NotSupportedError

Other checks:
  `git show ec9fc65:docs/modules/ROOT/pages/how-to/reasoning-traces.adoc` has no backend partial, and its NOTE says the core trace ops port to NAMS.
  `grep -n -i "bolt-only\|backend-both\|banner" docs/MAINTAINING.md` finds no rule or exception for this banner.

Also reported as: gap1-backend-support-labels#1 (`docs/modules/ROOT/pages/how-to/reasoning-traces.adoc:7`)

### howto-core-b#0 — Newly published eval-harness docstring tells NAMS users to run the preference dimension, which is unsupported
**major** · behaviour-claim · `examples/eval-harness/main.py:47` · **must fix**

This branch starts including examples/eval-harness/main.py in full on how-to/evaluation.adoc (include::example$eval-harness/main.py[] at line 219; the include and docs/extensions/example-files.json are both new since ec9fc65). The module docstring shown there tells readers: 'On NAMS, seed through the memory APIs and run --dimensions retrieval,preference'. On NAMS, the preference dimension calls long_term.get_preferences_for, which always raises NotSupportedError. The same page's Prerequisites say the opposite ('its preference calls are unsupported'). On top of that, build_settings() hard-codes backend="bolt", so the script cannot run against NAMS at all. examples/eval-harness/README.md:128 repeats the claim.

**Evidence.** examples/eval-harness/main.py:47-48: "On NAMS, seed through the memory APIs and run ``--dimensions retrieval,preference``." | src/neo4j_agent_memory/nams/long_term.py:549-554: "async def get_preferences_for(...): raise NotSupportedError(backend=\"nams\", ... message=\"NAMS does not expose a preferences endpoint.\")" | src/neo4j_agent_memory/memory/eval.py:214 calls self._client.long_term.get_preferences_for | docs/modules/ROOT/pages/how-to/evaluation.adoc:19-21: "The hosted client exposes `eval`, but its preference calls are unsupported" | examples/eval-harness/main.py:123: backend="bolt"

**Fix.** Change the docstring (and README.md:128) to say that on NAMS only the retrieval dimension can run, through the reader's own client, and that this script is Bolt-only.

**Independent reproduction.** 1) git show ec9fc65:examples/eval-harness/main.py | grep -n "On NAMS" -> 40 (the sentence predates the branch); | grep backend= -> no match (backend="bolt" is new, HEAD main.py:123).
2) git show ec9fc65:docs/extensions/example-files.json -> "fatal: path ... exists on disk, but not in 'ec9fc65'". git diff ec9fc65..HEAD -- docs/modules/ROOT/pages/how-to/evaluation.adoc shows +include::example$eval-harness/main.py[] and +"client exposes `eval`, but its preference calls are unsupported".
3) Scratch script (scratchpad/eval_nams.py): built EvalMemory with _client.long_term set to the NAMS LongTermMemory class from neo4j_agent_memory.nams.long_term, then ran ev.run(EvalSuite(preference=[PreferenceCase(user_identifier="u", expected_active_pref_ids={"x"})]), dimensions=["retrieval","preference"]).
Output: "NotSupportedError LongTermMemory.get_preferences_for is not supported on the 'nams' backend. NAMS does not expose a preferences endpoint." The exception propagates out of run(), so no report is produced.
4) examples/eval-harness/main.py:120-123: build_settings() returns MemorySettings(backend="bolt", ...), and main.py:391 uses it by default, so the script cannot target NAMS.

### howto-hosted#1 — Index says multi-tenancy scopes entities to users; the target page and scope reference say it does not
**major** · correctness · `docs/modules/ROOT/pages/how-to/index.adoc:47` · **must fix**

The how-to index says the multi-tenancy guide scopes conversations, entities and preferences to individual users. The rewritten guide and the scope reference say `user_identifier` is accepted only on some writes, is not accepted by Bolt `add_entity`, and does not filter entity searches. Entity knowledge is shared within a database or workspace. The index therefore overstates the isolation guarantee, which is a security-relevant behaviour claim.

**Evidence.** index.adoc:47: "Scope conversations, entities, and preferences to individual users in a multi-tenant deployment." how-to/multi-tenancy.adoc:46: "It is not accepted by every API; for example, Bolt `add_entity` does not take this argument." reference/backend-capabilities.adoc:132: "It is not a universal parameter and does not automatically filter entity, preference or trace searches." reference/backend-capabilities.adoc:148: "Entity knowledge can be shared within the selected database/workspace."

**Fix.** Reword the blurb, for example: "Associate supported conversation, message and preference writes with a user and use explicitly scoped reads; this is not access control."

**Independent reproduction.** 1) `sed -n 47p docs/modules/ROOT/pages/how-to/index.adoc` returns: "... -- Scope conversations, entities, and preferences to individual users in a multi-tenant deployment."
2) `git log --oneline ec9fc65..HEAD -S"Scope conversations, entities, and preferences" -- docs/modules/ROOT/pages/how-to/index.adoc` returns c90d191 (docs: implement the rendered-site review plan, phases A to D), so the branch introduced the text.
3) `git show ec9fc65:docs/modules/ROOT/pages/how-to/index.adoc` shows the old blurbs: "Use `user_identifier=` to scope writes and reads per end-user" and "keeps tenants isolated on a shared backend". The old text also overclaimed, but this branch rewrote it.
4) `uv run python -c "import inspect; from neo4j_agent_memory.memory.long_term import LongTermMemory as L; from neo4j_agent_memory.memory.short_term import ShortTermMemory as S; ..."` printed:
   - add_entity False
   - search_entities False
   - search_preferences False
   - add_preference True
   - get_preferences_for True
   - add_message True
5) `grep -rn "Scope conversations, entities" docs/build/site` returns docs/build/site/agent-memory/how-to/index.html:1072, so the claim is in the rendered site.
6) The contradicting text is at multi-tenancy.adoc:7 and :46, and at backend-capabilities.adoc:132 and :148.

### howto-hosted#0 — Claude Code .mcp.json snippet puts literal Aura password and OpenAI key in the committed project file
**major** · security · `docs/modules/ROOT/pages/how-to/team-memory-in-your-editor.adoc:181` · **must fix**

The Claude Code step tells readers to paste the Aura URI, username, password and an OpenAI key as literal values into the project-root `.mcp.json`, and says these fields need no interpolation. Two things on the same page contradict this. The `.mcp.json.example` template included on the page uses `${NEO4J_URI}`, `${NEO4J_USERNAME}`, `${NEO4J_PASSWORD}` and `${OPENAI_API_KEY}` expansion. The example README tells readers to copy that template to the project root and commit it because it holds no secret. So a reader who follows the page and then the README's copy/commit guidance ends up with a project-scoped file that contains database and model credentials. The page also dropped the old sentence explaining that Claude Code expands `${VAR}`.

**Evidence.** Page line 181: "For the stdio entry ... copy its URI, username and password into the literal JSON values. Also supply an OpenAI key ... these JSON fields do not require shell interpolation. Keep the populated credential file private." Page lines 198-202: "NEO4J_PASSWORD": "replace-with-your-Aura-password", "OPENAI_API_KEY": "replace-with-your-OpenAI-key". The template included at page line 90 (examples/claude-code-team-memory/.mcp.json.example:27-28): "NEO4J_USER": "${NEO4J_USERNAME}", "NEO4J_PASSWORD": "${NEO4J_PASSWORD}". examples/claude-code-team-memory/README.md:102: "# Claude Code (project scope — commit it, it holds no secret)".

**Fix.** Make the inline Claude Code snippet match the included template: use `${NEO4J_URI}`, `${NEO4J_USERNAME}`, `${NEO4J_PASSWORD}`, `${OPENAI_API_KEY}` and `${USER}`. Restore the sentence saying Claude Code expands `${VAR}`/`${VAR:-default}`, so no secret lands in the committed file. Keep literal values only for the Desktop and Cursor configs, which must stay untracked.

**Independent reproduction.** 1. Page text at HEAD:
   sed -n 80,230p docs/modules/ROOT/pages/how-to/team-memory-in-your-editor.adoc
   Line 181 contains "copy its URI, username and password into the literal JSON values ... these JSON fields do not require shell interpolation. Keep the populated credential file private." The snippet has "NEO4J_PASSWORD": "replace-with-your-Aura-password" and "OPENAI_API_KEY": "replace-with-your-OpenAI-key".

2. The included template:
   cat examples/claude-code-team-memory/.mcp.json.example
   Its env block is "NEO4J_URI": "${NEO4J_URI}", "NEO4J_USER": "${NEO4J_USERNAME}", "NEO4J_PASSWORD": "${NEO4J_PASSWORD}", "OPENAI_API_KEY": "${OPENAI_API_KEY}". docs/extensions/example-files.json:8 maps team-memory/.mcp.json.example to this file.

3. The README:
   sed -n 90,115p examples/claude-code-team-memory/README.md
   Line 102 reads "# Claude Code (project scope — commit it, it holds no secret)", followed by "cp .mcp.json.example ../../.mcp.json".

4. The old page:
   git show ec9fc65:docs/.../team-memory-in-your-editor.adoc | grep -n VAR
   Lines 136-137: "Project scope, so it is committed and every teammate gets it. `${VAR}` and `${VAR:-default}` are expanded from the environment, so no secret lands in git." Line 155: "NEO4J_PASSWORD": "${NEO4J_PASSWORD}".

5. Simulating a reader, in a scratch dir (scratchpad/review/mcpjson/agent-memory-tutorials):
   - Ran git init.
   - Saved the template to team-memory/ as the page says.
   - Extracted the page's inline Claude Code snippet to .mcp.json and parsed it. Output: {'NEO4J_URI': 'neo4j+s://<instance-id>.databases.neo4j.io', 'NEO4J_USER': 'neo4j', 'NEO4J_DATABASE': 'neo4j', 'NEO4J_PASSWORD': 'replace-with-your-Aura-password', 'OPENAI_API_KEY': 'replace-with-your-OpenAI-key', ...}
   - `git add -A; git status --short` gave "A  .mcp.json" and "A  team-memory/.mcp.json.example".
   - `git check-ignore .mcp.json` gave "not ignored".
   - `grep -c '${'` found 6 matches in the template and 0 in the inline snippet.

6. Mitigations:
   - The page says "Keep the populated credential file private" (line 181).
   - The repo's .gitignore:92 lists `.mcp.json` (git check-ignore -v confirms), but that covers only this repo, not the reader's tutorial folder.
   - doctor.py only flags literal `nams_` keys (lines 184-189), not Neo4j or OpenAI secrets, so it would not catch this.

Also reported as: x-security#0 (`docs/modules/ROOT/pages/how-to/team-memory-in-your-editor.adoc:181`)

### howto-ts#0 — Next.js guide pairs persistInteractions:false with an assistant-only write pattern, so user turns are lost
**major** · behaviour-claim · `docs/modules/ROOT/pages/how-to/typescript/nextjs-memory-chat.adoc:165` · **must fix**

The guide sends readers who need a guaranteed write to the edge-runtime 'application-owned write pattern' and tells them to pass `persistInteractions: false` to `createNamsProvider` 'so the response is not stored twice'. That pattern writes only the assembled assistant answer, because it relies on the SDK middleware's `persistResponses: false`, which still persists the user's input. In the NAMS provider, `persistInteractions: false` turns off the whole `persistTurn`, including the user-message write. A reader who combines the two instructions stores the assistant answers and never stores the user turns, so the transcript and the provider's later retrieval are missing half of each exchange.

**Evidence.** nextjs-memory-chat.adoc:165-169: "use the xref:how-to/typescript/edge-runtime.adoc[application-owned write pattern] and pass `persistInteractions: false` to `createNamsProvider` so the response is not stored twice."
edge-runtime.adoc:72-73: ". Disable automatic assistant persistence (`persistResponses: false`). . On a successful stream end, call `addMessage` once with the assembled answer."
Source: typescript/packages/vercel-ai-provider/src/vercel-ai-provider-middleware.ts:115-121: `async function persistTurn(params, assistantText) { if (!persist) return; ... if (userText) await client.shortTerm.addMessage(convId, 'user', userText)` (the user write is skipped when persist is false). typescript/src/middleware/vercel-ai.ts:244-254: the SDK middleware's persistInput is separate from persistResponses.

**Fix.** State that `persistInteractions: false` disables both user and assistant writes in the provider. Tell the reader to write both turns in the application-owned lifecycle (the user message, then the assembled answer, then `waitUntil`). Alternatively, point to the SDK middleware with `persistResponses: false`, which keeps input persistence.

**Independent reproduction.** 1) sed -n 115,125p typescript/packages/vercel-ai-provider/src/vercel-ai-provider-middleware.ts shows `async function persistTurn(params, assistantText) { if (!persist) return; ... if (userText) await client.shortTerm.addMessage(convId, 'user', userText) ... if (assistantText) await client.shortTerm.addMessage(convId, 'assistant', assistantText)`. Line 200: `const persist = config.persistInteractions ?? true;`.
2) grep -rn "persistInteractions|persistInput|persistUser" typescript/packages/vercel-ai-provider/src: persistInteractions is the only persistence switch on the provider/middleware path. persistUserPrompt appears only in vercel-ai-provider-hooks.ts, a different API.
3) The test at vercel-ai-provider-middleware.test.ts:335-342 calls createNamsMemory({ apiKey:'k', persistInteractions:false }).wrap(...), then doGenerate(...), then `expect(fake.shortTerm.addMessage).not.toHaveBeenCalled()`.
4) cd typescript/packages/vercel-ai-provider && npx vitest run test/vercel-ai-provider-middleware.test.ts -t persist: "Tests 10 passed | 8 skipped (18)". The persistInteractions=false test passes, so no addMessage call is made, the user write included.
5) grep for addMessage in typescript/examples/cloudflare-agents-edge/src finds handlers.ts:129 `persistResponses: false` and handlers.ts:197 `addMessage(turn.conversationId, "assistant", turn.answer)`. The application code writes only the assistant turn.
6) git diff ec9fc65..HEAD on nextjs-memory-chat.adoc shows the application-owned-pattern/persistInteractions sentence as added lines (+175/+176). The edge-runtime.adoc steps "Disable automatic assistant persistence (`persistResponses: false`)" and "call `addMessage` once with the assembled answer" are also added by this branch.

### integ-a#3 — Strands page dropped context_graph_tools, retrieval_config and constructor reference; no other page has them
**major** · lost-content · `docs/modules/ROOT/pages/how-to/integrations/aws-strands.adoc:111` · **must fix**

The rewrite deleted all Python usage for `context_graph_tools(...)` (its neo4j_uri/neo4j_password/embedding_provider parameters, StrandsConfig and environment configuration, and per-tool parameters). It also deleted the `Neo4jRetrievalConfig` / `retrieval_config=` retrieval-injection section and the Neo4jSessionManager constructor table. The old anchors (_retrieval_injection, _constructor_reference, _tool_details, _using_strandsconfig, _from_environment_variables) are kept, so inbound links land on a prose section that never names these APIs. Line 111 tells readers to 'Avoid duplicate retrieval injection from both adapters' but never names the session-manager setting (`retrieval_config`) that controls it. No other Python page documents these APIs.

**Evidence.** Old page sections: `git show ec9fc65:.../aws-strands.adoc` lines 407-530 (Memory Tools, context_graph_tools(...) examples, StrandsConfig, Tool Details), 717-812 (Retrieval Injection with Neo4jRetrievalConfig, Constructor Reference). HEAD aws-strands.adoc:89-103 keep those anchors; :107-113 contain only prose. `grep -rn 'StrandsConfig\|Neo4jRetrievalConfig' docs/modules/ROOT/pages` (excluding TypeScript pages) -> no hits. Source: src/neo4j_agent_memory/integrations/strands/session_manager.py:92-104 (retrieval_config: Neo4jRetrievalConfig | None), integrations/strands/tools.py:681 context_graph_tools(neo4j_uri, neo4j_user, neo4j_password, neo4j_database, embedding_provider, embedding_model, **kwargs).

**Fix.** Restore a short code-level section, or link to a maintained example, for `context_graph_tools(...)` (parameters, and `clear_client_cache()`) and for `Neo4jSessionManager(retrieval_config=Neo4jRetrievalConfig(...))`. Name `retrieval_config` in the 'avoid duplicate retrieval injection' sentence. Also link examples/strands-session-manager alongside the memory-store example.

**Independent reproduction.** Commands run from the repo root:

1. `uv run python -c "import inspect; from neo4j_agent_memory.integrations.strands import Neo4jSessionManager, Neo4jRetrievalConfig, StrandsConfig, context_graph_tools, clear_client_cache; print(inspect.signature(Neo4jSessionManager.__init__)); print(inspect.signature(Neo4jRetrievalConfig)); print(inspect.signature(context_graph_tools)); print(hasattr(StrandsConfig,'from_env'))"`
   - All imports succeed.
   - Signatures: `retrieval_config: Neo4jRetrievalConfig | None = None` (plus `user_id`, `extract_entities`, `request_timeout`); `Neo4jRetrievalConfig(top_k=10, min_score=0.2, ...)`; `context_graph_tools(neo4j_uri=None, neo4j_user='neo4j', neo4j_password=None, neo4j_database='neo4j', embedding_provider='bedrock', embedding_model=None, **kwargs)`.
   - `from_env` check prints True.

2. `grep -rn 'retrieval_config\|Neo4jRetrievalConfig\|StrandsConfig' docs/modules/ROOT/pages docs/modules/ROOT/partials docs/modules/ROOT/nav.adoc`: no output.

3. `grep -rl 'Neo4jRetrievalConfig' docs/build/site`: no output.

4. `grep -rn 'strands-session-manager' docs/modules/ROOT/pages`: no output, so no page links the example.

5. `grep -rln 'retrieval_config|StrandsConfig|injection=False' examples/strands-*`: examples/strands-session-manager/README.md and main.py.

6. `git show ec9fc65:docs/modules/ROOT/pages/how-to/integrations/aws-strands.adoc | grep -n '^=='`: the old page (934 lines) had "Using StrandsConfig" (467), "From Environment Variables" (484), "Tool Details" (531), "Retrieval Injection" (717) and "Constructor Reference" (770), with `Neo4jRetrievalConfig` at 722-760 and 902-921.

7. `sed -n 250,270p src/neo4j_agent_memory/integrations/strands/session_manager.py`: the warning text "Drop retrieval_config, or pass injection=False to MemoryManager." HEAD aws-strands.adoc:111 gives neither setting.

Also reported as: x-content-loss#0 (`docs/modules/ROOT/pages/how-to/integrations/aws-strands.adoc:98`)

### integ-a#2 — Vertex AI model table removed, but inbound 'model table' link still targets it (circular)
**major** · lost-content · `docs/modules/ROOT/pages/how-to/integrations/google-cloud.adoc:106` · **must fix**

The branch removed the 'Supported Models' table ([[vertex-ai-embedding-models]]) and the output-dimensionality guidance, including gemini-embedding-001 native 3072/1536/768, text-embedding-005, text-multilingual-embedding-002, and the retired text-embedding-004 / textembedding-gecko ids that raise errors. The id survives only as a bare `anchor:` in 'Adapt the integration'. That section has no table and sends readers back to configure-embedding-provider 'for the canonical model and configuration guidance'. configure-embedding-provider.adoc:164 still links there as 'the Vertex AI model table', so the two pages point at each other and the model list exists nowhere in the docs.

**Evidence.** Old: `git show ec9fc65:.../google-cloud.adoc` lines 159-184 ([[vertex-ai-embedding-models]] === Supported Models table + IMPORTANT retired-model block). HEAD google-cloud.adoc:106 'anchor:vertex-ai-embedding-models[]' and :120 'See xref:how-to/configure-embedding-provider.adoc[Configure embeddings] for the canonical model and configuration guidance.' configure-embedding-provider.adoc:164 'See xref:how-to/integrations/google-cloud.adoc#vertex-ai-embedding-models[the Vertex AI model table]'. `grep -rln 'text-multilingual-embedding-002\|textembedding-gecko' docs/modules/ROOT/pages` -> no results.

**Fix.** Restore the supported/retired model table (it matches src/neo4j_agent_memory/embeddings/vertex_ai.py) under the vertex-ai-embedding-models anchor, or move it into configure-embedding-provider and update that page's link text and target.

**Independent reproduction.** 1) `git show ec9fc65:docs/modules/ROOT/pages/how-to/integrations/google-cloud.adoc | sed -n 150,190p` shows `[[vertex-ai-embedding-models]] === Supported Models`, the table (gemini-embedding-001 3072, text-embedding-005 768, text-multilingual-embedding-002 768) and the IMPORTANT block on retired text-embedding-004 and textembedding-gecko*.
2) `sed -n 95,130p` of the HEAD google-cloud.adoc shows line 106 is `anchor:vertex-ai-embedding-models[]` with no table, and line 120 says 'See xref:how-to/configure-embedding-provider.adoc[Configure embeddings] for the canonical model and configuration guidance.'
3) configure-embedding-provider.adoc:164 reads 'See xref:how-to/integrations/google-cloud.adoc#vertex-ai-embedding-models[the Vertex AI model table]'. `git diff ec9fc65..HEAD` of that file shows the branch rewrote this line.
4) `grep -rln 'text-embedding-005\|text-multilingual-embedding-002\|textembedding-gecko' docs/modules/ROOT/pages docs/modules/ROOT/partials docs/modules/ROOT/examples` finds nothing (exit=1).
5) The built docs/build/site/agent-memory/how-to/integrations/google-cloud.html contains `id="vertex-ai-embedding-models"` but has 0 matches for text-embedding-005.
6) `uv run python -c` constructed VertexAIEmbedder for each model: text-embedding-004 raises EmbeddingError ('retired by Google on 2026-01-14'); textembedding-gecko@003 raises EmbeddingError ('retired ... 2025-04-09'); text-embedding-005 builds with 768 dimensions; text-multilingual-embedding-002 builds with 768 dimensions. The source (vertex_ai.py:3-12) still documents all of these.

Also reported as: howto-core-b#7 (`docs/modules/ROOT/pages/how-to/configure-embedding-provider.adoc:164`), x-content-loss#1 (`docs/modules/ROOT/pages/how-to/configure-embedding-provider.adoc:164`)

### integ-b#0 — LangChain @tool snippet has no docstring, so LangChain raises ValueError when the tool is defined
**major** · code-wont-run · `docs/modules/ROOT/pages/how-to/integrations/langchain.adoc:104` · **must fix**

The page tells readers to add a graph-reading tool with this snippet and then pass it to create_agent. langchain_core's @tool needs either a docstring or an explicit description. This function has neither, so it fails as soon as the decorator runs. The snippet also leaves out the `tool` import. The version on main had a docstring on every tool.

**Evidence.** docs/modules/ROOT/pages/how-to/integrations/langchain.adoc:104-107: "@tool\nasync def search_entities(query: str) -> list[str]:\n    return [e.name for e in await client.long_term.search_entities(query)]". Command: `uv run python -c` defining exactly this function under `from langchain_core.tools import tool` (langchain-core 1.6.2 installed) prints `ValueError Function must have a docstring if description not provided.` The old page (git show ec9fc65:.../langchain.adoc:257-259) had `"""Search the knowledge graph for people, places, products or organizations."""`.

**Fix.** Add `from langchain_core.tools import tool` and a docstring, e.g. `"""Search the knowledge graph for entities matching the query."""`, or use @tool(description=...).

**Independent reproduction.** 1) `sed -n 100,110p docs/modules/ROOT/pages/how-to/integrations/langchain.adoc` shows `@tool\nasync def search_entities(query: str) -> list[str]:\n    return [e.name for e in await client.long_term.search_entities(query)]`, with no docstring and no import.
2) `uv run python -c 'from langchain_core.tools import tool; import langchain_core; print(langchain_core.__version__)
@tool
async def search_entities(query: str) -> list[str]: return []'` (wrapped in try/except) prints `1.6.2` then `ValueError Function must have a docstring if description not provided.`
3) `git show ec9fc65:docs/modules/ROOT/pages/how-to/integrations/langchain.adoc | grep -n -A4 '@tool'` shows lines 257-259 with the docstring `"""Search the knowledge graph for people, places, products or organizations."""`. The other tools at 272-282 also have docstrings.
4) pyproject.toml:155 is `langchain = ["langchain-core>=1.0,<2"]`, so the tested version is inside the supported range.

### integ-b#1 — Says Microsoft create_memory_tools returns plain definitions to translate, but it returns FunctionTool objects
**major** · api-claim · `docs/modules/ROOT/pages/how-to/integrations/microsoft-agent.adoc:113` · **must fix**

The page tells readers to translate the returned definitions into framework tool objects and that they need a separate execution path. The adapter actually returns agent_framework FunctionTool instances that the framework calls automatically. You pass them straight to as_agent(tools=...). Readers who follow the page would write needless and possibly wrong wrapping code. The old page described this correctly.

**Evidence.** microsoft-agent.adoc:113: "`create_memory_tools(...)` returns tool definitions that require the corresponding execution path; inspect the installed adapter before translating them into framework tool objects." Source: src/neo4j_agent_memory/integrations/microsoft_agent/tools.py:27-35: "def create_memory_tools(memory, include_gds_tools=True) -> list[FunctionTool]: ... Returns FunctionTool instances that the agent framework auto-invokes during streaming. No manual ``execute_memory_tool()`` dispatch needed." Old page (ec9fc65 microsoft-agent.adoc 'Tool Execution'): "tools are callable `FunctionTool` instances that the agent framework auto-invokes during `agent.run()`".

**Fix.** Say that create_memory_tools(memory, include_gds_tools=...) returns FunctionTool instances you pass directly as `chat.as_agent(tools=tools, context_providers=[memory.context_provider])`. Add that the GDS tools also need a GDSConfig.

**Independent reproduction.** 1) sed -n 113p docs/modules/ROOT/pages/how-to/integrations/microsoft-agent.adoc
   Output: the "returns tool definitions that require the corresponding execution path; inspect the installed adapter before translating them into framework tool objects" sentence.
2) uv run python -c "from unittest.mock import MagicMock; from neo4j_agent_memory.integrations.microsoft_agent import create_memory_tools; import agent_framework; t=create_memory_tools(MagicMock(), include_gds_tools=False); print(len(t), [type(x).__module__+'.'+type(x).__name__ for x in t][:3], [x.name for x in t]); print(isinstance(t[0], agent_framework.FunctionTool))"
   Output: 6 ['agent_framework._tools.FunctionTool', ...] ['search_memory','remember_preference','recall_preferences','search_knowledge','remember_fact','find_similar_tasks'] / True
3) git show ec9fc65:docs/modules/ROOT/pages/how-to/integrations/microsoft-agent.adoc | grep -n FunctionTool
   Output: line 250 "tools are callable `FunctionTool` instances that the agent framework auto-invokes during `agent.run()`", plus lines 410, 545 and 705. None of these survive at HEAD.
4) grep -n create_memory_tools across the page and reference/api/adapters.adoc at HEAD
   Output: only line 113.

### integ-b#2 — Rewrites dropped adapter API detail that no other docs page now covers
**major** · lost-content · `docs/modules/ROOT/pages/how-to/integrations/microsoft-agent.adoc:106` · **must fix**

All six pages were cut down to one recipe each. Some public adapter API they used to document is now missing from the whole docs site. (1) Microsoft: constructor options for Neo4jContextProvider/Neo4jMicrosoftMemory (max_context_items, max_recent_messages, similarity_threshold, extract_entities_async, gds_config), the list of tools, the GDSConfig fields and the fallback table, and serialize()/deserialize(memory_client=). (2) OpenAI Agents: the names of the four tools and get_similar_traces/format_traces_for_prompt. (3) LangChain: the RunnableWithMessageHistory wiring for Neo4jAgentMemory, the Neo4jMemoryRetriever fields (session_id is required on NAMS, k, threshold), and the NAMS behaviour table. (4) PydanticAI: nams_memory_tools(), which is exported. The pages keep the old anchors, so old deep links land on text that no longer contains the material. Inbound links still promise it: framework-comparison.adoc:27 says the Microsoft guide "documents its own supported version range", and tutorials/microsoft-agent-memory.adoc:26 says the guide "owns the compatibility details".

**Evidence.** Command: `grep -rn "Neo4jContextProvider\|Neo4jChatMessageStore\|execute_memory_tool\|GDSConfig\|Neo4jMemoryRetriever\|RunnableWithMessageHistory\|nams_memory_tools" docs/modules/ROOT/pages docs/modules/ROOT/examples docs/modules/ROOT/partials | grep -v how-to/integrations/` returns only record_agent_trace/Neo4jLlamaIndexMemory hits and no API reference for these. reference/api/adapters.adoc covers only the LLM provider adapters (its headings are OpenAIProvider ... InstructorProvider). Source: src/neo4j_agent_memory/integrations/pydantic_ai/__init__.py exports "nams_memory_tools". langchain/retriever.py:56-57: "session_id: ... Required on the hosted NAMS backend". Old pages: ec9fc65 microsoft-agent.adoc 'API Reference' (618-719), openai-agents.adoc 'Available Tools' (145-207), langchain.adoc 'Thread history for a chain' (294-330) and 'Running on the hosted backend' (530-563).

**Fix.** Restore a short reference section on each page, or add a framework-adapter reference page that the recipes link to. It should cover constructor parameters and defaults, tool names, the GDS config and fallbacks, RunnableWithMessageHistory wiring, the retriever fields and NAMS behaviour, and nams_memory_tools.

**Independent reproduction.** 1) Checked which docs mention each term at HEAD and at the merge base: `for t in nams_memory_tools max_context_items fallback_to_basic format_traces_for_prompt "serialize(" ...; do grep -rln -F "$t" docs/modules/ROOT/{pages,partials,examples}; git grep -l -F "$t" ec9fc65 -- docs/modules/ROOT/...; done`
 - nams_memory_tools: none at HEAD; at the base, explanation/backends.adoc and how-to/integrations/pydantic-ai.adoc.
 - max_context_items: none at HEAD; at the base, microsoft-agent.adoc and tutorials/microsoft-agent-memory.adoc.
 - fallback_to_basic: none at HEAD; at the base, the same two pages.
 - format_traces_for_prompt: none at HEAD; at the base, microsoft-agent.adoc and openai-agents.adoc.
 - serialize(: none at HEAD; at the base, microsoft-agent.adoc.
2) Page sizes: `wc -l` gives 122 lines for microsoft-agent.adoc at HEAD, against 724 at ec9fc65. openai-agents.adoc is 123 lines, langchain.adoc 115 and pydantic-ai.adoc 104. Most section ids now survive only as `anchor:` lines. Examples: microsoft-agent.adoc:64-65 (`_gds_integration`, `_gds_fallback_behavior`), :99 (`_serialization`), :103 (`_api_reference`); langchain.adoc:71 (`_running_on_the_hosted_backend`); openai-agents.adoc:99-100 (`_available_tools`, `_save_preference`).
3) Confirmed the APIs are public by running `uv run --no-sync python -c "import inspect; from neo4j_agent_memory.integrations.microsoft_agent import Neo4jContextProvider, Neo4jMicrosoftMemory, GDSConfig; ..."`:
 - Neo4jContextProvider(memory_client, session_id, *, source_id='neo4j-context', ..., max_context_items=10, max_recent_messages=5, extract_entities=True, extract_entities_async=True, context_template=None, gds_config=None, similarity_threshold=0.7)
 - GDSConfig(enabled=False, use_pagerank_for_ranking=True, pagerank_weight=0.3, pagerank_damping_factor=0.85, use_community_grouping=False, expose_as_tools=<factory>, fallback_to_basic=True, warn_on_fallback=True)
 - `from neo4j_agent_memory.integrations.pydantic_ai import nams_memory_tools` succeeds and returns a function.
4) retriever.py:56-57: "session_id: Optional session scope for message search. Required on the hosted NAMS backend". langchain.adoc at HEAD does not mention this.
5) `ls docs/modules/ROOT/pages/reference/api/` shows no page for the framework adapters.
6) Counterpoint: `grep -n "1\.13" microsoft-agent.adoc` finds lines 25 and 36 (`agent-framework-core>=1.13,<2`). The inbound claim about a version range is therefore still met; only the loss of API detail stands.

### provider#0 — Docs imply omitting conversationId starts a new conversation; it silently reuses the user's latest
**major** · behaviour-claim · `docs/modules/ROOT/pages/how-to/typescript/nams-ai-provider.adoc:104` · **must fix**

The landing page tells readers to create one instance per user session and to pass a conversationId only when they have one to resume. That implies leaving it out starts a new conversation. In the source, a scope without conversationId resolves to the user's most recent conversation (listConversations limit 1), and a new one is created only when the user has none. So every 'fresh session' in the provider, middleware and tools demos writes into the same NAMS conversation, and the offline test asserts exactly that. None of the seven pages says so. A reader who wants a separate conversation per session will not pass an id and will get every session merged into one. Their 'current conversation' search then returns old sessions, and crossSessionLimit has no other conversations to search.

**Evidence.** docs/modules/ROOT/pages/how-to/typescript/nams-ai-provider.adoc:104-106: "construct one provider/middleware/tools/hooks instance per user session, and pass a `conversationId` once you have one to resume."  Source: typescript/packages/vercel-ai-provider/src/vercel-ai-provider-client.ts:83 "/** The conversation id: the given one, else the cached one, else the user's latest, else a new one. */" and :100-105 `const convs = await client.shortTerm.listConversations({ userId: scope.userId, limit: 1 }); if (convs.length > 0) { ... return convs[0].id; }`. Test: typescript/examples/nams-ai-provider/test/docs-pages.test.ts:136 `expect(stub.conversations.size).toBe(1);` after the provider demo's 'Session 2 -- fresh session, same user'. grep for 'latest|most recent|new conversation' across the 7 pages finds no statement of this rule.

**Fix.** Say it outright on the landing page (and in the reference's NamsScope section): without conversationId, the package resumes the user's most recent conversation and creates one only if none exists. To start a new conversation, create one and pass its id. Note on the provider and middleware pages that 'fresh session' means a fresh JS object, not a new NAMS conversation.

**Independent reproduction.** 1. `sed -n 83,114p typescript/packages/vercel-ai-provider/src/vercel-ai-provider-client.ts` shows resolveConversation. The doc comment reads "the given one, else the cached one, else the user's latest, else a new one", and the code runs listConversations({userId, limit:1}) and returns convs[0].id when one exists.
2. `sed -n 44,56p typescript/examples/nams-ai-provider/src/provider-mode.ts` shows that each session() builds a new createNamsProvider with `scope: { userId }` and no conversationId. The per-client convCache is therefore empty, and the listConversations path is the one that runs.
3. `cd typescript/examples/nams-ai-provider && npx vitest run test/docs-pages.test.ts -t "provider mode"` passes (1 passed, 7 skipped). That test asserts `expect(stub.conversations.size).toBe(1)` and `messages toHaveLength(4)` (test/docs-pages.test.ts:136-137): both sessions ran through different provider objects and ended up in a single NAMS conversation.
4. `grep -rniE "latest|most recent|new conversation|resum|conversationId|reuse"` over how-to/typescript/nams-ai-provider*.adoc and reference/nams-ai-provider.adoc found no statement that omitting conversationId resumes the user's latest conversation. The only hits are the "pass a conversationId once you have one to resume" line, type signatures, and the hooks 'created'/'resumed' reason names.
5. `git diff --stat ec9fc65..HEAD -- docs` shows every one of these pages as newly added on this branch.

### py-examples#0 — 29 example READMEs link to DOCUMENTATION_REMEDIATION_STATUS.md, which does not exist
**major** · broken-link · `examples/README.md:234` · **must fix**

The branch added a 'Historical verification report' preamble to every example README footer, plus one troubleshooting entry. Each one sends readers to 'current source and artifact evidence' at a relative path to DOCUMENTATION_REMEDIATION_STATUS.md at the repo root. No such file exists at HEAD, anywhere in the working tree, or anywhere in git history. Every one of these links 404s on GitHub, and the one place that offers 'current evidence' leads nowhere.

**Evidence.** examples/README.md:234 "See the [current source and artifact evidence](../DOCUMENTATION_REMEDIATION_STATUS.md) before selecting an SDK artifact." Same link at examples/audit-trail/README.md:103, examples/microsoft_agent_retail_assistant/README.md:369 and :412, and 26 more (`git grep -n DOCUMENTATION_REMEDIATION_STATUS HEAD -- examples` lists 29 hits). `ls DOCUMENTATION_REMEDIATION_STATUS.md` gives 'No such file or directory'. `find . -name 'DOCUMENTATION_REMEDIATION*'` finds nothing. `git log --all -- DOCUMENTATION_REMEDIATION_STATUS.md` is empty. `git grep` at ec9fc65 has 0 references, so the branch introduced every link.

**Fix.** Either commit the referenced status document at the repo root, or drop the sentence and link from all 29 READMEs (and point instead at a real page, such as the docs site's SDK pages or CHANGELOG.md).

**Independent reproduction.** From the repo root:
1. `git grep -n DOCUMENTATION_REMEDIATION_STATUS HEAD -- examples | wc -l` gives 29.
2. `git grep -ho '([^)]*DOCUMENTATION_REMEDIATION_STATUS.md)' HEAD -- examples | sort | uniq -c` gives 1x ../, 21x ../../, 5x ../../../ and 2x ../../../../. Every one resolves to the repo root.
3. A loop resolved each link from its README's directory and ran `[ -e "$d/$l" ]` on it. All 29 print MISSING, for example "MISSING examples/README.md -> examples/../DOCUMENTATION_REMEDIATION_STATUS.md" and "MISSING examples/financial-services-advisor/aws-financial-services-advisor/frontend/README.md -> .../frontend/../../../../DOCUMENTATION_REMEDIATION_STATUS.md". No link resolves.
4. `ls DOCUMENTATION_REMEDIATION_STATUS.md` fails with "No such file or directory".
5. `find . -name 'DOCUMENTATION_REMEDIATION*'` finds nothing.
6. `git log --all --oneline -- DOCUMENTATION_REMEDIATION_STATUS.md '**/DOCUMENTATION_REMEDIATION_STATUS.md'` and `git log --all --diff-filter=A -- '*DOCUMENTATION_REMEDIATION*'` both return nothing.
7. `git grep -c DOCUMENTATION_REMEDIATION_STATUS ec9fc65 | wc -l` gives 0, so the branch introduced all of them.
8. Outside examples/, the only hits are docs/audit-evidence/2026-09-13/readme-sweep.md:25 and validation.md:3. validation.md links to ../../../DOCUMENTATION_REMEDIATION_STATUS.md, which is also missing.

Also reported as: x-security#1 (`examples/lennys-memory/README.md:1321`), x-consistency#3 (`examples/README.md:234`), gap2-gap2-install-commands-sweep#3 (`examples/README.md:234`)

### py-examples#1 — make example-no-llm / example-eval-harness / examples now crash with KeyError on a clean checkout
**major** · correctness · `examples/no_llm/main.py:126` · **must fix**

Both scripts dropped their local defaults and now read NEO4J_URI and NEO4J_USERNAME with os.environ[...]. The Makefile was not updated. When NEO4J_URI is unset (no examples/.env), run_example starts the Docker Neo4j and passes only NEO4J_PASSWORD=test-password, so the script raises KeyError: 'NEO4J_URI' after Docker has started. Both targets are in RUNNABLE_EXAMPLES, so `make examples`, which CLAUDE.md calls key-free and auto-starting Docker, also fails. The same applies to examples/eval-harness/main.py:125-126.

**Evidence.** Makefile:573-576 `if [ -z "$$NEO4J_URI" ]; then ... $(MAKE) neo4j-start neo4j-wait-quiet; NEO4J_PASSWORD=test-password uv run python $(1) $(2);`. examples/no_llm/main.py:126-127 `uri=os.environ["NEO4J_URI"], username=os.environ["NEO4J_USERNAME"]`. examples/eval-harness/main.py:125-126 has the same lines. Makefile:694 and :699 list example-no-llm and example-eval-harness in RUNNABLE_EXAMPLES. Simulation: `env -u NEO4J_URI -u NEO4J_USERNAME NEO4J_PASSWORD=test-password uv run python -c '...load_env(); build_settings()'` prints `examples/no_llm/main.py KeyError 'NEO4J_URI'` and `examples/eval-harness/main.py KeyError 'NEO4J_URI'` (no examples/.env present).

**Fix.** In run_example's Docker branch, export NEO4J_URI=bolt://localhost:7687 and NEO4J_USERNAME=neo4j alongside NEO4J_PASSWORD. Alternatively, drop the Docker auto-start from these targets and fail early with a message pointing at examples/AURA_SETUP.md, then update CLAUDE.md to match.

**Independent reproduction.** From the repo root (`ls examples/.env` reports "No such file or directory"):

1) Run eval-harness end to end with the environment the Makefile's Docker branch provides:
   `env -u NEO4J_URI -u NEO4J_USERNAME -u NEO4J_DATABASE -u MEMORY_API_KEY NEO4J_PASSWORD=test-password uv run python examples/eval-harness/main.py`
   Output: a traceback ending `File ".../examples/eval-harness/main.py", line 125, in build_settings: uri=os.environ["NEO4J_URI"]` and `KeyError: 'NEO4J_URI'`.

2) Run no_llm/main.py the same way. It exits earlier in this venv because the local extraction stack is missing: "Local extraction stack is incomplete ... Missing: spaCy model, GLiNER". main() calls load_env() and then check_local_stack() before build_settings() (lines 148-151). So I ran the next step directly:
   `env -u NEO4J_URI -u NEO4J_USERNAME -u MEMORY_API_KEY NEO4J_PASSWORD=test-password uv run python -c 'import importlib.util; spec=importlib.util.spec_from_file_location("m","examples/no_llm/main.py"); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.load_env(); m.build_settings()'`
   Output: `KeyError 'NEO4J_URI'`. A user who has the extraction stack installed reaches this KeyError.

3) `git diff ec9fc65..HEAD -- examples/no_llm/main.py examples/eval-harness/main.py` shows `-uri=os.getenv("NEO4J_URI", "bolt://localhost:7687")` and `-username=os.getenv("NEO4J_USERNAME", "neo4j")` replaced by `+uri=os.environ["NEO4J_URI"]` and `+username=os.environ["NEO4J_USERNAME"]` in both files. The same diff for the Makefile shows no change to the run_example macro (Makefile:561-576), which still passes only `NEO4J_PASSWORD=test-password` in the Docker branch.

I did not run `make example-no-llm` with Docker: the project memory notes that ports are occupied here and that make neo4j-start fails. The KeyError happens before any connection attempt, so Docker availability does not change the outcome.

### py-lib#0 — Only live check of the rewritten get_active() is now skipped in every CI run
**major** · test-coverage · `tests/integration/nams/test_ontology.py:25` · **must fix**

The branch rewrites NamsOntology.get_active() so that validation_mode, revision and version_id come only from a `version` object in the GET /ontologies/active response. The second lookup through list()/get() is gone. At the same time the branch gates the whole live ontology module behind RUN_ISOLATED_ONTOLOGY_TESTS=1. Nothing in the repo sets that variable, so nams-integration.yml's consolidated `pytest tests/integration/nams/` run now skips these tests every night. The code being replaced says the service did NOT send version metadata: its comment reads 'GET /ontologies/active returns the schema body but no version metadata', and its unit test mocked the endpoint as {"ontology": DOC, "version": None}. If the service still answers that way, every Python caller now gets validation_mode, revision and version_id as None, and no test anywhere would catch it. I cannot observe the hosted service, so this is lost verification, not a proven regression.

**Evidence.** tests/integration/nams/test_ontology.py:25-31: `pytest.mark.skipif(os.environ.get("RUN_ISOLATED_ONTOLOGY_TESTS") != "1", ...)`. `grep -rn RUN_ISOLATED_ONTOLOGY_TESTS` matches only this file and typescript/test/e2e/ontology.test.ts; no .github/workflows file sets it. .github/workflows/nams-integration.yml:209 runs `uv run pytest tests/integration/nams/`. Old contract, `git show ec9fc65:src/neo4j_agent_memory/nams/ontology.py`: '``GET /ontologies/active`` returns the schema body but no version metadata, so we resolve the active ontology id ... and read its current version'. The old unit test mocked `respond(200, json={"ontology": DOC, "version": None})`. New code, src/neo4j_agent_memory/nams/ontology.py:409-411: `raw_version = payload.get("version"); if raw_version is None: return ActiveOntology(document=document)`.

**Fix.** Before releasing, confirm against the live service that /ontologies/active returns a populated `version`. Then either give the nightly workflow an isolated workspace and set RUN_ISOLATED_ONTOLOGY_TESTS=1 there, or add a non-mutating live check (call get_active() and assert version_id/validation_mode are populated) that is not gated.

**Independent reproduction.** 1. `MEMORY_API_KEY=dummy uv run pytest tests/integration/nams/test_ontology.py -rs -q` gives "5 skipped", each with the reason "Set RUN_ISOLATED_ONTOLOGY_TESTS=1 only for an exclusively owned test workspace" (lines 86, 96, 105, 118, 137).
2. `grep -rn RUN_ISOLATED_ONTOLOGY_TESTS . --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=audit-evidence` matches only tests/integration/nams/test_ontology.py:28-29 and typescript/test/e2e/ontology.test.ts:4,18. Nothing in .github/workflows sets it.
3. `sed -n 180,230p .github/workflows/nams-integration.yml` shows that the consolidated step runs `uv run pytest tests/integration/nams/`.
4. `git show ec9fc65:tests/integration/nams/test_ontology.py` shows that the old module had `pytestmark = pytest.mark.integration` and no skipif.
5. `git diff ec9fc65..HEAD -- src/neo4j_agent_memory/nams/ontology.py` shows the list()/get() lookup and _current_version removed, and the new `raw_version = payload.get("version"); if raw_version is None: return ActiveOntology(document=document)`.
6. `git show ec9fc65:tests/unit/nams/test_ontology.py` line 120 mocks `{"ontology": DOC, "version": None}`. `git show ec9fc65:typescript/src/ontology/index.ts` lines 410-411 say "the active response carries no version metadata".
7. `uv run pytest tests/unit/nams/test_ontology.py -q -k active` gives 24 passed. test_legacy_document_has_no_inferred_binding, parametrized with {"ontology": DOC, "version": None}, asserts that version_id, ontology_id and revision are all None.
8. `grep -rln get_active tests typescript/test` finds no other live caller. The docs, example and unit tests all use respx or mocks.

### ref-api-a#0 — get_facts_about described as matching subject or object; it matches subject only
**major** · behaviour-claim · `docs/modules/ROOT/pages/reference/api/long-term-preferences.adoc:169` · **must fix**

The new preferences/facts subpage says get_facts_about returns facts where the entity name is the subject or the object. The bolt implementation runs GET_FACTS_BY_SUBJECT, which filters only on f.subject. A reader who relies on the documented behaviour will miss every fact where the entity is the object. The parameter table on the same page (line 180, '`subject` | The fact subject') also disagrees with the prose.

**Evidence.** docs/modules/ROOT/pages/reference/api/long-term-preferences.adoc:169 "Return facts where the entity name occurs as the subject or object." vs src/neo4j_agent_memory/memory/long_term.py:2133-2153 (get_facts_about runs queries.GET_FACTS_BY_SUBJECT with {"subject": subject}) and src/neo4j_agent_memory/graph/queries.py:374-376 "MATCH (f:Fact) WHERE f.subject = $subject"

**Fix.** Change the sentence to: "Return facts whose subject exactly equals `subject`. Facts where the name appears as the object are not returned. There is no `get_facts` wrapper."

**Independent reproduction.** 1) sed -n 160,190p docs/modules/ROOT/pages/reference/api/long-term-preferences.adoc
   -> line 169: "Return facts where the entity name occurs as the subject or object. There is no `get_facts` wrapper."
   -> table: "| `subject` | The fact subject"

2) git show ec9fc65:docs/modules/ROOT/pages/reference/api/long-term-preferences.adoc
   -> "fatal: path ... exists on disk, but not in 'ec9fc65'" (the page is new on this branch)

3) Scratch script scratchpad/review/facts.py:
   - It builds LongTermMemory(client=MagicMock with execute_read=AsyncMock([]), embedder=None).
   - It awaits get_facts_about("Alice").
   - It prints the query and parameters from execute_read.call_args.
   Command: uv run python scratchpad/review/facts.py
   Output:
     MATCH (f:Fact)
     WHERE f.subject = $subject
     RETURN f
     ORDER BY f.confidence DESC, f.created_at DESC
     LIMIT $limit
     {'subject': 'Alice', 'limit': 100}

4) core/protocols.py:404-411 docstring: "Return facts where the given entity is the subject."
   nams/long_term.py:563-567: get_facts_about raises NotSupportedError("NAMS does not expose a facts endpoint.")

5) grep -rn "subject or object" docs/modules/ROOT/pages src/
   -> only long-term-preferences.adoc:169

### ref-api-b#0 — clear_session is documented as deleting a session's traces, but the SDK never creates the link it follows
**major** · behavior-claim · `docs/modules/ROOT/pages/reference/api/short-term-sessions.adoc:44` · **must fix**

Two pages say clearing a bolt session deletes the session's reasoning traces, steps and tool calls through `(Conversation)-[:HAS_TRACE]->(ReasoningTrace)`. No SDK code path writes that relationship. `start_trace` only CREATEs the trace node, plus an optional INITIATED_BY link to a message and a `(:User)-[:HAS_TRACE]` link. `LINK_CONVERSATION_TO_TRACE` is defined in queries.py but nothing uses it. So `DELETE_SESSION_DATA` never matches a trace, and `clear_session` leaves every trace, step and tool call for the session in the database. A reader who relies on `clear_session` to erase a session's data (for example, for privacy) keeps all of its reasoning data. how-to/messages.adoc:78 sends readers to this page as the contract to check before deleting.

**Evidence.** short-term-sessions.adoc:44: "Delete the matching conversation, its linked messages, and any traces, steps, and tool calls connected through its `:HAS_TRACE` relationships." reasoning-traces.adoc:152: "Clearing a bolt session deletes traces connected through its conversation's `:HAS_TRACE` relationship." Source: src/neo4j_agent_memory/graph/queries.py:482-495 CREATE_REASONING_TRACE creates only the node. queries.py:727-733 DELETE_SESSION_DATA uses `OPTIONAL MATCH (c)-[:HAS_TRACE]->(rt:ReasoningTrace)`. `grep -rn "LINK_CONVERSATION_TO_TRACE" src/` finds only its definition (queries.py:660). `grep -rn HAS_TRACE src/` finds only the User link (reasoning.py:507) and these two queries.

**Fix.** State that `clear_session` deletes the conversation and its messages but does not delete traces that `start_trace` created, because the SDK does not link conversations to traces. Say how to remove them instead, for example a Cypher delete on `ReasoningTrace {session_id: ...}` and its steps and tool calls. Alternatively, fix the SDK to link conversations to traces and document the fixed behaviour. Update reasoning-traces.adoc:152 to match.

**Independent reproduction.** I didn't run a live Neo4j test. The checks were a grep and a line-by-line trace of the code path.
1. `grep -rn "HAS_TRACE\|LINK_CONVERSATION_TO_TRACE\|DELETE_SESSION_DATA" src/` found:
   - users.py:13 and reasoning.py:448 (docstrings)
   - reasoning.py:507 `MERGE (u)-[:HAS_TRACE]->(rt)` (User link only)
   - queries.py:660/663 (the `LINK_CONVERSATION_TO_TRACE` definition only, with no callers)
   - queries.py:727/730 (`DELETE_SESSION_DATA`)
   - short_term.py:1009 (its only caller, `clear_session`)
2. `sed -n 480,500p queries.py`: `CREATE_REASONING_TRACE` is `CREATE (rt:ReasoningTrace {id, session_id, ...}) RETURN rt`, with no Conversation link.
3. `sed -n 720,740p queries.py`: `DELETE_SESSION_DATA` does `MATCH (c:Conversation {session_id})`, then `OPTIONAL MATCH (c)-[:HAS_TRACE]->(rt)`, then `DETACH DELETE c, m, rt, rs, tc`. Traces are reached only through the missing link.
4. `sed -n 50,62p examples/full-stack-chat-agent/backend/src/api/routes/threads.py`: the comment confirms the gap, and the example adds its own `DELETE_SESSION_TRACES` that matches `ReasoningTrace {session_id}`.
5. `git diff ec9fc65..HEAD --stat` on the two reference pages shows both are new files on this branch (+198 and +159 lines). The claims are at short-term-sessions.adoc:44 and reasoning-traces.adoc:152.

### ref-config#0 — conversation_ttl_days row names a nonexistent `older_than_days` argument (actual: `ttl_days`)
**major** · api-mismatch · `docs/modules/ROOT/pages/reference/configuration-operations.adoc:33` · **must fix**

The MemoryConfig table tells readers to pass the TTL to `archive_expired_conversations()` via `older_than_days`. The method has no such parameter; its keyword-only argument is `ttl_days`. A reader who follows the row gets a TypeError. The page also contradicts how-to/consolidation.adoc and how-to/privacy-and-audit.adoc, which both use `ttl_days=`.

**Evidence.** configuration-operations.adoc:33: "pass it explicitly to `archive_expired_conversations()` via `older_than_days`. †"
Source: src/neo4j_agent_memory/memory/consolidation.py:319-324 `async def archive_expired_conversations(self, *, ttl_days: int | None = None, dry_run: bool = True)`; line 332-336 raises ValueError asking for `ttl_days`.
`uv run python -c "...inspect.signature(ConsolidationMemory.archive_expired_conversations)"` -> `(self, *, ttl_days: 'int | None' = None, dry_run: 'bool' = True)`
how-to/privacy-and-audit.adoc:59 `ttl_days=settings.memory.conversation_ttl_days,`

**Fix.** Replace `via `older_than_days`` with `as `ttl_days=`` (for example `archive_expired_conversations(ttl_days=settings.memory.conversation_ttl_days)`).

**Independent reproduction.** 1) `uv run python -c "import inspect; from neo4j_agent_memory.memory.consolidation import ConsolidationMemory as C; print(inspect.signature(C.archive_expired_conversations))"` printed `(self, *, ttl_days: 'int | None' = None, dry_run: 'bool' = True) -> 'ConsolidationReport'`.
2) Calling it the way the docs say, `asyncio.run(C.__new__(C).archive_expired_conversations(older_than_days=30))`, printed `TypeError: ConsolidationMemory.archive_expired_conversations() got an unexpected keyword argument 'older_than_days'`.
3) `git show ec9fc65:docs/modules/ROOT/pages/reference/configuration-operations.adoc` printed `fatal: path ... exists on disk, but not in 'ec9fc65'`, so the page is new on this branch.
4) `grep -rn older_than_days src docs/modules` found only two lines: configuration-operations.adoc:33 and environment-variables.adoc:226. The ec9fc65 version of environment-variables.adoc has no match, so the branch added that line as well.
5) `grep -rn "ttl_days=" docs/modules/ROOT/pages` found how-to/privacy-and-audit.adoc:59 (`ttl_days=settings.memory.conversation_ttl_days,`) and how-to/consolidation.adoc:57 (`ttl_days=90, dry_run=True`); both match the source.

### ref-config#1 — audit_read row points to nonexistent `consolidation.audit_reads(...)`; the method is `record_read_audit`
**major** · api-mismatch · `docs/modules/ROOT/pages/reference/configuration-operations.adoc:34` · **must fix**

The row tells readers to call `consolidation.audit_reads(...)`. ConsolidationMemory has no such method; the read-audit API is `record_read_audit(query, *, user_identifier=None, kind='memory.read', result_count=None, metadata=None)`. The doc repeats a stale docstring in settings.py:382. The page also contradicts how-to/privacy-and-audit.adoc:29 and explanation/operational-primitives.adoc:70, which use `record_read_audit`.

**Evidence.** configuration-operations.adoc:34: "call consolidation.audit_reads(...) explicitly. †"
Dumping ConsolidationMemory's public methods lists archive_expired_conversations, dedupe_entities, detect_superseded_preferences, record_read_audit, summarize_long_traces. There is no audit_reads.
how-to/privacy-and-audit.adoc:29 `audit_id = await client.consolidation.record_read_audit(`

**Fix.** Change to `call `client.consolidation.record_read_audit(...)` explicitly`. Also fix the stale `audit_reads` in the Field description at src/neo4j_agent_memory/config/settings.py:382.

**Independent reproduction.** uv run python -c "from neo4j_agent_memory.memory.consolidation import ConsolidationMemory as C; print([m for m in dir(C) if not m.startswith('_')]); print(hasattr(C,'audit_reads'))"
-> ['archive_expired_conversations', 'dedupe_entities', 'detect_superseded_preferences', 'record_read_audit', 'summarize_long_traces']
-> False

grep -rn "audit_reads\|record_read_audit" src docs/modules (attachments excluded)
-> consolidation.py:385 def record_read_audit
-> settings.py:382 "When True, ``client.consolidation.audit_reads(...)`` records a "
-> configuration-operations.adoc:34 "call consolidation.audit_reads(...) explicitly"
-> environment-variables.adoc:227 "Audit preference for `consolidation.audit_reads(...)`"
-> privacy-and-audit.adoc:29 and operational-primitives.adoc:70/79/113 use record_read_audit

git show ec9fc65:docs/modules/ROOT/pages/reference/configuration-operations.adoc -> fatal: exists on disk, but not in 'ec9fc65' (the page is new on this branch)
git show ec9fc65:docs/modules/ROOT/pages/reference/environment-variables.adoc | grep AUDIT_READ -> no output (the row is new)
git show ec9fc65:src/neo4j_agent_memory/config/settings.py | grep audit_reads -> 382 (the stale docstring predates the branch)

### ref-config#2 — NAM_MEMORY__CONVERSATION_TTL_DAYS / AUDIT_READ rows repeat the wrong `older_than_days` and `audit_reads` names
**major** · api-mismatch · `docs/modules/ROOT/pages/reference/environment-variables.adoc:226` · **must fix**

The env-var table repeats both wrong API names from the operations page: `archive_expired_conversations(older_than_days=...)` at line 226 and `consolidation.audit_reads(...)` at line 227. The real names are `ttl_days` and `record_read_audit`.

**Evidence.** environment-variables.adoc:226: "TTL value for `archive_expired_conversations(older_than_days=...)` — not automatically applied"
environment-variables.adoc:227: "Audit preference for `consolidation.audit_reads(...)` — not automatically applied"
Source: src/neo4j_agent_memory/memory/consolidation.py:319-324 (`ttl_days`). ConsolidationMemory exposes `record_read_audit`, not `audit_reads`.

**Fix.** Use `archive_expired_conversations(ttl_days=...)` and `consolidation.record_read_audit(...)`.

**Independent reproduction.** sed -n 226,227p docs/modules/ROOT/pages/reference/environment-variables.adoc
  -> "TTL value for `archive_expired_conversations(older_than_days=...)`" / "Audit preference for `consolidation.audit_reads(...)`"
uv run python -c "import inspect; from neo4j_agent_memory.memory.consolidation import ConsolidationMemory as C; print(inspect.signature(C.archive_expired_conversations)); print([n for n in dir(C) if not n.startswith('_')])"
  -> (self, *, ttl_days: 'int | None' = None, dry_run: 'bool' = True) -> 'ConsolidationReport'
  -> ['archive_expired_conversations', 'dedupe_entities', 'detect_superseded_preferences', 'record_read_audit', 'summarize_long_traces']
uv run python -c "...asyncio.run(C.__new__(C).archive_expired_conversations(older_than_days=30)); print(hasattr(C,'audit_reads'))"
  -> TypeError: ConsolidationMemory.archive_expired_conversations() got an unexpected keyword argument 'older_than_days'
  -> False
git show ec9fc65:docs/modules/ROOT/pages/reference/environment-variables.adoc | grep -n NAM_MEMORY
  -> (no output: the branch added these rows)
grep -rn "older_than_days\|audit_reads" docs/modules/ROOT/pages
  -> configuration-operations.adoc:33,34 and environment-variables.adoc:226,227
grep -n audit_reads src/neo4j_agent_memory/config/settings.py
  -> 382 (stale source docstring the branch did not change; likely where the wrong name came from)

### ref-extract-schema#0 — DEFAULT_GLIREL_MODEL documented as jackboyla/glirel_base; the source default is jackboyla/glirel-large-v0
**major** · api-accuracy · `docs/modules/ROOT/pages/reference/extractor-relations.adoc:175` · **must fix**

The page gives the wrong default model for GLiRELExtractor, GLiNERWithRelationsExtractor.for_schema and GLiNERWithRelationsExtractor.for_poleo. A reader who sizes downloads or hardware, or who pins the model on the strength of this line, gets a different (large) model from the one they expect. No other docs page states the default, so this one is the only source and it is wrong.

**Evidence.** docs/modules/ROOT/pages/reference/extractor-relations.adoc:175: "`DEFAULT_GLIREL_MODEL` is `jackboyla/glirel_base`."  Source of truth: src/neo4j_agent_memory/extraction/gliner_extractor.py:827: `DEFAULT_GLIREL_MODEL = "jackboyla/glirel-large-v0"` (the same value at ec9fc65; the source is unchanged on this branch).

**Fix.** Change the sentence to: `DEFAULT_GLIREL_MODEL` is `jackboyla/glirel-large-v0`.

**Independent reproduction.** From /Users/lyonwj/github/neo4j-labs/agent-memory:
1) sed -n 175p docs/modules/ROOT/pages/reference/extractor-relations.adoc -> "`DEFAULT_GLIREL_MODEL` is `jackboyla/glirel_base`. Model output varies; ..."
2) uv run python -c "from neo4j_agent_memory.extraction.gliner_extractor import DEFAULT_GLIREL_MODEL as d; print(d)" -> jackboyla/glirel-large-v0
3) grep -rn "DEFAULT_GLIREL_MODEL" src -> gliner_extractor.py:827 DEFAULT_GLIREL_MODEL = "jackboyla/glirel-large-v0"; used as the default at lines 863, 903, 1096, 1191, 1232
4) git diff ec9fc65..HEAD --stat -- docs/modules/ROOT/pages/reference/extractor-relations.adoc -> 182 insertions(+) (a new file on this branch)
5) git show ec9fc65:docs/modules/ROOT/pages/reference/extractors.adoc | grep -n glirel_base -> 362: model: str = "jackboyla/glirel_base", (the wrong value was already on main and the branch repeats it)

Also reported as: gap1-bolt-programs-live#7 (`docs/modules/ROOT/pages/reference/extractor-relations.adoc:175`)

### ref-other#0 — Embedded Python SDK credentials named as NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD; MemorySettings ignores them
**major** · wrong-config-claim · `docs/modules/ROOT/pages/reference/deploy-an-application.adoc:26` · **must fix**

The embedded-SDK option lists `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD` as its credentials. `MemorySettings` uses `env_prefix="NAM_"` with `__` nesting, so it reads `NAM_NEO4J__URI` / `NAM_NEO4J__USERNAME` / `NAM_NEO4J__PASSWORD`. A reader who sets the documented variables in a deployment and constructs `MemorySettings()` connects to bolt://localhost:7687 with an empty password. The deployment page this branch replaced had a correct 'Application environment variables' table (`NAM_NEO4J__URI` etc.), so the branch introduced the regression. It also contradicts the environment-variables reference.

**Evidence.** Offending text, deploy-an-application.adoc:26: "Credentials:: `NEO4J_URI` / `NEO4J_USERNAME` / `NEO4J_PASSWORD`, plus embedding/LLM provider credentials...". Source of truth: src/neo4j_agent_memory/config/settings.py:629 `env_prefix="NAM_"`, env_nested_delimiter="__". The command `env -i ... NEO4J_URI=bolt://example:7687 NEO4J_USERNAME=bob NEO4J_PASSWORD=pw .venv/bin/python -c "from neo4j_agent_memory import MemorySettings; s=MemorySettings(); print(s.neo4j.uri, s.neo4j.username, repr(s.neo4j.password.get_secret_value()))"` prints `bolt://localhost:7687 neo4j ''`. With `NAM_NEO4J__URI=bolt://example:7687 NAM_NEO4J__PASSWORD=pw` it prints `bolt://example:7687 neo4j 'pw'`. environment-variables.adoc:310: "The Python settings family instead uses NAM_NEO4J__... and USERNAME." The old page (git show ec9fc65:docs/modules/ROOT/pages/reference/deployment.adoc) listed `NAM_NEO4J__URI`, `NAM_NEO4J__USERNAME`, `NAM_NEO4J__PASSWORD` under 'Application Environment Variables'.

**Fix.** State `NAM_NEO4J__URI` / `NAM_NEO4J__USERNAME` / `NAM_NEO4J__PASSWORD`, which `MemorySettings` reads. Alternatively, say the application must read `NEO4J_*` itself and pass the values into `MemorySettings(neo4j=...)`, and link reference/environment-variables.adoc.

**Independent reproduction.** I ran these from /private/tmp with the repo venv's python:
1) env -i PATH=/usr/bin:/bin HOME=$HOME NEO4J_URI=bolt://example:7687 NEO4J_USERNAME=bob NEO4J_PASSWORD=pw .venv/bin/python -c "from neo4j_agent_memory import MemorySettings; s=MemorySettings(); print(s.neo4j.uri, s.neo4j.username, repr(s.neo4j.password.get_secret_value()))"
   -> bolt://localhost:7687 neo4j ''
2) The same command with NAM_NEO4J__URI=bolt://example:7687 NAM_NEO4J__USERNAME=bob NAM_NEO4J__PASSWORD=pw
   -> bolt://example:7687 bob 'pw'
3) grep -n "NEO4J_URI|validation_alias|AliasChoices" src/neo4j_agent_memory/config/settings.py found only the comment at lines 636-637, which says plain NEO4J_URI keys are filtered out. There is no alias.
4) git show ec9fc65:docs/modules/ROOT/pages/reference/deploy-an-application.adoc -> "exists on disk, but not in 'ec9fc65'" (new page). git log shows it was added by c90d191 and d3db0ff on this branch.
5) git show ec9fc65:docs/modules/ROOT/pages/reference/deployment.adoc | grep NAM_NEO4J -> lines 173, 177 and 181 list NAM_NEO4J__URI, NAM_NEO4J__USERNAME and NAM_NEO4J__PASSWORD.
6) environment-variables.adoc:309: "The Python settings family instead uses NAM_NEO4J__... and USERNAME."

Also reported as: x-style#6 (`docs/modules/ROOT/pages/reference/deploy-an-application.adoc:26`)

### ref-other#1 — Active-binding caveat covers Python 0.6.0 only; released TS 0.5.0 has the same latest-revision bug
**major** · released-behavior · `docs/modules/ROOT/pages/reference/ontology-api.adoc:91` · **must fix**

The new 'Python 0.6.0 active binding' section warns that Python's `get_active()` can report the latest revision when an older one is active. It then says 'Current TypeScript source exposes versionId, revision and validationMode from the authoritative response'. The released npm package `@neo4j-labs/agent-memory@0.5.0`, which MAINTAINING.md tells application instructions to pin, still uses the old composed lookup: `list()` then `currentVersion(...)`, which picks the latest revision. The authoritative-version code exists only in this branch's unreleased typescript/src change. A TS 0.5.0 user reading this page would trust `getActive().versionId` / `validationMode` for a rollback target, which is exactly the hazard the page warns Python users about. The disclaimer 'this is not a statement that a corresponding npm release is available' does not say that 0.5.0 is affected.

**Evidence.** ontology-api.adoc:91-96: "Current TypeScript source exposes `versionId`, `revision` and `validationMode` from the authoritative response... this is not a statement that a corresponding npm release is available." The command `git show typescript-v0.5.0:typescript/src/ontology/index.ts` shows, at lines 410-424: "// Compose version metadata via a second lookup ... const summaries = await this.list(); ... const current = currentVersion(detail, match.currentRevision)". `git diff ec9fc65..HEAD -- typescript/src/ontology/index.ts` shows this branch replacing that code with `raw.version` parsing. The typescript/CHANGELOG.md [Unreleased] section is empty. docs/MAINTAINING.md: "Application instructions install the verified npm releases (`@neo4j-labs/agent-memory@0.5.0`...)" and "Python 0.6.0 still has the older active-ontology metadata inference" (TS 0.5.0 is not mentioned).

**Fix.** Extend the caveat to cover `@neo4j-labs/agent-memory` 0.5.0 (`getActive()` metadata can report the latest revision) and point TS readers to the same direct `GET /ontologies/active` read until a release ships the fix. Also add an [Unreleased] CHANGELOG entry for the source change.

**Independent reproduction.** 1. Put the tagged TS source in the scratch dir: `git archive typescript-v0.5.0 typescript/src | tar -x -C $S/ts050`.
2. Wrote $S/active-check.mts. It builds `new OntologyClient(mockTransport)`. The mock returns `{ontology: doc, version: v1}` for `get_active_ontology`, `{ontologies:[{id:'ont-1', is_active:true, current_revision: 2|undefined}]}` for `list_ontologies`, and `{record, versions:[v1(rev1, strict), v2(rev2, permissive)]}` for `get_ontology`.
3. Ran it from typescript/ with `./node_modules/.bin/tsx $S/active-check.mts <path to ontology/index.ts>`. Output:
   0.5.0 current_revision= 2 -> versionId ver-2 revision 2 mode permissive
   0.5.0 current_revision= undefined -> versionId ver-2 revision 2 mode permissive
   HEAD  current_revision= 2 -> versionId ver-1 revision 1 mode strict
   HEAD  current_revision= undefined -> versionId ver-1 revision 1 mode strict
4. `git show python-v0.6.0:src/neo4j_agent_memory/nams/ontology.py` (lines 391-405, and `_current_version` at 557-564) uses the same algorithm as the 0.5.0 TS code: typescript/src/ontology/index.ts lines 410-424 and `currentVersion` at 535-542.
5. The example node_modules link `@neo4j-labs/agent-memory` back to the local checkout, so the published npm tarball was not available locally. The tagged source was used in its place.
6. `sed -n '/Unreleased/,/^## \[0/p' typescript/CHANGELOG.md` shows an empty `[Unreleased]` section.
7. `grep` shows reference/typescript-api.adoc:440-441 still saying 'composed `validationMode` / `revision` / `versionId`' with no caveat. MAINTAINING.md:85 mentions only Python 0.6.0.

### tooling-ci#1 — make docs-lint skips all rendered-layout checks after the documented setup; the skip hint names the wrong install
**major** · tooling · `Makefile:469` · **must fix**

The docs-lint comment says the Playwright checks for inline TOC, undersized images, mobile overflow, heading case and scaffolding headings "fail this target". But tests/docs/test_rendered_site.py skips the whole module when docs/diagrams/node_modules/playwright is missing. The documented setup (`make docs-install && make docs && make docs-lint`, MAINTAINING.md:9-13) never installs that optional toolchain, because docs-install only runs `cd docs && npm ci`. So on a standard setup these checks report 'skipped' and docs-lint passes. The skip reason and MAINTAINING.md:45 both tell the reader to run `make docs-install`, which does not install Playwright. MAINTAINING.md:15 also says docs-lint "builds once into a fresh temporary directory", but the target now builds twice: docs-render-check depends on `docs` (docs/build/site) and then `npm run lint` builds again into a temp directory.

**Evidence.** Makefile:469-473 `# ... so inline TOC, undersized images ... fail this target` / `docs-lint: docs-render-check`. Makefile:451-454 `docs-install: ... cd docs && npm ci`. docs/package.json devDependencies has only @antora/cli, @antora/site-generator and http-server, with no Playwright. tests/docs/test_rendered_site.py:64-65 `if not (project_root / "docs/diagrams/node_modules/playwright").is_dir(): pytest.skip("... run `make docs-install`")`. Playwright is declared only in docs/diagrams/package.json, which says it is 'Optional ... not required for the Antora build'.

**Fix.** Choose one: (a) make docs-render-check fail rather than skip when Playwright is missing, and add a target that runs `npm ci --prefix docs/diagrams && npx --prefix docs/diagrams playwright install chromium`; or (b) keep the skip but remove the 'fail this target' claim. In either case, point the skip message and MAINTAINING.md:45 at the real install command, and correct 'builds once' in MAINTAINING.md:15.

**Independent reproduction.** 1) I copied tests/docs/test_rendered_site.py into the scratch dir (…/scratchpad/review/tooling-ci1/) with a conftest.py whose project_root fixture points at a fake root. That root has docs/build/site/agent-memory, as after `make docs`, but no docs/diagrams/node_modules/playwright, as after `make docs-install`. I ran `uv run pytest <copy> -rs -q`. Output: "SKIPPED [1] ...:83: Playwright not installed under docs/diagrams; run `make docs-install`", the same skip for the tests at lines 94, 109, 118, 131, 147 and 157, then "7 skipped, 1 warning". No test failed, so pytest reports success.
2) `grep -c playwright docs/package-lock.json` printed 0. Playwright is only in docs/diagrams/package.json, and `git check-ignore` shows docs/diagrams/node_modules/ is ignored at .gitignore:103. Grepping the Makefile for an npm install under docs/diagrams found nothing.
3) `make -n docs-lint` printed "cd docs && npm run build", then "uv run pytest tests/docs/test_rendered_site.py -v --timeout=300", then "cd docs && npm run lint". check_docs.py:271-275 then calls build_site() into a tempfile.TemporaryDirectory when --build is passed, so there are two builds, not one.
4) `git diff ec9fc65..HEAD -- Makefile` shows this branch added docs-lint, docs-render-check and the "fail this target" comment. test_rendered_site.py, render_docs.mjs and MAINTAINING.md are all new on this branch.

Also reported as: docs-tests-b#1 (`tests/docs/test_rendered_site.py:64`), entry#2 (`docs/MAINTAINING.md:44`)

### tooling-ci#0 — Keyboard users can't reach the new tutorial copy button: its container stays display:none unless hovered
**major** · accessibility · `docs/ui/css/tutorial-code.css:2` · **must fix**

tutorial-code.js swaps the upstream span for a native <button> inside `.code-inset`, and the CSS adds a :focus-visible outline to it. But the shared UI hides `.doc .listingblock .code-inset` with display:none and shows it only on `.listingblock:hover`. A display:none element is not focusable, so the button never gets keyboard focus and the focus-visible rule never applies. The claim in MAINTAINING.md ("make existing copy actions native buttons ... keyboard-focusable, with visible focus") is false for the button. Only the <pre> regions became reachable.

**Evidence.** Built site (antora --to-dir scratch), shared UI site.css: `.doc .listingblock .code-inset{display:none}` and `.doc .listingblock:hover .code-inset{display:block}`. Headless Chromium on tutorials/first-agent-memory.html: button computed display inline-block but parent `DIV.code-inset:none`, bounding rect 0x0. With the first <pre> focused, code-inset display is `none`. Pressing Tab moves focus to the next `PRE ... code block 2 source` and skips the button. Playwright click fails with 'Element is not visible' until the listing is hovered. docs/ui/css/tutorial-code.css:2 `body.code-nocollapse .doc .listingblock .code-inset button.btn-copy:focus-visible` has no effect. docs/MAINTAINING.md:107 claims the assets make copy actions keyboard-focusable.

**Fix.** In tutorial-code.css, add `body.code-nocollapse .doc .listingblock:focus-within .code-inset { display: block; }`. Then check with Tab that focus moves from each <pre> to its copy button.

**Independent reproduction.** Scripts are under scratchpad/review/ (kb.cjs, kb2.cjs, kb3.cjs), run with the Playwright copy in docs/diagrams/node_modules, from docs/diagrams.

1. `diff docs/ui/css/tutorial-code.css docs/build/site/_/css/tutorial-code.css && diff docs/ui/js/tutorial-code.js docs/build/site/_/js/tutorial-code.js` gives `same`, so the built site matches HEAD.
2. `grep -o '[^}]*code-inset[^}]*}' docs/build/site/_/css/site.css` gives `.doc .listingblock .code-inset{display:none}` and `.doc .listingblock:hover .code-inset{display:block}`. The code-nocollapse and focus-within greps return nothing relevant.
3. kb.cjs on file://.../docs/build/site/agent-memory/tutorials/first-agent-memory.html gives `{"tag":"BUTTON","disp":"inline-block","parentDisp":"none","rect":[0,0],"nButtons":17}`. The Tab sequence from the first pre is `["PRE code block 2 source","CODE language-bash hljs","SUMMARY title","SUMMARY title","PRE core_memory_settings.py source","PRE first_agent_memory.py source"]`, and `programmatic focus succeeds: false`.
4. kb2.cjs gives `HEAD copy-button focus hits in 300 tabs: 0`. With the suggested `.listingblock:focus-within .code-inset{display:block}` injected, it also gives 0.
5. kb3.cjs shows the DOM order `<div class="code-header"><div class="code-inset"><button ... aria-label="Copy code: code block 1">...</div></div><pre tabindex="0" role="region">`. With the fix injected, Shift+Tab from the pre gives `BUTTON Copy code: code block 1`, which confirms the suggested fix covers only reverse tabbing.

### tooling-ci#2 — Documented `export_diagrams.mjs --all` writes 23 untracked PNGs that check_manifest rejects as orphans
**major** · tooling · `scripts/export_diagrams.mjs:78` · **must fix**

The exporter always writes a PNG next to each SVG. The manifest tracks 30 SVG exports, and 23 of them have no tracked PNG (poleo-model, message-chain, tutorial-routes and others). check_manifest() reports any file in images/diagrams that is in neither the manifest nor a page reference as an 'Orphaned file'. Following the Makefile's docs-diagrams-generate step 4 (`node scripts/export_diagrams.mjs --all`) and the docs-excalidraw skill step 5 therefore leaves 23 orphan PNGs. docs-lint and CI's tests/docs/test_diagram_manifest.py then fail until the maintainer deletes them by hand. This also conflicts with MAINTAINING.md:103, which says diagram exports are SVG.

**Evidence.** export_diagrams.mjs:77-78 writes `output` (.svg) and `output.replace(/\.svg$/, '.png')`. Manifest analysis: Counter({('svg', True): 30, ('png', False): 8, ('png', True): 7}), with 23 SVG records whose .png is not tracked. Simulation on a copy of the docs tree: check_manifest before = [], after adding images/diagrams/poleo-model.png = ['Orphaned file (in neither the manifest nor a page reference): docs/modules/ROOT/images/diagrams/poleo-model.png']. Makefile:525 `4. Export: node scripts/export_diagrams.mjs --all`.

**Fix.** Write the PNG only when the manifest tracks one for that output, or behind a `--png` flag. Alternatively, have `--all` write only the outputs listed in the manifest.

**Independent reproduction.** 1. `git show ec9fc65:scripts/export_diagrams.mjs` exits 128, so the script is new on this branch.
2. `sed -n 1,140p scripts/export_diagrams.mjs`: lines 77-78 write `output` and then `output.replace(/\.svg$/, '.png')`; lines 20-23 build the `--all` jobs from every manifest record that has a `source`.
3. I copied docs/ to the scratch dir /private/tmp/claude-502/-Users-lyonwj-github-neo4j-labs-agent-memory/66a2977c-9670-4b56-8270-fc84ea0f1100/scratchpad/review/tc2. Then I ran `uv run python` with a script that imports scripts/manage_diagrams and calls check_manifest(copy). Before: `[]`. The script built the 37 jobs, touched each missing .svg and .png target, and called check_manifest again. Output: "new files written by --all: 25", "orphans: 25". The first orphans were `docs/modules/ROOT/images/diagrams/architecture-overview.svg`, `bolt-vs-nams-data-flow.png`, `buffered-write-flow.png`, `context-tiers-funnel.png` and `embedding-based-similarity.png`. There were no other errors.
4. `git check-ignore -v docs/modules/ROOT/images/diagrams/poleo-model.png` returned rc=1, so the file is not ignored.
5. `grep` shows tests/docs/test_diagram_manifest.py:43 `assert not check_manifest(PROJECT_ROOT)["errors"]`, scripts/check_docs.py:267 imports check_manifest, and Makefile:525 echoes the `--all` step.

I did not run the real exporter, because it needs Playwright, esbuild and Excalidraw in docs/diagrams. The simulation reproduces its file writes exactly, as traced from lines 20-23 and 77-78.

Also reported as: x-diagrams#1 (`scripts/export_diagrams.mjs:78`)

### ts-ex-a#1 — Hooks-mode test passes even when the deny hook and the retry hook are disabled
**major** · test-coverage · `typescript/examples/nams-ai-provider/test/docs-pages.test.ts:233` · **must fix**

The test is titled "runs all eight lifecycle events", but it never checks that any hook fired except the redaction check. The deny and retry assertions only check text that the mock model returns unconditionally once any tool result is in the prompt. A denied call, an executed delete_account and an unretried tool error all produce a tool message, so the mock gives the same answer each time. The comments "delete_account was denied, never executed" and "survived the flaky_lookup retry" describe checks the test does not make.

**Evidence.** docs-pages.test.ts:218-222 has the mock return `textResult("Graph databases are well documented.")` / `"I can't do that -- account deletion is disabled in this demo."` whenever steps>0, and :232-233 assert `answers[1]).toContain("documented")` and `answers[2]).toContain("disabled")`. Mutation run: copied src/hooks-mode.ts to the scratchpad, changed `permissionDecision: 'deny'` to `'allow'` and `attempt === 1` to `attempt === 99`, and ran the unmodified test (`npx vitest run -t "hooks mode"`). Result: `Tests 1 passed | 7 skipped`.

**Fix.** Assert on observable effects. Count delete_account executions (for example with a spy) and check that the tool result in the step-1 prompt is the `{ blocked: true, ... }` object. Assert that flaky_lookup ran twice and that the step-1 prompt holds a successful tool result. Record which hook events fired (Stop/SessionEnd log lines, or a spy per event) so the "eight events" title is actually tested.

**Independent reproduction.** I mirrored the example tree under scratchpad/review/mut2/typescript/examples/: copied nams-ai-provider/{src,test,package.json,tsconfig.json}, vercel-ai/test, shared/ and tsconfig.base.json, and symlinked nams-ai-provider/node_modules. Each mutation below replaces src/hooks-mode.ts with a fresh copy, edits it, and runs `npx vitest run -t "hooks mode"` against the unmodified test.
- Baseline, no change: `Tests 1 passed | 7 skipped (8)`.
- M1, `permissionDecision: 'deny'` changed to `'allow'` (line 46): `Tests 1 passed | 7 skipped (8)`.
- M2, `attempt === 1 ?` changed to `attempt === 99 ?` (line 54), so the retry never happens: `Tests 1 passed | 7 skipped (8)`.
- M3, removed SessionStart, PreToolUse, PostToolUse, PostToolUseFailure, Stop and SessionEnd, keeping only UserPromptSubmit and PreMemoryWrite: `Tests 1 passed | 7 skipped (8)`.
- M4, M1 plus a probe in delete_account's execute (`process.stderr.write('DELETE_EXECUTED\n')`): the output shows `DELETE_EXECUTED` and `Tests 1 passed | 7 skipped (8)`. The tool actually ran and the test still passed.
- Control, the same probe with the deny hook kept: no `DELETE_EXECUTED` in the output and `Tests 1 passed`. The hook works, but the test cannot tell whether it did.
Afterwards `git status --short typescript/examples/nams-ai-provider` shows only the package-lock.json change that was already there, so the repo is untouched.

Also reported as: provider#1 (`typescript/examples/nams-ai-provider/test/docs-pages.test.ts:232`)

### ts-ex-a#0 — Extraction wait treats only per-message status "done" as finished, so "completed" times out every cleanup
**major** · hosted-contract · `typescript/examples/shared/tutorial-cleanup.ts:38` · **must fix**

waitForTerminalExtraction returns only when every message status is exactly "done". It fails on "error"/"failed" and otherwise keeps polling until the deadline. The Python SDK documents the per-message statuses as pending / completed / failed. The Python hosted tutorial helper on this same branch accepts done, completed and skipped as terminal. If NAMS returns "completed" (or "skipped"), cleanupTutorial ends with "Extraction deadline expired; no records were deleted." and never deletes anything. That covers every TypeScript lesson (hosted-quickstart, first-agent, conversation, knowledge-graph, mcp), and the knowledge-graph seed/observe phases fail the same way. A "cancelled" status is also not treated as a failure; it waits for the full timeout. The offline stub returns "done", and tutorial-state-cleanup.test.ts:116 never tests "completed", so CI cannot see this.

**Evidence.** typescript/examples/shared/tutorial-cleanup.ts:37-38: `if (value.messages.some(m => ["error", "failed"].includes(m.status!))) throw ...; if (value.messages.every(m => m.status === "done")) return;`. Source of truth: src/neo4j_agent_memory/nams/short_term.py:240-241 ("``summary`` maps each per-message extraction status (``pending`` / ``completed`` / ``failed`` / …)"). The same branch's Python helper, docs/modules/ROOT/examples/hosted_tutorial_cleanup.py:56-58, accepts `terminal = {"done", "completed", "skipped"}` and treats `("failed", "error", "cancelled")` as failure. Repro: a scratch vitest that sets `stub.behavior.extraction = "completed"` (and "skipped") in docs-hosted-stub, seeds a run, then calls `cleanupTutorial(run, {timeoutMs:1500})`. Both cases rejected with "deadline expired" and the conversation stayed in the stub (2/2 passed).

**Fix.** Accept the same vocabulary as the Python helper: terminal = done|completed|skipped, failure = failed|error|cancelled, pending = pending|processing|running|in_progress|queued, and throw on any unknown status. Add "completed" and "skipped" cases to the stub-driven tests.

**Independent reproduction.** Scratch script /private/tmp/claude-502/-Users-lyonwj-github-neo4j-labs-agent-memory/66a2977c-9670-4b56-8270-fc84ea0f1100/scratchpad/review/repro-extraction.mts. It uses the branch's real TutorialRun, cleanupTutorial and startHostedStub. For each status it creates a conversation and one message, sets stub.behavior.extraction to that status, then calls cleanupTutorial(run, {timeoutMs:1500, intervalMs:200}).

Run from typescript/examples/vercel-ai:
`./node_modules/.bin/tsx <scratch>/repro-extraction.mts`

Output:
```
done OK {"complete":true,"retainedIds":[],"residualIds":[]} 46ms   DELETE calls: 2 status polls: 1
completed REJECTED: Extraction deadline expired; no records were deleted. 1511ms   DELETE calls: 0 status polls: 8
skipped REJECTED: Extraction deadline expired; no records were deleted. 1509ms   DELETE calls: 0 status polls: 8
cancelled REJECTED: Extraction deadline expired; no records were deleted. 1508ms   DELETE calls: 0 status polls: 8
```

Supporting greps:
- tests/docs/test_hosted_tutorial_cleanup.py:173 `@pytest.mark.parametrize("terminal_status", ["completed", "done"])`
- git show ec9fc65:typescript/examples/shared/tutorial-cleanup.ts → "exists on disk, but not in 'ec9fc65'", so the file is new on this branch.
- git log ec9fc65..HEAD for the file → d41e4bd, f1a4786.

Also reported as: tut-ts#1 (`typescript/examples/shared/tutorial-cleanup.ts:38`)

### ts-ex-b#1 — Relative links to the Python gallery and the CI workflow now resolve outside the repository
**major** · broken-link · `typescript/examples/README.md:41` · **must fix**

typescript/examples/README.md sits two levels below the repo root. This branch changed `../../examples/` to `../../../examples/` and `../../.github/...` to `../../../.github/...`, so both links now point above the repository root. The old paths were correct. The per-example READMEs, one level deeper, correctly use `../../../`, which is probably where the change came from.

**Evidence.** typescript/examples/README.md:41: `[`../../../examples/`](../../../examples/).` and :82: `[`.github/workflows/ci-typescript.yml`](../../../.github/workflows/ci-typescript.yml)`. From typescript/examples/: `ls -d ../../examples ../../.github/workflows/ci-typescript.yml` finds both; `ls -d ../../../examples ../../../.github` returns `No such file or directory`. On main (ec9fc65) these lines read `(../../examples/)` and `(../../.github/workflows/ci-typescript.yml)`.

**Fix.** Restore `../../examples/` and `../../.github/workflows/ci-typescript.yml` in typescript/examples/README.md.

**Independent reproduction.** cd /Users/lyonwj/github/neo4j-labs/agent-memory
grep -n '\.\./' typescript/examples/README.md
  41:[`../../../examples/`](../../../examples/).
  82:  matrix in [`.github/workflows/ci-typescript.yml`](../../../.github/workflows/ci-typescript.yml),
git diff ec9fc65..HEAD -- typescript/examples/README.md
  -[`../../examples/`](../../examples/).
  +[`../../../examples/`](../../../examples/).
  -  matrix in [...](../../.github/workflows/ci-typescript.yml),
  +  matrix in [...](../../../.github/workflows/ci-typescript.yml),
cd typescript/examples
ls -d ../../examples ../../.github/workflows/ci-typescript.yml   -> both exist
ls -d ../../../examples ../../../.github   -> "No such file or directory" for both
realpath ../../..   -> /Users/lyonwj/github/neo4j-labs (outside the repo)

Also reported as: x-consistency#2 (`typescript/examples/README.md:41`)

### ts-ex-b#2 — 'Running an example' walkthrough for nextjs-memory-chat omits the provider build and fails
**major** · instructions · `typescript/examples/README.md:46` · **must fix**

The index's run recipe uses nextjs-memory-chat as its worked example. It builds only the SDK (`cd typescript && npm ci && npm run build`), then runs `npm ci` and `npm run dev` in the example. The example now also needs typescript/packages/vercel-ai-provider installed and built, and that package's dist/ is gitignored. A reader who follows the index gets a module-resolution failure for `@neo4j-labs/nams-ai-provider`. The example's own README (lines 118-138) has the extra steps, but the index does not mention them.

**Evidence.** typescript/examples/README.md:46-53: `cd typescript` / `npm ci` / `npm run build` / `cd examples/nextjs-memory-chat` / `npm ci` / `cp .env.example .env` / `npm run dev`. typescript/examples/nextjs-memory-chat/README.md:130-138 also requires `cd packages/vercel-ai-provider`, `npm ci`, `npm run build`. The provider's package.json exports `./dist/index.js`, which is untracked (typescript/packages/vercel-ai-provider/.gitignore:5 `dist/`).

**Fix.** Add the vercel-ai-provider `npm ci && npm run build` step to the index snippet, or switch the worked example to one that depends only on the SDK and point to the nextjs README for its extra step.

**Independent reproduction.** 1. Compared the old and new versions. git show ec9fc65:typescript/examples/nextjs-memory-chat/package.json | grep nams gives no match, so the provider dependency was added on this branch. git diff ec9fc65..HEAD -- typescript/examples/README.md shows the branch rewrote the run snippet: cd typescript, npm ci, npm run build, cd examples/nextjs-memory-chat, npm ci, npm run dev. There is no provider step.

2. Checked the provider package. packages/vercel-ai-provider/package.json has only these scripts: build, dev, typecheck, test, test:watch, prepublishOnly. There is no prepare script. Its exports point at ./dist/index.js, and .gitignore lists dist/.

3. Reproduced the install. Copied the provider's package.json, src, tsconfig.json and tsup.config.ts (no dist) to scratch/review/tsex2/prov. Created an app with the dependency "@neo4j-labs/nams-ai-provider": "file:../prov" and ran npm install --legacy-peer-deps. It printed "added 1 package", and node_modules/@neo4j-labs/nams-ai-provider is a symlink to ../../../prov that contains no dist. Running node -e "import('@neo4j-labs/nams-ai-provider')" failed with: ERR_MODULE_NOT_FOUND Cannot find module '.../node_modules/@neo4j-labs/nams-ai-provider/dist/index.js'.

4. Checked where the example uses the provider. grep shows lib/handlers.ts:12 imports createNamsProvider from it, and app/api/memory/{context,trace,graph}/route.ts import from @/lib/handlers.

Also reported as: x-consistency#1 (`typescript/examples/README.md:44`), gap2-gap2-install-commands-sweep#4 (`typescript/examples/README.md:50`)

### ts-ex-b#3 — README still says the model gets the rail's three tiers and the recent history, but the provider injects neither
**major** · behaviour-claim · `typescript/examples/nextjs-memory-chat/README.md:214` · **must fix**

The chat route switched from `agentMemoryMiddleware` to `createNamsProvider`. The middleware called `shortTerm.getContext` and replayed reflections, observations and recent messages. The provider never calls getContext. It injects at most `maxMemories` (default 6) hits, interleaved from query-based `searchMessages`, `searchEntities`, graph expansion, `direct response` reasoning steps and cross-session search. Several unchanged or new README lines contradict this:
- Line 214-215 says the rail's `0 reflections · 1 observation · 6 recent messages` is 'exactly what the next model call will have prepended to it'. MemoryRail.tsx and the handleContext doc comment were updated to say the opposite.
- Lines 33-34 say 'the history the model sees comes back out of the graph'. In fact the model sees only search hits for the current question.
- Lines 28-32 present agentMemoryMiddleware as the choice 'if a conversation's own reflections, observations and recent messages were enough', which implies the provider supplies those and more.
- Line 25-26 lists 'reasoning history' as retrieved. The provider keeps only steps with `actionTaken === 'direct response'`, while this app records `generate_answer`, so its own trace is never retrieved.
The offline test cannot catch any of this. The msw `/conversations/:id/search` fake returns the conversation's last N messages whatever the query, so 'injects conversation history the request never sent' passes even though real retrieval depends on the query. The old observation-injection assertion ('avoids buses') was dropped.

**Evidence.** README.md:214-215: `the rail reads **0 reflections · 1 observation · 6 recent messages** — exactly what the next model call will have prepended to it;`. README.md:33-34: `the history the model sees comes back out of the graph.`. Provider retrieval, typescript/packages/vercel-ai-provider/src/vercel-ai-provider-client.ts:369-412, uses searchMessages(query, {threshold: 0.4}), searchEntities, listSteps filtered by `s.actionTaken === 'direct response'` (:411) and searchPastConversations, with no getContext call. By contrast typescript/src/middleware/vercel-ai.ts:181-184 has `const ctx = await client.shortTerm.getContext(id); ... ctx.observations ... ctx.recentMessages`. lib/handlers.ts:155 records `actionTaken: "generate_answer"`. test/nams-server.ts `/conversations/:id/search` returns `conv.messages.slice(-(body.limit ?? 10))` regardless of query. The handleContext doc comment in lib/handlers.ts now says the route's retrieval 'draws on a wider set of sources than this endpoint shows'.

**Fix.** Rewrite README lines 25-36 and 214-215 to describe what the provider actually injects: search-ranked hits capped at maxMemories, with no replay of recent turns or observations. Either drop 'reasoning history' or record steps the provider retrieves. Consider making the fake search filter by query so the test reflects retrieval that depends on the query. If full conversational continuity is intended, keep agentMemoryMiddleware for history alongside the provider.

**Independent reproduction.** 1. `sed -n 20,40p` and `sed -n 205,220p` on typescript/examples/nextjs-memory-chat/README.md: lines 25-26, 28-32, 33-34 and 214-215 contain the quoted text. `git diff ec9fc65..HEAD` shows lines 22-32 are new on this branch. Lines 33-34 and 214-215 are unchanged but describe the old middleware.
2. `grep -rn "getContext\|recentMessages\|observations" typescript/packages/vercel-ai-provider/src`: no matches.
3. `sed -n 330,420p vercel-ai-provider-client.ts`: retrieveMemories uses searchMessages with a threshold, searchEntities, listSteps filtered by `s.actionTaken === 'direct response'`, searchPastConversations and expandEntityGraph, then interleaves and caps the results.
4. `grep -n actionTaken lib/*.ts`: handlers.ts:155 has `actionTaken: "generate_answer"`.
5. `grep -rn maxMemories`: middleware.ts:199 has `config.maxMemories ?? 6`.
6. test/nams-server.ts:202-205: the search handler returns `conv.messages.slice(-(body.limit ?? 10))` whatever the query.
7. `git diff ec9fc65..HEAD -- test/routes.test.ts | grep buses`: `-    expect(prompt).toContain("avoids buses");` (removed).
8. MemoryRail.tsx:160-162 and handlers.ts:173-178 (the new comments) contradict README.md:214-215.

### ts-sdk#1 — Unreleased getActive() change and new ActiveOntology.schemaHash are not in the CHANGELOG
**major** · release-notes · `typescript/CHANGELOG.md:10` · **must fix**

This branch rewrites `OntologyClient.getActive()`: 
- It no longer composes metadata through `list()` and `get()`.
- Legacy or `version: null` responses now return no `validationMode`, `revision`, `versionId` or `ontologyId` (0.5.0 did fill them in).
- It throws a plain `Error` on malformed or conflicting metadata.
- It adds `ActiveOntology.schemaHash`.
The published typescript-v0.5.0 tag does not contain this commit, but package.json and VERSION still say 0.5.0 and `## [Unreleased]` is empty. The regenerated TypeDoc under docs attachments, titled "agent-memory - v0.5.0", now lists `schemaHash` on ActiveOntology, which is unreleased behaviour presented as 0.5.0. Meanwhile reference/typescript-api.adoc:440 still describes the old "composed" metadata, which contradicts ontology-api.adoc:88-92.

**Evidence.** `git merge-base --is-ancestor d41e4bd typescript-v0.5.0` prints `typescript-v0.5.0 lacks d41e4bd`, and `git show typescript-v0.5.0:typescript/src/ontology/index.ts` line 410 is `// Compose version metadata via a second lookup`.
HEAD typescript/src/ontology/index.ts:472 `if (raw.version == null) return { document };` and :103 `schemaHash?: string;`
typescript/CHANGELOG.md:10-12: `## [Unreleased]` followed directly by `## 0.5.0 — 2026-09-22`.
typescript/package.json:3 `"version": "0.5.0"`; typescript/src/version.ts:6 `VERSION = "0.5.0"`.
docs/modules/ROOT/attachments/api/typescript/interfaces/index.ActiveOntology.html has 2 `schemaHash` matches at HEAD and 0 at ec9fc65; its index.html title is `agent-memory - v0.5.0`.
docs/modules/ROOT/pages/reference/typescript-api.adoc:440 "Active version's parsed document + composed `validationMode` / `revision` / `versionId`."

**Fix.** Add an `[Unreleased]` entry under Changed/Added. Cover the getActive() binding source, legacy responses leaving metadata undefined (a behaviour change from 0.5.0), the plain Error throws, and the new `schemaHash`. Either stop publishing the regenerated TypeDoc as v0.5.0 until the release, or label it as unreleased. Update typescript-api.adoc:440 to match.

**Independent reproduction.** 1) `git log --oneline ec9fc65..HEAD -- typescript/src typescript/CHANGELOG.md typescript/package.json` shows d41e4bd and 8fc3ead touching src and nothing touching CHANGELOG. `git diff --quiet ec9fc65..HEAD -- typescript/CHANGELOG.md typescript/package.json typescript/src/version.ts` confirms all three are untouched.
2) `git merge-base --is-ancestor d41e4bd typescript-v0.5.0` prints "lacks", and `git tag --contains d41e4bd` is empty.
3) I extracted `git show typescript-v0.5.0:typescript/src/ontology/index.ts` to scratchpad/review/old/ and wrote scratchpad/review/run.mts. It feeds both OntologyClient versions a fake transport: get_active_ontology returns `{ontology: doc}` (legacy) or `{ontology: doc, version: {id:"v2"}}` (partial); list_ontologies returns `{ontologies:[{id:"o1",name:"d",is_active:true,current_revision:2}]}`; get_ontology returns `{record:{...}, versions:[{id:"v2",ontology_id:"o1",revision:2,validation_mode:"strict",schema_hash:"h"}]}`. I ran it with `npx tsx run.mts` from typescript/. Output:
   0.5.0 legacy: {"ontologyId":"o1","validationMode":"strict","revision":2,"versionId":"v2"}
   0.5.0 partial: ok
   HEAD legacy: {}
   HEAD partial throws: Error Invalid active ontology version metadata: ontology_id is required.
4) `grep -c schemaHash docs/modules/ROOT/attachments/api/typescript/interfaces/index.ActiveOntology.html` gives 2 at HEAD and 0 at ec9fc65. `<title>@neo4j-labs/agent-memory - v0.5.0</title>` is in attachments/api/typescript/index.html. The regen came in branch commit e2bcb93.
5) typescript-api.adoc:440-441 reads "Active version's parsed document + composed `validationMode` / `revision` / `versionId`". ontology-api.adoc:91-96 describes the HEAD behaviour and notes "this is not a statement that a corresponding npm release is available".

### ts-sdk#2 — README tutorial links now point to raw .adoc source whose Antora includes don't resolve
**major** · broken-link · `typescript/README.md:109` · **must fix**

The same diff turned every `./examples` link into an absolute GitHub URL, because the README ships in the npm package. It also replaced the published-site tutorial URL with two relative `../docs/modules/ROOT/pages/...adoc` links. From the npm package page, `../` escapes the package (package.json `files` is dist, README.md, LICENSE, CHANGELOG.md). On GitHub the link opens AsciiDoc source, whose `include::partial$...` Antora resource ids GitHub cannot resolve. The "Start here" tutorial therefore renders without its project setup, API and lifecycle sections.

**Evidence.** typescript/README.md:109 `[Start here: store and read back hosted memory](../docs/modules/ROOT/pages/tutorials/hosted-quickstart-typescript.adoc)` and :110 `(../docs/modules/ROOT/pages/tutorials/first-agent-memory-typescript.adoc)`.
The old README (ec9fc65) line 100 used `https://neo4j.com/labs/agent-memory/tutorials/first-agent-memory-typescript`.
docs/modules/ROOT/pages/tutorials/hosted-quickstart-typescript.adoc:21 `include::partial$typescript-tutorial-project.adoc[]`, :58 `include::partial$typescript-tutorial-api.adoc[]`, :130 `include::partial$typescript-tutorial-lifecycle.adoc[]`.
typescript/package.json `files`: ["dist","README.md","LICENSE","CHANGELOG.md"].

**Fix.** Use the published site URLs, like the other Documentation bullets: https://neo4j.com/labs/agent-memory/tutorials/hosted-quickstart-typescript and https://neo4j.com/labs/agent-memory/tutorials/first-agent-memory-typescript.

**Independent reproduction.** sed -n 107,111p typescript/README.md -> line 109 `(../docs/modules/ROOT/pages/tutorials/hosted-quickstart-typescript.adoc)` and line 110 `(../docs/modules/ROOT/pages/tutorials/first-agent-memory-typescript.adoc)`. In ec9fc65 this was one link to https://neo4j.com/labs/agent-memory/tutorials/first-agent-memory-typescript.
grep -n include:: on both tutorials -> hosted-quickstart-typescript.adoc:21,58,130 and first-agent-memory-typescript.adoc:24,99,197, each `include::partial$typescript-tutorial-{project,api,lifecycle}.adoc[]`.
`git show ec9fc65:docs/modules/ROOT/pages/tutorials/first-agent-memory-typescript.adoc | grep -c include::` -> 0, so the branch added the includes.
wc -l on the partials: project 47, api 26, lifecycle 45.
typescript/package.json has files ["dist","README.md","LICENSE","CHANGELOG.md"] and repository {url: github.com/neo4j-labs/agent-memory, directory: "typescript"}.
find docs/build/site -path '*tutorials/*typescript*' -> both hosted-quickstart-typescript.html and first-agent-memory-typescript.html are present, so the published URLs work.

Also reported as: gap2-gap2-markdown-link-check#3 (`typescript/README.md:109`)

### ts-sdk#0 — E2E cleanup expects NotFoundError, but the REST transport throws TransportError(404)
**major** · test-correctness · `typescript/test/e2e/ontology.test.ts:55` · **must fix**

After deleting each clone, afterAll asserts that `ontology.get(id)` rejects with `NotFoundError`. The REST transport never builds a NotFoundError. It maps every non-OK, non-auth response to `TransportError` with `statusCode`. So after a successful delete, this assertion always fails and the whole isolated ontology e2e run goes red. The mistake looks like a port of the Python integration test (`tests/integration/nams/test_ontology.py:71` uses `pytest.raises(NotFoundError)`), where Python does map 404 to NotFoundError. The branch's own docs say the TypeScript SDK does not: handle-errors.adoc:19 and typescript-api.adoc:486. So does its own contract test, which expects HTTP 404 to produce `TransportError`.

**Evidence.** typescript/test/e2e/ontology.test.ts:55 `await expect(client!.ontology.get(id)).rejects.toBeInstanceOf(NotFoundError);`
Source: typescript/src/transport/rest.ts:626-632 `const err = new TransportError(`${method} failed: ${errMsg}`, response.status, errorBody, { requestId });`. `grep -rn "new NotFoundError" typescript/src` returns no matches.
Repro (scratchpad nf.mts, fetch stubbed to return 404, then `client.ontology.get("ont_x")`): output `name= TransportError NotFoundError? false TransportError? true status 404`.
docs/modules/ROOT/pages/how-to/typescript/handle-errors.adoc:19 "`NotFoundError` exists for compatibility but is not the normal REST 404 mapping."

**Fix.** Assert the real mapping: `await expect(client!.ontology.get(id)).rejects.toMatchObject({ name: "TransportError", statusCode: 404 })`, or use `toBeInstanceOf(TransportError)` plus a statusCode check. Drop the NotFoundError import.

**Independent reproduction.** 1) `git show ec9fc65:typescript/test/e2e/ontology.test.ts | grep -n NotFound` returns nothing, so the branch introduced both the import and the assertion.
2) `grep -rn NotFoundError typescript/src` returns only errors.ts:44, errors.ts:47 (this.name) and index.ts:132 (re-export). None of them throws the error.
3) I wrote scratchpad/review/nf2.mts. It replaces globalThis.fetch with a function that returns 404 and the body {"error":"ontology not found"}, builds `new MemoryClient({endpoint:"https://memory.neo4jlabs.com/v1", apiKey:"nams_test", maxRetries:0})`, and calls `c.ontology.get("ont_x")`. I ran it with `cd typescript && npx tsx <scratch>/nf2.mts`. Output:
  req GET https://memory.neo4jlabs.com/v1/ontologies/ont_x
  name= TransportError NotFound? false Transport? true status 404
So `rejects.toBeInstanceOf(NotFoundError)` fails for the real 404 path.

### tut-ts#2 — MCP docs-assembly test builds from the SDK's own node_modules, not the lesson's install
**major** · test-coverage · `typescript/examples/mcp/test/docs-assembly.test.ts:49` · **must fix**

The test claims to compile the tutorial's server as assembled from the page. It skips the page's `npm install ../typescript @modelcontextprotocol/sdk@^1.30 zod@^4` and instead symlinks `@modelcontextprotocol`, `@types` and `zod` from the SDK's own `typescript/node_modules`. That gives it a single zod copy, so it passes while the reader's install fails to typecheck (see the blocker finding). It also writes a bare `{ type: "module" }` package.json instead of the page's package fields. The test cannot fail on the dependency layout it is meant to guard.

**Evidence.** docs-assembly.test.ts:47-49:
`await symlink(sdkRoot, join(directory, "node_modules", "@neo4j-labs", "agent-memory"));`
`for (const name of ["@modelcontextprotocol", "@types", "zod"]) await symlink(join(sdkRoot, "node_modules", name), join(directory, "node_modules", name));`

Compare mcp-server-typescript.adoc:62: `npm install ../typescript @modelcontextprotocol/sdk@^1.30 zod@^4`. The reader-path reproduction fails with TS2345, as shown in the blocker finding.

**Fix.** Have the test (or a separate opt-in check) install `@modelcontextprotocol/sdk` and `zod` into the temp project as the page does, or pin them to versions different from the SDK's lockfile, so a duplicate zod copy is exercised. Alternatively, assert that the page's install command matches the layout the test builds.

**Independent reproduction.** Scratch dir: /private/tmp/claude-502/-Users-lyonwj-github-neo4j-labs-agent-memory/66a2977c-9670-4b56-8270-fc84ea0f1100/scratchpad/review/mcp2 (contains a symlink typescript -> repo/typescript).

1) Reader path. In my-memory-mcp/: `npm init -y && npm install ../typescript @modelcontextprotocol/sdk@^1.30 zod@^4 && npm install --save-dev typescript@^5.9 tsx@^4 @types/node@^22`. This installed zod 4.6.5 and @modelcontextprotocol/sdk 1.30.1; the SDK's own node_modules has zod 4.6.1 and sdk 1.30.0. I copied the three tutorial helpers and pulled server.ts and tsconfig.json out of the page with the same regex the test uses. Then `npx tsc -p tsconfig.json`:
  src/server.ts(21,41): error TS2345: Argument of type 'McpServer' is not assignable to parameter of type 'RegisterToolCapable'. ... Type 'MemoryToolShape' is not assignable to type 'AnySchema | ZodRawShapeCompat | undefined' ... EXIT=2

2) The test's layout. `cd typescript/examples/mcp && npx vitest run test/docs-assembly.test.ts` gives: Test Files 1 passed (1), Tests 1 passed (1).

3) Cause check. In the reader project I replaced node_modules/zod with a symlink to typescript/node_modules/zod and ran `npx tsc -p tsconfig.json`, which gave EXIT=0. A single zod copy compiles and two copies do not. The test always builds the single-copy layout, so it cannot fail on the dependency layout the page tells readers to install.

## Minors (174), by area

### Cloud Run and MCPB deployment assets (`deploy`)

- **deploy#4** `deploy/cloudrun/README.md:45` — Local smoke test runs `fastmcp` on the host but the install step was removed
  - Fix: Restore an explicit host install step, such as `python -m pip install 'neo4j-agent-memory[mcp]==0.6.0'` in a venv or `uvx fastmcp list ...`, before the first `fastmcp list` command.
- **deploy#1** `deploy/cloudrun/README.md:117` — Documented endpoint `/mcp/` is a 307 redirect to an absolute http:// `/mcp` URL
  - Fix: Document the endpoint as `/mcp` (no trailing slash) in the README, the Dockerfile comment and the verification commands. Alternatively, start uvicorn with proxy headers trusted (forwarded_allow_ips) so redirects keep https. Either way, have the deployed-caller guidance use the exact path.
- **deploy#5** `deploy/cloudrun/env.yaml.example:22` — env.yaml.example contradicts the branch's new image config (OpenAI extraction, unused VERTEX_AI_LOCATION)
  - Fix: Update env.yaml.example to match: Aura `neo4j+s://` URI, GOOGLE_CLOUD_PROJECT, no VERTEX_AI_LOCATION or OpenAI extraction lines. Or delete it and point to the README's local env-file instructions.
- **deploy#0** `deploy/mcpb/manifest.json:16` — MCPB manifest fails the official validator; Quick Start's extension env setup cannot work
  - Fix: Rewrite the manifest to the MCPB schema: add `manifest_version`, make `author` an object (`{"name": "Neo4j Labs"}`) and `repository` an object (`{"type":"git","url":...}`), and use `server: {type: "uv" or "binary", entry_point, mcp_config: {command: "uvx", args: [...], env: {NEO4J_URI: "${user_config.neo4j_uri}", ...}}}`. Declare `user_config` entries for uri/user/password (sensitive)/database/openai_api_key (sensitive), and set `version` to the package version. Check the result with `mcpb validate`. Otherwise, drop the "install from extension directory" step and keep only the claude_desktop_config.json path.
- **deploy#3** `tests/docs/test_cloudrun_assets.py:91` — Test fakes vertexai availability but never asserts the Dockerfile installs an extra providing it
  - Fix: Parse the `RUN pip install` extras from the Dockerfile and assert they include `google` or `vertex-ai`, and that the pyproject extra lists google-cloud-aiplatform. Optionally, assert that the secret names in cloudbuild `--set-secrets` match the service.yaml `secretKeyRef` names and the README's secret loop.

### Runnable Python programs included into docs pages (`docs-examples-py`)

- **docs-examples-py#2** `docs/modules/ROOT/examples/conversation_memory.py:124` — Comment says 'seed' runs without the openai package, but seed makes OpenAI embedding calls
  - Fix: Reword both comments to say that only this branch calls the chat model; seed/ingest still need the openai extra for embeddings.

### Docs tests: tutorial and hosted-lifecycle contract tests (`docs-tests-a`)

- **docs-tests-a#0** `tests/docs/test_hosted_tutorial_contracts.py:214` — 'stops before reasoning' assertion is vacuous: nams_quickstart.exercise never calls reasoning
  - Fix: Drop the Reasoning stub and the reasoning assertions from the two nams tests. In the timeout test, keep the state object and assert `'seed_verified' not in state.data` (or that it is falsy). Also assert that the conversation and both messages are still recorded in `state.data['resources']` so cleanup can find them.

### Docs tests: build, checker, links, nav, diagrams, contracts, rendered site (`docs-tests-b`)

- **docs-tests-b#5** `tests/docs/test_code_snippets.py:57` — Obsolete is_signature_doc skip hides 141 blocks that all compile, including real programs, from syntax and drift checks
  - Fix: Remove the is_signature_doc skip, or narrow it to blocks that fail to compile. Also drop the is_signature_doc exclusion in TestSettingsFieldDrift.
- **docs-tests-b#7** `tests/docs/test_docs_checker.py:159` — test_complete_async_helper_keeps_future_import_at_module_level compiles a literal and exercises no project code
  - Fix: Build a CodeSnippet from that program and assert that test_code_snippets' compile path and `get_syntax_checkable_code()` both parse it. Otherwise delete the test.
- **docs-tests-b#6** `tests/docs/test_nav_labels.py:173` — test_perturbed_label_is_caught tests Python's assert, not the alignment check
  - Fix: Factor the mismatch computation into a helper that takes nav/index/H1 inputs. Feed it a perturbed nav text (for example with the memory-types label changed) and assert that it reports the mismatch.
- **docs-tests-b#8** `tests/docs/test_python_integration_contracts.py:174` — Trace-outcome assertions pass vacuously when a recipe records no trace
  - Fix: Assert `len(client.traces) == 1` (or `>= 1`) before each `all(...)` check.
- **docs-tests-b#9** `tests/docs/test_python_integration_contracts.py:337` — 'make test-docs' fails in the documented dev environment: this module needs agent-framework-openai, which no extra installs
  - Fix: Either add `--ignore=tests/docs/test_python_integration_contracts.py` to test-docs and give that module its own make target that follows MAINTAINING.md, or add agent-framework-openai to the microsoft-agent extra.
- **docs-tests-b#3** `tests/docs/utils/extract_code.py:429` — Import checker counts names imported only under TYPE_CHECKING as declared, so it certifies imports that fail at runtime
  - Fix: In visit(), skip the body of an `if` whose test is `TYPE_CHECKING` or `typing.TYPE_CHECKING`, and visit only its orelse.

### Entry points: index, getting started, SDK pages, nav, READMEs, CLAUDE.md, CONTRIBUTING, MAINTAINING (`entry`)

- **entry#4** `CLAUDE.md:45` — CLAUDE.md CI section misses the new docs triggers and still says the TCK runs on every PR _(also: x-consistency#6)_
  - Fix: Add the TypeScript docs paths to the ci-typescript trigger description, and change CLAUDE.md:83 to say the TCK suite is opt-in (`npm run test:tck`) and not run by TS CI.
- **entry#3** `CLAUDE.md:426` — CLAUDE.md still names the Excalidraw directory this branch moved away _(also: x-diagrams#11, gap2-gap2-markdown-link-check#0)_
  - Fix: Change the path in CLAUDE.md:426 to `docs/assets/diagrams/excalidraw/`.
- **entry#5** `CONTRIBUTING.md:294` — CONTRIBUTING still lists two published packages and omits the nams-ai-provider release flow _(also: x-consistency#7)_
  - Fix: Say the repo ships three packages. Add a '@neo4j-labs/nams-ai-provider → npm' publishing subsection (version bump in typescript/packages/vercel-ai-provider, typecheck/test/build/`npm pack --dry-run`, `nams-ai-provider-v<X.Y.Z>` tag), plus a workflow-table row.
- **entry#9** `README.md:195` — Aura quickstarts now tell readers to set ANTHROPIC_API_KEY but hard-code a retired Claude 3.5 model
  - Fix: Use a current model id in both READMEs (e.g. a Claude Sonnet 4.x id), or read it from an ANTHROPIC_MODEL variable as the tutorial does.
- **entry#8** `README.md:274` — Edited README MCP command still uses deprecated `--transport sse` for 'network deployment' _(also: x-consistency#4)_
  - Fix: Use `# Streamable HTTP (network deployment)` / `neo4j-agent-memory mcp serve --transport http --host 0.0.0.0 --port 8080 --backend bolt --user "$NEO4J_USERNAME"`, and note that the endpoint is /mcp/.
- **entry#7** `README.md:325` — README says 'All nine TypeScript examples' (there are ten) and misstates Python dependency files _(also: x-consistency#5)_
  - Fix: Change 'nine' to 'ten', and say Python examples declare dependencies in `pyproject.toml`, `requirements.txt` or PEP 723 metadata.
- **entry#6** `README.md:340` — README Development section still cds into nonexistent agent-memory/neo4j-agent-memory
  - Fix: Change README.md:340 to `cd agent-memory`.
- **entry#0** `docs/modules/ROOT/pages/index.adoc:83` — Retained 'Demos' anchors on index use wrong ids; the real former ids are still lost _(also: gap1-compat-anchor-landing#23)_
  - Fix: Replace the three anchors with `anchor:_lennys_podcast_memory_explorer_flagship[]`, `anchor:_full_stack_chat_agent[]` and `anchor:_domain_schema_examples[]`.

### Python static checks, unit tests, example and docs tests (no Neo4j) (`ex-python`)

- **ex-python#1** `tests/docs/test_rendered_site.py:21` — New pytest.mark.rendered used but not registered in pyproject.toml, causing a warning on every run _(also: ex-docs#0, tooling-ci#10, docs-tests-b#11)_
  - Fix: Add `"rendered: marks tests as requiring a rendered Antora build (see scripts/render_docs.mjs)"` to the `markers` list in pyproject.toml's `[tool.pytest.ini_options]`.

### Explanation pages, glossary, FAQ (`explanation`)

- **explanation#5** `docs/modules/ROOT/pages/explanation/context-tiers.adoc:57` — Says Strands and Mastra merge tiers into one block and replay recent messages; they do not
  - Fix: Describe each integration separately. Vercel middleware: one prepended block plus recent messages, falling back to flat history. Strands: one system message per reflection or observation, layered over the inner manager, left unchanged on failure. Mastra: the application reads `getContext()` itself.
- **explanation#4** `docs/modules/ROOT/pages/explanation/operational-primitives.adoc:19` — `write_mode="buffered"` placed on MemorySettings; it belongs on MemorySettings.memory _(also: x-style#5)_
  - Fix: Write `MemorySettings.memory.write_mode="buffered"`.
- **explanation#7** `docs/modules/ROOT/pages/explanation/why-provider-protocol.adoc:11` — Tells readers to compare against a 'version banner' the docs site does not have
  - Fix: Name the version the page describes (neo4j-agent-memory 0.6.0) and drop the reference to a banner.
- **explanation#3** `docs/modules/ROOT/pages/faq.adoc:89` — extra_forbidden FAQ dropped the fix and hints it may not be released
  - Fix: State that 0.2.1 and later (including 0.6.0) filter unrelated .env keys, so upgrading fixes it. If the error persists on 0.6.0, the cause is a misspelled MemorySettings keyword argument.
- **explanation#6** `docs/modules/ROOT/pages/glossary.adoc:30` — Observations/reflections called hosted-TS-only, but the Python MCP server has its own three-tier view
  - Fix: Say that the hosted three-tier context is available from both SDKs on NAMS (TypeScript `getContext`/`getObservations`/`getReflections`, Python `short_term.get_context`/`get_observations`/`get_reflections`). Separately note the Python MCP server's local observational memory (`memory_get_observations`) and its own observations and reflections.

### Check backend-support labels and NotSupportedError claims against the NAMS client (`gap1-backend-support-labels`)

- **gap1-backend-support-labels#8** `docs/modules/ROOT/pages/how-to/audit-reasoning.adoc:7` — NOTE blames 'the hosted Python bridge' for dropping touched_entities; REST client drops it too
  - Fix: Write: "The Python NAMS client accepts `touched_entities` but silently drops it (no error is raised), so no `:TOUCHED` edges are written on NAMS."
- **gap1-backend-support-labels#2** `docs/modules/ROOT/pages/how-to/messages.adoc:7` — Messages page newly labelled 'Available on NAMS: Yes' but its procedure and table fail on NAMS
  - Fix: Either label the page Bolt-only with a pointer to the NAMS conversation flow, or keep `backend-both` and add a NAMS column/NOTE. That note should cover: create_conversation → server ID, `bulk_add_messages` instead of `add_messages_batch`, required conversation ID for `search_messages`, and no summary/list_sessions/preferences on NAMS. Extend the backend-capabilities conversations row to match.
- **gap1-backend-support-labels#5** `docs/modules/ROOT/pages/reference/api/memory-client.adoc:164` — include_long_term now says 'facts and preferences'; long-term context has entities, not facts
  - Fix: Change to "Whether to include matching entities and preferences (bolt); NAMS long-term context is empty".
- **gap1-backend-support-labels#7** `docs/modules/ROOT/pages/reference/backend-capabilities.adoc:45` — Preferences row says NAMS methods raise NotSupportedError; documented call forms raise TypeError
  - Fix: Either make the NAMS stub signatures mirror Bolt (`get_preferences_for(self, user_identifier, **kwargs)`, `supersede_preference(self, old, new)`) so they reach `NotSupportedError`, or qualify the row, for example: "unsupported; keyword calls raise NotSupportedError, other call forms may raise TypeError/AttributeError".

### Run the Bolt docs programs against real Neo4j; check the stale hand-copied tests (`gap1-bolt-programs-live`)

- **gap1-bolt-programs-live#6** `docs/modules/ROOT/examples/integrations/hybrid_recipe.py:27` — hybrid recipe passes session_id to search_memory, but results include other sessions relabelled as this one
  - Fix: Add the same warning messages.adoc uses to aws-hybrid-memory.adoc: search_memory's session_id does not scope message search on Bolt. Either drop session_id from the recipe's search call or filter the results by stored IDs from get_session_memories.
- **gap1-bolt-programs-live#4** `tests/docs/test_tutorial_examples.py:18` — test_tutorial_examples.py still tests the old tutorial code, which the rewritten pages no longer show
  - Fix: Delete these classes, or replace them with tests that import and run the maintained programs' seed/verify/resume/ingest/inspect functions against the Neo4j fixture. Update the docstrings so they no longer claim to test page code.

### Do kept compatibility anchors land on matching content? (`gap1-compat-anchor-landing`)

- **gap1-compat-anchor-landing#6** `docs/modules/ROOT/pages/getting-started.adoc:68` — '2. Install the SDK' and Bolt 'Prerequisites' ids land on the See also list
  - Fix: Add _2_install_the_sdk to the anchor line at 17 ('Hosted memory with NAMS') and _prerequisites to the anchor line at 30 ('Python with Neo4j Aura').
- **gap1-compat-anchor-landing#10** `docs/modules/ROOT/pages/how-to/batch-processing.adoc:601` — Old section ids are stacked after See also although matching procedure steps exist _(also: gap1-compat-anchor-landing#11, gap1-compat-anchor-landing#12, gap1-compat-anchor-landing#13, gap1-compat-anchor-landing#14, gap1-compat-anchor-landing#15, gap1-compat-anchor-landing#16, gap1-compat-anchor-landing#17, gap1-compat-anchor-landing#18, gap1-compat-anchor-landing#19, howto-core-b#3)_
  - Fix: Put each anchor before its matching section heading.
- **gap1-compat-anchor-landing#21** `docs/modules/ROOT/pages/how-to/integrations/aws-bedrock-embeddings.adoc:77` — Bedrock troubleshooting and model-choice ids land in 'Run and verify'
  - Fix: Move the three exception ids next to anchor:_troubleshooting[], and the model-choice ids next to anchor:_supported_models[]. Move openai-agents _tool_calls_not_working next to its _troubleshooting.
- **gap1-compat-anchor-landing#4** `docs/modules/ROOT/pages/how-to/migrate-to-nams.adoc:117` — Old migration steps land on See also, Prerequisites and connection setup
  - Fix: Put _5_migrate_raw_cypher_calls at '== Keep raw-write requirements explicit' and _6_run_your_tests at '== 4. Verify the ported application'. Remove the dead [#] stacks and keep one inline anchor per id at its intended section.
- **gap1-compat-anchor-landing#5** `docs/modules/ROOT/pages/how-to/multi-tenancy.adoc:106` — Python page-level ids land on the TypeScript section, and TypeScript subsection ids land on Python steps
  - Fix: Move _goal to the page intro or Prerequisites, and move _schema and _steps to section 1. Put _what_ports_cleanly and _bridging_the_two_patterns under 'TypeScript counterpart (NAMS)'.
- **gap1-compat-anchor-landing#8** `docs/modules/ROOT/pages/how-to/team-memory-in-your-editor.adoc:177` — Old 'Step 2: seed...' id lands in Step 3 (wire the editors), off by one
  - Fix: Move the anchor under '== Step 2: seed a synthetic conversation and retain its ID' (line 160).
- **gap1-compat-anchor-landing#3** `docs/modules/ROOT/pages/how-to/use-nams.adoc:11` — _next_steps and _env_var_reference render in Prerequisites; the intended later anchors are dropped
  - Fix: Remove the stacked [#...] lines. Put anchor:_next_steps[] under '== See also' and anchor:_env_var_reference[] under '== Configuration and operational scope', and remove the copies at line 11.
- **gap1-compat-anchor-landing#9** `docs/modules/ROOT/pages/reference/api/memory-client.adoc:324` — get_context Example/Parameters ids land on See also and the Methods heading
  - Fix: Put anchor:_parameters_2[] and anchor:_example[] with anchor:_returns[] before '=== get_context'.
- **gap1-compat-anchor-landing#1** `docs/modules/ROOT/pages/reference/configuration-providers.adoc:80` — Old Schema Configuration ids land on Extraction configuration, not Graph schema configuration
  - Fix: Move these four anchors above '== Graph schema configuration' (next to anchor:schema[] at line 57).
- **gap1-compat-anchor-landing#22** `docs/modules/ROOT/pages/reference/schemas-custom.adoc:64` — 'Schema Best Practices' id lands on the Entity type mapping table
  - Fix: Move anchor:_schema_best_practices[] next to anchor:_schema_description_guidance[] at line 31.
- **gap1-compat-anchor-landing#20** `docs/modules/ROOT/pages/tutorials/hosted-quickstart-typescript.adoc:128` — TS tutorial ids meant for Next steps sit above the cleanup-result partial
  - Fix: Move these anchors below the '== Next steps' heading.

### Sweep the built site for rendering artifacts (`gap1-rendered-artifacts`)

- **gap1-rendered-artifacts#10** `docs/modules/ROOT/pages/how-to/migrate-embedding-model.adoc:142` — `Thought: ` / `Action: ` / `Observation: ` show literal backticks (trailing space inside code)
  - Fix: Use `+Thought: +`, `+Action: +` and `+Observation: +` (passthrough inside backticks), or describe it as `Thought:` followed by a space.
- **gap1-rendered-artifacts#11** `docs/modules/ROOT/pages/how-to/typescript/handle-errors.adoc:43` — `TypeError`s merges two identifiers into one code span with a literal backtick
  - Fix: Write ``TypeError``s or "Fetch `TypeError` exceptions are wrapped in `ConnectionError`".
- **gap1-rendered-artifacts#0** `docs/modules/ROOT/pages/how-to/typescript/nextjs-memory-chat.adoc:160` — `createNamsProvider`'s breaks the code span and turns the whole next sentence into monospace _(also: gap1-rendered-artifacts#1, gap1-rendered-artifacts#2, gap1-rendered-artifacts#3, gap1-rendered-artifacts#4, gap1-rendered-artifacts#5)_
  - Fix: Use the unconstrained form ``createNamsProvider``'s, or reword it ("The `createNamsProvider` stream wrapper awaits...").
- **gap1-rendered-artifacts#12** `docs/modules/ROOT/pages/how-to/typescript/strands.adoc:98` — `boolean \| ExtractionConfig` shows a literal backslash (escape only needed in tables) _(also: howto-ts#5)_
  - Fix: Remove the backslash: `boolean | ExtractionConfig`.
- **gap1-rendered-artifacts#13** `docs/modules/ROOT/pages/reference/api/long-term-deduplication.adoc:104` — New model-field tables publish a Description column that is empty in every row
  - Fix: Fill the Description cells from the dataclass docstrings (for example long_term.py:69-86), or drop the Description column from these tables. At minimum, restore the match_type values.
- **gap1-rendered-artifacts#9** `docs/modules/ROOT/pages/reference/api/memory-client.adoc:81` — `<<graph>>` points at a bare anchor with no title and renders as the link text "[graph]"
  - Fix: Use <<graph,graph>> or <<graph,the `graph` property>>, or give the anchor reftext: anchor:graph[graph].
- **gap1-rendered-artifacts#7** `docs/modules/ROOT/pages/reference/nams-ai-provider.adoc:43` — `=>`/`->` inside inline code render as ⇒/→, corrupting TS signatures and Cypher patterns
  - Fix: Wrap each span in a passthrough, e.g. `+(modelId: string) => LanguageModel+` and `+(:User)-[:HAS_PREFERENCE]->(:Preference)+`, or escape the arrow as `-\>`/`=\>`.
- **gap1-rendered-artifacts#8** `docs/modules/ROOT/pages/reference/nams-ai-provider.adoc:96` — Spread example `{ ...tools }` renders as `{ …tools }` (ellipsis character)
  - Fix: Use `+{ ...tools }+`.
- **gap1-rendered-artifacts#6** `docs/modules/ROOT/pages/reference/nams-ai-provider.adoc:163` — Nested backticks in the store_memory input schema break the schema rendering
  - Fix: Drop the inner backticks ("default []") or wrap the whole schema in a passthrough: `+{ content: ... default [] }+`.

### Compare every expected-output or 'you should see' listing with what the program prints (`gap2-gap2-expected-output-vs-progra`)

- **gap2-gap2-expected-output-vs-progra#2** `typescript/examples/langchain/README.md:86` — LangChain example: first turn shows injected memory the program no longer produces
  - Fix: Replace the first-turn line with `memory: nothing recalled yet (first turn)`, shown once per model call (before and after the tool call). Or add a note that it only reads 'injected N lines' when the workspace already holds matching entities.

### Check every documented install command against the imports it enables and the pin rule (`gap2-gap2-install-commands-sweep`)

- **gap2-gap2-install-commands-sweep#9** `README.md:115` — README uvx MCP commands are unpinned although the same README says its instructions use ==0.6.0
  - Fix: Use `uvx --from 'neo4j-agent-memory[mcp,openai]==0.6.0' neo4j-agent-memory mcp serve ...` (and the matching JSON args) in both READMEs.
- **gap2-gap2-install-commands-sweep#5** `docs/modules/ROOT/pages/how-to/typescript/nams-ai-provider-tools-mode.adoc:272` — Tools-mode page documents toolsWithMcp but its install command omits the optional @ai-sdk/mcp peer
  - Fix: Before the toolsWithMcp snippet, add: "Install the optional peer first: `npm install @ai-sdk/mcp@^2`".
- **gap2-gap2-install-commands-sweep#1** `docs/modules/ROOT/pages/reference/cli.adoc:84` — CLI page installs only [cli], but its YAML schema commands need PyYAML, which no extra provides
  - Fix: Change the install to `pip install 'neo4j-agent-memory[cli,gliner]==0.6.0' pyyaml`, or give separate per-command installs, and say that YAML schema files and `schemas show` need PyYAML. Consider adding pyyaml to the [cli] extra.
- **gap2-gap2-install-commands-sweep#8** `docs/modules/ROOT/pages/reference/typescript-api.adoc:41` — TypeScript API reference installs @neo4j-labs/agent-memory without the required exact version
  - Fix: Use `npm install @neo4j-labs/agent-memory@0.5.0` (and the pnpm/bun equivalents) on the reference page and in typescript/README.md.
- **gap2-gap2-install-commands-sweep#6** `examples/domain-schemas/README.md:62` — Installing glirel alone (without loguru) makes --relations silently skip
  - Fix: Use the same (corrected) command as the docs: `pip install glirel 'loguru>=0.7,<1'` plus the huggingface-hub/protobuf/sentencepiece pins.
- **gap2-gap2-install-commands-sweep#10** `examples/strands-session-manager/README.md:64` — Strands READMEs still install from git@main 'until released', though 0.6.0 on PyPI ships the classes
  - Fix: Replace with `uv pip install 'neo4j-agent-memory[strands,sentence-transformers]==0.6.0'` in both strands READMEs.

### Mechanically check Python API names, kwargs, attributes and literals across all pages and partials (`gap2-gap2-python-api-binding-sweep`)

- **gap2-gap2-python-api-binding-sweep#1** `docs/modules/ROOT/pages/reference/backend-capabilities.adoc:30` — Capabilities page implies add_relationship stores attributes; the Bolt write drops them
  - Fix: Change the Bolt cell to e.g. "Supported with `add_relationship(source, target, relationship_type, ...)`; `attributes` are returned on the model but not persisted in 0.6.0", or drop 'and attributes'.
- **gap2-gap2-python-api-binding-sweep#0** `docs/modules/ROOT/pages/reference/ontology-api.adoc:78` — Docs call Python get_active() unreliable, but this branch's SDK source fixes it
  - Fix: Decide which version these pages describe (needs a human decision). If the fix ships in the next Python release, keep the 0.6.0 caveat but say the source/next release reads the authoritative `version`. Add a CHANGELOG entry and list the ActiveOntology fields, including schema_hash, under Return types. Otherwise, if the docs must describe only published 0.6.0, flag the unreleased source change in the PR description.

### Type-check every inline TypeScript block on the docs pages (`gap2-gap2-ts-inline-snippet-typeche`)

- **gap2-gap2-ts-inline-snippet-typeche#0** `docs/modules/ROOT/pages/how-to/typescript/strands.adoc:250` — Manual-wiring Strands block fails strict tsc: Neo4jConversationManager is not a ConversationManager
  - Fix: In the block, import `type ConversationManager` from @strands-agents/sdk and pass `conversationManager: conversationManager as unknown as ConversationManager`, as connect.ts does. Alternatively, have Neo4jConversationManager's public typing satisfy ConversationManager. Change the compatibility sentence to say the test checks the name/reduce/initAgent shape, not full assignability.

### How-to (Bolt core): entities, extraction, dedup, messages, preferences, reasoning, batch (`howto-core-a`)

- **howto-core-a#5** `docs/modules/ROOT/pages/how-to/batch-processing.adoc:420` — Catalog example's "Avoid duplicates" filter never matches GLiNER output types
  - Fix: Filter on the mapped type and subtype, e.g. `if (entity.type, entity.subtype) == ("OBJECT", "PRODUCT") or entity.name in {product["name"], product.get("brand")}: continue`, or compare by name.
- **howto-core-a#2** `docs/modules/ROOT/pages/how-to/deduplication.adoc:57` — find_potential_duplicates confidence is always 0.0 on Bolt, and each pair is returned twice
  - Fix: Fix the query to project `r.confidence AS confidence` and use a directed match (or `elementId(e1) < elementId(e2)`), then keep the doc. Until then, document that confidence is not populated and pairs appear twice in 0.6.0.
- **howto-core-a#1** `docs/modules/ROOT/pages/how-to/deduplication.adoc:63` — Merge claim that every copied edge carries the source id and migrated_from is wrong for most types
  - Fix: State the actual per-type behaviour: RELATED_TO copies keep the source `id` and gain `migrated_from`; provenance, APPLIES_TO and TOUCHED copies gain `migrated_from` only; MENTIONS and SAME_AS copies carry no marker. Alternatively, fix MERGE_ENTITIES so every copy is marked, and correct the docstring.
- **howto-core-a#6** `docs/modules/ROOT/pages/how-to/index.adoc:32` — How-to index says the dedup page reviews a flagged SAME_AS pair; the recipe merges a manual pair
  - Fix: Reword the index entry, e.g. "Merge a known duplicate pair and verify aliases; review flagged SAME_AS candidates with review_duplicate".
- **howto-core-a#4** `docs/modules/ROOT/partials/python-tutorial-setup.adoc:17` — Setup partial on how-to pages tells readers to run a file manifest and offline assembly checks that aren't there _(also: howto-hosted#7, integ-a#7, integ-b#7, tut-py#6)_
  - Fix: Make that sentence conditional ("Tutorials provide a file manifest and offline checks…"), or split out a how-to variant of the partial without it.

### How-to (Bolt core): v0.2 primitives, providers, migration, privacy (`howto-core-b`)

- **howto-core-b#2** `docs/modules/ROOT/pages/how-to/adopt-existing-graph.adoc:52` — Retained anchors for the old dry-run and call sections point to the wrong sections _(also: gap1-compat-anchor-landing#7)_
  - Fix: Move anchor:_3_dry_run_before_mutating[] under '=== 2. Preview the full mapping' and anchor:_2_call_adopt_existing_graph[] under '=== 3. Apply the reviewed mapping'.
- **howto-core-b#4** `docs/modules/ROOT/pages/how-to/adopt-existing-graph.adoc:54` — The note that adoption writes no embeddings was removed
  - Fix: Add a Limitations bullet: adoption writes no embedding, so semantic search does not find adopted nodes until a backfill runs. Link to examples/existing-graph/retrieve.py for the backfill.
- **howto-core-b#9** `docs/modules/ROOT/pages/how-to/bring-your-own-model.adoc:18` — New Prerequisites omit the cli and mcp extras that the MCP CLI sections need
  - Fix: In each 'Configure via the MCP CLI' section, add an install line such as `pip install 'neo4j-agent-memory[cli,mcp,<provider extras>]==0.6.0'`.
- **howto-core-b#6** `docs/modules/ROOT/pages/how-to/configure-embedding-provider.adoc:42` — Claims Bring your own model has runnable embedding-instance code, but that page shows only llm=
  - Fix: Restore the short OpenAIEmbeddingProvider MemorySettings example here, or reword the sentence so it says the BYOM section covers llm= and the Bedrock and Vertex sections below show embedding instances.
- **howto-core-b#8** `docs/modules/ROOT/pages/how-to/migrate-to-providers.adoc:31` — How-tos describe a 'checked-out source' SDK, not the published 0.6.0 package
  - Fix: State the facts for neo4j-agent-memory 0.6.0, for example: 'In 0.6.0, MemorySettings still accepts EmbeddingConfig/LLMConfig and emits DeprecationWarning'. List 'neo4j-agent-memory==0.6.0' as the prerequisite.
- **howto-core-b#5** `docs/modules/ROOT/pages/how-to/multi-tenancy.adoc:30` — The page is still the UserMemory reference target, but the user API and :User schema were removed
  - Fix: Restore a short section with the upsert_user(identifier, attributes=) signature, get_user and list_users, the unique-constraint note and the :User schema bullets. Alternatively, move them to a reference page and repoint memory-client.adoc:83 there.

### How-to: NAMS, ontologies, context-graph MCP, team memory, how-to index (`howto-hosted`)

- **howto-hosted#6** `docs/modules/ROOT/pages/how-to/index.adoc:12` — Retained old anchors land on unrelated sections; stacked [#id] lines are silently overridden
  - Fix: Move each inline anchor to the section that now covers its topic: `_deployment_backend` to Hosted backend, `_core_context_graph_operations` to Core operations, `_entity_extraction_knowledge_building` to Entity extraction, `_next_steps` to See also. Delete the stacked `[#id]` lines that are overridden, or convert them to inline anchors.
- **howto-hosted#3** `docs/modules/ROOT/pages/how-to/index.adoc:53` — Several index blurbs overclaim relative to the rewritten pages (offline, ontology effect, migration effort, audit)
  - Fix: Align each blurb with its page: "...without constructing an LLM provider (Aura still required)"; "...activate a version and verify the active binding"; "...inventory unsupported operations and verify against a sandbox"; "Record explicit audit events and mark conversations for archival".
- **howto-hosted#2** `docs/modules/ROOT/pages/how-to/index.adoc:89` — Two index blurbs describe the opposite of what their target pages do (TypeScript MCP, hybrid provider)
  - Fix: typescript/mcp: "Register the SDK's 12 memory tools on your own MCP server or dispatch them programmatically." aws-hybrid-memory: "Route message, entity and preference retrieval within a Neo4j-backed MemoryClient."
- **howto-hosted#8** `docs/modules/ROOT/pages/how-to/team-memory-in-your-editor.adoc:233` — Cursor prose refers to ${VAR} expansion that the included cursor template does not use
  - Fix: Say: "Replace REPLACE_WITH_YOUR_NAMS_KEY (or use ${MEMORY_API_KEY} if your Cursor build expands variables) and keep the file untracked."
- **howto-hosted#5** `docs/modules/ROOT/pages/how-to/use-nams.adoc:95` — use-nams dropped the NAMS span/observability details and the runnable-example links; no other page has them _(also: x-content-loss#5)_
  - Fix: Add the NAMS span name and attributes to reference/configuration-advanced.adoc (observability) or rest-api.adoc, and point the `_observability` anchor there. Restore the runnable-example links in use-nams 'See also'.
- **howto-hosted#4** `examples/claude-code-team-memory/doctor.py:269` — Included doctor.py and seed_workspace.py still assert '47' hosted tools and a 'Platinum-tier' Cypher feature
  - Fix: Remove HOSTED_NAMS_TOOL_COUNT and print that the hosted surface is scope-dependent, to be checked with tools/list. Update the doctor docstring (line 11) and the seed comment (line 220).

### TypeScript how-tos (non-provider) (`howto-ts`)

- **howto-ts#4** `docs/modules/ROOT/pages/how-to/typescript/integrations-overview.adoc:20` — Overview names the NAMS provider's four modes differently from the mode-selection page
  - Fix: Name the modes as provider, middleware, tools and hooks, and list cross-session search and graph-expanded retrieval as what the automatic modes retrieve.
- **howto-ts#3** `docs/modules/ROOT/pages/how-to/typescript/integrations-overview.adoc:36` — Overview calls neo4j-agent-memory 'the self-hosted package' and sends hosted Python users elsewhere
  - Fix: Don't describe neo4j-agent-memory as self-hosted only. For example: 'For the neo4j-agent-memory package's framework integrations (Bolt or hosted NAMS), see ...'. Have a maintainer confirm that `neo4j_agent_memory_client` exists before publishing it.
- **howto-ts#2** `docs/modules/ROOT/pages/how-to/typescript/mastra.adoc:110` — Mastra follow-up snippet stores only the assistant reply in the new thread and drops the user turn _(also: gap2-gap2-expected-output-vs-progra#5)_
  - Fix: Add `await memory.saveMessage({ threadId: second.id, role: "user", content: "What did I want to book first?" });` before the assistant save.
- **howto-ts#1** `docs/modules/ROOT/pages/how-to/typescript/mcp.adoc:317` — MCP verify step runs `npm run lint`, but the mcp example has no lint script _(also: gap2-gap2-expected-output-vs-progra#3)_
  - Fix: Change the command to `npm run typecheck` and `npm test`, or add a `lint` script to typescript/examples/mcp/package.json.

### Integration how-tos: AWS, Google, index (`integ-a`)

- **integ-a#9** `docs/modules/ROOT/examples/integrations/google_adk_recipe.py:40` — ADK recipe iterates event.content.parts without guarding for None
  - Fix: Guard with `and event.content.parts`, or iterate `event.content.parts or []`.
- **integ-a#4** `docs/modules/ROOT/examples/integrations/hybrid_recipe.py:34` — Hybrid 'explicit route' verification cannot fail; search errors are swallowed
  - Fix: Describe the check as reporting the configured route, not verifying it. Alternatively, assert that message search returned the stored id (for example with threshold 0.0 and a session filter), or call `client.short_term.search_messages` directly so that errors surface.
- **integ-a#8** `docs/modules/ROOT/pages/how-to/integrations/aws-strands.adoc:72` — Strands how-to reuses the tutorial's program and session file but omits its inspect/recovery path
  - Fix: Add the `inspect` phase and a one-line pointer to the tutorial's recovery table. Alternatively, tell readers to run the how-to in a separate folder or with a fresh session file.
- **integ-a#1** `docs/modules/ROOT/pages/how-to/integrations/google-cloud.adoc:122` — 'Deployment reference' link points to the docs-site publication page, not app deployment
  - Fix: Change the xref to xref:reference/deploy-an-application.adoc[the deployment reference].
- **integ-a#6** `docs/modules/ROOT/pages/how-to/integrations/index.adoc:11` — Integrations index drops eleven former section ids, against the preserve-anchors rule
  - Fix: Add `anchor:_quick_start[]` and the other ids near the 'Available integrations' table, as the sibling pages do.
- **integ-a#5** `docs/modules/ROOT/pages/how-to/integrations/index.adoc:33` — Index rows describe Google Cloud and Hybrid pages contrary to their rewritten content
  - Fix: Reword the rows, for example 'Vertex AI embeddings (links to ADK and MCP guides)' and 'Route message/entity/preference searches inside one Neo4j-backed client'. Make the same change on how-to/index.adoc:71.

### Integration how-tos: CrewAI, LangChain, LlamaIndex, Microsoft, OpenAI Agents, PydanticAI (`integ-b`)

- **integ-b#8** `docs/modules/ROOT/pages/how-to/index.adoc:72` — New index entry says Microsoft wiring uses `ChatAgent`, which the page and framework no longer have
  - Fix: Change `ChatAgent` to `Agent` and align the summary with what the page shows.
- **integ-b#5** `docs/modules/ROOT/pages/how-to/integrations/openai-agents.adoc:119` — Overstates what the OpenAI Agents recipe does, and nothing tests the Agents SDK path
  - Fix: Say the recipe registers the tool and the model may call it. Add a contract test that installs openai-agents, or mocks `agents.function_tool`/`Runner.run`, so make_recall_tool and main() are at least imported and built.
- **integ-b#4** `docs/modules/ROOT/pages/how-to/integrations/openai-agents.adoc:121` — execute_memory_tool is named without its import path, and the package root does not export it
  - Fix: Give the import: `from neo4j_agent_memory.integrations.openai_agents.memory import execute_memory_tool`.

### NAMS AI provider family (new pages) vs provider source (`provider`)

- **provider#13** `docs/modules/ROOT/pages/explanation/nams-ai-provider-retrieval.adoc:88` — Explanation says assistant text is skipped only for tool-call-only steps; any step with an app tool call is skipped
  - Fix: Reword it as 'is skipped for any step that calls an app tool, even if that step also produced text'.
- **provider#3** `docs/modules/ROOT/pages/how-to/typescript/nams-ai-provider-hooks-mode.adoc:249` — Hooks-mode expected output shows 3/3/2/2 saved turns; one tool call per turn saves 4
  - Fix: Show 4/4/4/2 and the [nams] system-message lines, or state that the counts include tool-call and tool-result audit turns.
- **provider#6** `docs/modules/ROOT/pages/how-to/typescript/nams-ai-provider-provider-mode.adoc:20` — How-to prerequisites omit OPENAI_API_KEY, which all four programs need by default _(also: x-style#2)_
  - Fix: Add 'An `OPENAI_API_KEY` (or pass a different model factory)' to the Prerequisites on all four how-to pages.
- **provider#7** `docs/modules/ROOT/pages/how-to/typescript/nams-ai-provider-provider-mode.adoc:176` — 'Save as provider-mode.ts' has no matching run step; run instructions assume the repo checkout and src/ _(also: x-style#3)_
  - Fix: Add a standalone run command for the saved file (for example `MEMORY_API_KEY=... OPENAI_API_KEY=... npx tsx provider-mode.ts`), and present the repo-checkout command as the alternative.
- **provider#2** `docs/modules/ROOT/pages/how-to/typescript/nams-ai-provider-tools-mode.adoc:207` — Tools-mode expected output: wrong line order, missing final-step lines and turn-2 fallback line
  - Fix: Regenerate the expected output from a real or mocked run, in both the page and the example's header comment, or move the header print before agent.generate() and skip steps that have no tool calls.
- **provider#12** `docs/modules/ROOT/pages/reference/nams-ai-provider.adoc:6` — Reference claims 'every export' but omits exported types, including tool result shapes
  - Fix: Add the QueryOutput, StoreOutput and McpConnectionStatus shapes and a short list of the remaining exported type names, or soften 'every export' to 'the public API'.
- **provider#10** `docs/modules/ROOT/pages/reference/nams-ai-provider.adoc:43` — baseProvider typed as `(modelId) => LanguageModel`; a string model id is not accepted
  - Fix: Document it as `(modelId: string) => LanguageModelV4 | LanguageModelV3 | LanguageModelV2` (a model object, not a string id).
- **provider#9** `docs/modules/ROOT/pages/reference/nams-ai-provider.adoc:163` — query_memory limit documented as 1–20 without noting that results are capped at 12
  - Fix: Add 'at most 12 hits are returned regardless of `limit`' in both places.
- **provider#11** `docs/modules/ROOT/pages/reference/nams-ai-provider.adoc:217` — loadSession documented as 'Never throws', but it throws when no userId is available
  - Fix: Say 'Never throws on a backend error (returns `[]`); throws if no userId is set on the call or on createNamsHooks().'

### Python examples and their tests (`py-examples`)

- **py-examples#7** `Makefile:105` — `make help` describes docs-lint as 'Watch for changes and rebuild' _(also: tooling-ci#7)_
  - Fix: Change the help text to something like "Check doc sources and a fresh rendered build (links, images, diagrams, render checks)", and fix the column alignment.
- **py-examples#2** `Makefile:569` — Makefile, CLAUDE.md and examples/.env.example still describe Docker auto-start; READMEs now say Aura
  - Fix: Pick one story. Either keep the Docker path as a documented local alternative in AURA_SETUP.md and the example READMEs, or update the Makefile comments, CLAUDE.md:2039/2066 and examples/.env.example to the Aura flow.
- **py-examples#6** `examples/README.md:209` — Contributor guidance no longer asks for a 'verified against' footer, but the registry test requires one
  - Fix: Keep the words "a 'Verified against …' footer" in step 3, or widen the test regex to accept the new wording.
- **py-examples#3** `examples/eval-harness/README.md:100` — README says the eval runner ignores NEO4J_DATABASE, but main.py reads it _(also: howto-core-b#1, gap2-gap2-expected-output-vs-progra#4)_
  - Fix: Replace the sentence with "NEO4J_DATABASE defaults to neo4j" and add NEO4J_DATABASE to the YAML env block if a non-default database is used.
- **py-examples#8** `examples/financial-services-advisor/google-cloud-financial-advisor/GETTING_STARTED.md:13` — FSA GETTING_STARTED Node floors contradict the Node 22.13+/24 floor the branch set in the READMEs
  - Fix: Update both GETTING_STARTED tables to the same Node floor as the READMEs.
- **py-examples#4** `examples/lennys-memory/README.md:130` — Lenny's README says the backend reads NEO4J_DATABASE; the backend has no such setting
  - Fix: Say that only the loading scripts honour NEO4J_DATABASE and the backend uses the default `neo4j` database, or add a neo4j_database field to the backend config and pass it to Neo4jConfig.
- **py-examples#5** `examples/microsoft_agent_retail_assistant/README.md:369` — BaseContextProvider ImportError troubleshooting lost its fix and now points at a missing file _(also: gap2-gap2-markdown-link-check#2)_
  - Fix: Restore a concrete action, for example "Upgrade to neo4j-agent-memory 0.6.0 (`pip install -U 'neo4j-agent-memory[microsoft-agent,...]==0.6.0'`) and agent-framework GA", and remove the dead link.

### Python library, dependencies and their tests (`py-lib`)

- **py-lib#4** `CHANGELOG.md:8` — Branch changes shipped behaviour in src but leaves CHANGELOG [Unreleased] empty _(also: gap1-backend-support-labels#9)_
  - Fix: Add [Unreleased] entries for the get_active() contract change (including the new ValueError and schema_hash), the forked-chain fix in CREATE_MESSAGE and GET_LAST_MESSAGE, the Bolt/httpx import boundary, and the removal of the mkdocs docs group.
- **py-lib#3** `src/neo4j_agent_memory/graph/queries.py:11` — ORDER BY on GET_LAST_MESSAGE makes the tail lookup scan every message in the conversation
  - Fix: Accept the cost and document it, or track the tail explicitly (for example a LAST_MESSAGE relationship or a c.last_message_id property updated under the conversation lock) so neither query needs to scan the conversation.
- **py-lib#1** `tests/integration/test_short_term_memory.py:433` — Forked-chain test builds a fork races never produce; migrate 'repair' leaves the fork edge
  - Fix: Build the fork the way a race does, with two messages each receiving NEXT_MESSAGE from the same predecessor. Also assert that no message has more than one outgoing NEXT_MESSAGE after migrate. Either make MIGRATE_MESSAGE_LINKS delete out-of-order NEXT_MESSAGE edges before merging, or soften the queries.py:81 comment to 'restores a single tail'.

### Python API reference: MemoryClient, adapters, factory, LLM provider, long-term family (`ref-api-a`)

- **ref-api-a#5** `docs/modules/ROOT/pages/reference/api/adapters.adoc:13` — Overview promises an extra-to-adapter mapping that the 'Adapter availability' section lacks
  - Fix: Add a table to 'Adapter availability' mapping each extra to its adapters (for example [openai] -> OpenAIProvider, OpenAIEmbeddingProvider; [anthropic] -> AnthropicProvider; [bedrock] -> BedrockProvider, BedrockEmbeddingProvider; [litellm] -> LiteLLMProvider, LiteLLMEmbeddingProvider; [sentence-transformers], [vertex-ai], [instructor]), or reword the Overview sentence to match what the section contains.
- **ref-api-a#4** `docs/modules/ROOT/pages/reference/api/llm-provider.adoc:215` — Escaped `\{...}` renders with a literal backslash in the built page
  - Fix: Revert to `{...}`, or use a passthrough such as `+{...}+` inside the backticks.
- **ref-api-a#1** `docs/modules/ROOT/pages/reference/api/long-term-entities.adoc:79` — search_entities prose claims a subtype control that does not exist (also NAMS table 'Bolt subtypes')
  - Fix: Change line 79 to "Semantic search with entity-type and similarity-threshold controls." and change long-term-geospatial.adoc:133 to "Bolt `entity_types` (list) and `threshold` are not sent."
- **ref-api-a#2** `docs/modules/ROOT/pages/reference/api/long-term-geospatial.adoc:136` — NAMS table omits that get_entity_relationships takes an id and returns a different shape
  - Fix: Add to the row: "Takes an entity id (not a name) and returns `list[Relationship]`, not `(Entity, Relationship)` tuples."
- **ref-api-a#3** `docs/modules/ROOT/pages/reference/api/memory-client.adoc:92` — Says unsupported calls raise NotSupportedError; bolt-only long_term methods raise AttributeError on NAMS _(also: gap1-backend-support-labels#6)_
  - Fix: memory-client.adoc:92: "Unsupported accessors and Protocol methods raise `NotSupportedError`; bolt-only methods that NAMS does not define (for example `get_preferences_by_category`) raise `AttributeError`." In geospatial:138, name the methods that raise, or add `get_preferences_by_category` to the 'not exposed' row.

### Python API reference: short-term and reasoning families (`ref-api-b`)

- **ref-api-b#6** `docs/modules/ROOT/pages/reference/api/reasoning-search-stats.adoc:43` — search_steps note implies steps have no embeddings unless complete_trace generates them
  - Fix: Say that steps recorded with `generate_embedding=False` (including the StreamingTraceRecorder default) need `complete_trace(..., generate_step_embeddings=True)` before step search can find them, and that an embedder is required in all cases.
- **ref-api-b#5** `docs/modules/ROOT/pages/reference/api/reasoning-search-stats.adoc:141` — On NAMS, only get_tool_stats raises NotSupportedError; the other tool-stat methods raise AttributeError
  - Fix: Change the row to `get_tool_stats` and say that `migrate_tool_stats` and `get_tool_usage_stats` do not exist on NAMS and raise AttributeError.
- **ref-api-b#4** `docs/modules/ROOT/pages/reference/api/reasoning-steps.adoc:6` — The steps page says "Bolt only" though NAMS implements add_step, record_tool_call and link_trace_to_message
  - Fix: Say that these signatures are the bolt ones and link to the NAMS lifecycle table on reasoning-search-stats.adoc for hosted behaviour, on both reasoning-steps.adoc and reasoning-traces.adoc.
- **ref-api-b#2** `docs/modules/ROOT/pages/reference/api/short-term-messages.adoc:124` — delete_message raises a Neo4j error for stored messages; it does not return False
  - Fix: Say that on bolt, for messages stored through `add_message`, the call currently raises a Neo4j constraint error because the conversation and sequence relationships remain, and that False is returned only for unknown or invalid IDs.
- **ref-api-b#1** `docs/modules/ROOT/pages/reference/api/short-term-messages.adoc:147` — NAMS create_conversation looks like session_id is optional, but calling it without one raises TypeError
  - Fix: State that NAMS also requires a `session_id` (or the `conversation_id` alias). It is used only as the local `Conversation.session_id` label, and the server-issued `Conversation.id` is the value to pass to later calls.

### Configuration, environment variables, CLI, MCP tools, schema objects (`ref-config`)

- **ref-config#5** `docs/modules/ROOT/pages/reference/cli.adoc:244` — CLI `--profile` row says extended = 16 tools, but on NAMS the server registers 20
  - Fix: Change the Click help in src/neo4j_agent_memory/cli/main.py (--profile) to "core (6 tools) or extended (16 tools on bolt, 20 on NAMS)" and regenerate the table row, or add a note under the table.
- **ref-config#4** `docs/modules/ROOT/pages/reference/configuration-operations.adoc:37` — `<<integration-limits>>` renders with raw link text "[integration-limits]"
  - Fix: Write `<<integration-limits,integration limits>>` on lines 37 and 58, or use `<<_integration_limits>>`, which resolves to the section title.
- **ref-config#3** `docs/modules/ROOT/pages/reference/configuration.adoc:10` — Compatibility anchors for old Embedding/LLM sections forward to the wrong subpage bullets _(also: x-style#0, gap1-compat-anchor-landing#0)_
  - Fix: Move `_python_configuration_2`, `_environment_variables_2`, `_parameters_2`, `_python_configuration_6` and `_environment_variables_6` from the line 10/12 bullets to the providers bullet on line 11.

### Extractor and schema reference family (`ref-extract-schema`)

- **ref-extract-schema#3** `docs/modules/ROOT/pages/reference/extractor-builder.adoc:103` — with_llm_fallback is called a fallback, but build() runs the LLM on every extraction
  - Fix: Describe the method as adding an LLM stage that runs alongside the other stages and whose results are merged. To get real fallback behaviour, build ExtractionPipeline directly with stop_on_success=True or MergeStrategy.FIRST_SUCCESS.
- **ref-extract-schema#2** `docs/modules/ROOT/pages/reference/extractor-relations.adoc:12` — GLiREL install note omits spaCy and en_core_web_sm, which GLiRELExtractor needs for tokenization
  - Fix: Add that GLiRELExtractor also needs the `spacy` extra and `python -m spacy download en_core_web_sm`, or link to the how-to install step.
- **ref-extract-schema#1** `docs/modules/ROOT/pages/reference/extractor-streaming.adoc:10` — Says the 4000/200 chunk defaults change when token chunking is selected; the constructor keeps them
  - Fix: State that the constructor defaults are 4000/200 whatever the chunking mode, so pass chunk_size/overlap explicitly with chunk_by_tokens=True, or use create_streaming_extractor(chunk_by_tokens=True), which defaults to 1000 tokens and 50 overlap.
- **ref-extract-schema#4** `docs/modules/ROOT/pages/reference/schemas-custom.adoc:28` — DomainSchema example calls GLiNEREntityExtractor without importing it
  - Fix: Import both: `from neo4j_agent_memory.extraction import DomainSchema, GLiNEREntityExtractor`.
- **ref-extract-schema#5** `docs/modules/ROOT/pages/reference/schemas-custom.adoc:55` — SchemaManager(client.graph) goes through the deprecated graph proxy; load_schema emits a DeprecationWarning
  - Fix: Say what the SchemaManager constructor actually needs (a connected Neo4jClient). Show a Neo4jClient built from settings, or note that passing client.graph triggers the execute_read deprecation warning. Maintainers may prefer a non-deprecated public accessor in the SDK.

### Reference: backends, REST, NAMS limits/MCP, ontology/skills API, auth, TypeScript API, deployment (`ref-other`)

- **ref-other#6** `docs/modules/ROOT/pages/reference/deploy-an-application.adoc:32` — Self-hosted MCP server options list Bolt as the only backend; server also runs against NAMS
  - Fix: Say 'Bolt (a Neo4j instance you operate) or NAMS (`--backend nams` / `MEMORY_API_KEY`)' and name `MEMORY_API_KEY` among the credentials.
- **ref-other#3** `docs/modules/ROOT/pages/reference/nams-limits.adoc:46` — Language-neutral limits page says 'the SDK retries' and raises RateLimitError; TS does neither
  - Fix: Qualify these sentences as Python SDK behavior, note that the TypeScript client does not retry (link typescript-api#errors / handle-errors), and change '5xx' at line 27 to 500/502/503/504.
- **ref-other#4** `docs/modules/ROOT/pages/reference/nams-limits.adoc:94` — 'Capability matrix' links point to backends.adoc section that is no longer a matrix
  - Fix: Point these three references at xref:reference/backend-capabilities.adoc[backend capabilities] and reword 'capability matrix'.
- **ref-other#7** `docs/modules/ROOT/pages/reference/skills-api.adoc:49` — Skills page still fixes the MCP surface at '13 tools' after nams-mcp dropped fixed counts
  - Fix: Use one policy. Either say 'the tools below (per the service contract; confirm with tools/list)' here, or restore the counts on nams-mcp.adoc.
- **ref-other#5** `docs/modules/ROOT/pages/reference/typescript-api.adoc:321` — waitForExtraction prose says search limit is always at least 10; an explicit smaller limit wins
  - Fix: Say 'the search limit defaults to 10 and is raised to at least `minResults` and the number of expected names'.
- **ref-other#2** `docs/modules/ROOT/pages/reference/typescript-api.adoc:441` — getActive/activate rows contradict the revised ontology-api page and the HEAD TS source
  - Fix: Update the two rows to match ontology-api.adoc: `getActive()` returns the document plus the binding metadata from the response's `version` (absent for legacy responses; see the 0.5.0 caveat), and `activate()` binds the version without implying enforcement.
- **ref-other#8** `examples/claude-code-team-memory/README.md:225` — README links to nams-mcp for 'the 47-tool surface', but this branch removed that count
  - Fix: Decide on one policy. If counts are unguaranteed, reword both READMEs ('a scope-dependent surface; confirm with tools/list') and relax the test assertion. Otherwise restore the count on nams-mcp.adoc.

### Docs tooling, Antora extensions, UI JS, Makefile, CI workflows (`tooling-ci`)

- **tooling-ci#6** `.claude/skills/docs-excalidraw/SKILL.md:247` — Excalidraw skill tells authors to embed PNG exports with no caption, against MAINTAINING's SVG/caption rule
  - Fix: Change the skill to reference `.svg`, require a `.Caption` line and a manifest entry. Make add-refs emit the SVG path and a caption placeholder, or remove add-refs.
- **tooling-ci#4** `.github/workflows/ci-python.yml:683` — New tests/docs/test_nav_labels.py is not run by any CI job _(also: docs-tests-b#2)_
  - Fix: Add tests/docs/test_nav_labels.py to the docs-tests job, for example to the 'Run documentation link validation' step.
- **tooling-ci#5** `scripts/check_docs.py:62` — Image alt-quoting check flags valid named attributes whose quoted value has a comma
  - Fix: Tokenize the attribute list the way AsciiDoc does: treat quotes after `name=` as quoting the value. Alternatively, check only that the first positional field is quoted when it contains a comma.

### New TypeScript examples: nams-ai-provider, vercel-ai tutorials, shared tutorial helpers (`ts-ex-a`)

- **ts-ex-a#4** `typescript/examples/nams-ai-provider/README.md:112` — Hooks-mode README and header comment get the turn count and hook firing wrong _(also: provider#5, provider#4)_
  - Fix: README: four turns; [hook] lines come from Stop (once per turn) and SessionEnd. Comment: say which events fire on every turn and which fire once.
- **ts-ex-a#2** `typescript/examples/nams-ai-provider/src/hooks-mode.ts:121` — Entry-point check `file://${argv[1]}` silently does nothing when the path has spaces or other encoded characters _(also: provider#8)_
  - Fix: Compare against `pathToFileURL(realpathSync(process.argv[1])).href` (or reuse isTutorialEntryPoint), then re-embed the programs on the four how-to pages.

### Other TypeScript examples (`ts-ex-b`)

- **ts-ex-b#4** `typescript/examples/cloudflare-agents-edge/README.md:39` — README says the suite checks the abort and error settle paths, but no test covers either
  - Fix: Add tests that cancel the response body mid-stream and that make the mock model or NAMS fail, then assert that the deferred promise settles and nothing partial is stored. Otherwise remove 'The suite checks this lifecycle' and the 'abort or error' wording from the assertions list.
- **ts-ex-b#5** `typescript/examples/nextjs-memory-chat/README.md:111` — The streaming-persistence section misdescribes both the Cloudflare pattern and `persistInteractions: false`
  - Fix: Drop 'the client can see' (say 'observable by the server/runtime'). State that `persistInteractions: false` disables both user-turn and assistant-turn writes, so the explicit write must store both.
- **ts-ex-b#6** `typescript/examples/nextjs-memory-chat/README.md:120` — 'Build the shared packages' section makes two wrong claims: a shared tsconfig and that everything runs on current source
  - Fix: Remove the tsconfig.base.json clause for this example. Qualify the 'current source' claim by noting that the provider resolves its own devDependency copy of the SDK, or make the provider link resolve the in-tree SDK (for example, install the provider with install-links or dedupe).

### TypeScript SDK source and tests (`ts-sdk`)

- **ts-sdk#3** `typescript/README.md:80` — Edge-runtime sentence was left ungrammatical by a partial edit _(also: x-consistency#12)_
  - Fix: For example: "How edge runtimes expose environment variables differs: Cloudflare Workers pass bindings to the handler, while others (such as Vercel Edge) may provide `process.env`. Pass the key explicitly:"

### Python hosted tutorials (NAMS quickstart, ontology, skills) (`tut-hosted-py`)

- **tut-hosted-py#1** `docs/modules/ROOT/examples/hosted_tutorial_state.py:79` — inspect-file handoff summary omits the ontology's previous active version needed to restore the binding
  - Fix: Include a redacted restoration target in inspect_file(), e.g. `ontology: {previous: {version_id, ontology_id, revision, validation_mode}, clone_id, strict: {version_id}, status, restored, deleted}` without the document. Alternatively, say in the partial/ontology page that the owner also needs the previous active version ID and mode, and where to find them.
- **tut-hosted-py#2** `docs/modules/ROOT/pages/tutorials/nams-quickstart.adoc:11` — Step 3's first-write record is never recorded in the ledger or cleaned up
  - Fix: Either record the Step 3 conversation and message in the ledger and have cleanup remove them, or add an explicit deletion step for them, e.g. a DELETE of that conversation with readback. At minimum, tell the reader that this record is outside the lesson's cleanup.
- **tut-hosted-py#3** `docs/modules/ROOT/pages/tutorials/nams-quickstart.adoc:296` — Page says Use NAMS documents context, graph expansion and Cypher, but it covers none of them
  - Fix: Point to pages that do document these calls: reference/rest-api.adoc (context, /graph/expand, /query rows), reference/api/long-term.adoc for expand_graph, and how-to/use-ontologies.adoc for ontology management. Or add a short how-to covering the removed hosted calls.
- **tut-hosted-py#5** `docs/modules/ROOT/pages/tutorials/skills-quickstart.adoc:255` — After publish detects changed provenance, the page doesn't say to rerun inspect
  - Fix: Add: "After reviewing the new skills-review.json, run `python skills_quickstart.py inspect --state ...` again, then `publish`."

### Python tutorials (Bolt/Aura and local) (`tut-py`)

- **tut-py#4** `docs/modules/ROOT/pages/tutorials/knowledge-graph.adoc:22` — GLiREL xref lands on a legacy anchor on the index page, not on the explanation it promises
  - Fix: Change the xref to xref:reference/extractor-relations.adoc#_glirelextractor[the GLiRELExtractor reference].
- **tut-py#0** `docs/modules/ROOT/pages/tutorials/microsoft-agent-memory.adoc:12` — Preview note calls Microsoft Agent Framework 'pre-1.0' while the page pins the 1.x GA line _(also: integ-b#3)_
  - Fix: Keep the Preview label for the adapter but drop 'pre-1.0'. For example: 'tracks Microsoft Agent Framework 1.x (>=1.13,<2); APIs on either side can change between releases.' Make the same change in how-to/integrations/microsoft-agent.adoc:11.
- **tut-py#2** `docs/modules/ROOT/pages/tutorials/microsoft-agent-memory.adoc:96` — Shared model-selection partial asks for Chat Completions support, but this lesson uses the Responses API
  - Fix: Make the API name a parameter of the partial (for example an attribute set to 'Responses' on this page), or add a sentence on this page saying the model must support the Responses API.
- **tut-py#3** `docs/modules/ROOT/pages/tutorials/microsoft-agent-memory.adoc:101` — Missing OPENAI_MODEL is only detected after the preference has been written
  - Fix: Add the same presence/placeholder check after the exports, or read and validate OPENAI_MODEL at the top of main() before add_preference.
- **tut-py#1** `docs/modules/ROOT/partials/aura-tutorial-setup.adoc:22` — Docs say the Aura helper has 'no fallback database', but aura_config() defaults to 'neo4j' _(also: docs-examples-py#3)_
  - Fix: Add NEO4J_DATABASE to `required` and drop the default in aura_connection.py, or change the partial and the manifest rows to say the database defaults to 'neo4j' when unset.
- **tut-py#5** `docs/modules/ROOT/partials/python-typescript-equivalents.adoc:8` — Equivalents table pairs add_messages_batch with bulkAddMessages; the Python counterpart is bulk_add_messages
  - Fix: Map `bulk_add_messages` to `bulkAddMessages`, optionally noting that `add_messages_batch` is the Bolt-only form with progress callbacks.

### TypeScript tutorials (`tut-ts`)

- **tut-ts#5** `docs/modules/ROOT/pages/tutorials/conversation-memory-typescript.adoc:121` — Recall step says to expect output the program never prints (the retrieved memory)
  - Fix: Say to expect `Stored messages verified before this question: 1`, followed by a model answer that recalls both facts. Or have the program print the recalled context.
- **tut-ts#4** `docs/modules/ROOT/pages/tutorials/hosted-quickstart-typescript.adoc:79` — Lessons send readers to the API reference for reasoning cleanup limits, but it doesn't cover them
  - Fix: Add a short note to the `client.reasoning` section of reference/typescript-api.adoc: the hosted service has no verified delete route for steps or tool calls, so they persist until the workspace owner removes them. Or change the three sentences so they no longer promise cleanup information.
- **tut-ts#3** `docs/modules/ROOT/partials/typescript-tutorial-checkout.adoc:1` — Pages say Node.js 22 or later, but every command uses `--env-file-if-exists` (Node 22.9+)
  - Fix: State 'Node.js 22.9 or later' in the checkout partial and the MCP prerequisites, or use a flag that works on 22.0.

### Cross-cutting: consistency of facts across docs, READMEs and CLAUDE.md (`x-consistency`)

- **x-consistency#8** `typescript/README.md:8` — New text calls the Python SDK Experimental, but its package metadata says Beta
  - Fix: Choose one maturity level for the Python SDK and make the badges, the typescript/README sentence and the pyproject classifier agree.

### Cross-cutting: content loss and anchor breakage from the big rewrites (`x-content-loss`)

- **x-content-loss#6** `docs/modules/ROOT/pages/faq.adoc:21` — About 60 section fragments from before the branch no longer resolve, contrary to 4052e1b's 'every section id was preserved' claim
  - Fix: Add anchor:<old-id>[] macros for these ids next to the matching current section (the pattern the hubs already use). Consider extending scripts/check_docs.py to diff rendered ids against a stored baseline so section renames are caught.
- **x-content-loss#7** `docs/modules/ROOT/pages/getting-started.adoc:38` — Python extras table removed; several extras ([opentelemetry], [fuzzy], [cli] install) now undocumented
  - Fix: Restore a compact extras table, preferably in sdks/python.adoc or a reference page (the CLAUDE.md table is a good source), and name the extra in configuration-advanced's observability section.
- **x-content-loss#3** `docs/modules/ROOT/pages/how-to/integrations/langchain.adoc:100` — LangChain middleware/retriever options and NAMS session_id requirement no longer documented anywhere
  - Fix: Add a compact option table for Neo4jMemoryMiddleware and Neo4jMemoryRetriever to the 'Adapt the integration' section or to reference/api/adapters.adoc, including the NAMS session_id note.
- **x-content-loss#4** `docs/modules/ROOT/pages/how-to/integrations/pydantic-ai.adoc:96` — nams_memory_tools() (the PydanticAI hosted tool set) dropped from all docs
  - Fix: Add one sentence to 'Adapt the integration' naming nams_memory_tools(client) for NAMS and the extra tools it returns.

### Cross-cutting: diagrams, exports, manifest, captions (`x-diagrams`)

- **x-diagrams#2** `docs/assets/diagrams/excalidraw/nams-ai-provider-modes.excalidraw:852` — Modes diagram says NAMS retrieves and persists automatically in every mode, contradicting tools/hooks
  - Fix: Reword the NAMS box and caption: automatic before/after only for provider and middleware; tools mode on model tool calls; hooks mode when the app calls prepare()/onFinish(). Or draw per-mode trigger labels on the arrows.
- **x-diagrams#0** `docs/assets/diagrams/excalidraw/poleo-model.excalidraw:1` — Published POLE+O diagram shows five subtypes the SDK rejects
  - Fix: Replace the invalid subtypes with real ones (e.g. PERSON: Individual, Alias, Persona, Witness; EVENT: Meeting, Transaction, Incident, Communication; ORGANIZATION: Company, Government, Nonprofit, Educational), re-export, then update the manifest hashes and diagram-descriptions.md.
- **x-diagrams#7** `docs/assets/images/diagrams/diagram-descriptions.md:3` — diagram-descriptions.md disagrees with the manifest and with the diagrams' own text _(also: gap2-gap2-markdown-link-check#1)_
  - Fix: Update the header paths and SVG wording, drop the stale title claim, and rewrite section 7 from the current scene (or remove the file if it is no longer maintained).
- **x-diagrams#3** `docs/diagrams/manifest.json:26` — Manifest statuses inverted: stale PNGs recorded as clean, fresh SVGs as unresolved
  - Fix: Re-export the three PNGs (or drop them) and record their hashes. Set the SVG siblings to pending-placement and remove the 'Untracked file' notes.
- **x-diagrams#4** `docs/diagrams/manifest.json:204` — memory-architecture.svg referring_pages omits memory-types.adoc, which now embeds it
  - Fix: Add memory-types.adoc to referring_pages. Optionally have check_manifest() verify that referring_pages matches the pages that actually embed each output.
- **x-diagrams#6** `docs/diagrams/source-migrations.json:40` — Migration record points to a scene that does not exist
  - Fix: Point the record at three-extraction-approaches.excalidraw, or mark it as retired/replaced.
- **x-diagrams#8** `docs/modules/ROOT/pages/how-to/integrations/aws-strands.adoc:115` — Strands caption says embeddings feed all three surfaces; diagram says two
  - Fix: Change the caption and alt text to say the embeddings feed the memory store and graph tools, or change the diagram if all three are intended.
- **x-diagrams#9** `docs/modules/ROOT/pages/how-to/reasoning-traces.adoc:11` — Reasoning-trace caption promises touched entities that the diagram does not draw
  - Fix: Drop 'and touched entities' from the caption and alt text, or say that TOUCHED links are noted but not drawn.

### Cross-cutting: security and secret-handling sweep (`x-security`)

- **x-security#3** `examples/lennys-memory/README.md:270` — Claude Desktop MCP snippet still passes --password password with no URI after the Aura migration
  - Fix: Replace the args-based password with an env block that sets NEO4J_URI (neo4j+s://...), NEO4J_USER, NEO4J_PASSWORD and NEO4J_DATABASE placeholders, add `--backend bolt`, and note that the populated Desktop config is private (as deploy/mcpb/README.md now does).

### Cross-cutting: Diataxis and house-rule compliance of pages added by this branch (`x-style`)

- **x-style#1** `docs/modules/ROOT/pages/reference/extractors.adoc:17` — Old GLiRELExtractor anchors _constructor_5/_example_5 now forward to the builder page _(also: gap1-compat-anchor-landing#2, ref-extract-schema#6)_
  - Fix: Move `anchor:_constructor_5[]anchor:_example_5[]` to the relation-extractors bullet that links reference/extractor-relations.adoc.

## Nits (53), by area

### Cloud Run and MCPB deployment assets (`deploy`)

- **deploy#7** `deploy/cloudrun/README.md:122` — Review-process narration left in the user-facing deployment README
  - Fix: Remove the paragraph, or rephrase it as reader guidance, e.g. "Run the local build and the proxied round trip in your own project before relying on the deployment."

### Docs tests: tutorial and hosted-lifecycle contract tests (`docs-tests-a`)

- **docs-tests-a#1** `tests/docs/test_hosted_tutorial_contracts.py:149` — Skills seed runs only against permissive fakes; its SDK calls are never checked against real NAMS signatures
  - Fix: Add a parametrized test like test_tutorial_calls_bind_to_current_python_api for the hosted programs (nams_quickstart, skills_quickstart, hosted_tutorial_state), binding against NamsShortTermMemory, NamsLongTermMemory and the NAMS reasoning class. Or build the fakes with create_autospec(..., instance=True) on those classes.

### Docs tests: build, checker, links, nav, diagrams, contracts, rendered site (`docs-tests-b`)

- **docs-tests-b#12** `tests/docs/test_code_snippets.py:246` — Stale comments and docstrings still describe the removed async wrapper and allowed_missing allowlist
  - Fix: Update the docstrings and comments to match the current behaviour.
- **docs-tests-b#10** `tests/docs/test_nav_labels.py:29` — Stale ALLOWED_DIVERGENCE entry exempts how-to/integrations/index.adoc from drift detection
  - Fix: Remove the how-to/integrations/index.adoc entry from ALLOWED_DIVERGENCE.

### Entry points: index, getting started, SDK pages, nav, READMEs, CLAUDE.md, CONTRIBUTING, MAINTAINING (`entry`)

- **entry#1** `docs/modules/ROOT/pages/getting-started.adoc:66` — Former 'Next steps' / 'Where to go next' section ids dropped on getting-started and both SDK pages
  - Fix: Add `anchor:_next_steps[]` under 'See also' in getting-started.adoc (line 68), and `anchor:_where_to_go_next[]` under the 'See also' headings in sdks/python.adoc (line 58) and sdks/typescript.adoc (line 105).

### Explanation pages, glossary, FAQ (`explanation`)

- **explanation#8** `docs/modules/ROOT/pages/explanation/why-provider-protocol.adoc:87` — llm=None check attributed to _resolve_providers; it lives in _validate_llm_consistency
  - Fix: Attribute step 5 to the following `_validate_llm_consistency` validator.
- **explanation#9** `docs/modules/ROOT/pages/glossary.adoc:15` — Reasoning 'observation' described as a tool call's result; it is a ReasoningStep field
  - Fix: Describe it as a reasoning step's recorded observation (often derived from a tool result), part of the step's thought/action/observation.

### Do kept compatibility anchors land on matching content? (`gap1-compat-anchor-landing`)

- **gap1-compat-anchor-landing#26** `docs/modules/ROOT/pages/explanation/backends.adoc:18` — Stacked [#id] block lines: only the last survives; earlier ones are dead, duplicated ids
  - Fix: Keep one anchor per id (inline anchor:_x[] at the intended spot) and remove the stacked [#] lines that cannot take effect.
- **gap1-compat-anchor-landing#24** `docs/modules/ROOT/pages/how-to/entity-extraction-schemas.adoc:82` — Persist and GLiREL ids open on the next section, not on their own content
  - Fix: Move those three anchors next to anchor:_relationship_extraction[] at line 60.

### Compare every expected-output or 'you should see' listing with what the program prints (`gap2-gap2-expected-output-vs-progra`)

- **gap2-gap2-expected-output-vs-progra#6** `docs/modules/ROOT/pages/tutorials/skills-quickstart.adoc:274` — Skills download 'Expected' leaves out the attestation reminder printed before the listing
  - Fix: Add the second line to the Expected text: '..., then `Inspect skills-attestation.json; ZIP validation does not verify its signature`, then the archive listing.'

### Check every documented install command against the imports it enables and the pin rule (`gap2-gap2-install-commands-sweep`)

- **gap2-gap2-install-commands-sweep#11** `examples/no_llm/README.md:67` — no_llm README install is unpinned while its main.py (shown on the docs page) was changed to ==0.6.0
  - Fix: Pin the README command to ==0.6.0 to match main.py and the docs page.

### Mechanically link-check every changed Markdown file, including fragments and docs-site deep links (`gap2-gap2-markdown-link-check`)

- **gap2-gap2-markdown-link-check#4** `typescript/examples/nams-ai-provider/README.md:132` — README names ../vercel-ai/test/docs-hosted-stub.js; the file on disk is .ts
  - Fix: Change it to `../vercel-ai/test/docs-hosted-stub.ts`, or link to the file.

### How-to (Bolt core): entities, extraction, dedup, messages, preferences, reasoning, batch (`howto-core-a`)

- **howto-core-a#7** `docs/modules/ROOT/pages/how-to/batch-processing.adoc:60` — Chunk intro refers to a `deduplicate` keyword "shown below" that the code block doesn't use
  - Fix: Reword to "…instead of waiting for the combined result; the alternative `extract(..., deduplicate=True)` path is described after the example", and update the link texts to the new titles.
- **howto-core-a#8** `docs/modules/ROOT/pages/how-to/deduplication.adoc:14` — Redundant legacy anchors duplicate section auto-ids, so the sections render as _prerequisites_2 and _see_also_2 _(also: gap1-compat-anchor-landing#25)_
  - Fix: Drop the two inline anchors; the headings already generate `_prerequisites` and `_see_also`.

### How-to (Bolt core): v0.2 primitives, providers, migration, privacy (`howto-core-b`)

- **howto-core-b#11** `docs/modules/ROOT/pages/how-to/consolidation.adoc:28` — Changed xref link texts use stale or inconsistent titles for their target pages
  - Fix: Use each target's current title in the link text, or use an empty xref text so Antora supplies the title.

### How-to: NAMS, ontologies, context-graph MCP, team memory, how-to index (`howto-hosted`)

- **howto-hosted#10** `docs/modules/ROOT/pages/how-to/migrate-to-nams.adoc:14` — "the installation and connection check below" links to another page
  - Fix: Drop "below" or say "in Connect a Python application to NAMS".
- **howto-hosted#11** `docs/modules/ROOT/pages/how-to/team-memory-in-your-editor.adoc:170` — Seed step says it creates a conversation but omits that it also writes two entities to the shared workspace
  - Fix: Say: "...creates a conversation, adds two fixture entities (Atlas, Helios) and waits for extraction."
- **howto-hosted#9** `docs/modules/ROOT/pages/how-to/use-ontologies.adoc:120` — Appendix cross-reference <<_list_the_catalog>> points to the wrong section for the get_active note
  - Fix: Give the NOTE its own id (for example [#get-active-note]) and link to that, or move the note into section 1.

### TypeScript how-tos (non-provider) (`howto-ts`)

- **howto-ts#6** `docs/modules/ROOT/pages/how-to/typescript/integrations-overview.adoc:36` — Restructure keeps four old section anchors but drops the four TypeScript ones (and nextjs `_compatibility`)
  - Fix: Add `[[_vercel_ai_sdk_typescript]]`, `[[_langchain_js_typescript]]`, `[[_mastra_typescript]]` and `[[_strands_agents_typescript]]` to the matching table rows or guide links, and add `anchor:_compatibility[]` near the nextjs compatibility sentence.
- **howto-ts#7** `docs/modules/ROOT/pages/how-to/typescript/vercel-ai.adoc:143` — New streaming snippet defaults to gpt-4o-mini while the rest of the page uses gpt-5-mini _(also: gap2-gap2-ts-inline-snippet-typeche#1)_
  - Fix: Use `"gpt-5-mini"` in the streaming snippet.

### Integration how-tos: AWS, Google, index (`integ-a`)

- **integ-a#10** `docs/modules/ROOT/pages/how-to/integrations/aws-bedrock-embeddings.adoc:32` — Credential setup is instructed after the block that already runs aws sts get-caller-identity
  - Fix: Move the credential sentence above the bash block.
- **integ-a#11** `docs/modules/ROOT/pages/how-to/integrations/aws-hybrid-memory.adoc:77` — Retained hybrid anchors land on text that no longer mentions their topic
  - Fix: Add a sentence naming `get_session_memories`, `clear_session` and `get_entity_relationships` next to those anchors.

### Integration how-tos: CrewAI, LangChain, LlamaIndex, Microsoft, OpenAI Agents, PydanticAI (`integ-b`)

- **integ-b#9** `docs/modules/ROOT/pages/how-to/integrations/langchain.adoc:98` — get_conversation readback is shown without await
  - Fix: Write `(await client.short_term.get_conversation(session_id)).messages`.
- **integ-b#10** `docs/modules/ROOT/pages/how-to/integrations/microsoft-agent.adoc:117` — Screenshot is captioned as a TfL Explorer example application that doesn't exist in the repo
  - Fix: Remove the screenshot, or link the application it comes from. Otherwise use a screenshot of the linked retail assistant example.

### NAMS AI provider family (new pages) vs provider source (`provider`)

- **provider#14** `docs/modules/ROOT/pages/how-to/typescript/nams-ai-provider-hooks-mode.adoc:269` — Turn-4 card redaction is credited to PreMemoryWrite; UserPromptSubmit already redacted the saved prompt
  - Fix: Say that UserPromptSubmit redacts what the model sees and saves, and that PreMemoryWrite is a second line of defence for anything the model's reply or tool records echo back.

### Python examples and their tests (`py-examples`)

- **py-examples#10** `examples/financial-services-advisor/aws-financial-services-advisor/README.md:17` — 'through a example architecture' (should be 'an example')
  - Fix: Change to "through an example architecture" in both files.
- **py-examples#9** `examples/ontology-lifecycle/README.md:169` — Expected output drops the 'Done. Inspect …' prefix that main.py still prints
  - Fix: Change the README line to "Done. Inspect support-desk at https://memory.neo4jlabs.com. Retained ontology: ont_01J…. …".

### Python library, dependencies and their tests (`py-lib`)

- **py-lib#2** `src/neo4j_agent_memory/graph/queries.py:72` — The 'appends serialize' claim does not cover add_messages_batch, which can still fork the chain
  - Fix: Either limit the comment to single-message appends and note the batch gap, as the commit message does for _ensure_conversation, or take the conversation lock (SET c.updated_at) and read the tail inside the same transaction as the batch insert and linking.
- **py-lib#5** `src/neo4j_agent_memory/nams/ontology.py:285` — Python accepts a non-string version.schema_json; TypeScript rejects it
  - Fix: In _parse_active_version, raise ValueError when schema_json is not None and not a str, matching TypeScript, and add that case to the test_rejects_invalid_supplied_binding parametrization.

### Python API reference: MemoryClient, adapters, factory, LLM provider, long-term family (`ref-api-a`)

- **ref-api-a#6** `docs/modules/ROOT/pages/reference/api/memory-client.adoc:80` — query.cypher shown with a 'parameters' argument; the real parameter is 'params'
  - Fix: Write `await client.query.cypher(query, params)`.

### Python API reference: short-term and reasoning families (`ref-api-b`)

- **ref-api-b#7** `docs/modules/ROOT/pages/reference/api/reasoning-steps.adoc:78` — Internal page named as a code literal instead of an xref
  - Fix: Replace it with xref:how-to/audit-reasoning.adoc[Audit reasoning with `:TOUCHED` edges].
- **ref-api-b#3** `docs/modules/ROOT/pages/reference/api/reasoning.adoc:34` — The hub says the hosted lifecycle limits are "below", but they are on a subpage
  - Fix: Replace "below" with xref:reference/api/reasoning-search-stats.adoc#_nams_lifecycle_and_operations[NAMS lifecycle and operations].

### Configuration, environment variables, CLI, MCP tools, schema objects (`ref-config`)

- **ref-config#6** `docs/modules/ROOT/pages/reference/configuration.adoc:6` — Hub page still says field tables are "below" after they moved to subpages; "in this checkout" wording
  - Fix: Replace "below" with links to the relevant subpage, and "in this checkout" with "in 0.6.0".

### Extractor and schema reference family (`ref-extract-schema`)

- **ref-extract-schema#7** `docs/modules/ROOT/pages/reference/extractor-builder.adoc:93` — Sphinx roles (:meth:, :class:) copied from docstrings render literally in AsciiDoc
  - Fix: Remove the roles: "alias of `with_llm_fallback`" and "from an `EntitySchemaConfig`".
- **ref-extract-schema#8** `docs/modules/ROOT/pages/reference/extractor-relations.adoc:29` — Docstring bullet lists are flattened into single table cells
  - Fix: Rewrite as prose, e.g. "A dict of name to description (recommended), a list of names, or None for the default POLE+O relation types." Move the "Yields" text out of the parameter cell.

### Docs tooling, Antora extensions, UI JS, Makefile, CI workflows (`tooling-ci`)

- **tooling-ci#8** `.claude/skills/docs-diataxis/SKILL.md:189` — Skill says `npm run serve` previews the existing build, but the script rebuilds first
  - Fix: Change the comment to `# Build once and serve a static preview`.
- **tooling-ci#9** `.github/workflows/ci-typescript.yml:152` — Comment says nine of ten examples ship a vitest suite; all ten do
  - Fix: Change the comment to 'All ten ship an offline vitest suite'.

### New TypeScript examples: nams-ai-provider, vercel-ai tutorials, shared tutorial helpers (`ts-ex-a`)

- **ts-ex-a#5** `typescript/examples/nams-ai-provider/test/docs-pages.test.ts:6` — Test header and README still say the doc pages do not exist yet ("another worker") _(also: provider#15)_
  - Fix: Rewrite both to say the pages embed the programs verbatim and that the test fails whenever they drift.

### Other TypeScript examples (`ts-ex-b`)

- **ts-ex-b#8** `typescript/examples/langchain/README.md:31` — 'Graph, not buffer' bullet describes a readback that the run does not end with
  - Fix: Say that the run ends by printing three-tier context counts and one expandGraph hop, and describe the readback under Act 1.
- **ts-ex-b#9** `typescript/examples/mastra/test/fake-nams.ts:5` — Garbled sentence in the fake's header comment
  - Fix: Change to: 'The fake keeps messages per conversation, which proves the program explicitly reads the selected prior thread.'
- **ts-ex-b#7** `typescript/examples/nextjs-memory-chat/test/routes.test.ts:199` — Test comment says memory is appended as a second text part; the provider prepends it as the first
  - Fix: Reword to: 'prepended to the last user message as its first text part'.

### Python hosted tutorials (NAMS quickstart, ontology, skills) (`tut-hosted-py`)

- **tut-hosted-py#6** `docs/modules/ROOT/pages/tutorials/nams-quickstart.adoc:70` — The nams_first_write.py listing has no '.Save as' title, contrary to MAINTAINING.md
  - Fix: Add `.Save as \`nams_first_write.py\`` above the listing.

### Cross-cutting: consistency of facts across docs, READMEs and CLAUDE.md (`x-consistency`)

- **x-consistency#14** `examples/README.md:53` — Examples index still states '47 scope-gated tools', a count the hosted MCP reference now declines to give
  - Fix: Drop the count from examples/README.md:53 (and examples/claude-code-team-memory/README.md:28), or restore it in nams-mcp.adoc once a maintainer verifies it.
- **x-consistency#13** `typescript/README.md:50` — npm install commands are unpinned, against the pin rule MAINTAINING.md adds
  - Fix: Use `@neo4j-labs/agent-memory@0.5.0` in these places, or record the package README as a deliberate exception in MAINTAINING.md.

### Cross-cutting: diagrams, exports, manifest, captions (`x-diagrams`)

- **x-diagrams#12** `docs/assets/diagrams/excalidraw/multi-tenant-scoping.excalidraw:1` — Re-authored diagrams break house style: roughness 0 and labels well under 20px
  - Fix: Raise the labels to about 20px, set roughness to 1 and apply the semantic colours, then re-export.
- **x-diagrams#13** `docs/modules/ROOT/images/diagrams/three-extraction-approaches.svg:1` — three-extraction-approaches.svg is a byte-identical copy of extraction-pipeline.svg
  - Fix: Drop three-extraction-approaches.svg and its manifest record, or point README at one name.
- **x-diagrams#10** `scripts/manage_diagrams.py:55` — add-refs still inserts PNG embeds without a caption, against the new SVG policy
  - Fix: Use the .svg path and emit a `.{title}` caption line before the image macro.

### Cross-cutting: security and secret-handling sweep (`x-security`)

- **x-security#2** `examples/claude-code-team-memory/README.md:97` — README puts literal OpenAI and Aura credentials in a repo-root .cursor/mcp.json that git does not ignore
  - Fix: Add `.cursor/mcp.json` (or `.cursor/`) to .gitignore. Reword line 97 so the literal-credential instruction applies only to Desktop and Cursor, and say plainly that Claude Code's .mcp.json keeps ${VAR} references.

### Cross-cutting: Diataxis and house-rule compliance of pages added by this branch (`x-style`)

- **x-style#10** `docs/modules/ROOT/nav.adoc:20` — Nav drops the '(Preview)' label from the Agent Skills entries but keeps it elsewhere
  - Fix: Add '(Preview)' back to the two Agent Skills nav entries, or remove it from all entries consistently.
- **x-style#4** `docs/modules/ROOT/pages/how-to/typescript/nams-ai-provider-hooks-mode.adoc:274` — Mode how-tos don't end with verification: long reference sections follow 'Run and verify'
  - Fix: End each mode page's body with 'Run and verify'. Move the 'specifics' material into reference/nams-ai-provider.adoc, or the retrieval explanation where it's conceptual, and link to it. Rewrite 'Procedure' as reader actions or rename it (for example 'How the program works').
- **x-style#7** `docs/modules/ROOT/pages/how-to/typescript/nams-ai-provider.adoc:33` — 'Choose a NAMS AI provider mode' is a comparison and reference page filed as a how-to
  - Fix: Replace the configuration and environment tables with a link to the reference. Either frame the page as a short decision guide (what to do for each mode: install, pick, go to the mode page) or move the comparison to an explanation/landing page.
- **x-style#8** `docs/modules/ROOT/pages/reference/backend-capabilities.adoc:9` — Reference pages contain editorial notes about their own former layout, and tutorial narrative
  - Fix: Drop the layout-history sentences. Reduce the tutorial paragraph to the capability fact (no DELETE route for steps, tool calls or skills) and link to the tutorials.
- **x-style#9** `docs/modules/ROOT/pages/reference/schemas-custom.adoc:8` — schemas-custom reference keeps how-to material and unlabeled partial snippets
  - Fix: Rename the heading to a noun phrase (for example 'DomainSchema'), add the `GLiNEREntityExtractor` import, and add a 'Partial snippet' title or note to the persistence and observability snippets. Or link to how-to/entity-extraction-schemas.adoc for the procedure.

## Appendix A — uncertain and disputed

- **ts-sdk#4** [uncertain, nit] `typescript/README.md:8` — New README claim that the Python SDK is 'Experimental' contradicts the package's Beta classifier. Verifier: The facts are right. The new text at typescript/README.md:7-8 calls the Python SDK Experimental, and pyproject.toml:29 declares `Development Status :: 4 - Beta`. However, the root README.md:6 `Status: Experimental` badge predates the branch (present at ec9fc65), so the new sentence matches the repository's existing public label and does not introduce a new contradiction. The pyproject/README misma
- **tut-hosted-py#4** [uncertain, minor] `docs/modules/ROOT/pages/tutorials/skills-quickstart.adoc:280` — attestationConfigured is presented as part of the attestation file, but it comes from /skills/capabilities. Verifier: skills-api.adoc:28 documents attestationConfigured only on /v1/skills/capabilities, and the program saves that response in state.data['capabilities'] (skills_quickstart.py:325). skills-attestation.json holds the /verify response (skills_quickstart.py:263-264). The page at :279-281 mentions attestationConfigured right after printing that file. However, the /verify response shape isn't documented or
- **x-consistency#11** [uncertain, minor] `README.md:195` — Aura quickstarts hardcode anthropic/claude-3-5-sonnet-latest, unlike the tutorial's reader-supplied model. Verifier: README.md:195 and README-pypi.md:107 do hardcode `anthropic/claude-3-5-sonnet-latest`, and the tutorial reads ANTHROPIC_MODEL instead. But the line already existed on main (ec9fc65:README.md:149), and the branch only changed the surrounding recipe. Two things I could not settle from the repository: whether this model id is currently rejected by the Anthropic API (retirement is external knowledge),

## Appendix B — refuted by verifiers

- tooling-ci#3 `.github/workflows/ci-python.yml:676` — CI never runs check_docs source checks (nav coverage, hub routes, alt quoting) against real pages. Why refuted: tests/docs/test_links.py:157-163 (test_quadrant_indexes_link_to_content, changed on this branch) calls `source_report(docs_dir)` and asserts no errors. conftest.py:38-42 sets `docs_dir` to the real pages directory. CI runs test_links.py (ci-python.yml:678), so the source checks do run against the re
- deploy#2 `deploy/cloudrun/README.md:82` — New `--service-account` deploy needs actAs on the runtime SA; README never names the grant. Why refuted: The README does name the requirement. Prerequisites, deploy/cloudrun/README.md:9: 'Permission to create the required resources, deploy using the runtime service account, and grant ... roles/run.invoker'. Line 82 also says the build/deploy principal needs its own permissions, distinct from the runtim
- deploy#6 `deploy/mcpb/README.md:24` — "Maintained tutorial" link opens raw Antora source for a different server setup. Why refuted: Linking README files to the .adoc sources under docs/modules/ROOT/pages is an established repo pattern: typescript/README.md:109-110, typescript/examples/mcp/README.md:90 and typescript/examples/vercel-ai/README.md:129-132 do the same. So the 'raw Antora source' link is not a defect specific to this
- docs-tests-b#4 `tests/docs/utils/extract_code.py:208` — Snippet extractor can drop Python blocks silently: no count guard, and partials/ is not scanned. Why refuted: The main claim, that nothing checks the SDK imports of the example files included through partials, is false. Every one of those 8 blocks is only an `include::example$X.py[]` line. Contract tests load each file with importlib: core_memory_recipes and extraction_recipes in test_core_python_tutorials.
- howto-core-b#10 `docs/modules/ROOT/pages/how-to/running-without-an-llm.adoc:90` — The no-LLM summary table omits the PIPELINE configuration the page itself uses. Why refuted: The table row at running-without-an-llm.adoc:90 ('`llm=None` + `extractor_type=SPACY/GLINER/NONE`, `enable_llm_fallback=False`') is identical to the ec9fc65 version (old line 81). The ec9fc65 Configuration section also already used ExtractorType.PIPELINE. The branch changed only the Notes column of 
- integ-b#6 `docs/modules/ROOT/pages/how-to/integrations/crewai.adoc:14` — CrewAI page says Python 3.10+, but the locked CrewAI version needs Python below 3.14. Why refuted: 'Python 3.10+' is not new: the ec9fc65 crewai.adoc had 'Python 3.10+' at line 54. The reader's install resolves `crewai>=1.0,<2` (pyproject.toml:177), not the locked 1.6.1. Whether a newer crewai 1.x supports 3.14 could not be checked offline, so there is no evidence that a reader fails. The branch 
- x-diagrams#5 `docs/assets/diagrams/excalidraw/bolt-vs-nams-data-flow.excalidraw:1188` — Two referenced scenes use exportScale 2, doubling SVG width to near the undersize threshold. Why refuted: The facts are right: exportScale is 2 in bolt-vs-nams-data-flow and multi-agent-boundaries, and the SVGs declare viewBox 708 with width=1416 and viewBox 668 with width=1336. But nothing fails and no reader is affected. Both embeds use width=100%, so on-screen size comes from the column width against
- x-security#4 `examples/google_cloud_integration/README.md:235` — Troubleshooting step exposes the unauthenticated MCP HTTP server on 0.0.0.0 against the Aura database. Why refuted: The branch did not introduce the 0.0.0.0 binding. The old line (ec9fc65 examples/google_cloud_integration/README.md:241) was already `neo4j-agent-memory mcp serve --transport http --host 0.0.0.0 --port 8080 &`. It already served whatever NEO4J_URI pointed to, and the branch only added --backend bolt
- x-security#5 `docs/modules/ROOT/partials/aura-tutorial-setup.adoc:15` — Tutorials have readers export literal secrets on the command line, where they persist in shell history. Why refuted: The partial is new, and it does show `export NEO4J_PASSWORD='replace-with-the-generated-password'` (docs/modules/ROOT/partials/aura-tutorial-setup.adoc:15). But exporting placeholder credentials in a tutorial is standard practice. docs/MAINTAINING.md has no rule against it (grep for history/secret/u
- x-consistency#9 `README.md:340` — Root README's Development section still uses the nonexistent path cd agent-memory/neo4j-agent-memory. Why refuted: README.md:340 `cd agent-memory/neo4j-agent-memory` is really wrong: that directory does not exist. But the branch did not touch this line; `git diff ec9fc65..HEAD -- README.md` has no change there, and main already had the same bad path. The branch only fixed the copy in CONTRIBUTING.md, so the READ
- gap1-backend-support-labels#3 `docs/modules/ROOT/pages/how-to/entities.adoc:7` — Entities page keeps 'NAMS: Yes' label after rewrite to a Bolt-only relationship/fact recipe. Why refuted: The page already included backend-both at ec9fc65 (old line 9), so this branch did not introduce the label. Entity create/search are available on NAMS, so "Yes, with differences" is accurate. The page names the Bolt specifics explicitly. Step 1 is "Prepare the Bolt client". python-core-recipe-intro.
- gap1-backend-support-labels#4 `docs/modules/ROOT/pages/how-to/multi-tenancy.adoc:5` — Multi-tenancy page newly labelled NAMS 'Yes' while every Python step fails on NAMS. Why refuted: backend-both is new here, but the page scopes things correctly. Line 7 says "associate Bolt conversation writes". The prerequisites (line 15) require "a connected Python MemoryClient using Bolt". A dedicated "TypeScript counterpart (NAMS)" section (line 104) gives the NAMS path, and line 121 says NA
- gap2-gap2-install-commands-sweep#7 `docs/modules/ROOT/pages/how-to/bring-your-own-model.adoc:171` — Framework pass-through snippet imports langchain_anthropic, but no install on the page adds it. Why refuted: The `from langchain_anthropic import ChatAnthropic` snippet predates the branch (ec9fc65 bring-your-own-model.adoc:134, migrate-to-providers.adoc:120); the branch only pinned the install lines. The section frames the snippet as handing off 'a model you've already configured with your agent framework

## Appendix C — coverage notes per area

### ex-python — Python static checks, unit tests, example and docs tests (no Neo4j) (2 of 2 findings confirmed)

Ran from repo root at HEAD (e2bcb93 on docs-review), merge-base ec9fc65.

1. `make check` — FAILED at format-check (lint passed; format-check failed; typecheck and ty run separately below since the target aborts on first failure).
   - `lint` (ruff check): PASS — "All checks passed!"
   - `format-check` (ruff format --check): FAIL — 3 files not formatted: tests/docs/test_docs_checker.py, tests/docs/test_nav_labels.py, tests/docs/test_rendered_site.py (all touched/added by this branch per `git log ec9fc65..HEAD`). Reported as a blocker finding (CI's ci-python.yml "Run ruff format check" step runs this exact command).
   - `typecheck` (mypy --strict, run separately): PASS — "Success: no issues found in 151 source files" plus all 11 example main.py files pass.
   - `ty` (run separately): FAIL locally with 2 `unresolved-import` diagnostics for `gliner` in src/neo4j_agent_memory/extraction/gliner_extractor.py. Verified this is a pre-existing local-environment gap, not a branch regression: the file is untouched by this branch (`git diff ec9fc65..HEAD` on it is empty), `gliner` is simply not installed in this venv (`uv run python -c "import gliner"` → ModuleNotFoundError), and CI's ty job runs after `uv sync --all-extras --group dev` which would install it. Not reported as a finding; noted here per instructions to mention pre-existing/environment issues in coverage only.

2. `make test-unit`: PASS — 1854 passed, 0 failed, 11 warnings (all in files untouched by this branch: tests/unit/integrations/test_google_adk.py, tests/unit/mcp/test_mcp_cli.py, tests/unit/nams/test_cli_nams.py — pre-existing, not findings).

3. `uv run pytest tests/examples -q -rs`: 4 failed, 918 passed, 53 skipped, 1 xfailed on first run. All 4 failures are in `tests/examples/test_examples_registry.py`, parametrized over an `examples/ontology-extraction/` directory that exists only as a stray, untracked, gitignore-shadowed leftover (containing solely a `__pycache__/main.cpython-312.pyc`) from a prior local checkout of an unrelated branch/commit (`b296ae2`, not on this branch's history: `git log --oneline ec9fc65..HEAD` is empty for that path, `git ls-files examples/ontology-extraction` is empty, `git status --short` does not list it). It is not part of `git diff ec9fc65..HEAD` and is picked up only because `_example_dirs()` walks every non-underscore/dot directory under `examples/`. Confirmed the branch's own change to `_example_dirs()`/`test_examples_registry.py` (adding `TS_NOT_AN_EXAMPLE` for the TypeScript side) does not touch this Python-side helper's exclusion logic. Treated as local environment noise, not a branch defect; not reported as a finding. All other examples tests (918) pass; the 53 skips are expected (no live Neo4j / no AWS creds / vector-index dimension mismatch from a differently-configured local Neo4j, `set NEO4J_URI to run the example end-to-end`) and are not branch-caused.

4. `SKIP_INTEGRATION_TESTS=1 uv run pytest tests/docs -q -rs`: first run had 1 failed, 853 passed, 169 skipped — the failure (`test_microsoft_selected_client_and_agent_constructor_match_current_package`) was `ModuleNotFoundError: agent_framework_openai` not installed locally; confirmed this is exactly the extra CI installs separately via `uv pip install 'agent-framework-openai>=1.13,<2'` in ci-python.yml (a step this branch did not touch: `git log ec9fc65..HEAD -- .github/workflows/ci-python.yml` shows only doc/tutorial-related commits, that install step already existed). After installing that one package locally, reran the full suite clean: 854 passed, 169 skipped, 0 failed. The three pre-existing main-branch failures named in the task brief (preference-search related) were not encountered because SKIP_INTEGRATION_TESTS=1 skips test_howto_examples.py and test_tutorial_examples.py entirely in this mode — consistent with the task's expectation that they "skip cleanly" here.
   - One warning surfaced and persisted across reruns: `PytestUnknownMarkWarning: Unknown pytest.mark.rendered` from tests/docs/test_rendered_site.py:21, a file newly added by this branch. Reported as a finding (minor) since it's a warning this branch introduced and the fix is one line in pyproject.toml.

5. `python3 scripts/check_docs.py --help`: printed usage as expected (--build | --site-dir, --report). Then ran the source-only path (no --build/--site-dir, as instructed — another executor covers --build): `uv run python3 scripts/check_docs.py --report <scratchpad>/check_docs_report.json` → "Checked 145 pages; 0 errors." Clean pass.

New test modules added by this branch (`git diff --diff-filter=A --name-only ec9fc65..HEAD -- tests`): tests/docs/test_aura_tutorial_persona.py (23 passed), test_aura_tutorial_setup.py (39 passed), test_cloudrun_assets.py (4 passed), test_core_python_tutorials.py (105 passed), test_diagram_manifest.py (4 passed), test_docs_checker.py (32 passed), test_hosted_tutorial_cleanup.py (38 passed), test_hosted_tutorial_contracts.py (36 passed), test_hosted_tutorial_lifecycle.py (23 passed), test_nav_labels.py (15 passed), test_ontology_tutorial.py (42 passed), test_operational_howto_contracts.py (18 passed), test_python_integration_contracts.py (32 passed), test_python_reference_contracts.py (175 passed), test_rendered_site.py (7 passed, 1 warning), test_skills_tutorial.py (19 passed), plus tests/unit/test_bolt_optional_dependencies.py (1 passed). None of the new modules skipped everything; none need reporting under the "new test module that skipped everything" rule.

Not run / out of scope per task: `--build` docs build (explicitly deferred to another executor), Neo4j-backed integration tests (RUN_INTEGRATION_TESTS not set), TypeScript checks (separate task per branch conventions), and hosted-NAMS-credential tests.

Repository state: `git status --short` at the end shows only the pre-existing untracked `docs/audit-evidence/2026-09-17/` (explicitly out of scope per task) plus one unexpected tracked-file diff: `typescript/examples/nams-ai-provider/package-lock.json` (one line, a `"peer": true` removed from a transitive dep entry). I did not run any npm/yarn/typescript command in this session — every command I ran was `uv run`/`python3`/`make check`/`make test-unit`/pytest, none of which touch that subtree — so I cannot attribute this to a command I issued. Flagging it here per the "tracked file changed" instruction since I could not identify the cause; a human should check whether something else in the environment (e.g. an IDE, a background process, or a stale npm install from before this session) touched it, since it is not something this review session did.

### ex-integration — Neo4j-backed integration and docs tests via testcontainers (0 of 0 findings confirmed)

Environment: `docker info` succeeded, so the Docker-dependent checks ran via testcontainers (RUN_INTEGRATION_TESTS=1) as instructed.

Checks run, all against HEAD of docs-review, from /Users/lyonwj/github/neo4j-labs/agent-memory:

1. `RUN_INTEGRATION_TESTS=1 uv run pytest tests/integration/test_short_term_memory.py -v` — 26 passed, 0 failed, 0 skipped (~15s). Includes the new TestForkedChainRecovery and TestMessageLinking classes covering the CREATE_MESSAGE/GET_LAST_MESSAGE rewrite.

2. `RUN_INTEGRATION_TESTS=1 uv run pytest tests/integration -q -rs` — 527 passed, 92 skipped, 0 failed (~87s). All skips are expected: NAMS sandbox/TCK tests (no MEMORY_API_KEY/NAMS_SANDBOX_KEY), AWS integration tests (no AWS credentials), Vertex AI integration tests (no GOOGLE_CLOUD_PROJECT), and ontology tests gated behind RUN_ISOLATED_ONTOLOGY_TESTS=1 (deliberately not enabled — shared workspace). No new/unexpected skips found.

3. `RUN_INTEGRATION_TESTS=1 uv run pytest tests/docs -q -rs` — 877 passed, 142 skipped, 4 failed initially (~89s). Three of the four failures are exactly the documented pre-existing failures (TestPreferencesHowTo::test_store_preferences, TestMessagesHowTo::test_search_messages_semantic, TestConversationMemoryTutorial::test_store_user_preferences — all `search_preferences`/`search_messages` returning empty because the local sentence-transformers/mock embedder used in this environment doesn't produce close-enough vectors for these queries; matches the task's pre-existing-failure list). The fourth failure, `test_microsoft_selected_client_and_agent_constructor_match_current_package`, is NOT a branch defect: it needs the separately-published `agent-framework-openai` package, which `.github/workflows/ci-python.yml` installs explicitly at line ~201-202 ("Install framework documentation client": `uv pip install 'agent-framework-openai>=1.13,<2'`) as a dedicated step right after `uv sync --group dev --all-extras` and before this specific test file runs. My initial `uv sync --all-extras` (used for tests/docs as a whole) does not include that package since it isn't declared in any pyproject.toml extra (by design — see the code comment at pyproject.toml:190-199). After manually installing `agent-framework-openai>=1.13,<2` to mirror the CI step, `uv run --no-sync pytest tests/docs/test_python_integration_contracts.py -q --timeout=60` passed 32/32. So this is an environment-setup gap in my own run, not a branch bug or CI misconfiguration; CI's own job correctly installs it before running that exact test file.

4. Stress test beyond the committed suite: wrote /private/tmp/claude-502/-Users-lyonwj-github-neo4j-labs-agent-memory/66a2977c-9670-4b56-8270-fc84ea0f1100/scratchpad/review/stress_create_message.py, which starts its own Neo4j 5.26-community testcontainer, then for 5 rounds: adds 1 message to establish the conversation (matching the documented pattern in test_concurrent_message_additions, since `_ensure_conversation`'s own read-then-create race for brand-new sessions is explicitly called out in that test's docstring as a separate, out-of-scope data-model issue, not something CREATE_MESSAGE/GET_LAST_MESSAGE fix), then fires 24 more `add_message` calls concurrently via `asyncio.gather` (25 total), then verifies via Cypher: exactly one `FIRST_MESSAGE`, exactly one tail (no outgoing NEXT_MESSAGE), an unbroken NEXT_MESSAGE chain from FIRST_MESSAGE to the tail covering every HAS_MESSAGE node exactly once, and no constraint errors from `asyncio.gather(..., return_exceptions=True)`. Then calls `add_messages_batch` with 5 more messages and re-verifies the same invariants for all 30 messages, confirming the batch links after the true (concurrently-established) tail. All 5 rounds passed cleanly with zero problems reported — no forked chains, no orphaned messages, no duplicate/missing chain coverage, no exceptions. This is consistent with (and stress-confirms beyond the committed unit-level tests) the CREATE_MESSAGE rewrite's locking comment in src/neo4j_agent_memory/graph/queries.py:71-73 (the `SET c.updated_at = datetime()` write-lock-then-read-tail pattern serializing concurrent appends to one conversation). My first script attempt (25 fully-concurrent adds with no pre-established conversation) reproduced the pre-existing, already-documented `_ensure_conversation` multi-conversation race — this is explicitly out of scope per the committed test's own docstring (tests/integration/test_short_term_memory.py:350-355) and is not something this branch's CREATE_MESSAGE change claims to fix, so I did not report it as a finding against this branch's diff.

Not fully covered / needs a human decision: I did not line-by-line review the Antora docs content itself (nav/xref/API-claims accuracy) — the task scoped my work specifically to the Neo4j-backed integration/docs-test/testcontainers workstream, and I stayed within that scope as instructed ("you are an executor: your job is to run checks and report failures, not to read the diff line by line"). A separate reviewer presumably covers the documentation content itself.

Repository state: `git status --short` at the end shows `docs/audit-evidence/2026-09-17/` still untracked (pre-existing, not reviewed per instructions) and, unexpectedly, `typescript/examples/nams-ai-provider/package-lock.json` modified (one line removed: a stray `"peer": true` on a `dev` dependency entry). I did not run any npm/node/typescript command in this session — all commands I ran were `uv run`/`git`/`docker info`/Python script execution scoped to the Python SDK and a scratch script. I cannot attribute this change to any command I issued, and did not revert it since git-state-changing commands are disallowed by the rules; flagging it here as required so a human can check whether something else in the environment (e.g., an IDE extension, editor autosave, or background process) touched it, or whether it predates this session's snapshot.

### ex-docs — Documentation build, checkers, rendered-site and link/image checks (1 of 1 findings confirmed)

Scope: docs build/checkers/rendered-site/link-image checks only (per assigned sub-task), on branch docs-review at HEAD e2bcb93, merge-base ec9fc65.

Commands run (all exit 0, no new failures found vs. main):
1. `cd docs && npm run build` (Antora) — clean, zero warnings/errors in the log (grep -iE "warn|error" on log: no matches).
2. `uv run python3 scripts/check_docs.py` — "Checked 145 pages; 0 errors."
3. `uv run python3 scripts/check_docs.py --build` — "Checked 145 pages; 0 errors."
4. `uv run python3 scripts/manage_diagrams.py status` — "45 tracked image exports in the provenance manifest / 54 canonical editable scenes"; `... missing` — "All published image sources and exports are current."
5. `cd docs && npm run lint` — delegates to check_docs.py --build; "Checked 145 pages; 0 errors."
6. `uv run pytest tests/docs/test_rendered_site.py tests/docs/test_build_pipeline.py tests/docs/test_links.py tests/docs/test_nav_labels.py tests/docs/test_diagram_manifest.py tests/docs/test_docs_checker.py -q -rs` — 87 passed, 0 skipped, 1 warning (see finding). Playwright was available so test_rendered_site.py ran for real, not skipped.
7. Own link/fragment/image checker (script at scratchpad/review/linkcheck.py) walked every HTML file under docs/build/site: 0 broken internal links (excluding root-relative `/docs/...`, `/labs/` links, which are the Neo4j Labs UI-bundle nav/footer pointing at the production site, not local build targets — expected to 404 locally), 0 broken same-page or cross-page `#fragment` anchors, 0 broken `<img>`/`<object>` sources. The one root-relative-looking miss (`_attachments/api/typescript/index.html` → `media/LICENSE`) is inside the generated TypeDoc output, excluded from review per task instructions.
8. Image reference check: cross-referenced `docs/modules/ROOT/images/**` against `image::`/`image:` includes in pages+partials. ~20 files (mostly `diagrams/*.svg`/`.png` pairs, plus `assets/logo.svg`/`favicon.svg` which are UI-bundle assets not page images) have no `image::` include. Verified this is a known, tracked, deliberate state, not a defect: `docs/diagrams/manifest.json` (e.g. line 170) explicitly notes some outputs as "already-unreferenced, pending-placement... Left on disk pending maintainer triage", and `scripts/manage_diagrams.py missing` (the authoritative checker) reports nothing missing. Not filed as a finding.

Only issue found: an unregistered pytest marker (`rendered`) used by a new test file, producing a `PytestUnknownMarkWarning` (reported as a finding).

Not caused by my commands, noted for transparency: `git status --short` at the end shows `typescript/examples/nams-ai-provider/package-lock.json` as modified (a `"peer": true` line removed) in addition to the pre-existing untracked `docs/audit-evidence/2026-09-17/`. None of the commands I ran in this sub-task touch the `typescript/` tree (no npm install/build there), so I cannot attribute this to anything in my command list; it may be another concurrent process on this machine. Flagging for the orchestrator/human to check `git diff typescript/examples/nams-ai-provider/package-lock.json` and decide whether to revert.

Not covered (out of scope for this sub-task, per the assignment which covers only docs build/checkers/rendered-site/links): line-by-line diff review of Python/TypeScript source changes, CI workflow correctness, and content-accuracy review of prose against SDK source — those are presumably other reviewers' sub-tasks in this comprehensive review.

### ex-ts — TypeScript SDK, provider package, ten examples, TypeDoc freshness (0 of 0 findings confirmed)

Scope: typescript/ SDK (lint, test:unit, test:integration, build), typescript/packages/vercel-ai-provider (typecheck, test, build, npm pack --dry-run), all ten typescript/examples/* directories (tsc --noEmit, npm test --if-present, npm run build --if-present), and TypeDoc freshness (regenerated into scratchpad and diffed against docs/modules/ROOT/attachments/api/typescript).

Results, all green:
- typescript/: `npm run lint` (tsc --noEmit + tsc -p tsconfig.test.json) clean; `npm run test:unit` 293/293 pass; `npm run test:integration` 96/96 pass; `npm run build` (tsup) succeeded.
- typescript/packages/vercel-ai-provider: `npm run typecheck` clean; `npm test` 136/136 pass (one test's stderr output is the test itself exercising an error path, not a failure); `npm run build` succeeded; `npm pack --dry-run` produced a 16-file, 92.4kB tarball with no errors.
- All 10 example directories under typescript/examples/ (cloudflare-agents-edge, eve-commerce-agent, langchain, mastra, mcp, nams-ai-provider, nextjs-memory-chat, ontology-lifecycle, strands, vercel-ai) match exactly the `type-check-examples` matrix in .github/workflows/ci-typescript.yml (verified by reading the matrix). Ran `npx tsc --noEmit`, `npm test --if-present`, `npm run build --if-present` in each (nextjs-memory-chat's build ran a real `next build`; eve-commerce-agent's ran `eve build`; cloudflare-agents-edge's ran `wrangler deploy --dry-run`). All passed with no type errors, no test failures, and no build errors. EBADENGINE warnings appeared only because the local environment is Node 25 (not in CI's 22/24 matrix); this is expected per the task and not a defect.
- One dependency-resolution failure: `npm ci`/`npm install` in typescript/examples/strands fails with an ERESOLVE conflict (openai@7.15 vs @strands-agents/sdk@1.17.0's peerOptional openai@^6.45.0, itself pulled in via @neo4j-labs/agent-memory's peerOptional strands range). I reproduced this identically against the merge-base commit (ec9fc65) in a clean archive checkout — the failure is pre-existing (package.json/package-lock.json for that example are byte-identical between ec9fc65 and HEAD per `git diff`), not introduced by this branch, so I did not report it as a finding. Worth a human decision on whether main's CI is currently green for this job, since a literal `npm ci` reproduces the conflict — but that's out of scope for a branch-diff review.
- TypeDoc: regenerated the API reference with `npx typedoc --out <scratchpad>/typedoc` from typescript/ (typedoc.json entry points unchanged). Zero warnings. `diff -rq` against docs/modules/ROOT/attachments/api/typescript showed the same 133 HTML files present on both sides, each differing only in the embedded GitHub "Defined in" permalink's commit SHA (regenerating today embeds HEAD's SHA e2bcb93..., the committed output embeds an earlier branch commit 4052e1b..., which itself is on this branch's own history and made no changes to typescript/src except the version.ts bump, which is not part of the documented public surface). After normalizing that commit-hash substring, the two trees are byte-identical. No missing, extra, or content-stale pages — the committed TypeDoc output is fresh for this branch's HEAD. Not a finding.
- docs/modules/ROOT/pages/reference/nams-ai-provider.adoc's peer-dependency table (`@neo4j-labs/agent-memory` range `~0.4.0 || ~0.5.0`) was spot-checked against typescript/packages/vercel-ai-provider/package.json peerDependencies and matches exactly.

Not fully covered / needs a human decision:
- Did not line-by-line review docs/modules/ROOT/pages/reference/nams-ai-provider.adoc, typescript-api.adoc or sdks/typescript.adoc prose beyond the one spot-check above (per task instructions, this task is scoped to running checks, not diff reading; deep prose review of those pages is presumably another reviewer's slice).
- Did not attempt real network calls against the hosted NAMS service (out of scope, per task facts).

Side effect to flag: `npm install` (not `npm ci`) in typescript/examples/nams-ai-provider, run before I confirmed node_modules was current, rewrote typescript/examples/nams-ai-provider/package-lock.json (removed a stale `"peer": true` flag on one dev-dependency entry — cosmetic, npm-version-related, not a source change). `git status --short` at the end shows this one tracked file modified: `M typescript/examples/nams-ai-provider/package-lock.json`. I attempted `git checkout -- typescript/examples/nams-ai-provider/package-lock.json` to revert it but the harness's destructive-action guard blocked that command, so the modification is still present in the working tree — a human should run `git checkout -- typescript/examples/nams-ai-provider/package-lock.json` (or equivalent) to restore it before committing/reviewing further. No other tracked files changed. The only other git-status entry, `docs/audit-evidence/2026-09-17/`, was untracked before I started and I did not touch it.

### py-lib — Python library, dependencies and their tests (6 of 6 findings confirmed)

I fully checked every changed file in scope: pyproject.toml, uv.lock, src/neo4j_agent_memory/__init__.py, core/_unsupported.py, graph/queries.py, nams/_unsupported.py, nams/ontology.py, tests/integration/nams/test_ontology.py, tests/integration/test_short_term_memory.py, tests/unit/nams/test_ontology.py, tests/unit/nams/test_unsupported.py and tests/unit/test_bolt_optional_dependencies.py.

Verified by running things:

- **CREATE_MESSAGE fix.** Against neo4j:5.26 in a testcontainer, the old CREATE_MESSAGE forked or hit ConstraintError in 10 of 10 concurrent 1+5 trials; the new one forked in 0 of 10. The SET-before-read lock works for single appends.
- **Edge cases.** An empty conversation still yields one row with last=null, so FIRST_MESSAGE is created. Properties, metadata, embedding and timestamp are still written. updated_at is still set, now before the create. Callers in short_term.py (single add ignores the result; batch reads results[0]["m"]["id"]) see the same shape.
- **Integration tests.** RUN_INTEGRATION_TESTS=1 on tests/integration/test_short_term_memory.py: 26 passed. The new deterministic forked-chain test fails on the old query, because the constraint error comes from the fan-out.
- **Unit tests.** tests/unit/nams plus test_bolt_optional_dependencies: 474 passed. The bolt import-boundary test fails when pointed at the ec9fc65 source ("Blocked optional backend import: neo4j_agent_memory.nams"), so it guards the real invariant.
- **Sentinel move.** Class identity is preserved through nams._unsupported, there is no import cycle (core/_unsupported imports only core.exceptions), and no public name is removed from __init__.
- **Static checks and lock.** mypy src is clean. ty reports only an environment-specific gliner unresolved-import. ruff lint and format are clean. `uv lock --check --offline` is consistent; the lock removes only the mkdocs tree, and nothing imports those packages.
- **get_active parity.** Pydantic document equality ignores explicit-vs-default fields, so the conflict check matches TypeScript's normalizedDocument.

Not findings, but worth knowing:

- **Tail lookup cost.** In CREATE_MESSAGE the tail lookup still expands every HAS_MESSAGE relationship; that was already O(n) before the branch.
- **Timestamp ties.** Among forked tails with equal timestamps (the same statement's datetime(), for example batch rows), the chosen tail is arbitrary because there is no secondary sort key. This only matters once a chain is already forked.
- **Legacy response shape (pre-existing).** Python get_active falls back to treating a bare document payload as the ontology; TypeScript raises NotSupportedError for the same payload.
- **Leftover clones.** The ontology integration fixture no longer deletes leftover "conservation-clone" ontologies from earlier failed runs. That is deliberate (it deletes only IDs it owns), but a crashed run may block later clone() calls until someone cleans up by hand.

Needs a human decision:

- Whether the hosted /ontologies/active now returns a populated `version`. The previous code and its unit test say it returned version: null, and I cannot observe the service. If it still does, the Python and TypeScript get_active rewrite silently drops validation_mode, revision and version_id.

Not done: the live NAMS ontology tests, which need a MEMORY_API_KEY and an isolated workspace.

### ts-sdk — TypeScript SDK source and tests (4 of 5 findings confirmed)

Fully checked (diff plus HEAD version): typescript/src/errors.ts, typescript/src/types.ts, typescript/src/long-term/index.ts, typescript/src/middleware/vercel-ai.ts, typescript/src/integrations/langchain.ts, typescript/src/integrations/strands/memory-store.ts, typescript/src/ontology/index.ts, typescript/test/unit/ontology.test.ts, typescript/test/e2e/ontology.test.ts, typescript/test/integration/docs-contract.test.ts, typescript/README.md. typescript/package.json and typescript/CHANGELOG.md are unchanged on the branch; I checked both for version and changelog coverage.

Verification run: `npx vitest run test/unit/ontology.test.ts test/integration/docs-contract.test.ts` passed 42/42. `tsc --noEmit` and `tsc -p tsconfig.test.json` are clean. A scratch tsx script (scratchpad/review/nf.mts) showed that a 404 from `ontology.get` is a TransportError, not a NotFoundError.

Checked with no finding:
- Comment-only changes: errors.ts, types.ts (the namespace really is unused; only types.ts:338 references it), long-term waitForExtraction (it does propagate errors), vercel-ai persist options (write errors are caught), strands `extraction`, and `@inline` TypeDoc tags. None of these narrows or removes an exported type or signature.
- ActiveOntology gains only an optional field, and the removed `currentVersion` was not exported.
- Parity with Python `_parse_active_version` and `get_active` is equivalent: the same required fields, revision ≥ 1, the mode enum, a schema_json document check, and a conflict check (Python's `extra=\"ignore\"` equality matches the TS normalization). Small differences: TS throws plain Error where Python raises ValueError, and TS also requires a safe integer.
- The unit tests can fail: each invalid case exercises a distinct validation branch, and the call-count assertion guards against the old list()/get() fallback.
- docs-contract.test.ts assertions match rest.ts: a single attempt with no retries, 401/403 mapped to AuthenticationError, other codes to TransportError, raw DOMException TimeoutError propagated, bridge-only methods rejected with NotSupportedError before fetch. Headers are a plain object, so the namespace check can fail.

Needs a human decision:
1. The new getActive() depends on the hosted `GET /ontologies/active` response carrying `version`. At ec9fc65, the source comment said the response \"carries no version metadata\", and the old unit mock returned `version: null`. If the hosted service still sends null, TS (and Python) getActive now return no validationMode/revision/versionId, where 0.5.0 filled them in. I cannot observe NAMS from here.
2. The ontology e2e test is now gated on RUN_ISOLATED_ONTOLOGY_TESTS=1, which no workflow sets. It was never run by e2e-typescript.yml (that workflow runs only hosted-service.test.ts and strands.test.ts), so nothing live verifies the new getActive contract.

Outside my paths but related: the root CHANGELOG.md `[Unreleased]` is also empty for the equivalent Python get_active change. reference/typescript-api.adoc:440 is stale (noted inside finding 2).

### ts-ex-a — New TypeScript examples: nams-ai-provider, vercel-ai tutorials, shared tutorial helpers (7 of 7 findings confirmed)

Fully checked (HEAD version plus diff against ec9fc65):
- typescript/examples/shared/tutorial-state.ts, tutorial-cleanup.ts, tutorial-mcp.ts. Reviewed: state validation, atomic write with lock/temp/fsync/rename, 0600/0700 modes, symlink refusal, scrypt credential binding, redacted inspect, mutation ledger, middleware write tracking, the cleanup ownership/provenance/neighbor/residual logic, and the 404-only absence check. Also checked each call against typescript/src (core middleware addMessage path, the nams_resolution merge metadata in long-term/index.ts, and the short-term method signatures).
- typescript/examples/vercel-ai: src/tutorials/{conversation,first-agent,hosted-quickstart,knowledge-graph}.ts, src/index.ts diff, README.md diff, .env.tutorial.example, and the tests docs-hosted-stub.ts, docs-restart-child.ts, docs-tutorials.test.ts, persona-recovery.test.ts, tutorial-state-cleanup.test.ts, fake-nams.ts and vercel-ai.test.ts. README links and the #copying-an-example anchor resolve.
- typescript/examples/nams-ai-provider: all four src/*-mode.ts, test/docs-pages.test.ts, README.md, .npmrc, .env.example, package.json and tsconfig.json. In package-lock.json both local packages keep "resolved": "file:../.." and "file:../../packages/vercel-ai-provider", at versions 0.5.0 and 0.3.0. Provider peer `~0.4.0 || ~0.5.0` is satisfied. Engines >=22 agree with the CI legs (Node 22/24), and CI builds the provider dist before `npm ci`. The shared helpers resolve @neo4j-labs/agent-memory through package self-reference to typescript/dist in CI.
- typescript/packages/vercel-ai-provider/README.md and examples/README.md diffs.

Commands run:
- `tsc --noEmit` and `vitest run` in vercel-ai (72 passed) and nams-ai-provider (8 passed), locally on Node 25.
- Scratch mutation test: disabling the hooks-mode deny and retry hooks still passes the hooks test.
- Scratch stub test: TS cleanup times out on per-message status "completed" or "skipped".
- Scratch check: the entry-point comparison fails when the path contains a space.

Not verified (hosted service is not observable):
- The real per-message extraction-status vocabulary and the messages[].id field name. The status finding rests on the Python SDK docstring and this branch's Python helper, not on a live capture.
- Whether hosted extraction keeps the UUID-suffixed name that knowledge-graph.ts requires to match exactly.
- Whether hosted graphs link entities with EXTRACTED_FROM (the TS provenance query needs this for derived-entity deletion), and whether extra neighbor nodes (e.g. Extractor) would cause every entity to be retained.

Needs a human decision: confirm the NAMS extraction-status values against the live service and align the TS and Python helpers.

Not reported (low impact): a stale `.lock` file is possible if the process dies inside atomicWrite. vercel-ai README "Tests" section describes only the fake-transport suite, not the new tutorial suites. index.ts now lists entities only when the exact name "Euro-style board games" is matched.

### ts-ex-b — Other TypeScript examples (10 of 10 findings confirmed)

Fully checked, using the diff and the HEAD version of every changed in-scope file:
- **nextjs-memory-chat:** .env.example, README.md, app/api/chat/route.ts, components/MemoryRail.tsx, lib/handlers.ts, lib/memory.ts, package.json, the package-lock.json diff, test/nams-server.ts, test/routes.test.ts.
- **langchain:** README.md, src/index.ts, src/nams-memory.ts, test/fake-nams.ts, test/langchain.test.ts.
- **mastra:** README.md, src/index.ts, src/nams-threads.ts, test/fake-nams.ts, test/mastra.test.ts.
- **mcp:** .env.tutorial.example, README.md, test/docs-assembly.test.ts.
- **ontology-lifecycle:** README.md, test/fake-nams.ts.
- **README-only examples:** strands/README.md, cloudflare-agents-edge/README.md (claims checked against src/handlers.ts and test/edge.test.ts), eve-commerce-agent/README.md (claims checked against agent/lib/nams-memory.ts, agent/tools/checkout.ts and the RestTransport "unsupported" routes).
- **Index:** typescript/examples/README.md.

Commands run:
- Offline suites: nextjs 15/15, langchain 5/5, mastra 11/11, mcp 10/10 (including the new docs-assembly test), ontology-lifecycle 10/10. All pass locally.
- `tsc --noEmit` for nextjs, with tsbuildinfo redirected to the scratchpad: exit 0.

Checked against the source:
- Fake NAMS request/response shapes checked against typescript/src/transport/rest.ts ROUTES and long-term getEntity parsing. `/conversations/:id/search`, `GET /conversations?user_id`, `GET /entities/:id` with target_name, `GET /reasoning/steps?conversation_id` and `/ontologies/active {ontology, version}` all match.
- The provider's createNamsProvider, middleware and retrieval were read in full.
- Downloaded the published tarballs to the scratchpad and confirmed @neo4j-labs/agent-memory 0.5.0 on npm ships ontology import/diff/migrate/getMigration, so removing the ontology footer's "not published" caveat is correct.
- Confirmed from the provider's realpath that it resolves @neo4j-labs/agent-memory 0.4.0 from its own node_modules.

Not done:
- Did not run CI and did not reproduce the nextjs CI failure end-to-end; that would require deleting the local provider dist. The blocker rests on the workflow condition and the gitignored dist.
- Did not run the cloudflare (workerd pool), eve (Node 24) or strands suites; strands has no node_modules locally.
- Did not run `next build`.
- Did not judge hosted-service claims such as whether NAMS search is embedding-based or exact text. The nams-server.ts comment ("ranks by embedding similarity") contradicts the provider's own comment ("NAMS search matches exact text"); a human with service knowledge should decide which is right.
- The package-lock diff drops @emnapi/core, @emnapi/runtime and yaml entries. They are optional or wasm-only, and I found no failure, but `npm ci` on Linux was not verified.

Needs a human decision:
- Whether the nextjs flagship should keep conversational continuity (recent turns and observations) now that it relies only on provider search hits. See the major finding on README.md:214.

### py-examples — Python examples and their tests (11 of 11 findings confirmed)

Fully checked: every changed file in scope. That is the Makefile diff (help text, RUFF_PATHS, docs/diagram targets and their referenced scripts and paths, the example targets and run_example macro), docs/extensions/example-files.json (all 9 entries exist, map to the intended files and match every example$ id used under docs/modules/ROOT), examples/AURA_SETUP.md, examples/README.md, and the READMEs for audit-trail, buffered-writes, existing-graph, domain-schemas (checked against run.py's --store/--no-store and env handling), hello-memory (plus .env.example against main.py), eval-harness, no_llm, ontology-lifecycle, full-stack-chat-agent (plus its frontend, checked against backend config.py and .env.example), lennys-memory (plus its frontend, checked against backend config and client), google_adk_demo, google_cloud_integration (_common.py env names), microsoft_agent_retail_assistant (plus its frontend and the NEO4J_USER config), strands-memory-store, strands-session-manager, nams-fastapi, nams-langchain and nams-quickstart. For financial-services-advisor I checked the top-level README, both app READMEs and GETTING_STARTED guides and both frontend READMEs against the AWS and GCP config env names, env_file locations and the AWS integration-test env reads. I checked eval-harness main.py and ci_gate.py, no_llm/main.py, and ontology-lifecycle/main.py against src (MigrationJob.errored, ActiveOntology.version_id, get_active reading `version`, wait_for_extraction -> bool). All three claude-code-team-memory configs are valid JSON, and their command, args and env match the CLI in src/neo4j_agent_memory/cli/main.py (--backend/NAM_BACKEND, --transport, --profile, --session-strategy, NEO4J_USER, NEO4J_DATABASE, MCP_USER_ID). `doctor.py --configs-only` passes. I read the tests/examples diffs for team-memory, eval-harness, registry, full_stack_apps, google_cloud_integration, hello_memory, nams_quickstart, no_llm and ontology_lifecycle.

Commands run: pytest on the 9 changed test modules with `-m 'not requires_neo4j'` gave 326 passed and 4 failed. All 4 failures are for `examples/ontology-extraction`, a stale untracked directory in this checkout that holds only __pycache__; it is not a branch defect but will fail locally until removed. ruff check on src, tests, examples and docs/modules/ROOT/examples passes, and ruff format --check passes on the changed example and test dirs.

Not done: I did not run requires_neo4j tests, any live Aura or NAMS runs, or `make docs-lint`/`docs-render-check`, which need a docs build and Playwright. I did not verify the external Aura console and docs URLs or the claim that Aura allows one Free instance per account. The frontend READMEs' 'Node 22.13+' floor is stricter than package.json engines (>=22); I left that unflagged because it may reflect the lint toolchain.

Pre-existing issues outside this branch's changes: the strands-memory-store and strands-session-manager READMEs still say Neo4jMemoryStore and Neo4jSessionManager are unreleased and not on PyPI, although src at 0.6.0 exports both.

Needs a human decision: whether the Makefile example targets should keep the Docker auto-start (and fix the env it passes) or move to Aura-only, and whether DOCUMENTATION_REMEDIATION_STATUS.md was meant to be committed.

### tooling-ci — Docs tooling, Antora extensions, UI JS, Makefile, CI workflows (10 of 11 findings confirmed)

Files fully checked (diff plus HEAD): scripts/check_docs.py, scripts/render_docs.mjs, scripts/export_diagrams.mjs, scripts/manage_diagrams.py, docs/extensions/example-files.js, docs/extensions/example-files.json, docs/extensions/tutorial-ui.js, docs/ui/js/tutorial-code.js, docs/ui/css/tutorial-code.css, docs/antora-playbook.yml, docs/package.json, docs/diagrams/package.json (plus its lockfile), Makefile, .github/workflows/ci-python.yml, .github/workflows/ci-typescript.yml, .gitignore, .claude/skills/docs-diataxis/SKILL.md, .claude/skills/docs-excalidraw/SKILL.md.

What I ran:
- `python3 scripts/check_docs.py` and `--build`: 145 pages, 0 errors; 290 HTML files, 3009 links, 30 images.
- `manage_diagrams.py status` and `missing`: exit 0.
- `ruff check` and `ruff format --check` on docs/modules/ROOT/examples: clean.
- A fresh Antora build into the scratchpad, then Playwright probes of all 15 code-nocollapse pages: no JS errors; buttons and focusable <pre> elements are present; clicking copies the right text. The keyboard-reachability defect is reported above.
- render_docs.mjs plus the test_rendered_site assertions against that build: all 7 pass.
- tests/docs/test_docs_checker, test_diagram_manifest, test_nav_labels and test_links: 64 passed.
- The hosted-tutorial-minimum job reproduced in a clean Python 3.10 venv with only `.[nams]` plus the pytest packages: 198 passed, no skips.

Also verified:
- The GitHub matrix include entries correctly add 4 Node 22 legs.
- Lockfiles match package.json for docs/, docs/diagrams/ and packages/vercel-ai-provider.
- The TypeScript CI docs path filters cover every .adoc file that the TS example tests read (mcp, nams-ai-provider, vercel-ai).
- None of the example-files.json resource ids collide with files in docs/modules/ROOT/examples.
- .gitignore hides no tracked file.

Not verified / needs a human decision:
1. The production site is built by neo4j-contrib/labs-pages with its own playbook. docs/extensions/example-files.js is needed by the `example$no_llm/…`, `example$eval-harness/…` and `example$team-memory/…` includes in how-to/running-without-an-llm.adoc, how-to/evaluation.adoc and how-to/team-memory-in-your-editor.adoc. If the labs-pages playbook does not load that extension (and tutorial-ui.js plus `supplemental_files`), those includes will not resolve in production. I could not see that playbook. MAINTAINING.md asks for the extension to be enabled there. Also, .github/workflows/trigger-labs-build.yml, which CLAUDE.md mentions, does not exist in this checkout.
2. example-files.js reads files from the working tree for every component version. That is fine with the current single `branches: HEAD` source but would give older versions HEAD's files if more branches are added.
3. I did not run the CI steps for the nams-ai-provider example, because they would write node_modules and dist into the repo. The provider package's devDependency `@neo4j-labs/agent-memory ^0.4.0` may resolve through the symlinked file: dependency ahead of the example's 0.5.0 SDK. Unverified.
4. The working tree now shows an uncommitted change to typescript/examples/nams-ai-provider/package-lock.json (one removed `"peer": true`). It did not come from my commands; another concurrent process appears to have run npm there.
5. I did not review docs/audit-evidence or the generated TypeDoc output.

### deploy — Cloud Run and MCPB deployment assets (6 of 8 findings confirmed)

Files fully checked at HEAD against the ec9fc65 diff: deploy/cloudrun/Dockerfile, deploy/cloudrun/cloudbuild.yaml, deploy/cloudrun/service.yaml, deploy/cloudrun/README.md, deploy/mcpb/manifest.json, deploy/mcpb/README.md and tests/docs/test_cloudrun_assets.py. I also read the unchanged deploy/cloudrun/env.yaml.example, which one finding covers.

Verified OK:
- **Dockerfile:** every CMD flag (`--transport http`, `--host`, `--port`, `--backend bolt`, `--embedding`, `--embedding-dimensions`, `--no-auto-preferences`) exists in src/neo4j_agent_memory/cli/main.py. `http` is Streamable HTTP in mcp/server.py. The `[mcp,google]` extras supply click (through uvicorn), rich (through fastmcp) and vertexai. README-pypi.md is the pyproject readme. The container runs as uid 1000. `NAM_EXTRACTION__EXTRACTOR_TYPE=none` gives ExtractorType.NONE with llm=None.
- **Vertex path:** VertexAIEmbeddingProvider and VertexAIEmbedder default to 768 dimensions and us-central1, and read GOOGLE_CLOUD_PROJECT.
- **Secret and account names:** neo4j-uri/neo4j-user/neo4j-password and neo4j-memory-sa are consistent across all four Cloud Run files. The cloudbuild substitutions (_REGION, _SERVICE_NAME, _REPOSITORY) and the $BUILD_ID tags are correct. The service.yaml env, containerPort 8080 and TCP startup probe are fine.
- **gcloud flags:** `--[no-]invoker-iam-check` and `services proxy --port` are confirmed on the gcloud reference pages. All external links in both READMEs return 200. The relative links to examples/AURA_SETUP.md and the tutorial .adoc exist.
- **CI:** ci-python.yml triggers on `deploy/cloudrun/**` and runs tests/docs/test_cloudrun_assets.py in the docs job.

Commands run:
- The test file passes (4 passed) in the project venv and in a fresh `uv sync --group dev --frozen` venv that mimics CI (under scratchpad/review).
- `docker build` of HEAD from a minimal git-archive context succeeded. The image serves `mcp serve --help`. Against a throwaway neo4j:5.26 container it started the HTTP server, and `fastmcp list` returned 16 tools. It also started with `--user $(id -u):$(id -g)` and the read-only ADC mount from README section 1. All review containers, the network and the image were removed afterwards.
- The MCPB manifest was checked with `npx @anthropic-ai/mcpb@2.1.2 validate` on a scratch copy.

Could not verify:
- The live Cloud Run deploy, the `gcloud run services proxy` behaviour, and Vertex AI embedding calls (no GCP project).
- The `/mcp/`-redirect consequence behind Cloud Run is reasoned from the observed 307 with an absolute http:// Location; I did not observe it in the cloud.
- Whether the extension is actually listed in the Claude Desktop extension directory.

Needs a human decision:
- Whether to make deploy/mcpb a real MCPB bundle (with user_config) or reduce it to the claude_desktop_config.json path.
- Whether to keep or delete env.yaml.example.

Unrelated observation: `git status` during the review showed `M typescript/examples/nams-ai-provider/package-lock.json`, which was not in the starting snapshot. I did not modify it; it is presumably another concurrent process.

### docs-tests-a — Docs tests: tutorial and hosted-lifecycle contract tests (2 of 2 findings confirmed)

I found two minor test-quality gaps and no blockers or majors. Across the eight modules, the tests run the real maintained programs from docs/modules/ROOT/examples, so they are not testing copies. None of them touch the network; the Bolt assembly checks go further and block sockets with a sitecustomize module, which I confirmed loads in the venv. The tests use no skip markers and, apart from the tolerances below, no try/except that swallows failures.

Fully checked (read the HEAD version, since all eight are new on this branch):
- tests/docs/test_aura_tutorial_persona.py
- tests/docs/test_aura_tutorial_setup.py
- tests/docs/test_core_python_tutorials.py
- tests/docs/test_hosted_tutorial_cleanup.py
- tests/docs/test_hosted_tutorial_contracts.py
- tests/docs/test_hosted_tutorial_lifecycle.py
- tests/docs/test_ontology_tutorial.py
- tests/docs/test_skills_tutorial.py

Run results with `uv run pytest <file> -q -rs` in the project venv (Python 3.12, pytest 9.0.2). Nothing was skipped:

| Module | Passed | Skipped |
|---|---|---|
| test_aura_tutorial_persona | 23 | 0 |
| test_aura_tutorial_setup | 39 | 0 |
| test_core_python_tutorials | 105 | 0 |
| test_hosted_tutorial_cleanup | 38 | 0 |
| test_hosted_tutorial_contracts | 36 | 0 |
| test_hosted_tutorial_lifecycle | 23 | 0 |
| test_ontology_tutorial | 42 | 0 |
| test_skills_tutorial | 19 | 0 |

All eight together in reverse file order also passed (325), so I found no dependence on test order.

CI replication:
- **docs-tests job** (`uv sync --group dev`, no extras, Python 3.12). I rebuilt it in scratchpad/review/venv-docs with `UV_PROJECT_ENVIRONMENT` and `uv sync --frozen --group dev`. All 8 modules: 325 passed, 0 skipped. The lesson modules import framework SDKs lazily, so the import and `--help` checks work without extras.
- **hosted-tutorial-minimum job** (Python 3.10, `.[nams]` plus unpinned pytest, pytest-asyncio, pytest-timeout and respx). I rebuilt it in scratchpad/review/venv-hosted and ran the exact CI command: 198 passed.
- Both jobs run with no markers and `--timeout=60`. `make test-docs` also runs all of these modules.

Other things I verified:
- The lesson modules bind to the Bolt SDK: the collected `client.*` calls bind to the current signatures, and the relationship-property check compares against `queries.CREATE_ENTITY_RELATIONSHIP` (`r.type`).
- The REST paths the hosted helpers call match the SDK route specs (query body `{cypher, params}`, entities, conversations, extraction-status, ontologies). The ontology test's fake payload fields match the SDK's `OntologyVersion` and `_parse_active_version`.
- Hosted pages that drop a helper include are caught by tests/docs/test_build_pipeline.py::test_python_tutorial_supplies_complete_local_files, so the hard-coded ASSEMBLIES list in test_hosted_tutorial_lifecycle.py is not a real gap.
- `restore_active_ontology.__wrapped__` works because pytest's FixtureFunctionDefinition calls `functools.update_wrapper`.

Brittleness I noted but did not report as findings:
- Many assertions match exact prose, such as `Copy the entire block`, `Reuse unchanged helper files`, `:page-role: code-nocollapse`, `Verified: merged Desktop JSON` and `Lesson imports verified`. Any wording edit will break them, which appears intentional.
- test_ontology_tutorial.py uses `pytest.raises(Exception)` in about 8 places. That also accepts the fake service's own `AssertionError("Unexpected request")`, but the state assertions that follow keep those tests meaningful.
- test_skills_tutorial.py::test_seed_cli_requires_owner_disposition_before_creating_state calls `NamsSettings()` without isolating the environment or the working directory.

Needs a human decision:
- The tutorials tell readers to install `neo4j-agent-memory[...]==0.6.0` from PyPI, but both CI jobs test against the HEAD source. This branch changes `src/neo4j_agent_memory/nams/ontology.py` `get_active()` (it no longer composes version metadata from the list and detail endpoints) without bumping the version, so HEAD's 0.6.0 is not the published 0.6.0. The ontology tutorial avoids `get_active` by using a raw reader, and the test comment at test_ontology_tutorial.py:180-183 describes the released behaviour correctly. So nothing in scope breaks today, but no CI job checks the tutorials against the package readers actually install.

Not done: I did not mutation-test every assertion. My spot checks were the socket-block check, the NAMS binding check, and the grep of nams_quickstart for any use of reasoning.

I left no files in the repository. Scratch files are under /private/tmp/claude-502/-Users-lyonwj-github-neo4j-labs-agent-memory/66a2977c-9670-4b56-8270-fc84ea0f1100/scratchpad/review/. The working tree shows `typescript/examples/nams-ai-provider/package-lock.json` as modified; I did not make that change.

### docs-tests-b — Docs tests: build, checker, links, nav, diagrams, contracts, rendered site (12 of 13 findings confirmed)

I fully checked every in-scope file against `git diff ec9fc65..HEAD` and read each HEAD version: tests/docs/test_build_pipeline.py, test_code_snippets.py, test_diagram_manifest.py, test_docs_checker.py, test_links.py, test_nav_labels.py, test_operational_howto_contracts.py, test_python_integration_contracts.py, test_python_reference_contracts.py, test_rendered_site.py, tests/docs/utils/extract_code.py and tests/fixtures/nams/skill-generate-request-schema.json. For context I also read tests/docs/conftest.py, scripts/check_docs.py, check_manifest in scripts/manage_diagrams.py, the CI changes in .github/workflows/ci-python.yml, and the Makefile, pyproject.toml and docs/MAINTAINING.md changes.

Module runs, each with `uv run pytest <file> -q -rs` in the full local venv:
- test_build_pipeline: 16 passed.
- test_code_snippets: 213 passed, 142 skipped (141 signature-doc skips, 1 placeholder).
- test_diagram_manifest: 4 passed.
- test_docs_checker: 32 passed.
- test_links: 13 passed.
- test_nav_labels: 15 passed.
- test_operational_howto_contracts: 18 passed.
- test_python_integration_contracts: 31 passed, 1 failed (agent-framework-openai is not installed locally; CI installs it).
- test_python_reference_contracts: 175 passed.
- test_rendered_site: 7 passed in 45s, using the existing local docs/build/site and Playwright.

CI-like environment: I built a dev-group-only venv in the scratchpad (`uv sync --group dev --frozen`) and ran the docs-tests CI subset (code_snippets, links, docs_checker, reference contracts, operational contracts, diagram manifest): 453 passed, 144 skipped.

Lost-coverage check:
- test_links: its removed lines were no-op or lenient assertions (a `pass` loop, a `>10 missing images` threshold, a `>15 orphans` threshold). They are now strict, and the quadrant route check moved to scripts/check_docs.source_report, which test_docs_checker covers. Nothing was lost.
- test_code_snippets: the allowlist import check was replaced by a stricter static declaration check, and I verified all 93 documented SDK imports resolve at runtime. The async wrapper was replaced by a top-level-await compile.
- test_build_pipeline: the dropped tests were weak breadcrumb, search, highlighting, favicon and build-time checks; favicon.svg still exists.

Extractor check: 341 `[source,python]` headers and 341 extracted snippets, with every include expanded. It can still drop blocks silently (see findings).

Two claims I could not verify: the hosted-service fixture in tests/fixtures/nams is a capture of the live OpenAPI and cannot be checked from here, and the CI-only agent-framework-openai path in the integration-test job was not run locally.

For a human decision:
- The Makefile help text calls `make docs-lint` 'Watch for changes and rebuild' (Makefile outside my scope; the text is wrong).
- `git status` now shows ` M typescript/examples/nams-ai-provider/package-lock.json`, which was not modified at the start of the session. None of my commands touched typescript/, so another concurrent process probably did; I left it alone.

### docs-examples-py — Runnable Python programs included into docs pages (4 of 4 findings confirmed)

I fully checked all 19 in-scope files, which are all new on this branch: anthropic_local_memory, aura_connection, conversation_memory, core_memory_recipes (every tag), core_memory_settings, extraction_recipes (every tag), first_agent_memory, hosted_tutorial_cleanup, hosted_tutorial_helpers, hosted_tutorial_state, knowledge_graph, mcp_local_tutorial, microsoft_shopping_tutorial, nams_first_write, nams_quickstart, ontology_quickstart, skills_quickstart, strands_memory_tutorial and wait_for_tutorial_neo4j. The files under docs/modules/ROOT/examples/integrations/ are outside my scope.

What I checked:
- **Compile and CLI:** all 19 files pass py_compile. `--help` works for every argparse script.
- **API calls:** every SDK call matches the HEAD source, checked with inspect.signature and by reading the code. That covers MemoryClient, short/long/reasoning memory, the NAMS short-term, reasoning and ontology clients, from_provider, the extraction pipeline and streaming, GLiNER/GLiREL, the MCP factory, and the Microsoft and Strands integrations. The installed agent_framework (1.19) and strands match the calls these files make.
- **Settings:** the core settings construct correctly with fake environment variables. Adapter class names and the 384-dimension figure in the Anthropic tutorial are correct. Geocoding and enrichment are off by default.
- **Include sites:** every include is listed. The tag regions exist, and the surrounding prose matches the code, apart from the findings.
- **Live run:** I started a neo4j:5.26-community testcontainer with a mock 1536-dimension embedder. I stopped my launcher at the end and left removal of the container to testcontainers' reaper. Results against it:
  - The entities, preferences, reasoning, deduplication and audit recipes passed 3 of 3 runs each.
  - first_agent_memory seed/verify passed, and conversation_memory seed/resume passed with a fake LLM.
  - knowledge_graph ingest/inspect passed with a fake extractor.
  - The messages recipe failed intermittently: 4 of 10 runs, plus 3 of 3 in an earlier run. That is finding 1.
- **Tests:** tests/docs for these programs (core tutorials, hosted lifecycle/contracts/cleanup, skills, ontology, Aura persona): 286 passed. Because they are mocked, they can't catch the ordering bug.
- **Hosted helpers:** I reviewed the ledger code for exclusive creation, 0600 temp-file replace, symlink refusal, redaction of the salt and digest in inspect/inspect-file, and the scrypt credential digest. I also reviewed the ownership gating before deletions: owned is reset every run, pre-existing clones are never deleted, and entities are deleted only when they have exclusive provenance and neighbours. I found no secret printing, and the ontology recovery does not delete anything the run didn't create.

What I could not do:
- **Hosted service:** I couldn't observe NAMS, so the hosted Cypher property names (createdAt, conversationId, EXTRACTED_FROM) in hosted_tutorial_cleanup queries, the response shapes for skills, provenance and extraction status, and whether NAMS creates a conversation automatically on a message write are all unverified. Finding 2 rests on in-repo docs and the SDK source.
- **Real extraction:** GLiNER isn't installed in the venv, so I only confirmed that extraction_recipes fails cleanly, with the correct errors, when the dependency is missing.
- **External services:** I didn't run anything against real Aura, OpenAI, Anthropic, Bedrock or Claude Desktop.

Needs a human decision:
- **SDK behaviour changed under the same version number:** this branch changes nams/ontology.py get_active so it reads the response's version metadata instead of inferring the latest revision, while still calling the SDK 0.6.0. hosted_tutorial_helpers.py:67 says 'SDK 0.6.0 get_active() infers version metadata from the latest revision'. That is true of the PyPI python-v0.6.0 release readers install, but false of the source at HEAD. Similarly, deduplication.adoc attributes merge-query behaviour to 'SDK 0.6.0'. Someone should decide whether the HEAD SDK changes need a version bump or whether these docs statements should follow HEAD.
- **Test gap:** the docs tests mock the database, so no CI job runs the Bolt recipes against Neo4j.

### tut-py — Python tutorials (Bolt/Aura and local) (7 of 7 findings confirmed)

Checked in full: the diff and HEAD version of every in-scope file. Pages: tutorials/first-agent-memory, conversation-memory, knowledge-graph, anthropic-and-local-embeddings, mcp-server, microsoft-agent-memory, strands-agent-quickstart, index. All 16 in-scope partials.

Included example programs, each checked against the HEAD source: aura_connection.py, wait_for_tutorial_neo4j.py, core_memory_settings.py, first_agent_memory.py, conversation_memory.py, knowledge_graph.py, anthropic_local_memory.py, mcp_local_tutorial.py, microsoft_shopping_tutorial.py, strands_memory_tutorial.py.

How I verified:
- Every SDK call used (add_message, get_conversation, add_entity tuple/stored-id adoption, add_relationship RELATED_TO.type and NotFoundError, link_entity_to_message, add_preference/get_preferences_for, query.cypher, search_entities metadata['similarity'], start_trace/add_step/record_tool_call/complete_trace/get_trace_with_steps/get_session_traces, from_provider, create_mcp_server, FastMCP.run, the MCP tool parameters, Neo4jMicrosoftMemory/record_agent_trace, Neo4jSessionManager, GLiNER/GLiREL/DomainSchema constructors) was checked with inspect.signature in the project venv or by reading the source, including the Cypher property names used in the pages' queries.
- Ran settings() to confirm `backend=bolt, embedding=OpenAIEmbeddingProvider`. Ran the first lesson's import check and --help. Confirmed the from_provider adapters give AnthropicProvider and SentenceTransformersProvider with 384 dimensions.
- A scripted pass over every xref, fragment, include and image in scope found none missing; <<resume-this-lesson>> resolves on every page that includes the setup and cleanup partials.
- Confirmed the {cli-help-suffix} rendering in the built site.
- Ran tests/docs/test_aura_tutorial_persona.py, test_aura_tutorial_setup.py, test_core_python_tutorials.py and test_python_integration_contracts.py: 199 passed.
- Checked that each partial fits the pages that include it (python-tutorial-check-failed's 'step 2' reference is correct on all three pages that include it), TS method names in the equivalents table, the Labs disclaimer against README, and the index route claims against the diagram text and the example fixtures (9 steps / 9 tool calls, 60 s extraction wait).

Not verified: live Aura, OpenAI, Anthropic, Bedrock or Claude Desktop behaviour (no credentials, no web access). External URLs were checked for plausible form only.

Needs a human decision:
1. This branch removed the GraphAcademy ':page-ad-*' attributes from tutorials/index, first-agent-memory, conversation-memory and knowledge-graph (and from getting-started and how-to/index), while faq, index, memory-types and graph-architecture keep them. Confirm this is intended.
2. The old tutorial and how-to text for upgrading from the 1.0.0b preview (BaseContextProvider -> ContextProvider rename) no longer appears on any docs page; it survives only in CHANGELOG.md. The owning how-to is outside this area.
3. first-agent-memory, conversation-memory and knowledge-graph each emit both `anchor:_clean_up[]` and a '== Clean up' section. The built HTML has both `_clean_up` and `_clean_up_2`: harmless but redundant.

Scratch files are under the shared scratchpad review/pytut/. Another reviewer overwrote my first script in review/, so I moved into a subdirectory.

### tut-hosted-py — Python hosted tutorials (NAMS quickstart, ontology, skills) (6 of 7 findings confirmed)

Fully checked (read the HEAD version and the diff against ec9fc65):
- docs/modules/ROOT/pages/tutorials/nams-quickstart.adoc
- docs/modules/ROOT/pages/tutorials/ontology-quickstart.adoc
- docs/modules/ROOT/pages/tutorials/skills-quickstart.adoc
- partials: python-hosted-cleanup-file.adoc, python-hosted-helpers-file.adoc, python-hosted-lifecycle.adoc, python-hosted-state-file.adoc
- examples: hosted_tutorial_cleanup.py, hosted_tutorial_helpers.py, hosted_tutorial_state.py, nams_first_write.py, nams_quickstart.py, ontology_quickstart.py, skills_quickstart.py

SDK checks against src/neo4j_agent_memory/nams (short_term, long_term, reasoning, ontology, query) and the python-v0.6.0 tag:
- Checked: NamsSettings env aliases (confirmed by running it), connect(), create_conversation / bulk_add_messages / get_conversation, wait_for_extraction kwargs, the NAMS reasoning start_trace/add_step/record_tool_call/get_session_traces, and the ontology methods list/get/clone/update/activate/delete.
- Checked: the OntologyDocument export, NotFoundError on 404, and the REST paths used by the helpers (/query, /conversations/{id}[/messages|/extraction-status], /entities/{id}, /ontologies/active).
- These all match. The one exception is Step 3's first-write, which uses a client-chosen conversation ID.
- The pages say SDK 0.6.0's get_active() infers the latest revision. That is correct for the released tag python-v0.6.0 (it composed metadata via list()+get()).
- For other reviewers: this branch changes src/neo4j_agent_memory/nams/ontology.py get_active() to read the bound version, yet __version__ is still 0.6.0. That source change is outside my scope.

API key safety:
- The key is never printed or stored. The ledger holds only a salted scrypt digest, and inspect/inspect-file strip the salt and digest.

Resume and cleanup:
- Traced new_run_status, check_new_run, the exclusive-create refusal, the identity check on load, the pending-operation guards, cleanup's exit status 2 and retained mapping, and the ontology restore-before-delete path.
- The printed milestones match the page text, and the illustrated outputs match the print statements.
- The lesson files compile. `--help` for all three programs and for hosted_tutorial_state.py works offline with no key (ran in the scratchpad).
- The hosted tutorial docs tests pass: test_hosted_tutorial_contracts/cleanup/lifecycle, test_skills_tutorial, test_ontology_tutorial.

Links and anchors:
- Every xref target exists, including reference/authentication#_key_categories, how-to/use-nams#_recover_from_an_interrupted_tutorial_run and reference/backend-capabilities#hosted-cleanup. The partial$ and example$ includes resolve.
- Every former auto-generated section id of the three pages is kept as [[id]] or anchor:.
- No inbound fragment links to these pages exist elsewhere.

Hosted-only claims I could not verify from this checkout (per MAINTAINING.md:68 these are release-verification items, not defects):
- Skills: the POST /skills/{id}/review body {"decision":"approve"}, the explain-provenance response shape (the parser accepts only sourceId(s)/sourceNodeId(s) keys), whether skill provenance may reference the conversation ID (not in the 'known' set, so it would block publication), and the /verify response fields.
- Whether GET /ontologies/active returns a 'version' object. python-v0.6.0 said it returns no version metadata; if so, the ontology lesson always stops before mutation, which the page does state as a prerequisite.
- NAMS entity property names used in PROVENANCE_QUERY (e.createdAt, EXTRACTED_FROM from messages) and RESIDUAL_QUERY (n.conversationId). A mismatch fails safe by retaining entities or raising.
- The extraction-status summary keys and whether reasoning steps count toward its total.

Needs a human decision:
- The severity of the nams_first_write finding. The evidence is the integration smoke test, the SDK docstrings, the strands comments, the backend-capabilities reference and the removed page text. One SDK comment (nams/short_term.py:156-157) mentions arbitrary string conversation IDs. A live check against NAMS would settle it.

### tut-ts — TypeScript tutorials (6 of 6 findings confirmed)

Fully checked against HEAD, with the diff from ec9fc65 read for each:
- the five TypeScript tutorial pages (first-agent-memory, conversation-memory, knowledge-graph, hosted-quickstart, mcp-server)
- the four partials (typescript-tutorial-api, -checkout, -lifecycle, -project)
- typescript/examples/vercel-ai/src/tutorials/*.ts
- typescript/examples/shared/tutorial-state.ts, tutorial-cleanup.ts, tutorial-mcp.ts
- typescript/examples/mcp/.env.tutorial.example, README.md (diff), test/docs-assembly.test.ts

How:
- **Displayed code vs source:** the four programs shown on the pages match their files byte for byte (compared with a script).
- **Typecheck:** `tsc --noEmit` passes in examples/vercel-ai and examples/mcp against the built 0.5.0 dist.
- **API claims:** checked against typescript/src (0.5.0): MemoryClient options, the shortTerm/longTerm methods used, the MCP tool schemas and dispatch (12 tools, user_id/metadata, conversation_id/messages, name/type, search requires conversation_id), registerMemoryTools, onCall, isError, the startup message, the VERSION export, package exports, optional peers, middleware best-effort writes, the V4 middleware and the gpt-5-mini JSDoc claim, and the nams_resolution merge metadata.
- **Links:** every xref and image in scope resolves, including authentication.adoc#_key_lifecycle; no inbound fragment links to these pages exist. README relative links and the #copying-an-example anchor resolve.
- **Removed content:** the old Zod-extraction and custom-tool/restrict steps now live in how-to/typescript/mcp.adoc or were deliberately dropped, and the old anchors are kept.
- **MCP lesson reproduced end to end** in the scratchpad (npm init, the documented installs, copied helpers, the page's server.ts/tsconfig/package fields, `npm run build`, a stdio tools/list probe). This produced the blocker.
- **Source build vs npm:** MAINTAINING.md:85 records building the tutorials from source as a deliberate exception, so I did not flag the build-from-source step itself. The one leftover that breaks is the standalone MCP project installing `../typescript`.

Not done:
- I did not run vitest in the repo (it would write caches inside the checkout), so the docs-assembly and vercel-ai tutorial tests were read but not executed.
- The hosted service's extraction-status vocabulary could not be observed. The status finding rests on the conflict between the Python client/fixtures and the TS helper.
- The Node 22.9 floor for `--env-file-if-exists` comes from Node's changelog; I could not test an older Node here.

Needs a human decision: whether the MCP lesson should switch to the npm release (`@neo4j-labs/agent-memory@0.5.0`) or keep the source build and pin zod. Scratch files are in /private/tmp/claude-502/-Users-lyonwj-github-neo4j-labs-agent-memory/66a2977c-9670-4b56-8270-fc84ea0f1100/scratchpad/review/my-memory-mcp.

### howto-core-a — How-to (Bolt core): entities, extraction, dedup, messages, preferences, reasoning, batch (9 of 9 findings confirmed)

Fully checked (HEAD version and diff against ec9fc65): how-to/entities.adoc, entity-extraction.adoc, entity-extraction-batch.adoc, entity-extraction-schemas.adoc, deduplication.adoc, messages.adoc, preferences.adoc, reasoning-traces.adoc, batch-processing.adoc. I also reviewed the files they include: examples/core_memory_recipes.py, core_memory_settings.py, aura_connection.py, extraction_recipes.py, and the partials backend-both, backend-bolt-only, python-tutorial-setup, python-core-recipe-intro, python-core-recipe-files, python-extraction-recipe-file and python-typescript-equivalents.

Method:
- Checked every Python call in the pages and recipes against inspect.signature and the source at HEAD, including the tuple return of add_entity and the fields of DeduplicationConfig, DeduplicationResult, DeduplicationStats, EntityRef, TraceOutcome, ToolCallStatus, Batch*/Streaming* results and ExtractedEntity/Relation.
- Checked the behaviour claims against the Cypher in graph/queries.py: MERGE on name/type, RELATED_TO.type vs relation_type, NotFoundError, MERGE_ENTITIES, the search_messages session filter, the get_conversation 1000 cap, preference dedup sharing, and extraction_mode='skip'.
- Checked every TypeScript method name in the equivalents partial exists in typescript/src.
- Ran `python3 scripts/check_docs.py --build` (145 pages, 0 errors), so xrefs, fragments and images resolve. Ran a separate Antora build to look for duplicate ids.
- `uv run pytest tests/docs/test_core_python_tutorials.py`: 105 passed.

Not verified:
- The recipes were not run end-to-end against Aura/OpenAI, and GLiNER models were not downloaded.
- The claim that GLiREL needs loguru can't be checked without installing glirel.
- Removed content (TypeScript tabs, the framework-integration and best-practice sections) appears to have moved to reference/api/*, the tutorials and how-to/typescript/*, but I did not audit that line by line.
- I did not flag the pre-existing batch-processing issues left unchanged by this branch: 'Prepare larger imports' treats `documents` as dicts, and `all_documents` is undefined.

Needs a human decision:
- For the find_potential_duplicates confidence bug, choose between a source fix and a docs caveat.
- Decide whether reasoning-traces should say backend-both, or have a page-specific note that the recipe needs Bolt.

### howto-core-b — How-to (Bolt core): v0.2 primitives, providers, migration, privacy (11 of 12 findings confirmed)

Fully checked against HEAD source (diff read, HEAD version read, code samples cross-checked with src/neo4j_agent_memory), all 13 in-scope pages: adopt-existing-graph, audit-reasoning, bring-your-own-model, buffered-writes, configure-embedding-provider, configure-llm-provider, consolidation, evaluation, multi-tenancy, privacy-and-audit, running-without-an-llm, migrate-embedding-model, migrate-to-providers. I also reviewed the included files: partials python-tutorial-setup and python-core-recipe-files, examples core_memory_recipes.py (audit fragment matches the page verbatim) and core_memory_settings.py, and examples/eval-harness/main.py, examples/eval-harness/ci_gate.py and examples/no_llm/main.py (published via example-files.json).

Verified as correct:
- Signatures and behaviour of adopt_existing_graph and the AdoptionReport fields.
- The :TOUCHED edge paths (id / name+type / name), hook error suppression, TraceOutcome persistence, error_kind index and search_steps.
- MemoryClient Generic typing.
- The from_provider native-first dispatch, adapter kwargs, the Vertex adapter's dimension fallback and non-forwarding, EMBEDDING_DIMENSIONS entries, and EmbeddingDimensionMismatchError behaviour.
- MCP CLI flags and env vars.
- All ConsolidationMemory queries and report properties.
- EvalMemory, including the empty-suite 0.0 score and NAMS NotSupportedError for preferences.
- Multi-tenant enforcement points, add_preference dedupe semantics and the ignored session_id in search_messages.
- BufferedWriter semantics, MemoryConfig fields, the encryption protocol, managed vector index names, drop_all prefixes and embedding source-text construction.
- The ExtractionConfig defaults and llm=None validation.
- The llm_provider_from_* helpers in all eight integrations.

Link checks:
- A script resolving every xref, fragment, local <<>>, image and include across all docs pages found no missing targets. The example$ includes are mapped in example-files.json.
- scripts/check_docs.py reports 0 errors.
- tests/docs/test_operational_howto_contracts.py and test_code_snippets.py pass.

Not done:
- No Antora build or rendered-HTML check was run.
- No code was executed against Neo4j or providers.
- The hosted (NAMS) claims were judged only against the SDK clients.

Needs a human decision:
- The repo-wide convention of parking retained anchors at the page foot, when the content moved rather than disappeared.
- Whether to restore UserMemory API documentation somewhere, since reference/api/memory-client.adoc still points to multi-tenancy for it.

### howto-hosted — How-to: NAMS, ontologies, context-graph MCP, team memory, how-to index (12 of 12 findings confirmed)

All six in-scope pages were checked in full against the diff from ec9fc65 and the HEAD file: use-nams, migrate-to-nams, use-ontologies, create-context-graph-mcp, team-memory-in-your-editor and how-to/index.

Included files reviewed:
- partials: backend-*, python-tutorial-setup, python-hosted-state-file, python-hosted-helpers-file.
- example files: hosted_tutorial_state.py and hosted_tutorial_helpers.py.
- team-memory ids from example-files.json: _shared.py, seed_workspace.py, doctor.py, and the three .json.example configs.

How I checked:
- Links: every xref and fragment on the six pages was resolved by rendering each target with asciidoctor. All resolve.
- Old section ids: every old h2-h4 id from ec9fc65 still exists on each page.
- Built site: docs/build/site has the includes resolved.
- Code samples: NamsSettings/connect/close, the ontology method names and ID kinds, read_active_binding and http_client were checked against src and the python-v0.6.0 tag.
- NamsSettings env lifting: confirmed at runtime that MEMORY_API_KEY and MEMORY_ENDPOINT populate NamsSettings().
- CLI: `mcp serve` flags and env vars (NEO4J_USER, NEO4J_DATABASE, --backend, --transport) checked against `neo4j-agent-memory mcp serve --help`.
- MCP tool counts (6/16/20) checked against mcp/_tools.py.
- doctor.py: ran `doctor.py --configs-only` offline in a scratch copy. It passes, but prints "47".
- create_api_key really sends no category; seed's wait_for_extraction and exit codes checked.
- Index: its links match nav.adoc and every how-to page is indexed.

Context for the findings:
- Python 0.6.0 get_active(): the use-ontologies note describes the released python-v0.6.0 behaviour (latest-revision inference). This branch changes src/neo4j_agent_memory/nams/ontology.py so that HEAD reads the exact binding. The note is correct for the published package pinned by the page, but will go stale at the next release. A human should decide whether HEAD src counts as "0.6.0".

Not covered or not verifiable:
- Hosted-service claims (key-to-workspace association, admin-key defaults, OAuth workspace selector, mcp-remote behaviour) could not be observed.
- Did not live-run check_nams.py, activate_ontology.py or seed_workspace.py against NAMS.
- Only spot-checked the index blurbs for non-scope pages (TS/integrations); integrations/crewai and TS observability/strands were judged acceptable.

Needs a human decision:
- migrate-to-nams dropped its per-method NotSupportedError / NAMS-only method tables. The information is now spread across reference/api/* and backend-capabilities, and is less discoverable. For example, add_messages_batch does not exist on NAMS; the migration inventory does not list it, though reference/api/short-term-messages.adoc does. I did not rate this a defect.
- Also dropped: the create-context-graph-mcp Desktop config file paths and the use-ontologies default validation_mode (permissive). Both are minor losses; no finding filed.

### integ-a — Integration how-tos: AWS, Google, index (12 of 12 findings confirmed)

Fully checked, reading the diff and the HEAD file: how-to/integrations/index.adoc, aws-bedrock-embeddings.adoc, aws-hybrid-memory.adoc, aws-strands.adoc, google-adk.adoc, google-cloud.adoc; examples/integrations/common.py, cloud_embeddings_recipe.py, hybrid_recipe.py, google_adk_recipe.py. Also read the included files: partials/python-tutorial-setup.adoc, python-integration-troubleshooting.adoc, python-aura-connection-file.adoc, examples/aura_connection.py and examples/strands_memory_tutorial.py.

How I checked:
- Confirmed signatures against HEAD src with `uv run python -c inspect...` (package 0.6.0 resolved from src): BoltSettings/MemorySettings embedding validation, from_provider, MemoryClient, the short_term, reasoning and get_context signatures, BedrockEmbedder, VertexAIEmbedder, HybridMemoryProvider and its parent Neo4jMemoryProvider, Neo4jMemoryService (ADK), Neo4jSessionManager, Neo4jMemoryStore(Config), context_graph_tools, nams_context_graph_tools.
- Checked third-party APIs in the venv: google-adk 2.7.0 (Runner kwargs, run_async, InMemorySessionService async methods, load_memory/preload_memory, Event.error_code, LlmAgent has no memory field), google-genai 2.22.0 (Content.parts Optional), strands-agents 1.55.1 (MemoryManager(stores=...), Agent session_manager).
- Reproduced the blocker by constructing the recipe settings with both cloud embedders (TypeError).
- Ran tests/docs/test_python_integration_contracts.py: 32 passed. The test does not cover the failing path.
- Resolved every xref (all target pages exist; first-agent-memory#_step_2_set_up_neo4j exists as an anchor), every include (example$ files exist; none need example-files.json), the two images, and the four GitHub tree links (the directories exist in the repo).
- Compared old and new section ids for the six pages. Only index.adoc lost ids; the Strands _model_ids/_limitations ids were explicit and are kept.
- Checked inbound xrefs with fragments across the docs; the only one is configure-embedding-provider -> google-cloud#vertex-ai-embedding-models (reported).

Not verified:
- Live runs against Aura, Bedrock, Vertex or Gemini (no credentials or network).
- Whether Strands' `Agent(model=<str>)` picks up AWS_REGION; I assumed standard Strands/boto behaviour.

Needs a human decision:
- Whether the large removals from the Strands, Bedrock and Google Cloud pages were deliberate, as a move to "one observable recipe" pages. I reported the Strands API content (context_graph_tools, retrieval_config) and the Vertex model table because no other page now documents them.
- The google-cloud:122 link probably should be deploy-an-application.adoc. create-context-graph-mcp.adoc:66 has the same 'deployment routes' link to reference/deployment.adoc; it is out of scope but has the same problem.

### integ-b — Integration how-tos: CrewAI, LangChain, LlamaIndex, Microsoft, OpenAI Agents, PydanticAI (10 of 11 findings confirmed)

Fully checked (HEAD against ec9fc65 diff, with source at HEAD and installed framework packages): the six pages crewai.adoc, langchain.adoc, llamaindex.adoc, microsoft-agent.adoc, openai-agents.adoc and pydantic-ai.adoc; the example files common.py, crewai_recipe.py, langchain_recipe.py, llamaindex_recipe.py, openai_agents_recipe.py and pydantic_ai_recipe.py; and the files these pages include: partials python-tutorial-setup, python-integration-troubleshooting (both tags exist) and python-aura-connection-file, plus examples/microsoft_shopping_tutorial.py and aura_connection.py.

What I verified:
- Every xref target exists, including the first-agent-memory.adoc#_step_2_set_up_neo4j anchor. Both images exist. The tag=function_tool include exists.
- Every old section id (auto ids plus [[api-compatibility]], [#agent], [#legacy], [#shipped-adapters]) is kept as an anchor: macro on each page, and no docs page links to these pages with a fragment.
- Signatures in common.py and the recipes match (from_provider, BoltSettings, get_context, start_trace/complete_trace/get_trace_with_steps, add_message, Neo4jMemoryMiddleware, Neo4jLlamaIndexMemory, MemoryDependency/create_memory_tools, Neo4jOpenAIMemory/record_agent_trace, Neo4jMicrosoftMemory, OpenAIChatClient/as_agent, Agent.context_providers).
- Prose claims checked against the adapter source: CrewAI's sync bridge and unscoped recall, the LangChain middleware hooks, LlamaIndex's aget_all limit of 10 and its unscoped search, and Microsoft after_run persistence.
- Ran tests/docs/test_python_integration_contracts.py (32 passed) and test_links.py plus test_code_snippets.py (226 passed, 142 skipped). The integration src at HEAD is identical to the python-v0.6.0 tag.

Could not verify:
- The openai-agents package (Agent, Runner, function_tool) is not installed or locked, so the recipe's main() and the function_tool snippet were not executed.
- No recipe was run against real Aura or a paid model.
- Whether a newer crewai 1.x supports Python 3.14 (no web access).

Needs a human decision:
- Whether dropping the framework-adapter API reference from the six rewritten pages is intended (finding 3). If it is, a separate reference page should hold that material.
- The how-to/integrations/index.adoc summaries ('automatic tracing' for PydanticAI, 'document + graph retrieval' for LlamaIndex) now go further than what the rewritten pages say. Those lines were not changed on this branch, so I did not report them.

Out of scope but noticed: HEAD's MemoryClient imports neo4j_agent_memory.core._unsupported where the python-v0.6.0 tag imports nams._unsupported. This does not affect these docs.

### howto-ts — TypeScript how-tos (non-provider) (8 of 8 findings confirmed)

I fully checked all 12 pages in scope against HEAD and against the diff from ec9fc65: authenticate, edge-runtime, handle-errors, integrations-overview, langchain, mastra, mcp, nextjs-memory-chat, observability, strands, troubleshooting and vercel-ai. The line numbers below are in typescript/src at HEAD.

**Checked against source:**
- Client and transport: MemoryClient options and env resolution (client.ts: MEMORY_API_KEY, MEMORY_WORKSPACE_ID, X-Workspace-Id override, tokenProvider precedence), the RestTransport error mapping (401/403 -> AuthenticationError, other statuses -> TransportError, raw DOMException TimeoutError, connect() wrapping) and the auth sub-client methods.
- Errors and events: the error classes, bulkAddMessages throwing a plain Error above 100 messages, and the LogEvent shape and default User-Agent format.
- Vercel AI middleware: the options, conversationId resolved at construction time, fire-and-forget wrapStream and awaited wrapGenerate.
- Integrations: LangChain and Mastra adapter methods and metadata fields, MCP tool names and annotations, READ_ONLY_MEMORY_TOOLS, registerMemoryTools only/onCall/return value, the legacy aliases, and the Strands exports, options, forNams, connectMemoryToAgent and registerReasoningHooks.
- Other: the NAMS provider's createNamsProvider, persistInteractions and stream flush, `BridgeTransport` exported from ./testing, `nams_resolution` on a merged addEntity, the Conversation type fields, and CHANGELOG 0.5.0 (spec v4).

**Checked against runnable examples:** cloudflare-agents-edge handlers, langchain, mastra, mcp, nextjs-memory-chat (handlers, route, page, lock versions) and the vercel-ai/strands test lists.

**Links:** every xref resolves, and so do the fragments #streaming-memory-persistence and <<why-not-a-storage-adapter-yet>>. The anchor:/[[...]] preservation ids appear in the rendered HTML. None of these pages uses include::.

**Tests I ran:**
- typescript `npx vitest run test/integration/docs-contract.test.ts test/unit/edge-runtime.test.ts`: 16 passed.
- typescript/examples/mcp `npx vitest run test/docs-assembly.test.ts`: passed. It compiles the tutorial server plus this page's custom and restricted recipes and checks 6/7/2 tools.
- `npm run lint` in examples/mcp fails with "Missing script".

**Needs a human decision or can't be verified from here:**
- The 'Other languages' claims in integrations-overview: the `neo4j_agent_memory_client` LangGraph/PydanticAI integrations, the C# `MemoryConnector` and the R `register_memory_tools` with '12 memory tools'. These predate the branch; no source for them exists in this repo.
- Hosted-only behaviour: the auth management permissions and the hosted MCP surface at mcp.memory.neo4jlabs.com.

**Low-value issues I found and did not report:**
- The Strands page says a failed reasoning write 'logs through the constructor logger', but the hooks swallow the error with an empty catch; only the client transport logger sees HTTP failures. This line predates the branch.
- The edge page attributes User-Agent stripping to Cloudflare, but the SDK itself drops the override when it detects no runtime. Also unchanged by this branch.

I did not run the full example test suites or a docs build; I used the existing docs/build/site, which was built after HEAD.

### provider — NAMS AI provider family (new pages) vs provider source (16 of 16 findings confirmed)

Checked in full against the provider source at HEAD (all 9 files under typescript/packages/vercel-ai-provider/src plus package.json and CHANGELOG): the landing page how-to/typescript/nams-ai-provider.adoc; the provider-, middleware-, tools- and hooks-mode how-tos; reference/nams-ai-provider.adoc; explanation/nams-ai-provider-retrieval.adoc; and typescript/examples/nams-ai-provider (README, .env.example, .npmrc, package.json, tsconfig.json, the 4 src programs, test/docs-pages.test.ts, and the key entries of package-lock.json at HEAD).

Verified correct:
- Every xref in the 7 pages resolves, the in-page anchors (tools-mode, hooks-mode, errors, hook-events) exist, the 3 SVGs exist, and nav/index entries are present.
- Each program is byte-identical to its embedded page. `npx tsc --noEmit` passes and `npx vitest run` passes 8/8.
- Defaults (maxMemories 6, cap 12, crossSessionLimit 5, graphExpansionLimit 2, 5 triples per entity, sessionLimit 40, graceSteps 3, 30 s hook timeout, 20 queued context entries, endpoint) all match the source.
- Peer ranges, engines >=22, the single ESM entry, the 0.3.0 tag date (2026-09-22), the removal of extractionModel from provider/memory in 0.3.0, the MCP optional/prefix/401 behaviour, hook matcher rules, the matcherless events and the additionalContext timing all match.
- The retrieval explanation matches the implementation: sources, order (entities, graph, conversation, cross-session, reasoning), round-robin merge, word-by-word fallback (4 longest words, >=3 chars, as typed plus Title Case, then overlap rank), graph-expansion caps, and the prompt-block format and placement.
- The TS CI path filter covers these docs pages, and the example is in the type-check-examples matrix.

Runtime evidence came from a scratch runner in the scratchpad that drove the real example programs against the repo's hosted stub and MockLanguageModelV4, plus one mutation run of a scratch copy of hooks-mode.ts. No repo files were changed; the only working-tree change is the pre-existing one in package-lock.json.

Not verified:
- Hosted claims: that NAMS uses vector search with a text fallback, server-side extraction from persisted turns, and which end of the conversation getConversation's limit keeps.
- Whether `--env-file-if-exists` (used in the page run commands and the npm scripts) works on every Node 22.x. I believe it arrived in a later 22.x minor (around 22.9), which would conflict with the stated 'Node 22 or newer', but I couldn't confirm the version offline. A human should check.
- The SVG diagrams were checked only for their text labels, not their layout. The hooks diagram's label order ('prepare() resolves messages' before UserPromptSubmit) may suggest history loads first; the page and the source say UserPromptSubmit runs before history loads. Worth a look.

Needs a human decision: the conversation-resolution finding. Either document the current 'reuse the latest conversation' behaviour, or treat it as unintended; the offline test currently asserts it (conversations.size 1).

### ref-api-a — Python API reference: MemoryClient, adapters, factory, LLM provider, long-term family (7 of 7 findings confirmed)

Fully checked all 9 changed files in scope: memory-client.adoc, adapters.adoc, factory.adoc, llm-provider.adoc, long-term.adoc (hub), long-term-entities.adoc, long-term-preferences.adoc, long-term-deduplication.adoc and long-term-geospatial.adoc. None of them includes a partial or example file.

What I checked:
- **Signatures and models.** Checked every `// contract:` signature against inspect.signature at HEAD: MemoryClient ctor, get_context, get_graph and get_locations; all 10 adapter constructors including `_DEFAULT_MAX_TOKENS`=4096; from_provider; the Protocols and schema_aligned_extract; and every bolt/NAMS LongTermMemory method on the four subpages. Checked every field table against the models: GraphNode, GraphRelationship, MemoryGraph, ChatMessage (frozen), Completion, Usage, Entity, Relationship, Preference, Fact, and the four dedup dataclasses. All match. tests/docs/test_python_reference_contracts.py passes (175 passed).
- **Behaviour claims.** Read the source for:
  - get_context scoping on bolt and NAMS
  - get_stats keys
  - graph proxy deprecation
  - write_errors, flush and connect on NAMS
  - add_entity merge/id re-read
  - add_relationship NotFoundError, MERGE id reuse and unpersisted attributes
  - merge_duplicate_entities edge list
  - DeduplicationConfig validation
  - geocode_locations skip_existing
  - bolt get_context kwargs
  - every row of the NAMS wrapper table (add_entity body, search body, get_entity_by_name limit 20, related/relationships shapes, get_context "", NotSupportedError methods)
  - wait_for_extraction, expand_graph, set_entity_feedback mapping, get_entity_history
  - factory resolution, native sets, ImportError hint and ValueError
  - adapter notes: SentenceTransformers ValueError for unknown models, Vertex retired default and 768 resolution, the OpenAI strict path
- **Links and anchors.** A script resolved every xref and fragment; none are broken. That includes first-agent-memory#_step_2_set_up_neo4j (a legacy anchor), configuration-advanced#deduplication, configuration-operations#geocoding, reasoning-models#_entityref and adapters#_adapter_availability. Every old auto-id of long-term.adoc at ec9fc65 (34 ids) is kept as an anchor in the hub. Old memory-client ids are kept as well, though some legacy anchors such as _parameters_2 and _example now sit at different positions. asciidoctor -v shows no duplicate-id warnings, and the new subpages are in nav.adoc and reference/index.adoc. test_links.py and test_code_snippets.py pass.
- **Lost content.** Confirmed that the content removed from the hub moved to the four subpages, and that the removed get_entity, update_entity, delete_entity, get_preferences, delete_preference and get_facts entries are replaced by notes saying those wrappers do not exist, which is correct.

Not verified: the hosted-side claims (NAMS reasoning compatibility traces, and the server-side behaviour behind the /entities endpoints) cannot be observed from here. I judged them only against the SDK client code.

Needs a human decision: legacy anchors placed in hub list items (long-term.adoc:34-37) take old links to the hub rather than to the subpage section. MAINTAINING.md allows this, but a forwarding approach may be preferred. Unchanged older text I noticed but did not report: the factory resolution algorithm omits the `embedding-*` bare-name prefix, and the install-hint whitespace differs from the source.

### ref-api-b — Python API reference: short-term and reasoning families (8 of 8 findings confirmed)

Fully checked all nine changed files in scope against the source at HEAD:
- docs/modules/ROOT/pages/reference/api/short-term.adoc
- docs/modules/ROOT/pages/reference/api/short-term-messages.adoc
- docs/modules/ROOT/pages/reference/api/short-term-search.adoc
- docs/modules/ROOT/pages/reference/api/short-term-sessions.adoc
- docs/modules/ROOT/pages/reference/api/reasoning.adoc
- docs/modules/ROOT/pages/reference/api/reasoning-models.adoc
- docs/modules/ROOT/pages/reference/api/reasoning-search-stats.adoc
- docs/modules/ROOT/pages/reference/api/reasoning-steps.adoc
- docs/modules/ROOT/pages/reference/api/reasoning-traces.adoc

Sources compared: src/neo4j_agent_memory/memory/short_term.py, memory/reasoning.py, nams/short_term.py, nams/reasoning.py, graph/queries.py, core/memory.py and schema/models.py.

What I checked:
- **Signatures:** every signature matches inspect.signature output for ShortTermMemory, NamsShortTermMemory, ReasoningMemory, StreamingTraceRecorder and NamsReasoningMemory. `tests/docs/test_python_reference_contracts.py -k 'short-term or reasoning'` passes (39 passed).
- **Model tables:** Message, Conversation, ExtractionStatus, SessionInfo, ConversationSummary, ReasoningTrace, ReasoningStep, ToolCall, Tool, ToolStats, ReasoningStepWithContext, EntityRef and TraceOutcome all match the Pydantic fields and defaults.
- **Behaviour claims:** checked get_conversation's 1000-message cap, search_messages ignoring session_id, the get_context kwargs, the list_conversations ordering and default, the summarizer precedence, and the NAMS kwarg handling and NotSupportedError methods.
- **Anchors:** every old auto-generated id from `git show ec9fc65` for short-term.adoc and reasoning.adoc is kept as an `anchor:` on the new hubs, and the ids are present in the built HTML (docs/build/site is newer than the sources).
- **Links:** every xref target in these pages exists, and the fragment xrefs (#_entityref, #_nams_and_shared_conversation_operations) resolve to ids in the built HTML. The nav lists every subpage.
- **Lost content:** the old content moved to the subpages or to explicit "method does not exist" notes, and wait_for_extraction is still documented on other pages.

Not verified:
- I did not run delete_message against a live Neo4j. The finding rests on the Cypher in queries.py and the existing integration-test comment.
- Hosted NAMS behaviour was judged only against the SDK client code.

Needs a human decision: whether the clear_session trace-deletion gap should be fixed in the SDK (wire up the unused LINK_CONVERSATION_TO_TRACE in start_trace) or only documented.

### ref-config — Configuration, environment variables, CLI, MCP tools, schema objects (7 of 7 findings confirmed)

I fully checked all 10 in-scope files against HEAD source: docs/modules/ROOT/pages/configuration.adoc (legacy forwarder), reference/configuration.adoc (hub), reference/configuration-connections.adoc, reference/configuration-providers.adoc, reference/configuration-operations.adoc, reference/configuration-advanced.adoc, reference/environment-variables.adoc, reference/cli.adoc, reference/mcp-tools.adoc and reference/schema-objects.adoc.

What I checked:
- **Settings fields and env vars.** I dumped every settings.py field, default and constraint and compared them with the tables. The `// settings-fields` and `// cli-options` contract tests pass (tests/docs/test_python_reference_contracts.py and test_links.py: 188 passed).
- **Settings behaviour, run for real.** `NAM_EMBEDDING`/`NAM_LLM` provider strings, `NAM_BACKEND` with `NAM_NAMS__TIMEOUT`, the example dotenv file, the hub precedence example (its assert holds), the `llm=None` validation, and a partial `NAM_NEO4J__` set without a password (fails, so "required" is right).
- **MemoryClient claims.** The legacy embedder factory builds only openai and sentence_transformers; `multi_tenant`, `write_mode` and `max_pending` are forwarded; the geocoder and `enrichment_provider` injection; `DeduplicationConfig` and the `LongTermMemory` signature; `get_tracer` and the OTLP endpoint; the ResolutionConfig validation error type; the Vertex validator; `stop_on_success`; resolver wiring.
- **CLI.** Checked against cli/main.py: options, env aliases, backend resolution, stats JSON keys, `--confidence-threshold` wiring. `schemas validate` on the page's YAML example succeeds.
- **MCP.** Tool names, parameters and defaults per profile (6 core, 16 extended, plus 4 NAMS-only), resources, prompts, the `session_id` claim for `memory_search`, graph_query, the NAMS NotSupported methods, the fastmcp 4 pin.
- **Links.** Every xref, fragment, local `<<>>` and image in the scope files resolves. No duplicate ids.
- **Old anchors.** Every old auto-id from main's configuration.adoc, reference/configuration.adoc, environment-variables.adoc, cli.adoc and mcp-tools.adoc still resolves; some land on the wrong bullet (reported).
- **Removed content.** Nav and reference index list all four subpages. What the shrunken pages lost is covered elsewhere, apart from the old "Complete example" and "Geospatial usage example". Their anchors now land on bullets without that content; I judged that acceptable and did not report it.
- **Rendering.** I read the existing docs/build/site output, which is newer than the sources.

Not done or needs a human:
- I did not run a fresh Antora build.
- I did not verify hosted NAMS behaviour; hosted claims were judged against the SDK only.
- The wrong `audit_reads` name also sits in the `audit_read` Field description in src/neo4j_agent_memory/config/settings.py:382, so a maintainer should decide whether to fix the source as well.

### ref-extract-schema — Extractor and schema reference family (9 of 9 findings confirmed)

Checked all ten in-scope files against the HEAD source: reference/extractors.adoc (hub), extractor-classes, extractor-relations, extractor-pipeline, extractor-builder, extractor-streaming, schemas.adoc (hub), schemas-domains, schemas-custom and schemas-api. None of them has include:: or image:: directives.

**What I checked:**
- **Signatures and models.** Every signature on these pages matches inspect.signature output for the classes in src/neo4j_agent_memory/extraction/* and schema/*. That covers SpacyEntityExtractor, GLiNEREntityExtractor, LLMEntityExtractor, GLiRELExtractor, GLiNERWithRelationsExtractor, ExtractionPipeline, ExtractorBuilder, StreamingExtractor and SchemaManager. The result-model field tables match the Pydantic model_fields and the dataclass fields: ExtractionResult, ExtractedEntity, ExtractedRelation, ExtractedPreference, StageResult, PipelineResult, BatchItemResult, BatchExtractionResult, StoredSchema, SchemaListItem, DomainSchema, EntityTypeConfig, RelationTypeConfig and EntitySchemaConfig.
- **Contract test.** tests/docs/test_python_reference_contracts.py passes (175 passed).
- **Enums and domain schemas.** The MergeStrategy values match the pipeline enum and the config.settings enum. The eight domain schemas and all their labels and descriptions in schemas-domains match DOMAIN_SCHEMAS in gliner_extractor.py exactly. There is no extraction/domain_schemas.py module; the page's corrected import from gliner_extractor is right.
- **Mappings and helpers.** The GLiNER label mapping (unmapped labels become OBJECT with the uppercased label as subtype), the spaCy default mappings, and the EntitySchemaConfig is_valid_type/normalize_type claims all match the source.
- **Links and anchors.** Every xref target page exists, and the fragment xref how-to/entity-extraction-schemas.adoc#_write_effective_schema_descriptions resolves. tests/docs/test_links.py, test_nav_labels.py and test_code_snippets.py pass. nav.adoc lists all eight new subpages.
- **Old anchors and moved content.** Every section id from main's extractors.adoc and schemas.adoc is preserved as an anchor on the hubs (see the nit about _constructor_5/_example_5). Content removed from the old pages reappears in the subpages. The old "Schema best practices" list moved to how-to/entity-extraction-schemas.adoc "Write effective schema descriptions".

**Not done:**
- I did not run the GLiNER, GLiREL or spaCy models; they are not installed. Behaviour claims were verified from source only.
- I did not render the site.

**Needs a human decision:**
- The branch changed `client._client` to `client.graph` for constructing SchemaManager (finding 6). Maintainers should decide which public accessor the docs should recommend.
- tutorials/knowledge-graph.adoc:22 (outside my scope) links to extractors.adoc#_glirelextractor "for why those two packages are named explicitly". After the split, that anchor lands on a one-line hub bullet, so the tutorial may want to link to reference/extractor-relations.adoc directly.

### ref-other — Reference: backends, REST, NAMS limits/MCP, ontology/skills API, auth, TypeScript API, deployment (9 of 9 findings confirmed)

Fully checked, against the HEAD source, the ec9fc65 versions and the rendered docs/build/site: backend-capabilities.adoc, rest-api.adoc, nams-limits.adoc, nams-mcp.adoc, ontology-api.adoc, skills-api.adoc, authentication.adoc, typescript-api.adoc, deploy-an-application.adoc, deployment.adoc and index.adoc.

What was checked:
- **Links:** every xref target and fragment in the 11 pages resolves: script plus manual anchor check, and the built HTML has 0 'unresolved' xrefs. Incoming fragment links (#scope, #hosted-cleanup, #errors, #python-0-6-active-binding, #_key_categories, #_key_lifecycle) resolve. Former anchors are retained on deployment.adoc (all 29 appear in the built HTML), index.adoc and rest-api.adoc (_base_url_versioning, _cypher_and_auth). Nav entries exist.
- **REST tables:** checked against the Python EndpointSpec registries in nams/short_term.py, long_term.py, reasoning.py, query.py, auth_keys.py and ontology.py, and the TS ROUTES in typescript/src/transport/rest.ts. Methods and paths all match. There is no TS extraction-status route, as documented.
- **Python behavior:** checked the Python error mapping and retry set (transport.py), NamsAuth signatures, the NAMS `add_entity` merge fallback and confidence default, `list_conversations` params, and `get_conversation`'s two requests.
- **Capability matrix:** checked against the `_NamsUnsupported` wiring in `__init__.py`, the NotSupportedError raises in nams/*.py, Bolt `wait_for_extraction` (no-op), Bolt `search_messages` (session_id not applied; verified in the SEARCH_MESSAGES_BY_EMBEDDING Cypher), and the MCP registration counts (6/16/20 in mcp/_tools.py).
- **TypeScript API page:** checked against typescript/src 0.5.0: client options and the regex, `namespace` unused, lazy connect, subclient methods and defaults, bulk limit, waitForExtraction, the error classes and the absence of retries, the 7 subpath exports, Node >=22, the 12 MCP tools, and the expandGraph fix (via the snakeBody route; confirmed in the typescript-v0.4.1 tag).
- **Other:** Cloud Run claims against deploy/cloudrun, MCP transports against server.py and the CLI, and the MAINTAINING.md conventions.

Not treated as defects (hosted-only claims I could not verify): rate limits, quotas, OAuth endpoints, the skills endpoints and gates, and the ~28 ontology templates.

Pre-existing issues on lines this branch left unchanged, not reported as findings:
- typescript-api.adoc:195 says the bridge transport raises NotSupportedError for (hosted) methods, but bridge.ts POSTs any method name.
- typescript-api.adoc:327 says 'The SDK normalizes both directions' for entity types, but `addEntity` sends `entityType` unchanged over REST and `toEntity` returns `type` unchanged.
- typescript-api.adoc:41 has an unpinned `npm install`, against MAINTAINING's rule to pin exact versions.

Needs a human decision:
1. This branch changes Python `nams/ontology.py` `get_active()` and TS `getActive()` behavior, but the Python version stays 0.6.0 and neither CHANGELOG has an [Unreleased] entry. The ontology-api caveat describes released PyPI 0.6.0 correctly, but HEAD source labelled 0.6.0 now behaves differently.
2. Whether the hosted MCP tool counts (47 / 13) should be stated at all: the READMEs and a test enforce them, while nams-mcp.adoc now disclaims them.

### explanation — Explanation pages, glossary, FAQ (10 of 10 findings confirmed)

Fully checked (diff against ec9fc65 and the HEAD text, factual claims checked against source): explanation/index.adoc, backends.adoc, context-tiers.adoc (new), extraction-pipeline.adoc, framework-comparison.adoc, graph-architecture.adoc, memory-types.adoc, multi-agent-sharing.adoc, ontologies.adoc, operational-primitives.adoc (new), poleo-model.adoc, resolution-deduplication.adoc, skills.adoc, structured-extraction.adoc, why-provider-protocol.adoc, glossary.adoc and faq.adoc, plus the included partials backend-*.adoc.

Links, anchors and images: I ran `python3 scripts/check_docs.py --build --report <scratch>` (a full Antora build in a temp dir) and got 145 pages and 0 errors, covering xrefs, fragments and images. I also built the site to scratch and confirmed backends.html has no duplicate ids despite the stacked `[#id]` lines. `pytest tests/docs -k "explanation or faq or glossary"` passes. Every old FAQ `[[id]]` anchor is kept (60 questions before and after).

Checked against source and found correct: search_messages ignores session_id; NAMS NotSupportedError for preferences, facts and add_relationship; the read-only hosted query; MergeStrategy names and semantics; `_entity_key`; RELATED_TO `relation_type` on the extraction path; HAS_MESSAGE, MENTIONS and INITIATED_BY; the StreamingExtractor defaults; the OpenAI strict mode, Anthropic tool mode and Bedrock-Anthropic toolConfig fallbacks to schema_aligned_extract; StructuredExtractionError; `_ProviderToEmbedderAdapter`; `prefer_litellm`; `EmbeddingDimensionMismatchError`; DeduplicationConfig defaults 0.95/0.85; the Nominatim and Google geocoders; `geocode_locations`; the consolidation dry_run defaults, the superseded-preference owner gap, ConsolidationRun and MemoryReadAudit/PERFORMED_READ; the single buffered drain task and write_errors; and the LangChain BaseChatMessageHistory and middleware.

Content that moved: ontology details are in reference/ontology-api.adoc and skills lifecycle, attestation and gates are in reference/skills-api.adoc, so nothing was lost there. The POLE+O subtype lists and the FAQ Neo4j-version answer were lost (reported).

Not verifiable here (hosted-only, per docs/MAINTAINING.md:68): the context-tiers claim that reflections are generated past a compression threshold, the NAMS workspace/admin-key semantics, and skills preview behaviour. These need a maintainer with NAMS access.

Not reported (judgement calls for a human):
- operational-primitives.adoc gives no backend note, though client.users/buffered/consolidation are NAMS sentinels that raise NotSupportedError (CHANGELOG.md:627).
- The framework-comparison `:description:` omits Google ADK, which the table includes.
- The explanation/index 'read the first three in order' sequence (memory types, graph, POLE+O) differs from the nav order (memory types, backends, POLE+O).

explanation/nams-ai-provider-retrieval.adoc was not in my assigned scope and was not reviewed.

### entry — Entry points: index, getting started, SDK pages, nav, READMEs, CLAUDE.md, CONTRIBUTING, MAINTAINING (10 of 10 findings confirmed)

Fully checked, reading the diff and the HEAD file: docs/modules/ROOT/pages/index.adoc, getting-started.adoc, sdks/python.adoc, sdks/typescript.adoc (plus the partials they include: labs-disclaimer.adoc, typescript-tutorial-checkout.adoc), docs/modules/ROOT/nav.adoc, README.md, README-pypi.md, CLAUDE.md (branch hunks plus untouched lines those hunks make wrong), CONTRIBUTING.md, docs/MAINTAINING.md.

How I checked:
- A script resolved every xref, fragment, include and image in the four pages and nav. None missing; the targets `first-agent-memory.adoc#_step_2_set_up_neo4j` and `backend-capabilities.adoc#scope` exist.
- Nav vs pages: no duplicates. The only page missing from nav is the top-level configuration.adoc, a legacy-redirect forwarding page that MAINTAINING allows. No page was dropped from the old nav. Label/title differences are deliberate shortenings.
- Former section ids: I rendered the old and new versions of each page with the repo's Asciidoctor.js. That is how the wrong or lost anchors in the first two findings were found.
- README/README-pypi links and images: all relative links and images exist at HEAD. The three diagram PNGs are tracked in docs/diagrams/manifest.json, and `manage_diagrams.py status` reports no errors. README-pypi has only absolute links.
- Python claims checked against the installed 0.6.0 package: MemoryClient/MemorySettings fields, Neo4jConfig username/database, NAMS create_conversation/add_message/get_conversation, add_preference, get_context, NAMS NotSupported for preferences/facts/relationships, the CLI mcp serve options (--backend, --user/NEO4J_USER, NEO4J_DATABASE), and 16 extended tools plus 4 platinum (20) on NAMS. The fastmcp dependency chain pulls in click and rich.
- TypeScript claims checked against typescript/src and package.json: version 0.5.0, engines >=22, optional peers, subpath exports, createConversation/addMessage/addEntity/getContext signatures, check:version, lint, test and test:tck scripts, tsup ESM-only.
- CI claims checked: the type-check-examples matrix with its Node 22 legs, the vercel-ai-provider job, the new docs path triggers, the Ruff paths in the Makefile and in CI, and the integration-contracts job.
- MAINTAINING file references checked: scripts, tests, partials, extensions, docs/diagrams, .claude/skills (four), the playbook UI bundle, and the check_docs flags.

Not checked or out of scope:
- Hosted NAMS behaviour claims (conversation resume semantics, workspace sharing). The SDK clients are consistent with them.
- The external npm/PyPI release state.
- Whether PyPI's sanitizer keeps the `<a id>` tags in README-pypi. They are harmless either way.

Out-of-scope issues seen in passing:
- Makefile:105 help text says `make docs-lint       Watch for changes and rebuild`, which is wrong. The Makefile is not in my scope; worth flagging to whoever reviews it.
- Many docs pages outside my scope also hard-code `anthropic/claude-3-5-sonnet-latest` (bring-your-own-model, configure-llm-provider, migrate-to-providers, cli, factory reference).

Needs a human decision:
- Confirm the retired-model finding against Anthropic's current model list.
- Decide whether README's second embed of the-three-layer-memory-architecture.png (lines 23 and 168) is intentional.

### x-content-loss — Cross-cutting: content loss and anchor breakage from the big rewrites (8 of 8 findings confirmed)

Scope: docs/modules/ROOT/pages; 145 files changed, 34 added, 0 deleted or renamed. nav.adoc keeps every old xref and adds the new subpages.

Automated checks, run over all 111 old pages and all HEAD pages:
(1) Anchors. I rendered ec9fc65 (via git archive into the scratchpad) and HEAD with Asciidoctor 2.0.26 (default idprefix/idseparator), collected every rendered HTML id and diffed them per page. The results are in the anchor finding. The hub pages (reference/configuration, api/long-term, api/short-term, api/reasoning, extractors, schemas) and the top-level configuration.adoc redirect do keep all their old ids, via anchor: macros.
(2) Links. Every xref#fragment and <<id>> in HEAD pages, partials and nav resolves. The repo-wide neo4j.com/labs/agent-memory/...#fragment links (README, README-pypi, the two strands example READMEs) resolve.
(3) Includes. Every include:: (partial$, example$ including example-files.json ids, and tags) resolves.
(4) Images. Every image:: target in pages and partials exists.
(5) Lost identifiers. A global check of source-defined names (functions, classes, dataclass fields under src/) that the old docs mentioned and that appear nowhere in the HEAD docs. This found the Strands, PydanticAI (nams_memory_tools), LangChain option, Vertex model and extras losses. Other names on that list were deliberate removals of APIs that don't exist (WikimediaEnricher, Neo4jChatStore, ObservabilityConfig, the NAM_OBSERVABILITY/NAM_CLI/NAM_DEDUPLICATION env vars, update_entity and similar) or trivia.
(6) Method coverage. Every public method of ShortTermMemory, LongTermMemory, ReasoningMemory, UserMemory, ConsolidationMemory and EvalMemory still appears in HEAD docs, except UserMemory.get_user/list_users (dropped from the migrate-to-nams table; minor, not reported). Every MemorySettings sub-config field appears in the reference/configuration* tables.

Pages I read in full (old against HEAD): how-to/integrations aws-strands, pydantic-ai, langchain, llamaindex, crewai, openai-agents, google-cloud, aws-hybrid-memory, microsoft-agent; how-to entities, preferences, reasoning-traces, messages, use-nams, migrate-to-nams; explanation/poleo-model; the configuration.adoc redirect; reference/configuration plus its four subpages; reference/api/long-term, short-term and reasoning (hubs and sizes; the subpages grew); reference/extractor-builder. I compared headings only for the faq, getting-started, batch-processing and explanation/backends.

Not reviewed line by line for content loss, beyond the automated identifier and anchor checks: the tutorials (knowledge-graph, conversation-memory, first-agent-memory, microsoft-agent-memory, strands-agent-quickstart and the TypeScript tutorials; these now include maintained example files, so the cuts look deliberate), explanation/framework-comparison, resolution-deduplication, graph-architecture and extraction-pipeline, reference/deployment, reference/environment-variables, and how-to deduplication and entity-extraction-schemas.

Not reported but a human may want to decide:
- Microsoft Agent and OpenAI Agents pages lost their API-reference and troubleshooting sections (format_traces_for_prompt, the GDSConfig field docs, the tool list); they now point to example apps.
- Enrichment is covered only by the config table; how enriched data surfaces on entities is no longer described.
- The old explanation/backends list of the four core.protocols Protocols was removed.
- Many compatibility anchors are retained on generic paragraphs. They resolve but no longer lead to the promised content; the Strands and Vertex cases are reported because a reader needs the missing content.

### x-diagrams — Cross-cutting: diagrams, exports, manifest, captions (13 of 14 findings confirmed)

Checked in full: git diff --name-status for every path in scope (125 files). This covers all 54 scenes in docs/assets/diagrams/excalidraw (renames verified R100 or content-checked), all 47 files under docs/modules/ROOT/images, docs/diagrams/manifest.json, source-migrations.json, package.json, docs/assets/images/diagrams/diagram-descriptions.md, scripts/export_diagrams.mjs and scripts/manage_diagrams.py (diff and HEAD).

Manifest:
- Recomputed every source and output sha256; all match.
- Every recorded file exists, and `python3 scripts/manage_diagrams.py status` exits 0.
- Re-exported every recorded source to scratch with the repo exporter. All SVGs reproduce byte-for-byte; three PNGs do not (reported).

Image references:
- Every image:: in pages/partials resolves and is in the manifest.
- Unreferenced but manifest-tracked orphans (20): 1-natural-relationship-modeling.png/.svg, a-three-layer-solution.png, architecture-overview.png, architecture.png, background-entity-enrichment.png/.svg, financial-advisor-app-chat-aml-agent.png, graph-schema.png/.svg, mcp-server-architecture.png, overview.png, pipeline-architecture.png, short-term-memory.png, tfl-explorer-full-stack-architecture.png, the-three-layer-memory-architecture.png, three-extraction-approaches.png/.svg.
- README.md references three of those PNGs, and the manifest records that. images/assets/favicon.svg and logo.svg are outside the diagrams check.

Deleted files: grepped README.md, README-pypi.md, CLAUDE.md, examples, docs, typescript, scripts, tests, Makefile and .github for every deleted or moved filename. No dangling file references; the only stale hit is the CLAUDE.md directory path (reported).

Captions and alt text: compared against each referenced scene's own text elements. Diagram claims were checked against source for:
- POLE+O subtypes
- MCP tool and prompt counts (6 / 16 / +4 NAMS)
- TypeScript MCP (12 tools)
- dedup thresholds
- max_pending
- HAS_STEP.order, TOUCHED.recorded_at, HAS_PREFERENCE/APPLIES_TO, RELATED_TO.type
- extractor stage order
- user_identifier params
- provider retrieval constants (5 / 2 / 5 / 6 / 12, prepend to last user message)
- hook matcherless events
- provider entry points
- Microsoft class names
- tutorial route branch counts

House style: fonts, roughness, min font size and exportScale were scanned for all scenes.

Not done or needs a human:
- I did not visually inspect every SVG at 648px/390px. docs/build/render-report/report.json is from Sep 18 and predates the HEAD page changes (it still shows memory-types using the old diagram).
- Hosted-only claims in context-tiers-funnel, bolt-vs-nams and nams-hosted-memory-flow were checked only against SDK clients.
- tests/docs/test_diagram_manifest.py has no test for the new orphan check (outside my path scope).
- .claude/skills/docs-excalidraw/SKILL.md:235 still says the export is a PNG (outside scope).
- A maintainer needs to decide the fate of the 20 unreferenced legacy exports and whether README should move to SVG.

### x-security — Cross-cutting: security and secret-handling sweep (4 of 6 findings confirmed)

Swept the whole diff ec9fc65..HEAD, excluding attachments, audit-evidence, svg/png/excalidraw, uv.lock and package-lock files (74k lines, saved to scratchpad/review/full.diff).

Secret scan: added lines checked for nams_*, sk-*, AKIA*, ghp_*, AIza*, private-key blocks, curl|sh and literal key exports. Only placeholders and test fixtures turned up (e.g. nams_offline, nams_realLookingKey123456 in a test that asserts it is never echoed). No filled .env file is committed.

Fully checked:
- CI and deploy files: .github/workflows/ci-python.yml and ci-typescript.yml (least-privilege `contents: read`, no pull_request_target, no new github.event interpolation inside run:); deploy/cloudrun Dockerfile (runs as non-root appuser), README, cloudbuild.yaml (now --no-allow-unauthenticated plus --invoker-iam-check and a dedicated SA) and service.yaml; deploy/mcpb README and manifest.
- TypeScript tutorial helpers: typescript/examples/shared/tutorial-state.ts, tutorial-cleanup.ts and tutorial-mcp.ts.
  - The scrypt KDF uses Node defaults (N=16384, r=8, p=1) with a 16-byte random per-run salt. The comparison is non-constant-time, which is irrelevant for a local check.
  - State files are written 0600 with an exclusive lock, symlinks are refused, requests use redirect:error, and the key is never persisted.
  - The TypeScript and Python digests differ: TypeScript salts with the hex string, Python with its decoded bytes. They are separate ledgers, so this is not a defect.
  - Cleanup deletes only recorded entities that pass provenance, freshness and neighbour checks.
- Python tutorial helpers: docs/modules/ROOT/examples/hosted_tutorial_state.py, hosted_tutorial_cleanup.py, the ontology restore/delete in hosted_tutorial_helpers.py, and aura_connection.py. Cleanup scope is narrow, scrypt parameters are explicit, and state files are 0600.
- typescript/examples/nams-ai-provider: .npmrc (install-links=true only affects the file: deps; the committed lockfile keeps resolved file: entries; no registry tokens), package.json and .env.example.
- New .env.tutorial.example files: both tutorials copy them to .env under umask 077 and noclobber, and .env plus .tutorial-state/ are gitignored.
- Claude Code / Desktop / Cursor MCP example configs and the team-memory README and how-to.
- Examples: eval-harness, no_llm and financial-advisor reset scopes (label/name-scoped, with confirmation); ontology-lifecycle main.py.
- Code: nextjs-memory-chat lib/app diffs; Python SDK src diffs (no security impact); TS SDK src diffs (the `namespace` doc now correctly says it does not isolate); scripts/render_docs.mjs and export_diagrams.mjs (bind 127.0.0.1 with a path-traversal guard); docs/extensions/*.js and docs/ui/js/tutorial-code.js (textContent only, no innerHTML).

Not re-read line by line: the bulk of the prose-only doc page rewrites and the long tests/docs/* contract tests, beyond the credential/key/delete greps above.

Pre-existing issues this branch did not introduce, left for a human decision:
- The nextjs-memory-chat 'npx vercel deploy' section publishes unauthenticated /api routes that spend the owner's NAMS/OpenAI keys and read any conversationId.
- The financial-advisor GCP README still deploys with --allow-unauthenticated.
- cypher-shell -p "$NEO4J_PASSWORD" puts the password in process arguments in a few READMEs.

The broken DOCUMENTATION_REMEDIATION_STATUS.md link is outside the security focus but was confirmed with commands, so it is included.

### x-consistency — Cross-cutting: consistency of facts across docs, READMEs and CLAUDE.md (13 of 15 findings confirmed)

Files fully checked for cross-cutting facts, against the HEAD diff and the source: README.md, README-pypi.md, CLAUDE.md (diff hunks plus the MCP/TCK/CI sections they touch), CONTRIBUTING.md, docs/MAINTAINING.md, examples/README.md, typescript/README.md, typescript/examples/README.md, docs pages sdks/python.adoc, sdks/typescript.adoc, getting-started.adoc and index.adoc, and the partials labs-disclaimer, aura-tutorial-setup/cleanup/resume, python-tutorial-setup, typescript-tutorial-checkout and python-typescript-equivalents.

Tree-wide greps over docs/modules/ROOT (pages, partials, examples) and the in-scope READMEs:
- Versions: 0.6.0, 0.5.0 and 0.3.0 are consistent. The only stale version is the historical examples footer, which is labelled as history.
- pip extras: every extras name used is valid against pyproject.toml.
- npm pins: see the nit about unpinned installs.
- NEO4J_USER vs NEO4J_USERNAME: consistent. The CLI reads NEO4J_USER (cli/main.py:722); Python helpers read NEO4J_USERNAME explicitly.
- NAM_* names: all valid against the MemorySettings fields, and the invalid names are called out as invalid in the docs. Unknown nested fields are confirmed to raise extra_forbidden.
- MEMORY_* / NAMS_* names: checked.
- Defaults: embedding default text-embedding-3-small/1536 matches; dedup 0.95/0.85 matches DeduplicationConfig(); resolution and search defaults match; Vertex 768 matches.
- Minimum versions: Node 22 (Python 3.10) agrees across pages.
- Hosted URLs: memory.neo4jlabs.com/v1 matches the Python settings and TS client defaults.
- MCP tool counts: 6/16/20 match mcp/_tools.py; TS MCP has 12 tools.
- CLI command names: match `neo4j-agent-memory --help`.
- Neo4j setup: Aura is used consistently; Docker/localhost appears only as documented SDK defaults.
- README links into neo4j.com/labs/agent-memory: resolve to existing pages. The how-to/typescript index link was already broken on main and is not reported.
- README image paths: exist.
- MAINTAINING.md: the Makefile targets, scripts and CI wiring it cites exist.

Not done / needs a human:
- I did not read every one of the ~400 changed docs pages line by line. Coverage outside the files above came from targeted greps for the facts listed in the task.
- I did not execute tutorials or builds. The nextjs-memory-chat CI failure follows from the workflow condition, the gitignored dist/ and the package exports; I did not reproduce it with a clean checkout.
- The claude-3-5-sonnet retirement comes from general knowledge, not from anything in the repository.
- Which maturity level (Beta or Experimental) is correct for the Python SDK is a maintainer decision.
- Hosted-only claims (NAMS tool counts, endpoint behaviour) were not judged.
- Separately from the findings: docs/modules/ROOT/examples/__pycache__/*.pyc files exist in the working tree but are untracked, so they are not reported.

### x-style — Cross-cutting: Diataxis and house-rule compliance of pages added by this branch (11 of 11 findings confirmed)

Scope: the 34 pages this branch added (`git diff --diff-filter=A ec9fc65..HEAD -- docs/modules/ROOT/pages`) and nav.adoc.

Fully read:
- explanation/context-tiers.adoc
- explanation/operational-primitives.adoc
- explanation/nams-ai-provider-retrieval.adoc
- how-to/typescript/nams-ai-provider.adoc
- how-to/typescript/nams-ai-provider-provider-mode.adoc
- how-to/typescript/nams-ai-provider-middleware-mode.adoc
- reference/nams-ai-provider.adoc
- reference/deploy-an-application.adoc
- reference/backend-capabilities.adoc
- reference/configuration-connections.adoc
- reference/configuration-advanced.adoc
- reference/configuration-providers.adoc (prose; table rows skipped)
- reference/configuration-operations.adoc (prose; table rows skipped)
- reference/schemas-custom.adoc
- reference/schemas-domains.adoc ('Using schemas' section)
- reference/api/short-term-search.adoc
- short-term-messages.adoc (first 60 lines)

Read in full except the embedded program listings:
- how-to/typescript/nams-ai-provider-tools-mode.adoc
- how-to/typescript/nams-ai-provider-hooks-mode.adoc

Checked through the headings/structure scan and a prose scan only (all non-table, non-code lines over 100–160 chars), not line by line:
- reference/api/long-term-{entities,preferences,deduplication,geospatial}.adoc
- reference/api/reasoning-{traces,steps,search-stats,models}.adoc
- reference/api/short-term-sessions.adoc
- reference/extractor-{builder,classes,pipeline,relations,streaming}.adoc
- reference/schemas-api.adoc

Mechanical checks over all added pages and nav:
- Every added page ends with 'See also' as its last heading.
- No heading or nav label fails the repo's own `looks_title_case` heuristic from tests/docs/test_rendered_site.py.
- All four images have a caption, width=100% and link=self. Their SVGs exist and are listed in docs/diagrams/manifest.json.
- No Cypher code blocks in the added pages, so the Cypher style rules don't apply.
- Every added page is in nav.adoc and in its quadrant index or linked subindex.
- Every nav xref resolves. The only page missing from nav is the intentional root forwarding page configuration.adoc.
- Nav labels now match page titles for all how-to and reference entries.
- Internal xref fragments checked and resolving: `_write_effective_schema_descriptions`, `_entityref`, `integration-limits`, `_nams_and_shared_conversation_operations`, and the `<<tools-mode>>`/`<<hooks-mode>>`/`<<hook-events>>`/`<<errors>>` anchors on reference/nams-ai-provider.adoc.
- Labs disclaimer: per MAINTAINING.md only root/PyPI/site entry points need the full disclaimer. The added pages use no 'production-ready' or 'officially supported' language.

Compatibility-anchor forwarding: I checked with a heuristic script comparing old section ids at ec9fc65 against the subpage each anchor now points to, for reference/configuration.adoc, extractors.adoc, schemas.adoc, api/short-term.adoc, api/long-term.adoc and api/reasoning.adoc. Only the configuration and extractors mis-mappings were confirmed. The other hits were heading-name mismatches that map correctly, for example Step Operations to reasoning-steps.

Not done:
- I didn't verify every signature, default or hosted claim on the split API, extractor and schema reference pages against source. That falls under accuracy reviewers.
- NAMS hosted claims (context tiers, retrieval behaviour) weren't checked against a live service.
- The TypeScript program bodies in the mode how-tos weren't compiled.

Needs a human decision:
- Whether the NAMS-mode how-tos should run from the reader's own project or from the repo checkout. Their current mix contradicts MAINTAINING.md's 'install the verified npm releases' guidance.
- Whether '(Preview)' labels belong in the nav at all.

Nit not filed: 'See also' link text on several new reference pages uses old how-to titles, for example 'Store and search messages' for how-to/messages.adoc (now 'Store, retrieve, and summarize messages'), 'Configure entity extraction' and 'Use NAMS'.

### gap1-compat-anchor-landing — Do kept compatibility anchors land on matching content? (27 of 27 findings confirmed)

Method: I extracted docs/modules/ROOT from ec9fc65, from HEAD, and from 11 intermediate branch commits with git archive. I parsed every page with Asciidoctor 2.0.26 using default idprefix/idseparator, resolving partial$ and example$ includes, and collected section ids and titles plus the ids present in the rendered HTML. The added anchors came from git diff -U0 ec9fc65..HEAD over pages: 1,664 ids on about 1,100 added lines. For each one I recorded its HEAD line, the section or first text where it lands, and its old heading (from ec9fc65, or the branch commit that introduced it). Forwarding xrefs were followed to the target page, and the hubs reference/configuration, extractors, long-term, short-term, reasoning and schemas were checked by comparing each id's old parent section with the target landing. Scratch files are under the scratchpad review/anch directory.

Mechanical checks:
- Every added id is present in the HEAD HTML exactly once, so no kept id is lost.
- (a) found 6 sections displaced to _x_2.
- (b) and (c) found stacked [#] lines and duplicate ids in 4 files.

Fully checked, every added anchor reviewed against its old heading: configuration.adoc, reference/configuration*.adoc (5), reference/extractors.adoc and extractor-*.adoc (5), reference/schemas*.adoc, reference/api/*.adoc (hubs plus 13 split pages), reference/environment-variables, deployment, index, rest-api, getting-started, index.adoc, all explanation/*, all how-to/* (including integrations/* and typescript/*), all tutorials/*, glossary, sdks/python.

Judgment calls, not reported:
- Thematic consolidation on explanation pages and the integration how-tos, where many old ids point to the nearest related paragraph. These are loose but on-topic.
- Hub-level page redirects on configuration.adoc and the API hubs.
- _example on the old API hubs landing on See also; the old page-level Example sections no longer exist.

Possible overlap: the skip list's IDs (howto-hosted#6 and others) are not visible to me. My use-nams, migrate-to-nams and stacked-[#] findings could overlap already-reported items, so please dedupe.

Not done: I did not check whether old ids that were not kept (neither re-added nor present as a section) were silently dropped, because that is outside 'kept anchors'. Several of the minor 'See also dump' findings share one root cause, anchor stacks placed under a '// Historical section links resolve to the maintained task and reference pointers' comment. A human should decide whether that page-end placement is the intended convention; MAINTAINING.md:64 only says 'Preserve old anchors when restructuring', and the in-page comment elsewhere says 'at the current related topic'.

### gap1-rendered-artifacts — Sweep the built site for rendering artifacts (14 of 14 findings confirmed)

Built the site from HEAD into a scratch dir (npx antora antora-playbook.yml --to-dir scratchpad/review/site; content source is git HEAD). The build logged no warnings at warn level. docs/build/site dates from Sep 18, older than HEAD (Sep 23), so I didn't reuse it. I scanned all 146 HTML pages outside _attachments with BeautifulSoup scripts for: raw [id] link text; literal backslashes before | { } * _ [ ] # in prose and in inline code; Sphinx/RST roles; double backticks; undefined {attribute} text in prose (none found); 'Unresolved directive' and raw include:: (none); callout markers without a colist and raw <N> (none); empty <pre> blocks (none); empty table cells; leftover delimiters (|===, ----), block attributes, ifdef, raw headings (none); stray backticks, * and + in prose; replacement-substitution glyphs (→ ⇒ … ’ —) inside inline code; missing internal link targets, missing #fragments, and missing images (none: every href and fragment resolves). I traced each hit to its .adoc line and used git blame against ec9fc65 to separate branch-added lines from untouched ones. Every page under docs/modules/ROOT/pages and partials (all 169 changed files in scope) is covered by the rendered sweep, because partials render into pages.

Hits I did not report as findings:
(1) reference/extractor-builder.adoc:93 and :123 contain leftover RST roles ":meth:`with_llm_fallback`" and ":class:`EntitySchemaConfig`", which render literally. They are new on this branch. They probably correspond to the skipped ref-extract-schema#7/#8.
(2) reference/configuration-operations.adoc:37 and :58 use "<<integration-limits>>" against a bare anchor:integration-limits[] (:143), which renders as "[integration-limits]". This is probably the skipped ref-config#4. The fix is <<integration-limits,integration limits>>.
I couldn't map the skip IDs with certainty. If they don't match, promote (1) as minor and (2) as minor.

Pre-existing, on untouched lines of touched pages, so not reported:
- how-to/audit-reasoning.adoc:89: pass:[...] ends at the first ']' and renders as "(:ReasoningStep)-[:TOUCHED {recorded_at}→(:Entity)]".
- reference/authentication.adoc:119: "create_api_key(label, *, ...)" pairs its '*' with "*admin*" and renders as "create_api_key(label, , scopes=…)" plus a stray "*admin".
- The `x`'s possessive bug also appears at how-to/typescript/strands.adoc:65 and :119, reference/typescript-api.adoc:9 and how-to/migrate-to-providers.adoc:161.
- `->`/`=>` inside code also appears at reference/typescript-api.adoc:98 and :123, reference/api/llm-provider.adoc:222, how-to/typescript/nextjs-memory-chat.adoc:300, how-to/evaluation.adoc:36 and how-to/privacy-and-audit.adoc:40.

Deliberately not flagged: the empty ✓ cells in the bring-your-own-model.adoc capability matrix, which are an intentional sparse matrix; the "(…)" placeholder ellipses in inline code, which are cosmetic; the {id} path parameters, which are left literal as intended; and the empty admonition icon cells.

Needs a human decision: the project could lint for these patterns (`x`'s, `x`s, `-> or => inside backticks, <<id>> to a bare anchor) in scripts/check_docs.py, because the Antora build does not warn on any of them.

### gap1-backend-support-labels — Check backend-support labels and NotSupportedError claims against the NAMS client (8 of 10 findings confirmed)

Fully checked against the NAMS client at HEAD, using `uv run` introspection plus a MemoryClient(backend="nams") driven by a fake transport. Probe scripts: /private/tmp/claude-502/-Users-lyonwj-github-neo4j-labs-agent-memory/66a2977c-9670-4b56-8270-fc84ea0f1100/scratchpad/review/nams_probe.py and nams_settings.py.

Files fully checked:
- the three partials backend-bolt-only.adoc, backend-both.adoc, backend-nams-only.adoc
- explanation/backends.adoc (rendered with asciidoctor; no duplicate-ID problems)
- reference/backend-capabilities.adoc (every row checked against the source, including the MCP 16/20 tool count)
- how-to pages: adopt-existing-graph, audit-reasoning, batch-processing, buffered-writes, consolidation, deduplication, entities, evaluation, messages, multi-tenancy, preferences, privacy-and-audit, migrate-embedding-model, running-without-an-llm, use-ontologies
- reference/api pages: memory-client.adoc, long-term-geospatial.adoc, short-term-messages.adoc
- reference/index.adoc
- src/neo4j_agent_memory/nams/_unsupported.py, core/_unsupported.py (pure move, behavior identical) and nams/ontology.py

All xref targets and #anchors in these files resolve.

Label and claim checks that came out correct:
- buffered-writes, consolidation, adopt-existing-graph, privacy-and-audit, preferences and migrate-embedding-model: bolt-only is right; `_NamsUnsupported`/`client.graph` raise NotSupportedError.
- use-ontologies: nams-only is right.
- evaluation: backend-both plus its own caveat is right; eval uses `query.cypher` and keyword `get_preferences_for`.
- The NAMS behavior tables in long-term-geospatial and short-term-messages match nams/long_term.py and nams/short_term.py, including `set_entity_feedback`/`get_entity_history` raising on Bolt and `get_observations`/`get_reflections`.
- memory-client's get_stats/get_graph/get_locations "Bolt only" matches the NotSupportedError branches.

Following the "same pattern elsewhere" instruction, I also checked pages outside the list that this branch newly labelled: reasoning-traces, entity-extraction(-batch/-schemas), configure-embedding-provider, configure-llm-provider, bring-your-own-model, migrate-to-providers and create-context-graph-mcp. They are covered by the partial finding plus a separate reasoning-traces finding. Per instructions I skipped howto-core-a#0/#3 and ref-api-a#3, ref-api-b#4/#5.

Not done: I did not check TypeScript REST behavior for the TS rows of backend-capabilities beyond spotting that long-term addPreference/addFact/addRelationship are bridge-method requests. I did not re-run the tutorial recipes against live Bolt or NAMS.

Needs a human decision:
1. Fix the generic bolt-only partial wording, or split out a "client-side only" partial for the extraction and provider-configuration pages.
2. Should the docs describe the unreleased get_active() fix in the checked-out source, or keep describing the published 0.6.0? Some reference pages claim to describe the source tree.

### gap1-bolt-programs-live — Run the Bolt docs programs against real Neo4j; check the stale hand-copied tests (8 of 8 findings confirmed)

Live environment: neo4j:5.26-community testcontainer (bolt://localhost:59801, APOC). Harness at scratchpad/review/live/harness.py replaces aura_connection/core_memory_settings so they point at the container, uses a local sentence-transformers embedder (all-MiniLM-L6-v2; BAAI/bge-small-en-v1.5 for the MCP/Anthropic programs) with llm=None, and patches openai.AsyncOpenAI with a stub for the chat steps. No OPENAI/ANTHROPIC key was available, so no real model output was judged. Previous reviewers' scratch (probe_msgs.py, msgs10.py, kg.py) showed the messages flake was probed before but left no result logs, so I reran everything.

Checked live, 5+ runs each:
- core_memory_recipes.py: all 6 tags. messages failed 8 of 9 runs; entities, preferences, reasoning, deduplication and audit passed 5/5 and their output matched the page expectations.
- extraction_recipes.py: extract, schema, batch, streaming passed 5/5 each in a gliner venv.
- first_agent_memory.py: seed, verify, search and the re-seed guard passed 5/5; the page's Cypher returns WORKS_AT.
- conversation_memory.py: seed and resume (stub LLM) passed 5/5; the trace and conversation Cypher on the page match.
- knowledge_graph.py: ingest fails with the documented PyPI install and with a working GLiREL. The storage, inspect and answer path passed 5/5 with a deterministic extractor.
- anthropic_local_memory.py: fails 5/5 at the entity-candidate step (structured LLM call patched).
- mcp_local_tutorial.py: --config and --check-config (correctly rejects bolt://), --prepare (384 dims), and a stdio server driven by the fastmcp Client: 6 core tools, store then search found cedar-lantern-47 in 5/5 runs.
- integrations/common.py and hybrid_recipe.py: exercise() and recorded_turn() passed 5/5; cross-session search results noted as a finding.

Also: tests/docs/test_core_python_tutorials.py passes 105/105 in the full venv and in a dev-only venv. ruff check and ruff format are clean on docs/modules/ROOT/examples. test_tutorial_examples.py plus test_howto_examples.py against the container: 24 passed, 3 known failures (after dropping the 384-dim indexes; the 1536-dim fixture otherwise skips everything). ci-python.yml diff reviewed. hosted-tutorial-minimum's pytest set passes (198) on Python 3.10. No job runs the docs programs against Neo4j.

Not a finding / needs a human:
- TestBatchProcessingHowTo and TestIntegrationExamples never matched their pages even on main, so they are not listed as branch regressions.
- CLAUDE.md:345 describes `make test-docs-integration` as 'Doc examples against Neo4j'; that is now inaccurate but outside the branch diff.
- Whether to keep GLiREL in the knowledge-graph lesson at all is a product decision; the SDK span bug (gliner_extractor.py:989-993) predates this branch.
- The Anthropic finding could be fixed in the docs or in the SDK (embedding extracted entities); that choice needs a maintainer.

Nothing in the repository was modified; scratch files are under scratchpad/review/live/.

### gap2-gap2-ts-inline-snippet-typeche — Type-check every inline TypeScript block on the docs pages (2 of 2 findings confirmed)

Method: I extracted every [source,typescript|ts|tsx] block from the 20 in-scope pages, plus how-to/typescript/nams-ai-provider.adoc and integrations-overview.adoc. That gave 56 blocks and no include:: blocks. Each block went into a scratch env under scratchpad/review/env/<example>/ that uses the matching typescript/examples/* node_modules, and those resolve @neo4j-labs/agent-memory to typescript/dist and @neo4j-labs/nams-ai-provider to packages/vercel-ai-provider/dist. dist contains the new ActiveOntology.schemaHash, so it looks built from HEAD. The strands env links typescript/node_modules/@strands-agents/sdk 1.17.0. I added only declarations each fragment clearly omits. For the one elided line in nextjs-memory-chat.adoc:206 ('// ... same for edges') I filled in the obvious edges map. Every block was compiled with tsc 5.9.3 --strict --noEmit (bundler resolution), then again with nodenext + verbatimModuleSyntax + noUncheckedIndexedAccess. A TS compiler-API pass (verified on a planted case) found no `await` on a non-thenable. LogEvent (observability.adoc:52) and ConversationContext (context-tiers.adoc:50) are assignable in both directions to the exported SDK types. Status and role literals match typescript/src/types.ts (ToolCallStatus list at typescript-api.adoc:381, MessageRole, LogEvent kinds, HostedEntityType). Every backticked method name on the in-scope pages exists in the dist .d.ts files. MCP tool arg `user_id` matches src/mcp/index.ts.

Result: everything compiles cleanly except strands.adoc:250 (reported) and vercel-ai.adoc:179-184. The latter, `async fetch(req, env)`, fails with TS7006 implicit-any under strict. Its lines are untouched by this branch and the branch doesn't make them newly visible, so it is not reported. A human may still want to type it like edge-runtime.adoc:26 (`req: Request, env: { MEMORY_API_KEY: string }`).

The four provider mode pages (tools/provider/middleware/hooks, blocks at lines 36/36/35/36) are byte-identical to typescript/examples/nams-ai-provider/src/*.ts. They pass that example's own `tsc --noEmit`. Compiling them outside it produced only duplicate @ai-sdk/provider-utils identity errors from my env setup, not doc defects. The mcp.adoc custom-tool recipe (lines 118 and 128) compiles when joined with the tutorial's server.ts imports and the shared tutorial-state/cleanup helpers.

Fully checked: nextjs-memory-chat, mcp, vercel-ai, strands, observability, langchain, mastra, edge-runtime, handle-errors, authenticate, troubleshooting (a vitest config fragment, checked by inspection), the four nams-ai-provider-*-mode pages, reference/typescript-api, sdks/typescript, multi-tenancy (TS block only), explanation/context-tiers. reference/nams-ai-provider.adoc and how-to/typescript/nams-ai-provider.adoc have no TS blocks; their option tables were not checked here and belong to the provider reviewer. Not checked: TS diffs in typescript/src (changes are docs comments and ontology getActive logic, covered by the ts-sdk reviewer), and runtime/hosted behaviour claims in prose.

### gap2-gap2-python-api-binding-sweep — Mechanically check Python API names, kwargs, attributes and literals across all pages and partials (2 of 2 findings confirmed)

Method. I wrote an AST scanner (scratchpad/review/scan.py) and ran it over all 349 `[source,python]` blocks in docs/modules/ROOT/pages and partials. It also scanned the 34 `example$` programs those blocks include, among them the example-files.json ids that map to examples/no_llm, eval-harness and claude-code-team-memory. Type environment is shared across blocks on the same page. For each block it: (1) checked every `from neo4j_agent_memory... import` name; (2) resolved `client.<layer>.<method>` for short_term/long_term/reasoning/users/buffered/consolidation/eval/schema (graph.schema.SchemaManager)/query/ontology/auth/graph against both the Bolt and NAMS classes; (3) used inspect.signature(...).bind_partial on every positional and keyword argument, covering layer methods, imported classes and functions, settings and pydantic models, and dict-valued settings groups; (4) inferred return types to check model attribute reads and writes, for example tuple unpacking from add_entity, Entity/ReasoningStepWithContext/ConsolidationReport/AdoptionReport attributes, and settings.memory.* assignments; (5) checked string literals against Literal/Enum parameters and fields (extraction_mode, order_by, write_mode, backend, extractor_type, merge_strategy, ToolCallStatus, MessageRole, DeduplicationResult.action values). Self-tests confirmed it catches bad kwargs, attributes and literals. Separate passes over inline literals in prose and tables covered `client.x.y(...)`, `name(kw=...)` binding against a package-wide index, `Class.attr`, dotted `neo4j_agent_memory.*` paths, `kw=value` default claims, settings paths, and parameter tables under every declaration block against the declared signature. A further pass looked for NAMS-context blocks calling methods that always raise NotSupportedError or using Bolt-only accessors.

Results. Beyond the two findings, every mechanical hit was a false positive, TypeScript text, a framework (non-SDK) name, or a deliberate negative statement ('there is no X'). Bolt-only calls such as link_entity_to_message, register_extractor and add_messages_batch appear only on pages declared Bolt-only. get_extraction_status appears only in NAMS code.

Manual checks against source:
- Pages/partials read in full: backend-capabilities; how-to messages, preferences, entities, reasoning-traces, audit-reasoning, buffered-writes, consolidation, evaluation, multi-tenancy, adopt-existing-graph, privacy-and-audit, running-without-an-llm, use-nams; explanation/operational-primitives; reference api/short-term-messages, reasoning-traces, reasoning-steps and reasoning-search-stats prose, long-term-entities (part), llm-provider, factory, ontology-api; all python-*/aura-* partials plus python-typescript-equivalents (TS method names verified in typescript/src).
- Behaviours verified: MCP tool counts 6/16/20, hook ordering, TOUCHED edge queries, consolidation queries, DeduplicationConfig validation, eval report keys, get_stats keys, the search_messages session-filter caveat, and the NAMS add_entity/search/reasoning tables.
- Docs tests: tests/docs (excluding build/rendered) gives 820 passed and 3 failed, the 3 known pre-existing failures. The contract tests (test_python_reference_contracts etc.) pass: 261 passed.

Excluded as probably already reported ('ref-config#0-2 names'):
- reference/environment-variables.adoc:226 `archive_expired_conversations(older_than_days=...)`, where the real kwarg is `ttl_days`.
- reference/environment-variables.adoc:227 `consolidation.audit_reads(...)`, where the real method is `record_read_audit`.
- The same two wrong names at reference/configuration-operations.adoc:33-34.
If these are not among the ref-config findings, they are major wrong-name defects.

Not done:
- I did not line-review TypeScript pages or the nams-ai-provider pages (not Python), or generated TypeDoc output.
- I did not read every remaining reference page's prose (extractor-*, schemas-*, configuration-* beyond the mechanical checks, cli, mcp-tools, rest-api) or the integration how-to prose in full. Their code, signatures and inline call literals were covered mechanically and by the passing contract tests.
- src changes (core/_unsupported move, CREATE_MESSAGE lock/fork fix, ontology get_active) were read; only the docs impact of the ontology change is reported here.

Needs a human decision: whether the docs should describe published 0.6.0 or HEAD source where they differ (ontology get_active).

### gap2-gap2-expected-output-vs-progra — Compare every expected-output or 'you should see' listing with what the program prints (7 of 7 findings confirmed)

Method: for each 'Expected'/'You should see'/sample-output block I compared the text with the program's print/log statements, and ran programs where possible.

Programs run:
- Against a neo4j:5.26 testcontainer with the local MiniLM embedder: hello-memory/main.py (bolt), eval-harness/main.py, eval-harness/ci_gate.py, audit-trail/main.py, buffered-writes/main.py. Every output matches its README expected block (buffered timings vary, as the README says).
- Under their fakes via tsx: typescript/examples/langchain main() and typescript/examples/mastra main(). Mastra matches its README exactly; langchain gives finding 3.
- `npx vitest run` in typescript/examples/mcp: 2 files, 10 tests pass. The docs-assembly test confirms the 6/7/2 tool counts claimed in mcp.adoc.
- nams_first_write.py against the repo's hosted stub (finding 2).
- The full tests/docs suite: only the three known pre-existing failures (878 passed, 142 skipped).
- Also checked: NamsSettings Step 2 output (`nams https://memory.neo4jlabs.com/v1`), `--help` of nams/skills/ontology quickstart in an isolated folder, first-agent-memory settings output, and settings construction for the cloud embedders (finding 1).

Fully checked by reading prints against expected text:
- nams-quickstart.adoc (seed milestones, verify, cleanup outcomes and exit codes against hosted_tutorial_state/cleanup)
- ontology-quickstart.adoc (illustrative output order against hosted_tutorial_helpers)
- skills-quickstart.adoc (seed/generate/inspect/publish/download/cleanup)
- strands-agent-quickstart.adoc (record/recall/inspect against strands_memory_tutorial.py and session_manager)
- microsoft-agent-memory.adoc (milestones against microsoft_shopping_tutorial.py; the context provider's after_run persists the input)
- all how-to/integrations pages' Expected lines against integrations/*.py and common.py
- typescript mcp, mastra, langchain and strands pages
- evaluation.adoc
- running-without-an-llm.adoc
- the eval-harness, no_llm, hello-memory, existing-graph, buffered-writes and audit-trail READMEs
- the TS mcp/mastra/langchain READMEs
- partials python-tutorial-setup, python-tutorial-import-check and aura-tutorial-setup against wait_for_tutorial_neo4j.py

Could not finish or not run:
- no_llm/main.py: gliner and the en_core_web_sm model are not installed in the venv, and I did not install anything. Its README output was only compared statically; the prints and their order match.
- existing-graph: not executed; its README output block is unchanged by this branch.
- LLM-backed programs (Strands/Bedrock, Microsoft/OpenAI, the integration recipes, knowledge_graph and conversation_memory): not executed live. Only print order and signatures were checked.
- NAMS seed/verify/cleanup flows: not run against the hosted stub beyond nams_first_write. The existing tests/docs contract tests cover them and pass.
- The core tutorial example files (first_agent_memory, conversation_memory, knowledge_graph, mcp_local_tutorial, anthropic_local_memory) were only spot-checked against their pages' Expected lines, because those pages are outside my page list. No mismatch found.

Needs a human decision:
- For finding 2: whether the first-write smoke step should exist at all on a page whose cleanup guarantees depend on every created ID being in the ledger.

Side note, not a finding in my area: tests/docs/test_rendered_site.py uses an unregistered `pytest.mark.rendered`, which raises PytestUnknownMarkWarning.

Scratch outputs are in /private/tmp/claude-502/-Users-lyonwj-github-neo4j-labs-agent-memory/66a2977c-9670-4b56-8270-fc84ea0f1100/scratchpad/review/.

### gap2-gap2-install-commands-sweep — Check every documented install command against the imports it enables and the pin rule (11 of 12 findings confirmed)

Method: listed every pip / python -m pip / uv add / uv pip / uv sync / uvx / npm install / pnpm add command on docs/modules/ROOT/pages and partials (67 lines) and in the changed READMEs. For Python, confirmed each extra exists in pyproject.toml [project.optional-dependencies]. Ran `uv pip install --dry-run` for all 23 distinct commands on Python 3.12, and on 3.10, 3.13 and 3.14 for the framework and ML sets; all resolve. Then did real installs into scratch venvs and imported every third-party module that the included example$ programs and recipes use: bedrock, vertex-ai, hybrid ([openai]), openai-agents, langchain-agents+langchain-openai, crewai, llamaindex, pydantic-ai, google-adk, microsoft-agent+agent-framework-openai (OpenAIChatClient constructed), strands+bedrock, nams, nams+mcp, cli, anthropic+sentence-transformers (LLMEntityExtractor built with the Anthropic provider, no openai needed), extraction+sentence-transformers (local pipeline extracted 3 entities, local embedder ran), and openai+gliner+spacy+glirel (GLiREL fails; see finding 1). Checked the CLI entry points: `neo4j-agent-memory mcp serve` works with [mcp] because click and rich come in through fastmcp; `uvx "neo4j-agent-memory[mcp,openai]" mcp serve --help` works; `[cli]` alone fails for YAML schema commands and the default extractor. For npm, ran `npm install --dry-run` and real installs for the sdks/typescript, nams-ai-provider (4 mode pages plus the overview), nextjs-memory-chat and provider-README commands. `npm ls` showed a single zod, ai and @ai-sdk/provider copy with no peer conflicts; @ai-sdk/mcp is missing from the tools-mode install. Checked peer ranges of @neo4j-labs/agent-memory@0.5.0 and nams-ai-provider@0.3.0 against the docs. Checked the pin rule in docs/MAINTAINING.md against every command. Checked that the pyproject.toml change (empty `docs` dependency group) leaves no references, and `uv lock --check` passes.

Fully checked pages: sdks/python, sdks/typescript, reference/cli, reference/typescript-api, reference/api/factory, reference/nams-ai-provider (peers), all how-to Python pages with installs (team-memory-in-your-editor, deduplication, configure-llm/embedding-provider, create-context-graph-mcp, messages, migrate-to-providers, reasoning-traces, use-nams, entity-extraction(-batch/-schemas), audit-reasoning, entities, running-without-an-llm, use-ontologies, batch-processing, bring-your-own-model, preferences, evaluation), all how-to/integrations/*, all Python tutorials with installs, the TS how-to nams-ai-provider pages, nextjs-memory-chat, and the TS tutorial partials (checkout/project) and mcp-server-typescript. Changed READMEs checked: README.md, README-pypi.md, typescript/README.md, typescript/examples/README.md, vercel-ai-provider/README.md, nams-ai-provider README/.npmrc/lock, nextjs-memory-chat README, strands README, examples/{AURA_SETUP, README, no_llm, domain-schemas, hello-memory (+ .env.example and the PEP 723 header), claude-code-team-memory (+3 templates), strands-session-manager, strands-memory-store, google_adk_demo, google_cloud_integration, lennys-memory, microsoft_agent_retail_assistant}. Skimmed only the diffs for the remaining example READMEs (financial-services, full-stack-chat-agent, nams-*, ontology-lifecycle, TS langchain/mastra/mcp/cloudflare/eve/ontology-lifecycle); their install lines are unchanged `npm ci` / `uv sync` from committed lockfiles.

Not re-reported: tut-ts#0 (npm install ../typescript), gap1-bolt-programs-live#2, howto-core-b#9, x-consistency#13.

Not verified: runtime behaviour needing Aura, NAMS or paid model keys. I did not run the full knowledge-graph lesson. With the huggingface-hub<1 workaround, GLiREL returned 0 relations at threshold 0.5 for the two tutorial documents. That would trip the lesson's own \"No resolved relationships were stored\" check, but it may depend on the model or environment and needs a human run.

Pre-existing issues outside scope: the typescript/examples/strands README note says openai is pinned at ^6.45, but package.json has ^7.15 (a dependabot bump already on main). The TS how-to pages for langchain, mastra, strands, vercel-ai and mcp give no application-level npm install command; they defer to the checkout examples. That is a design decision for a human.

A file typescript/examples/vercel-ai/test/.zz-scratch-not-created.txt appeared in the working tree during this review; I did not create it. All my scratch files are under the scratchpad review/ directory.

### gap2-gap2-markdown-link-check — Mechanically link-check every changed Markdown file, including fragments and docs-site deep links (5 of 5 findings confirmed)

Method: I built the Antora site fresh from HEAD (npx antora antora-playbook.yml --to-dir <scratchpad>/review/site; the build had no warnings and wrote 289 pages to agent-memory/*.html, with the version segment dropped). I then ran a Python link checker (<scratchpad>/review/linkcheck.py) over all 55 .md files in `git diff --name-only ec9fc65..HEAD` (excluding docs/audit-evidence). For each file it:
- parses inline links, reference definitions, href/src attributes, autolinks and bare neo4j.com/labs/agent-memory URLs, skipping fenced code and inline code;
- resolves relative targets on disk and confirms each target is tracked in git at HEAD;
- resolves #fragments against GitHub-style heading slugs (including duplicate suffixes and explicit <a id>/name), or against ids in the rendered HTML for .adoc and docs-site targets;
- maps every https://neo4j.com/labs/agent-memory/... URL to <path>.html or <path>/index.html in the fresh build and checks the fragment ids;
- flags any link that leaves the repository.

I also spot-checked the tricky anchors by hand (README.md#option-c-self-hosted-neo4j-bolt resolves through the explicit `<a id>` at line 149; the examples/README.md index anchors; typescript/examples/README.md#copying-an-example; the vercel-ai-provider README in-page anchors; aws-strands#_session_manager_push_based and #_memory_store; first-agent-memory.html#_step_2_set_up_neo4j; authentication.adoc#_key_lifecycle). As an extra pass, I checked the repository paths in inline code on added lines, and cross-referenced renamed or deleted files (the diagram move) against Markdown references in the repo.

Files fully checked (all 55): .claude/skills/docs-diataxis/SKILL.md, .claude/skills/docs-excalidraw/SKILL.md, CLAUDE.md, CONTRIBUTING.md, README-pypi.md, README.md, deploy/cloudrun/README.md, deploy/mcpb/README.md, docs/MAINTAINING.md, docs/assets/images/diagrams/diagram-descriptions.md, examples/AURA_SETUP.md, examples/README.md, and every changed README.md / GETTING_STARTED.md / frontend/README.md under examples/ (audit-trail, buffered-writes, claude-code-team-memory, domain-schemas, eval-harness, existing-graph, financial-services-advisor and its aws/gcp subtrees, full-stack-chat-agent (+frontend), google_adk_demo, google_cloud_integration, hello-memory, lennys-memory (+frontend), microsoft_agent_retail_assistant (+frontend), nams-fastapi, nams-langchain, nams-quickstart, no_llm, ontology-lifecycle, strands-memory-store, strands-session-manager), typescript/README.md, typescript/examples/README.md, and the READMEs of all ten typescript/examples/*, typescript/packages/vercel-ai-provider/README.md and its examples/README.md.

Results: every relative link and every in-file or cross-file fragment resolves. Every docs-site URL maps to a built page with a valid fragment, except the one pre-existing case below. The only links that leave the repository are the already-reported typescript/examples/README.md:41 and :82 (ts-ex-b#1). The DOCUMENTATION_REMEDIATION_STATUS.md footers in 28 example READMEs are the already-reported py-examples#0 and were not re-reported; microsoft_agent_retail_assistant/README.md:369 is a separate body link and is reported.

Pre-existing broken links on lines this branch did not touch (left out of the findings under the untouched-lines rule; a human should decide whether to fix them in this PR):
- typescript/README.md:111 https://neo4j.com/labs/agent-memory/how-to/typescript: no how-to/typescript.html or how-to/typescript/index.html exists in the build, and none existed on main.
- typescript/README.md:160 https://github.com/neo4j-labs/agent-memory/blob/main/SECURITY.md: no SECURITY.md exists anywhere in HEAD (git ls-tree | grep -i security finds nothing), so the security-reporting pointer is dead.
- examples/financial-services-advisor/google-cloud-financial-advisor/GETTING_STARTED.md:257 ../COMPARISON.md: missing, and no COMPARISON.md appears anywhere in the git history.
- typescript/packages/vercel-ai-provider/README.md links to ./examples and examples/*.ts, which are not in the package's npm "files", so on npm they depend on npm's link rewriting. These lines are unchanged.

For a human decision (neither form is called broken): the changed Markdown contains 25 .html-form docs URLs, 84 extensionless, and 20 root/directory URLs. The .html form appears at README.md:37,103,153,222,251; README-pypi.md:80; examples/audit-trail, buffered-writes, eval-harness, existing-graph, google_cloud_integration, microsoft_agent_retail_assistant READMEs line 15; examples/claude-code-team-memory/README.md:55; examples/financial-services-advisor/README.md:30,139,203; aws-financial-services-advisor/GETTING_STARTED.md:168; examples/full-stack-chat-agent/README.md:47,166; examples/google_adk_demo/README.md:21,239,246; examples/google_cloud_integration/README.md:248; examples/lennys-memory/README.md:163; examples/microsoft_agent_retail_assistant/README.md:405. All other docs URLs are extensionless, and they dominate README.md, README-pypi.md, typescript/README.md, the NAMS/no_llm/domain-schemas/strands/ontology example READMEs and all typescript/examples READMEs. The two forms are mixed within README.md, README-pypi.md and examples/buffered-writes/README.md (html at :15, extensionless at :39). I could not verify which form the live neo4j.com/labs deployment serves.

Not done: hosted-service behaviour and live-URL reachability, since external sites were not fetched.
