# Configuration

Runtime wiring is configured with TOML and validated through the typed config
models in the wiring layer, then resolved into effective module configs before
objects are built.

Use runnable environment files in `config/` for active setups. Use
`config/reference.toml` as a catalog of valid section shapes and fields.

## Configuration design guidance

The project currently uses TOML not only as a settings format, but as the
human-facing description of how a runtime is assembled. Because of that, the
shape of the config matters. The goal is to keep the TOML explicit enough to
reflect real dependencies without adding artificial nesting that only exists to
please the builders.

Current design preference:

- top-level sections describe top-level runtime components
- fields directly under a section describe that component itself
- nested sections are used for real child dependencies, not for wrapper names
  with no domain meaning
- shared dependencies should be referenced explicitly rather than inherited
  implicitly
- different entrypoints may assemble different shared resources, so "shared"
  always means shared within that runtime, not globally across the repository

In practice that means:

- if a component simply has its own parameters, keep them directly under the
  component section
- if a component owns another configurable object, model that object as a real
  child section using the child's actual name
- if a component intentionally reuses a runtime-shared dependency, prefer an
  explicit shared-reference variant instead of silent fallback to a top-level
  dependency
- builders should consume resolved effective configs, not raw cross-section
  references

For future wiring changes, avoid patterns like:

- synthetic wrapper sections such as `backend` when the child dependency is
  really just `llm`
- implicit rules like "if local config is missing, use the global one"
- flattening genuine child objects so aggressively that the TOML no longer
  makes the dependency graph understandable

The current repo has not yet fully adopted this style everywhere. Treat it as
the preferred direction for future changes rather than as a claim that every
existing section already follows it perfectly.

## Raw vs resolved config

The repo now distinguishes between two config stages:

- raw config
  the author-facing TOML shape, including reference variants such as
  `type = "shared_llm"`
- resolved config
  the builder-facing effective shape after references have been expanded into
  concrete child configs

That means:

- TOML can stay explicit and ergonomic for humans
- builders can stay simple and mostly consume fully effective configs
- the wiring layer owns reference resolution rather than pushing that logic down
  into individual builders

This pattern is implemented for LLM-backed components such as qualification
and reply generation.

## Runnable configs

- `config/dev.toml`: development API wiring with tracking enabled
- `config/dev-ui-llm.toml`: development NiceGUI wiring with LLM-based routing and replies
- `config/dev-no-api.toml`: local workflow smoke-test without outbound LLM calls

## Sections

### `llm`

Allowed `type` values:
- `pydantic_ai`
- `claude`
- `log`

Fields by type:
- `pydantic_ai`: `model`, `api_key_env`
- `claude`: `model`, `api_key_env`
- `log`: no extra fields

Example:

```toml
[llm]
	type = "pydantic_ai"
	model = "claude-sonnet-4-6"
	api_key_env = "ANTHROPIC_API_KEY"
```

### `messaging`

Allowed `type` values:
- `log`

Fields by type:
- `log`: no extra fields

Example:

```toml
[messaging]
	type = "log"
```

### `storage`

Allowed `type` values:
- `json`
- `memory`

Fields by type:
- `json`: `path`
- `memory`: no extra fields

Example:

```toml
[storage]
	type = "json"
	path = "data/conversations"
```

### `extractor`

Allowed `type` values:
- `instructor`
- `regex`

Fields by type:
- `instructor`: `model`, `api_key_env`
- `regex`: no extra fields

Default:
- omitted sections default to `regex`

### `message_classifier`

Allowed `type` values:
- `heuristic`
- `llm`

Fields by type:
- `heuristic`: no extra fields
- `llm`: `model`, `api_key_env`

Default:
- omitted sections default to `heuristic`

### `structured_extraction`

Allowed `type` values:
- `heuristic`
- `llm`

Fields by type:
- `heuristic`: no extra fields
- `llm`: `model`, `api_key_env`

Default:
- omitted sections default to `heuristic`

### `qualification`

Allowed `type` values:
- `heuristic`
- `shared_llm`
- `llm`

Fields by type:
- `heuristic`: no extra fields
- `shared_llm`: `shared`
- `llm`: nested child section `[qualification.llm]` using the normal `LLMConfig` shape

Default:
- omitted sections default to `heuristic`

Design note:
- qualification returns one of `service`, `not_service`, or `unclear`
- `unclear` keeps the job open and asks for clarification
- raw `shared_llm` explicitly references shared config, currently only `shared = "llm"`
- raw `llm` owns a local child LLM config under `[qualification.llm]`
- resolution converts `shared_llm` into an effective local `llm` config before builders run

### `reply_generation`

Allowed `type` values:
- `rules`
- `shared_llm`
- `llm`

Fields by type:
- `rules`: no extra fields
- `shared_llm`: `shared`
- `llm`: nested child section `[reply_generation.llm]` using the normal `LLMConfig` shape

Default:
- omitted sections default to `rules`

Design note:
- raw `shared_llm` explicitly references shared config, not a prebuilt runtime
  object
- raw `llm` owns a local child LLM config under `[reply_generation.llm]`
- resolution converts `shared_llm` into an effective local `llm` config before
  builders run
- there is no implicit fallback from local-missing to top-level shared LLM
- in the current first slice, `shared_llm` supports only `shared = "llm"`

### `tracking`

Allowed `type` values:
- `mlflow`
- `off`

Fields by type:
- `mlflow`: `experiment`
- `off`: no extra fields

Default:
- omitted sections default to `off`

## Current code-based wiring

These dependencies are still wired directly in code rather than configured
through TOML:

- quote drafter
- scheduler
- reminders

That is intentional for now because each currently has only one practical
implementation in this repo. They can move into config later if real runtime
variation appears.

## Shared vs local dependency examples

These examples are guidance for future config evolution. They show the intended
direction for components that may either reuse a shared resource or own a local
child dependency.

Example of reusing a runtime-shared LLM explicitly:

```toml
[llm]
	type = "pydantic_ai"
	model = "claude-sonnet-4-6"
	api_key_env = "ANTHROPIC_API_KEY"

[reply_generation]
	type = "shared_llm"
	shared = "llm"
```

Example of a component owning its own child LLM config:

```toml
[reply_generation]
	type = "llm"

[reply_generation.llm]
	type = "claude"
	model = "claude-haiku-4-5"
	api_key_env = "ANTHROPIC_API_KEY"
```

Those examples now match the active raw config schema for `reply_generation`.
The same shape is supported by `qualification`. The resolved builder-facing
config is simpler and always carries a concrete child `LLMConfig` when a
component is LLM-backed.
