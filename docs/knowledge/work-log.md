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
