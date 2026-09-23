# Diagram Descriptions for neo4j-agent-memory Docs

Generated diagrams for Antora documentation. All PNGs go to
`docs/modules/ROOT/images/diagrams/`. Excalidraw sources go to
`docs/assets/images/diagrams/excalidraw/`.

---

## 1. poleo-model.svg
**Page**: `explanation/poleo-model.adoc`
**Replaces**: ASCII art table showing 5 entity types

### Layout
5 colored boxes in a 3-2 grid, each showing entity type name + key subtypes.

| Box | Color | Subtypes to show |
|-----|-------|-----------------|
| PERSON | Light green (`#b2f2bb`) | Individual, Professional, Alias |
| OBJECT | Light orange (`#ffd8a8`) | Vehicle, Device, Document, Weapon |
| LOCATION | Light blue (`#a5d8ff`) | Address, Region, Landmark, Country |
| EVENT | Light yellow (`#fff3bf`) | Meeting, Transaction, Incident |
| ORGANIZATION | Light purple (`#d0bfff`) | Company, Government, NGO |

Title at top: "POLE+O Entity Model". Camera XL (1200x900).

---

## 2. message-chain.svg
**Page**: `how-to/messages.adoc`
**Describes**: How messages are stored and linked in short-term memory

### Layout
Vertical flow (2026-09-18 re-export, no in-image title):
```
:Conversation
  --FIRST_MESSAGE-->
:Message role=user · "Hello, Maya"
  --NEXT_MESSAGE-->
:Message role=assistant · "Northstar can help"
  --NEXT_MESSAGE-->
:Message role=user · "Thanks"
```
On the right side, branch arrows from the first two messages:
```
:Message "Hello, Maya"          --MENTIONS--> :Entity:Person type=PERSON
:Message "Northstar can help"   --MENTIONS--> :Entity:Organization type=ORGANIZATION
```
Caption text under the diagram: "HAS_MESSAGE links from the Conversation to
every Message are omitted for clarity." and "MENTIONS links are created by
extraction; entity labels use PascalCase, type values use uppercase."
Colors follow the house semantic palette: Conversation and all Messages are a
single short-term green, and both Entity nodes are long-term yellow/orange
(not the earlier teal/blue/green/purple mix).

---

## 3. multi-tenant-scoping.svg
**Page**: `how-to/multi-tenancy.adoc`
**Describes**: How User nodes scope data per tenant in a shared Neo4j instance

### Layout
Two parallel columns:
```
[:User sara-demo]      [:User liam-demo]
     |                      |
HAS_CONVERSATION      HAS_CONVERSATION
     v                      v
[Conv: sara-2026-05-01] [Conv: liam-2026-05-01]

[Messages (sara only)] [Messages (liam only)]

[Pref: healthcare focus] [Pref: fintech focus]
```
Underneath both columns: shared Neo4j instance box, plus a caption noting
`user_identifier=` scopes reads/writes only on the operations that accept it.
Only the `:User -> Conversation` edges are drawn; the Messages and Preference
ellipses sit below each conversation without a drawn edge (membership implied).
Colors follow the house semantic palette: `:User` nodes are neutral grey
(outside the three memory layers), Conversation/Messages are short-term green,
Preferences are long-term yellow, and the Shared Neo4j Instance box is storage
blue. Both tenant columns use the same palette; they are distinguished by
position and label, not by color.

---

## 4. buffered-write-flow.svg
**Page**: `how-to/buffered-writes.adoc`
**Describes**: Fire-and-forget buffered write architecture

### Layout
Vertical flow (2026-09-18 re-export, no in-image title):
```
[Agent submits a write] --submit()--> [Bounded queue, max_pending=200 by default]
                                              |
                                           consume
                                              v
                                [Background drainer: consumes queued jobs]
                                              |
                                         execute_write
                                              v
                                    [Neo4j write attempt] --failure--> [Failure recorded in
                                                                        client.write_errors;
                                                                        optional error callback]
```
Plain-text annotations (no boxes) alongside the flow: "Queue has space: return
after enqueueing. Queue full: wait for free space. This is intentional
backpressure." and "Success and failure both finish the queued attempt; the
drainer continues to the next job." A separate callout box reads
"flush() / wait_for_pending() waits for queued attempts to finish. Then
inspect write_errors and read back the required data.", followed by plain
text: "Flush completion is not a guarantee that every write succeeded. Stop
submitting new writes before a final flush; concurrent submissions can race
with it."
Colors: "Agent submits a write" and the failure/flush callout boxes are light
purple/lavender; the queue, drainer, and write-attempt boxes are blue (not the
earlier purple/yellow/teal scheme).

---

## 5. entity-dedup-flow.svg
**Page**: `how-to/deduplication.adoc`
**Describes**: How entity deduplication works with similarity thresholds

### Layout
Vertical decision flowchart (2026-09-18 re-export; this is the one diagram in
this set that still carries an in-image title, "Entity Deduplication Flow"):
```
[New Entity]
     |
[Compute Similarity]
(embedding + fuzzy)
     |
  <sim >= 0.95?>
   YES /          \ NO
      /            \
[Auto-Merge      <sim >= 0.85?>
(keep aliases)]    YES /       \ NO
                      /         \
              [Flag SAME_AS]  [Create New]
              (status=pending)
```
Caption: "Thresholds: auto_merge_threshold=0.95 | flag_threshold=0.85".
Colors: New Entity / Auto-Merge / Flag SAME_AS / Create New are all a single
long-term yellow/orange; the similarity-compute box and both decision
diamonds are neutral grey (not the earlier five-color blue/yellow/green/
orange/teal scheme).

---

## 6. reasoning-trace-graph.svg
**Page**: `how-to/reasoning-traces.adoc`
**Replaces**: ASCII art trace structure diagram

### Layout
Graph structure showing node types and relationships (2026-09-18 re-export,
no in-image title; no Entity node or TOUCHED edge is drawn in this diagram —
TOUCHED is called out only in a caption, see below):
```
:Message <--INITIATED_BY-- :ReasoningTrace "Product search"
                                    |
                              HAS_STEP
                    ┌───────────────┼───────────────┐
                    |               |               |
            :ReasoningStep  :ReasoningStep  :ReasoningStep
             "1 · Search"    "2 · Filter"   "3 · Recommend"
                    |               |               |
              USES_TOOL        USES_TOOL       USES_TOOL
                    |               |               |
            :ToolCall        :ToolCall       :ToolCall
            search_api       get_prefs       rank_items
```
Captions: "Steps are ordered by step_number and HAS_STEP.order; no
inter-step edges are shown." and "Optional TOUCHED links record
application-supplied entity references; they do not prove a modification."
Colors: `:Message`=short-term green, `:ReasoningTrace`/`:ReasoningStep`/
`:ToolCall` are all reasoning purple, in the same family rather than the
earlier blue/purple/orange/green mix (there is no Entity node to color).

---

## 7. mcp-server-architecture.png
**Page**: `reference/mcp-tools.adoc` / `tutorials/mcp-server.adoc`
**Describes**: How the MCP server connects Claude to Neo4j memory

### Layout
Top-to-bottom flow with layers:
```
[Claude Desktop / Claude Code / Any MCP Client]
              |
     MCP Protocol (stdio | SSE | HTTP)
              |
     [MCP Server]
       |           |
  [Core Profile]  [Extended Profile]
  6 tools         16 tools
  2 resources     4 resources
  1 prompt        3 prompts
              |
      [MemoryClient]
       |       |       |
     [STM]   [LTM]   [RTM]
     Short   Long   Reasoning
              |
          [Neo4j]
```
Colors: Client=light blue, Server=light purple, Profiles=light yellow,
MemoryClient=light teal, Neo4j=light teal (darker).

---

## 8. nams-ai-provider-modes.svg
**Page**: `how-to/typescript/nams-ai-provider.adoc`
**Describes**: The four ways `@neo4j-labs/nams-ai-provider` 0.3.0 adds memory to a
Vercel AI SDK app, and what the hosted NAMS workspace does for every one of them

### Layout
"Your application" spans the top as one neutral-grey box. Four neutral-grey
mode boxes sit in a row underneath it, each fed by a short arrow from the
application box, one per entry call:
```
[Your application]
   |        |         |          |
[Provider [Middleware [Tools    [Hooks
 mode]     mode]       mode]     mode]
createNamsProvider createNams()  createNams()  createNams()
(...)               .wrap(model,  .tools(scope)  .hooks(...)
wraps                scope)       query_memory,  prepare, withHooks,
languageModel                     store_memory    onFinish, end
   |        |         |          |
   +--------+----+----+----------+
                 v
        [NAMS workspace] (storage blue)
   Retrieves relevant memory before the model call
   Persists the turn and extracts entities after
```
Colors: the application box and all four mode boxes are neutral grey (they
are client-side integration points, not one of the three memory layers); the
NAMS workspace box is storage blue, matching the Neo4j/storage semantic used
elsewhere. No in-image title; the page caption carries it.

Recommended caption: "The four NAMS AI provider modes, and what the hosted
workspace does before and after every one of them."

---

## 9. nams-ai-provider-hooks.svg
**Page**: `how-to/typescript/nams-ai-provider-hooks-mode.adoc`
**Describes**: The eight lifecycle events hooks mode fires around one
generation, in order, and which ones have nothing to match on

### Layout
A vertical flow spine on the left (plain outlined boxes: `prepare() called`,
`prepare() resolves messages`, `Your app calls the model`, `withHooks() wraps
the tool call`, `Tool executes`, `Tool call settles`, `onFinish() builds the
turns`, `Turns persisted to NAMS` [storage blue], `Generation finishes`,
`Your app calls end()`), each linked top-to-bottom by a vertical arrow. A
side column of eight neutral-grey hook boxes sits to the right, one per
lifecycle event, each linked to its spine step by a short arrow:
`SessionStart` (once per session, reason: created | resumed),
`UserPromptSubmit` (matcherless; block or rewrite the prompt), `PreToolUse`
(allow or deny, rewrite the input), `PostToolUse` / `PostToolUseFailure`
(rewrite the output; failure retries once, attempt 1 only), `PreMemoryWrite`
(matcherless; block the write or rewrite the turns), `Stop` (matcherless;
last chance to add context or a message), `SessionEnd` (reason, e.g.
`"idle-timeout"`; clears session state). A Labs-purple dashed frame labelled
"Repeats for each tool call" surrounds the `PreToolUse` / `Tool executes` /
`PostToolUse`+`PostToolUseFailure` rows. A caption at the bottom reads: "A
hook that throws or times out is logged and skipped — it never breaks the
generation."
Colors: spine boxes are plain white/outline (neutral grey stroke); hook
boxes are filled neutral grey; the one storage step (`Turns persisted to
NAMS`) is storage blue; the loop frame is Labs purple, used only for
framing. Matcherless events (`UserPromptSubmit`, `PreMemoryWrite`, `Stop`)
carry a `(matcherless)` note directly in their box.

Recommended caption: "The eight NAMS hook lifecycle events around one
generation, and which ones have no matcher."

---

## 10. nams-ai-provider-retrieval.svg
**Page**: `explanation/nams-ai-provider-retrieval.adoc`
**Describes**: The five memory sources the provider queries for a turn, how
they are merged, and where the result lands in the prompt

### Layout
Three source boxes across the top row, two more centered in a second row,
all five feeding down into one "Memory block" box, which feeds one more box
below it:
```
[Current conversation]  [Cross-session messages]  [Long-term entities]
searchMessages(query,   up to crossSessionLimit    searchEntities(query,
{ sessionId: convId })  other conversations (5)     { limit: 5 })

      [Graph triples]          [Reasoning steps]
 expand graphExpansionLimit   listSteps(convId)
 matched entities (2), at     direct-response steps
 most 5 relationships each

                  v (all five, round-robin)
          [Memory block] (neutral grey)
  Merged round-robin, one hit per source in turn,
  capped at maxMemories (default 6, max 12)
                  |
                  v
          [Last user message] (neutral grey)
  Memory block text is prepended
  to the last user message's content
```
The two row-1 outer arrows (from Current conversation and Long-term
entities) drop straight down past the second row before angling into the
memory block, so no arrow crosses a box.
Colors: Current conversation and Cross-session messages are short-term
green (both are message sources); Long-term entities and Graph triples are
long-term yellow; Reasoning steps is reasoning purple; Memory block and
Last user message are neutral grey (neither is one of the three memory
layers, nor Neo4j storage itself — this is a client-side prompt-assembly
step).

Recommended caption: "The five memory sources merged into one prompt-ready
memory block."
