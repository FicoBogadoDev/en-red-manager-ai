---
name: docs-maintainer
description: Use this skill when updating the maintained modular documentation in `docs/knowledge/`. It helps place information in the right file, keep docs small and current, and connect changes back through the project map.
---

# Docs Maintainer

Use this skill when the task is to update the maintained documentation hub for this repository.

## Primary Targets

- `docs/knowledge/README.md`
- `docs/knowledge/project-map.md`
- `docs/knowledge/chatbot-behavior.md`
- `docs/knowledge/implementation-architecture.md`
- `docs/knowledge/active-context.md`
- `docs/knowledge/update-process.md`

## Goal

Keep documentation modular, current, and easy to maintain.

## Workflow

### 1. Classify the information

Decide whether the information belongs in:

- maintained project knowledge in `docs/knowledge/`
- chronological history in `docs/knowledge/work-log.md`
- research/report outputs in `docs/research/`
- broader repo docs such as `README.md`

Prefer the smallest correct home.

Then decide whether maintained knowledge belongs to:

- chatbot behavior and workflow intent
- implementation architecture and current code reality

### 2. Update in place

- extend an existing file before creating a new one
- create a new file only when a topic becomes large enough to deserve its own home
- update `project-map.md` when the documentation map changes
- keep intended behavior and implementation details in separate files unless a tiny cross-reference is enough

### 3. Preserve modularity

- one topic per file
- short sections
- clear headings
- avoid duplicating the same fact across multiple files unless one is a short pointer

## Good Outcomes

- a future teammate can quickly find the right file
- the docs reflect current reality
- broad summaries point to focused documents
- behavior and implementation can evolve without getting tangled together

## Guardrails

- Do not dump large research excerpts into `docs/knowledge/`.
- Do not let `project-map.md` become a giant catch-all narrative.
- Do not fully duplicate the same explanation in both the behavior and implementation files.
- When information is tentative, label it as current understanding or open question.
