# Configuration

Runtime wiring is configured with TOML and validated through the typed config
models in `manager_ai.wiring.settings`.

Use runnable environment files in `config/` for active setups. Use
`config/reference.toml` as a catalog of valid section shapes and fields.

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

### `reply_generation`

Allowed `type` values:
- `rules`
- `llm`

Fields by type:
- `rules`: no extra fields
- `llm`: no extra fields

Default:
- omitted sections default to `rules`

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
