# Active Context

This file is for the current working picture of the project.

## Keep Updated With

- current priorities
- active refactors
- unresolved questions
- documentation gaps
- known conflicts between docs and code

## Suggested Format

### Current priorities

- Keep maintained documentation aligned with the current thread/job workflow rather than the older linear-only story.
- Gradually reconcile `README.md` and older docs with the newer workflow architecture.
- Keep the behavior/implementation split clean as the knowledge base grows.
- Keep the new wiring split and configuration reference in sync as runtime options change.
- Keep the raw-versus-resolved config split clear as more subsystems move out of the old central settings module.
- Keep the text-generation LLM boundary centralized in `adapters/llm/text_generation/wiring.py` as provider options change.

### Open questions

- Whether the local `.codex` skills should remain local-only or move into a tracked location.
- How much of the older linear flow should stay documented versus being explicitly marked legacy.
- Whether to add automation or scripts for day-wide work-log aggregation across multiple conversations.
- Whether the next config slice should introduce named shared LLM profile maps or first move more effective config contracts close to their modules.
- Whether to finish moving API-key environment lookup out of the remaining non-text-generation LLM-adjacent adapters after the Claude text-generation slice.

### Documentation gaps

- `chatbot-behavior.md` still needs more specific rules around reply style, handoff wording, and post-install behavior.
- `implementation-architecture.md` can still be expanded with NiceGUI boundary details and remaining architecture leaks.
- Broader repo docs still contain stale architecture descriptions.
