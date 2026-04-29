# Work Log

Append one section per day.

Keep entries practical:

- what changed
- why it changed
- important decisions
- follow-up work

---

## 2026-04-15

### Documentation foundation

- Created `docs/knowledge/` as the maintained documentation hub inside the existing `docs/` tree.
- Separated maintained project knowledge from report-style and generated documentation already living under `docs/`.
- Added a modular starter structure with a tie-together map plus focused topic files.
- Added local Codex skill scaffolds for updating the work log and maintained docs in a consistent way.

### Why this direction

- The repository already uses `docs/`, so keeping the maintained knowledge base inside it avoids splitting project memory across multiple top-level locations.
- A dedicated subtree makes the purpose clear and prevents collision with research/report outputs.

### Follow-up

- Fill in the architecture and product files with current source-of-truth content from the codebase and research docs.
- Use the new skills to keep this area current as work continues.
- Consider a future automation or helper script if we want better day-wide summaries across multiple conversations.

### Documentation model update

- Split maintained documentation more explicitly into chatbot behavior versus implementation architecture.
- Renamed the topic files so future updates land in clearer homes and drift is less likely.
- Updated the docs-maintenance guidance so the behavior/implementation split is part of the maintenance workflow.

### Current-state documentation pass

- Expanded `chatbot-behavior.md` with concrete workflow expectations for qualification, evidence intake, quoting, scheduling, escalation, and job reuse.
- Expanded `implementation-architecture.md` with the actual runtime flow, persisted models, config modes, and service-level rules reflected in code.
- Updated `active-context.md` to track the next documentation questions and gaps.

## 2026-04-27

### Message flow diagram

- Added `message-flow-diagram.md` to show the rough end-to-end path from inbound message through routing, extraction, workflow services, persistence, and outbound reply generation.
- Linked the new diagram from the maintained documentation hub so it is easy to find alongside the behavior and implementation docs.
- Added `message-flow-diagram.html` as a standalone browser-rendered view while keeping the Mermaid markdown file as the editable source of truth.
- Simplified Mermaid node labels after the first browser render exposed a syntax-parsing issue in Mermaid 11.14.0.

### Qualification softening and dependency injection

- Investigated why qualification was too harsh: the workflow treated missing service evidence as non-service evidence, so greetings like `hola` could receive a negative response and casual follow-up could disqualify an open job.
- Changed the active workflow qualification decision to preserve three outcomes: `service`, `not_service`, and `unclear`.
- Added clarification behavior for unclear messages so the job remains open and the customer is asked whether they need En Red's safety-net service.
- Added `QualificationPort` plus heuristic and LLM-backed qualification adapters, then wired qualification through TOML config with `heuristic`, `shared_llm`, and local child `llm` options.
- Kept workflow state transitions in `workflow_agent.Agent`; qualifiers decide service fit, while the agent still owns disqualification, clarification, extraction, persistence, and outbound events.
- Updated configuration docs, reference TOML, and maintained architecture/behavior docs to reflect the new injectable qualification dependency.
- Added regression tests for greetings, request-after-greeting job reuse, chitchat on an open service job, injected qualifier behavior, LLM qualification parsing, and config resolution.

### Verification

- `uv run pytest tests/unit/src/adapters/test_qualification.py tests/unit/src/agent/test_workflow_agent.py tests/unit/src/test_config_loading.py -q` passed.
- `uv run pytest tests/unit/src -q` passed with 29 passing tests and 2 skipped tests.
- Full `uv run pytest -q` still stops during integration collection because `mlflow` and `instructor` are missing in the current environment; this appears unrelated to the qualification work.

### Follow-up

- Decide whether to remove or migrate the older binary `services/qualification.py` flow once no active entrypoint needs it.
- Consider richer evaluation data for the LLM qualifier before enabling it in a production-like config.

## 2026-04-18

### Config and wiring cleanup

- Split the previous all-in-one `src/manager_ai/config.py` responsibilities into a focused `src/manager_ai/wiring/` package.
- Added `wiring/settings.py` for typed config models and dedicated builder modules for LLM, messaging, storage, workflow dependencies, and top-level assembly.
- Kept `src/manager_ai/config.py` as a compatibility surface so existing imports from the API and NiceGUI entrypoints did not need to change immediately.
- Added lazy imports in the wiring builders so optional LLM-related packages are only imported when their configured implementations are actually used.

### Configuration reference and runnable config cleanup

- Added `config/reference.toml` as a non-runnable catalog of supported TOML section shapes and `type` variants.
- Added `docs/configuration.md` so valid config fields are discoverable without inspecting Python source.
- Simplified `config/dev.toml` and `config/dev-ui-llm.toml` by removing commented-out alternative blocks now that the reference file exists.
- Left `config/dev-no-api.toml` functionally unchanged for now because the local file resisted in-place cleanup during this pass.

### Verification and follow-up

- Added `tests/unit/src/test_config_loading.py` to verify reference and runnable config parsing/building.
- Verified the wiring refactor with the config-loading test plus the existing workflow-agent unit tests.
- Updated maintained docs so `implementation-architecture.md`, `project-map.md`, `active-context.md`, and `current_documentation_index.md` reflect the new wiring/config layout.
- Follow-up: clean up the remaining `dev-no-api.toml` legacy comment block and continue reducing boundary leaks, especially the NiceGUI access to private agent/storage internals.

## 2026-04-19

### Raw vs resolved config split

- Started the next dependency-injection config refactor by separating author-facing raw app config from builder-facing resolved config.
- Added `src/manager_ai/wiring/raw_app_config.py` for TOML-facing shapes and `src/manager_ai/wiring/resolved_app_config.py` for the resolved effective app config.
- Added `src/manager_ai/wiring/resolution.py` so shared references are expanded before builders run.

### Module-owned effective config contracts

- Moved the effective LLM config contract into `src/manager_ai/adapters/llm/config.py`.
- Moved the effective reply-generation config contract into `src/manager_ai/adapters/reply_generation/config.py`.
- Kept app-level reference semantics such as `shared_llm` out of the module-owned effective config and in the wiring/config layer instead.

### Important design decision

- Clarified that `shared_llm` should mean shared config choice rather than shared runtime object identity.
- In the current first slice, `type = "shared_llm"` with `shared = "llm"` resolves to the top-level LLM config before object construction.
- Simplified `build_reply_generation()` so it now consumes only resolved effective reply-generation config and no longer performs shared-reference lookup itself.

### Verification and follow-up

- Updated config-loading tests so they now check both raw config and resolved config behavior for reply generation.
- Re-ran the config-loading tests and workflow-agent unit tests after the refactor and they passed.
- Updated maintained docs to describe the new raw-versus-resolved flow and the current limitation that `shared_llm` only supports `shared = "llm"` in this first slice.
- Follow-up: decide whether the next slice should introduce named shared LLM profile maps or move more effective config contracts out of `wiring/settings.py` first.

## 2026-04-28

### LLM port and Claude adapter cleanup

- Fixed Anthropic SDK typing issues in `ClaudeAdapter` by converting only `user` and `assistant` turns into Anthropic `MessageParam` values and reading only text response blocks.
- Moved Claude API key environment lookup out of `ClaudeAdapter`; TOML still stores `api_key_env`, but `wiring/llm.py` now resolves the environment value before constructing the adapter.
- Changed `LLMTextGenerationPort.complete()` to take `system_prompt: str` separately from `messages: list[Message]`.
- Updated Claude, log, qualification, reply-generation, tracing, service call sites, and test fakes to follow the new LLM boundary.

### Design decisions

- System prompts are now invocation context rather than fake conversation messages.
- The Anthropic message list is treated as conversation history only, which matches the SDK's typed API shape.
- The API-key cleanup was intentionally applied only to `ClaudeAdapter` for this slice; other LLM-adjacent adapters still need the same boundary cleanup later.

### Documentation and verification

- Updated maintained implementation docs with the new LLM invocation boundary and Claude secret-resolution behavior.
- Added an active-context follow-up to finish moving environment lookup out of the remaining LLM-adjacent adapters.
- `uv run pytest tests\unit\src -q` passed with 29 passing tests and 2 skipped tests.
- `uv run mypy src\manager_ai\adapters\llm\claude.py` passed.
- Broader mypy remains noisy because of existing unrelated missing stubs/imports around `instructor`, `mlflow`, and pre-existing workflow typing issues.

## 2026-04-29

### Text-generation LLM wiring consolidation

- Removed the unused PydanticAI text-generation adapter and switched the runnable/reference LLM config examples to the existing Claude adapter.
- Consolidated the text-generation LLM port, config variants, and builder into `src/manager_ai/adapters/llm/text_generation/wiring.py`.
- Renamed the text-generation protocol to `LLMTextGenerationPort` so it is distinct from structured-output LLM use cases.
- Updated agent, service, qualification, reply-generation, wiring, and config imports to use the new text-generation wiring module.

### Claude adapter dependency cleanup and tests

- Changed `ClaudeAdapter` to receive an explicit Anthropic-compatible client dependency instead of constructing one from an API key internally.
- Moved Anthropic client construction and API-key environment resolution into the text-generation wiring module.
- Added a focused unit test for `ClaudeAdapter` using a fake client that verifies Anthropic request shape and text-block-only response handling.
- Tightened Claude adapter typing to use Anthropic SDK response/content block types instead of broad object-shaped response protocols.

### Verification

- `uv run pytest tests/unit/src -q` passed with 30 passing tests and 2 skipped tests.
- Targeted mypy checks for the Claude adapter, text-generation wiring, and Claude adapter test passed.
