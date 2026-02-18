# Proposal: Align neo4j-agent-memory with Microsoft Agent Framework v1.0.0b260212

> **No backward compatibility.** This is a clean cut-over to the latest framework API. No aliases, no deprecation shims, no dual-path support. All code, tests, examples, and documentation upgrade to `agent-framework >= 1.0.0b260212` in a single atomic pass.

## Problem Statement

The neo4j-agent-memory integration module targets Microsoft Agent Framework v1.0.0b251223, which has since undergone significant API changes. The current codebase imports classes and uses patterns that no longer exist in the framework:

- **`ChatAgent` and `ChatMessage` have been removed.** The framework now exports `Agent` and `Message`. There are no aliases — importing `ChatAgent` or `ChatMessage` will raise `ImportError`.
- **`ContextProvider` and `Context` have been removed.** The framework now exports `BaseContextProvider` and `SessionContext` with a completely different method contract (`before_run`/`after_run` instead of `invoking`).
- **The agent construction pattern has changed.** `ChatAgent(chat_client=...)` is replaced by `Agent(client=...)` or the convenience method `client.as_agent(...)`.
- **`ChatCompletionClient` has been removed.** The framework now provides `BaseChatClient` and provider-specific clients like `AzureOpenAIResponsesClient`.

Every source file in `src/neo4j_agent_memory/integrations/microsoft_agent/` will fail to import against the current framework version. The example app, all tests, and all documentation are broken.

## Proposed Solution

Update all integration code, tests, examples, and documentation in a single atomic pass to target `agent-framework >= 1.0.0b260212`. This means:

1. Replace all removed class references with their current equivalents.
2. Rewrite `Neo4jContextProvider` to inherit from `BaseContextProvider` and implement the new `before_run`/`after_run` lifecycle instead of `invoking`.
3. Rewrite `Neo4jChatMessageStore` to implement or align with `BaseHistoryProvider`.
4. Update the retail assistant example to use `AzureOpenAIResponsesClient` and `client.as_agent(...)`.
5. Update all tests to use the new classes and method signatures.

No compatibility layers, no phased migration, no aliases.

## Requirements

1. All imports from `agent_framework` must resolve against `agent-framework >= 1.0.0b260212`.
2. `Neo4jContextProvider` must inherit from `BaseContextProvider` and implement `before_run` and `after_run`.
3. `Neo4jChatMessageStore` must use `Message` for all type annotations and instantiation.
4. All docstring examples must show the `client.as_agent(...)` pattern with `AzureOpenAIResponsesClient`.
5. All unit and integration tests must pass with the updated API.
6. The `pyproject.toml` dependency pin must be updated to `>= 1.0.0b260212`.
7. The retail assistant example must run end-to-end with the new API.

---

## API Mapping (Old → New)

Each mapping references the actual source in the agent-framework at `/Users/ryanknight/projects/azure/agent-framework/python/packages/core/`.

| Old (current in project) | New (framework v1.0.0b260212) | Framework Source |
|---|---|---|
| `ChatAgent` | `Agent` | `agent_framework/_agents.py:1283` — full middleware + telemetry agent |
| `ChatMessage` | `Message` | `agent_framework/_types.py:1403` — role + contents, `.text` property preserved |
| `ContextProvider` | `BaseContextProvider` | `agent_framework/_sessions.py:272` — requires `source_id`, `before_run`/`after_run` |
| `Context` | `SessionContext` | `agent_framework/_sessions.py:120` — per-invocation pipeline context |
| `ChatCompletionClient` | `BaseChatClient` / `AzureOpenAIResponsesClient` | `agent_framework/_clients.py` / `agent_framework/azure/_responses_client.py:54` |
| `ChatAgent(chat_client=...)` | `Agent(client=...)` or `client.as_agent(...)` | `agent_framework/_clients.py:431` — `as_agent()` method |
| `context_providers=provider` | `context_providers=[provider]` | `agent_framework/_agents.py:1303` — must be `Sequence[BaseContextProvider]` |
| N/A (custom chat store) | `BaseHistoryProvider` | `agent_framework/_sessions.py:337` — `get_messages` / `save_messages` abstract methods |

### Key Signature Changes

**`BaseContextProvider.__init__`** (`_sessions.py:288`):
```python
def __init__(self, source_id: str)
```
Requires a `source_id` string. `Neo4jContextProvider.__init__` takes an optional `source_id` defaulting to `"neo4j-context"` and passes it to `super().__init__(source_id=...)`.

**`BaseContextProvider.before_run`** (`_sessions.py:296`):
```python
async def before_run(
    self,
    *,
    agent: SupportsAgentRun,
    session: AgentSession,
    context: SessionContext,
    state: dict[str, Any],
) -> None
```
Replaces the old `invoking(self, messages, **kwargs) -> Context`. Context is now injected by mutating `context.context_messages` or `context.instructions` rather than returning a `Context` object.

**`BaseContextProvider.after_run`** (`_sessions.py:316`):
```python
async def after_run(
    self,
    *,
    agent: SupportsAgentRun,
    session: AgentSession,
    context: SessionContext,
    state: dict[str, Any],
) -> None
```
New hook for post-invocation processing (entity extraction, trace recording). Currently this logic is triggered differently in our code.

**`BaseHistoryProvider`** (`_sessions.py:337`):
```python
def __init__(
    self,
    source_id: str,
    *,
    load_messages: bool = True,
    store_inputs: bool = True,
    store_context_messages: bool = False,
    store_context_from: set[str] | None = None,
    store_outputs: bool = True,
)
```
Abstract methods to implement:
```python
async def get_messages(self, session_id: str | None, **kwargs) -> list[Message]
async def save_messages(self, session_id: str | None, messages: Sequence[Message], **kwargs) -> None
```

**`Message.__init__`** (`_types.py:1451`):
```python
def __init__(
    self,
    role: RoleLiteral | str,
    contents: Sequence[Content | str | Mapping[str, Any]] | None = None,
    *,
    text: str | None = None,  # Deprecated, backward compat
    author_name: str | None = None,
    message_id: str | None = None,
    ...
)
```
The `text=` kwarg is deprecated. Use the positional `contents` parameter: `Message("user", ["Hello"])`. The `.text` property still returns concatenated text content for reading.

**`Agent.__init__`** (`_agents.py:1283`):
```python
def __init__(
    self,
    client: SupportsChatGetResponse[OptionsCoT],
    instructions: str | None = None,
    *,
    tools: ToolTypes | Callable | Sequence[...] | None = None,
    context_providers: Sequence[BaseContextProvider] | None = None,
    middleware: Sequence[MiddlewareTypes] | None = None,
    ...
)
```
Note: first positional arg is `client` (was `chat_client`).

---

## Implementation Plan

### Phase 1: Analysis — Identify All Affected Code

All file paths are relative to the project root.

#### Source Files (imports + logic changes)

| File | Changes Required |
|---|---|
| `src/neo4j_agent_memory/integrations/microsoft_agent/__init__.py` | Replace `ChatAgent` import in docstring. Update example to `client.as_agent(...)`. Update version constant. |
| `src/neo4j_agent_memory/integrations/microsoft_agent/context_provider.py` | **Major rewrite.** Change base class from `ContextProvider` to `BaseContextProvider`. Add optional `source_id` parameter defaulting to `"neo4j-context"`. Replace `invoking()` method with `before_run()` and `after_run()`. Replace `Context` return with `SessionContext` mutation. Replace all `ChatMessage` refs with `Message`. |
| `src/neo4j_agent_memory/integrations/microsoft_agent/memory.py` | Replace `from agent_framework import ChatMessage` with `Message`. Update all type annotations. Update docstring examples. |
| `src/neo4j_agent_memory/integrations/microsoft_agent/chat_store.py` | **Major rewrite.** Extend `BaseHistoryProvider`. Implement `get_messages()` and `save_messages()`. Replace all `ChatMessage` with `Message("role", ["content"])`. Add `source_id` defaulting to `"neo4j-history"`. |
| `src/neo4j_agent_memory/integrations/microsoft_agent/tools.py` | Update docstring examples from `ChatAgent` to `client.as_agent(...)`. |
| `src/neo4j_agent_memory/integrations/microsoft_agent/tracing.py` | Replace `from agent_framework import ChatMessage` with `Message`. |

#### Context Provider Rewrite Detail

The `invoking()` method (`context_provider.py:151`) currently:
1. Receives `messages` and `**kwargs`
2. Builds context from short-term, long-term, and reasoning memory
3. Returns a `Context` object with injected messages

The new `before_run()` must:
1. Receive `agent`, `session`, `context: SessionContext`, `state`
2. Build context from the same memory sources
3. Mutate `context.context_messages[self.source_id]` with the injected messages
4. Mutate `context.instructions` if adding system-level context

The post-invocation entity extraction (currently triggered after `invoking`) moves to `after_run()`, where `context.response` contains the agent's response.

#### Chat Store → History Provider Rewrite

The current `Neo4jChatMessageStore` is a custom class with no framework base. It becomes a `BaseHistoryProvider` subclass (`_sessions.py:337`), which integrates directly into the agent's context provider pipeline — the agent automatically loads history via `before_run` and saves via `after_run`.

Required implementation:
1. Extend `BaseHistoryProvider` with `source_id` defaulting to `"neo4j-history"`
2. Implement `get_messages(session_id) -> list[Message]` — load from Neo4j
3. Implement `save_messages(session_id, messages: Sequence[Message])` — persist to Neo4j
4. Remove all `ChatMessage` references, use `Message("role", ["content"])` for instantiation
5. The existing `add_messages` / `list_messages` public API can remain as convenience wrappers delegating to the abstract methods

#### Example App

| File | Changes Required |
|---|---|
| `examples/microsoft_agent_retail_assistant/backend/agent.py` | Replace `from agent_framework import ChatAgent, ChatMessage` with `Agent, Message`. Replace `ChatAgent(chat_client=...)` with `client.as_agent(...)`. Replace `ChatMessage(role=..., text=...)` with `Message("role", ["content"])`. Update type annotations on `create_agent` and `run_agent_stream`. |

#### Tests

| File | Changes Required |
|---|---|
| `tests/unit/integrations/test_microsoft_agent.py` | Replace all `ChatMessage` imports and instantiations with `Message`. Update mocked method signatures from `invoking` to `before_run`/`after_run`. |
| `tests/integration/test_microsoft_agent_integration.py` | Replace all `ChatMessage` and `Context` imports. Update instantiation patterns. Verify against live framework. |

#### Documentation

| File | Changes Required |
|---|---|
| `README.md` | Update code examples from `ChatAgent` to `client.as_agent(...)`. |
| `docs/tutorials/microsoft-agent-memory.adoc` | Update all code snippets. |
| `docs/how-to/integrations/microsoft-agent.adoc` | Update all code snippets. |
| `docs/how-to/integrations/index.adoc` | Update code snippets. |

#### Dependency

| File | Change |
|---|---|
| `pyproject.toml` | Update `agent-framework>=1.0.0b` to `agent-framework>=1.0.0b260212` |

### Phase 2: Implementation

Execute all changes atomically:

- [x] Update `pyproject.toml` dependency pin to `>= 1.0.0b260212`
- [x] Rewrite `context_provider.py`: new base class `BaseContextProvider`, new lifecycle methods `before_run`/`after_run`, optional `source_id` defaulting to `"neo4j-context"`
- [x] Rewrite `chat_store.py`: extend `BaseHistoryProvider`, implement `get_messages`/`save_messages`, `source_id` defaults to `"neo4j-history"`
- [x] Update `memory.py`: all `ChatMessage` → `Message`, update docstrings
- [x] Update `tools.py`: docstring examples
- [x] Update `tracing.py`: `ChatMessage` → `Message`
- [x] Update `__init__.py`: version constant, docstring examples, exports
- [x] Update `examples/microsoft_agent_retail_assistant/backend/agent.py`
- [x] Update all test files
- [x] Update all documentation files

### Phase 3: Verification

- [x] All unit tests pass with `agent-framework >= 1.0.0b260212`
- [x] All integration tests pass (35 collected, skipped due to no Neo4j instance — no import or syntax errors)
- [x] Retail assistant example imports verified (requires live Azure/OpenAI credentials for full e2e)
- [x] No remaining references to `ChatAgent`, `ChatMessage`, `ContextProvider`, or `Context` from `agent_framework`
- [x] `grep -r "ChatAgent\|ChatMessage\|from agent_framework import.*Context[^P]" src/ examples/ tests/` returns zero results

---

## Decisions

1. **`Neo4jChatMessageStore`**: Rewrite as a `BaseHistoryProvider` subclass. Implement `get_messages()` and `save_messages()`. No standalone utility path.
2. **`Message` constructor style**: Use `Message("user", ["Hello"])` everywhere. Do not use the deprecated `text=` kwarg.
3. **`source_id`**: `Neo4jContextProvider` takes an optional `source_id` parameter defaulting to `"neo4j-context"`.