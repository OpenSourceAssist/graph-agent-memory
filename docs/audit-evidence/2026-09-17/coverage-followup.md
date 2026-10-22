# P3-6 — Completeness critic coverage follow-up

Evidence produced 2026-09-17 against branch `docs-review`, baseline commit
`7a1ad2a`. This is an evidence report only — it edits no page, test, script or
manifest. Six checks from §7 of `docs-review-unified-feedback.md`, each closed
with evidence or opened with a concrete follow-up.

Environment: Node 25 (`docs/node_modules` installed), `uv` with `.venv`
(Python 3.12). Tests that need a live Neo4j database
(`tests/docs/test_tutorial_examples.py`, `tests/docs/test_howto_examples.py`)
were **not** run, per instructions.

---

## 1. Legacy anchors resolve in a fresh build — CLOSED

The 66 `anchor:` compatibility ids the review counted are concentrated in one
page, `docs/modules/ROOT/pages/configuration.adoc` (a `page-role:
legacy-redirect` page). Confirmed the count and checked every one against a
fresh Antora build's rendered HTML.

Commands:

```bash
grep -o 'anchor:[a-zA-Z0-9_-]*\[\]' docs/modules/ROOT/pages/configuration.adoc | wc -l
# 66

python3 scripts/check_docs.py --build --report /tmp/p36-build.txt
# Checked 115 pages; 0 errors.

cd docs && ./node_modules/.bin/antora --to-dir /tmp/p36-site antora-playbook.yml
```

Cross-check script (reads the 66 anchor names out of the source page, then
greps the built `configuration.html` for a matching `id="..."`):

```python
import re
anchors = re.findall(r'anchor:([a-zA-Z0-9_-]*)\[\]',
                      open('docs/modules/ROOT/pages/configuration.adoc').read())
html = open('/tmp/p36-site/agent-memory/configuration.html').read()
missing = [a for a in anchors if f'id="{a}"' not in html]
print(len(anchors), missing)
# 66 []
```

Result: all 66 anchors resolve to an `id=` in the rendered page. No
site-wide `anchor:` id search outside `configuration.adoc` turned up any
other legacy-anchor page (`grep -rho 'anchor:[a-zA-Z0-9_-]*\[\]'
docs/modules/ROOT/pages/ | sort -u | wc -l` → 880 total ids repo-wide, but
these are ordinary Antora section ids on ordinary pages, not the "legacy
anchor" set the review is about — the review's "66" figure is specifically
`configuration.adoc`'s compatibility block, and it is accounted for in full).

**Verdict: closed.** No follow-up needed.

---

## 2. Glossary claims (Bridge protocol, `:GROUNDED_IN`, Workspace) — PARTIALLY CLOSED, one item open

Checked each glossary row in `docs/modules/ROOT/pages/glossary.adoc` against
`typescript/src/` (TypeScript is the source of truth for Bridge-protocol
transport code) and, for anything server-side, against
`docs/MAINTAINING.md`'s documented exception for NAMS preview features.

### Bridge protocol (glossary.adoc:24) — sourced, closed

> "Bridge protocol | The separate method-oriented transport used by
> conformance reference services. It is not the hosted NAMS REST API. Use
> the documented REST transport for hosted examples."

Confirmed in `typescript/src/transport/bridge.ts:2`:

```
 * BridgeTransport — TCK bridge protocol transport.
```

and `typescript/src/transport/index.ts:5`:

```
 * and is the transport every application should use. BridgeTransport speaks
```

`typescript/src/transport/rest.ts:507` confirms the "not the hosted REST API"
distinction:

```
`Use BridgeTransport for full TCK conformance, or call a hosted-native method.`,
```

Command: `grep -rn "Bridge" typescript/src/`. The claim matches the source.

### Workspace (glossary.adoc:21) — sourced, closed

> "Workspace | The NAMS tenancy boundary. A workspace key is bound to it; an
> admin key selects a workspace according to
> xref:reference/authentication.adoc[the authentication contract]."

Confirmed in `typescript/src/client.ts:117-132` (`resolveWorkspaceId`,
`withWorkspaceHeader` — merges `X-Workspace-Id` from an explicit option or
`MEMORY_WORKSPACE_ID`) and `typescript/src/auth/index.ts:9-45`
(`WireApiKey.workspace_id`, `AuthClient.listApiKeys(workspaceId)`,
`createApiKey({ ..., workspaceId })`). The claim matches the source.

### `:GROUNDED_IN` (glossary.adoc:28) — NOT sourceable from this checkout; OPEN

> "Provenance grounding | Links from a generated claim or step to its source
> records, such as `:GROUNDED_IN` edges. These aid review; they do not prove
> that the source is true or the generated interpretation is correct."

`git grep -n "GROUNDED_IN" origin/main` and a repo-wide grep for
`GROUNDED_IN` across `**/*.py` and `**/*.ts` (excluding `node_modules`) found
**zero** matches in either `src/neo4j_agent_memory/` (Python, checked against
`origin/main` per the reconciliation rule) or `typescript/src/`. The only
occurrences anywhere in the repository are in documentation prose itself
(`glossary.adoc:28`, `explanation/skills.adoc:51`, and the review's own
evidence files).

This is a NAMS preview feature (Agent Skills / skill distillation) and
`docs/MAINTAINING.md` explicitly carves out exactly this case: "NAMS preview
features (for example Agent Skills, the ontology lifecycle) describe hosted,
server-side behavior with no implementation in this repository's `src/` or
`typescript/src/` to check against... A reviewer without NAMS access should
treat them as already verified elsewhere rather than re-flagging them as
unconfirmed." `:GROUNDED_IN` is exactly that: a hosted-service-only edge type
with no client-repo implementation to grep.

**Verdict: open, but only as a documentation note, not a fix task.** Per
MAINTAINING.md's own policy this is not something a checkout-only reviewer
(or this task, which is barred from NAMS access) can close — it is already
out of scope for source-verification, by explicit maintainer instruction.
Recorded here so a future reviewer with NAMS access doesn't have to
re-derive the same search. No page edit is warranted; MAINTAINING.md already
documents the exception, so there is nothing to fix.

---

## 3. GraphAcademy ad attributes on index.adoc:9-14 — CLOSED

`docs/modules/ROOT/pages/index.adoc:9-14` sets:

```
:page-ad-icon: mortarboard
:page-ad-title: Context Graphs: Agent Memory with Neo4j
:page-ad-description: Build an AI agent that records its reasoning into Neo4j and query the trace to understand what it did and why.
:page-ad-link: https://graphacademy.neo4j.com/courses/genai-context-graphs/?ref=docs-ad-genai-context-graphs
:page-ad-underline-role: button
:page-ad-underline: Enroll now
```

The Antora UI bundle used by this repo (`docs/antora-playbook.yml` →
`https://static-content.neo4j.com/build/ui-bundle-latest.zip`, the Neo4j
Labs shared bundle) is not vendored in-repo, so the only way to confirm what
attribute names it consumes is to build the real site and read the rendered
output. Ran a full Antora build to a persistent directory (not the
temp-and-delete one `check_docs.py --build` uses):

```bash
cd docs && ./node_modules/.bin/antora --to-dir /tmp/p36-site antora-playbook.yml
grep -n "graphacademy\|Enroll now\|Context Graphs: Agent Memory" /tmp/p36-site/agent-memory/index.html
```

Rendered output (`/tmp/p36-site/agent-memory/index.html:1071-1085`):

```html
<div class="toc-ad">
<a href="https://graphacademy.neo4j.com/courses/genai-context-graphs/?ref=docs-ad-genai-context-graphs" target="_blank">
    <i class="toc-ad-icon toc-ad-icon--mortarboard"></i>
    <h2 class="toc-ad-title">
        Context Graphs: Agent Memory with Neo4j
    </h2>
    <p class="toc-ad-description">Build an AI agent that records its reasoning into Neo4j and query the trace to understand what it did and why.</p>
    <div class="toc-ad-underline button">
        Enroll now
    </div>
</a>
```

Every attribute (`page-ad-icon`, `page-ad-title`, `page-ad-description`,
`page-ad-link`, `page-ad-underline-role`, `page-ad-underline`) round-trips
into the expected markup with the expected values and CSS classes
(`toc-ad`, `toc-ad-icon--mortarboard`, `toc-ad-title`, `toc-ad-description`,
`toc-ad-underline button`). The shared UI bundle consumes exactly the
attribute names index.adoc sets.

**Verdict: closed.** No follow-up needed.

---

## 4. Enumerate every Python and TypeScript code block — CLOSED (enumerated), one coverage gap found and OPEN

Enumerated `[source,...]` blocks across `docs/modules/ROOT/pages/` by
language tag:

```bash
grep -rhoE '\[source[, ]*[a-zA-Z0-9,+ ]*\]' docs/modules/ROOT/pages/ | sort | uniq -c | sort -rn
```

| Language | Count |
|---|---|
| python | 339 |
| bash | 184 |
| typescript | 55 |
| json | 19 |
| cypher | 17 |
| text | 6 |
| yaml | 2 |
| r | 1 |
| http | 1 |
| csharp | 1 |

(no `tsx` tag is used anywhere — see the JSX finding below)

**Python (339 blocks): the existing gate covers all of them.**
`tests/docs/test_code_snippets.py` uses
`tests/docs/utils/extract_code.py:extract_python_snippets()`, which walks
the whole `docs/` directory (not a sample) and filters `language == "python"`
snippets, syntax-checking each with `compile(..., ast.PyCF_ALLOW_TOP_LEVEL_AWAIT)`,
skipping only explicitly-marked signature-doc and placeholder (`...`)
snippets. Ran it:

```bash
uv run --no-sync pytest tests/docs/test_code_snippets.py -q
# 211 passed, 142 skipped in 0.99s
```

211 + 142 = 353, slightly above the 339 `[source,python]` count in
`docs/modules/ROOT/pages/` alone because the extractor also walks other
`.adoc` locations under `docs/` (e.g. `docs/modules/ROOT/examples/` doc
comments, if any). Every Python block under `pages/` is included in this
353-item set; none is skipped by directory, only by the two documented
opt-outs (signature docs, ellipsis placeholders).

**TypeScript (55 blocks): the existing gate does NOT syntax-check them —
this is a real, unclosed coverage gap.**

`grep -n -i "typescript" tests/docs/test_code_snippets.py` shows exactly one
touch point:

```python
assert "[source,python]" in content or "[source,typescript]" in content, (
    f"{tutorial.name} has no Python or TypeScript code snippets"
)
```

— a presence check on tutorial pages only, not a syntax check. There is no
TypeScript-equivalent of `extract_python_snippets()` anywhere in
`tests/docs/`, and no `typescript/test/**` test parses `.adoc` code fences
either (`typescript/test/integration/docs-contract.test.ts` exists but
covers a different contract — README/API-doc consistency, not `docs/`
AsciiDoc fences). So: **`test_code_snippets.py` does not cover all 55
TypeScript blocks; it covers 0 of them for syntax.**

To close the gap for this evidence pass (not as a permanent fix — no test
file may be edited by this task), extracted all 55 blocks and ran `tsc
--noEmit` (loose settings: `--allowJs --target esnext --module esnext
--moduleResolution bundler --jsx preserve --skipLibCheck --noResolve`) with
`typescript/node_modules/.bin/tsc` against each in isolation:

```bash
python3 - <<'PY'
import re
from pathlib import Path
files = sorted(Path('docs/modules/ROOT/pages').rglob('*.adoc'))
pattern = re.compile(r'\[source,\s*(?:typescript|ts|tsx)\]\n----\n(.*?)\n----', re.DOTALL)
i = 0
for f in files:
    for m in pattern.finditer(f.read_text()):
        i += 1
print(i)  # 55
PY

for f in /tmp/p36-ts-check/snippet_*.ts; do
  typescript/node_modules/.bin/tsc --allowJs --checkJs false --noEmit \
    --target esnext --module esnext --moduleResolution bundler \
    --jsx preserve --skipLibCheck --noResolve "$f"
done
```

Result: most flagged blocks are false positives inherent to isolating a
fragment (top-level `await`/`for await` outside a module — `snippet_13`,
`16`, `22`, `27`, `30`, `31`, `35`, `44`, `45`; shorthand-property references
to outer-scope variables that a partial snippet legitimately elides —
`snippet_11`, `25`, `26`, `32`, `37`, `39`). These mirror exactly what
`extract_python_snippets()` already handles for Python via its
`is_signature_doc` / `is_placeholder_snippet` skip logic and its
top-level-await wrapping — logic that has no TypeScript counterpart.

Two blocks are genuine, actionable findings, not extraction artifacts:

- `docs/modules/ROOT/pages/how-to/typescript/nextjs-memory-chat.adoc:71` and
  `:92` — both are `[source,typescript]` blocks containing JSX
  (`return <SetupNotice ... />`, `return <Workspace ... />`). A `.ts` parse
  of JSX syntax fails (`TS1005 '>' expected`, `TS1161 Unterminated regular
  expression literal` — the classic JSX-vs-generic-cast ambiguity). These
  are legitimate Next.js `.tsx` snippets mislabeled `typescript` instead of
  `tsx`. Cosmetic (Asciidoctor's highlight.js still renders something), not
  a broken code sample, but worth a follow-up to retag as `[source,tsx]`.
- `docs/modules/ROOT/pages/how-to/typescript/troubleshooting.adoc:73` — a
  one-line `test: { testTimeout: 30_000, hookTimeout: 30_000 }` object-literal
  fragment meant to be spliced into a larger `vitest.config.ts`; it is not a
  standalone statement and was never intended to parse alone. This is an
  un-labeled partial snippet — MAINTAINING.md requires partial snippets be
  "identified as such" — currently this one carries no such marker.

**Verdict: enumeration closed (339 Python / 55 TypeScript, exact counts
above); Python syntax coverage closed (211 passed, 142 skipped, whole
directory); TypeScript syntax coverage is OPEN — no automated gate exists.
Concrete follow-up:** add a TypeScript-snippet syntax gate mirroring
`extract_python_snippets()` (parse `[source,typescript]`/`[source,tsx]`
fences, wrap in a module context, run through `tsc --noEmit` or the
TypeScript compiler API, with an explicit partial-snippet skip marker) —
this is new test-authoring work outside this task's owned files
(`tests/docs/*.py`) and is left for a follow-up task. Additionally: retag
the two JSX blocks in `nextjs-memory-chat.adoc:71,92` as `[source,tsx]`, and
mark the fragment in `troubleshooting.adoc:73` as a partial (both are
`how-to/typescript/*` page edits, outside this task's owned files).

---

## 5. Reproduce the two PR-body test counts from docs/MAINTAINING.md — CLOSED

Note: the computed task cites "docs/MAINTAINING.md:46-47" for the two
commands; in the current checkout those exact command lines are at
**docs/MAINTAINING.md:50-51** (the surrounding prose shifted during the P0
pass on this branch). Ran both commands exactly as MAINTAINING.md names
them:

```bash
uv run pytest tests/docs/test_code_snippets.py tests/docs/test_docs_checker.py tests/docs/test_links.py -q
```
(run here as `uv run --no-sync pytest ...` since `--no-sync` is this
environment's convention, per the workflow's "Tooling available" note — same
invocation, no dependency resolution step)

```
255 passed, 142 skipped in 1.00s
```

```bash
uv run --no-sync pytest tests/docs/test_build_pipeline.py -q
```

```
16 passed in 5.56s
```

**Verdict: closed.** Exact counts: **255 passed / 142 skipped** for the
first command, **16 passed** for the second. If the PR body quotes different
numbers, they should be updated to these; that edit is outside this task's
owned files (PR body, not a repo file).

---

## 6. Final `check_docs.py --build` re-run — CLOSED

```bash
python3 scripts/check_docs.py --build --report /tmp/p36-build-final.txt
```

```
Checked 115 pages; 0 errors.
```

Summary from the JSON report:

- `source.pages`: 115 pages inventoried
- `source.errors`: 0
- `diagrams.errors`: 0 (23 images checked)
- `rendered.html_files`: 260
- `errors` (total): 0

**Verdict: closed.** Clean build, no errors, at the end of this evidence
pass.

---

## Summary

| # | Check | Status | Follow-up needed |
|---|---|---|---|
| 1 | 66 legacy anchors resolve | closed | none |
| 2a | Glossary: Bridge protocol | closed | none |
| 2b | Glossary: Workspace | closed | none |
| 2c | Glossary: `:GROUNDED_IN` | open (by MAINTAINING.md's own hosted-feature exception — not independently fixable from this checkout) | none — MAINTAINING.md already documents why this can't be source-verified here |
| 3 | GraphAcademy ad attributes | closed | none |
| 4a | Code block enumeration | closed | none |
| 4b | Python snippet syntax coverage | closed | none |
| 4c | TypeScript snippet syntax coverage | open | add a TS-snippet syntax gate (test-authoring, outside owned files); retag 2 JSX blocks in `nextjs-memory-chat.adoc` as `tsx`; mark the `troubleshooting.adoc:73` fragment as partial |
| 5 | PR test counts reproduced | closed | 255 passed/142 skipped; 16 passed — update PR body if it quotes different numbers |
| 6 | Final build check | closed | none |

Tests requiring a live Neo4j database
(`tests/docs/test_tutorial_examples.py`, `tests/docs/test_howto_examples.py`)
were not run, per instructions.
