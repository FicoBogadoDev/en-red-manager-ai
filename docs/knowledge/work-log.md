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
