# Project Map

This file is the tie-together document for the maintained knowledge base.

## Purpose

The project has multiple documentation needs:

- durable documentation about how the system works
- evolving context about what we are changing now
- research/report artifacts generated from conversation analysis
- a chronological work record

This folder is for the first, second, and fourth categories.

## Documentation Layers

### 1. Maintained knowledge

Location: `docs/knowledge/`

Use this for current project understanding that should stay readable and easy to update over time.

### 2. Research and generated artifacts

Location: `docs/research/`

Use this for conversation-derived research, generated HTML, structured exports, and evidence-heavy reports.

### 3. Legacy or broad repo docs

Examples:

- `README.md`
- `docs/overview.md`
- `docs/project_overview.md`

Some of these are still useful, but parts may lag behind the latest workflow. Prefer this maintained area for ongoing project memory.

## How To Use This Folder

- Start here when you want the current documentation map.
- Jump to `chatbot-behavior.md` for intended workflow and business behavior.
- Jump to `implementation-architecture.md` for technical structure and code reality.
- Jump to `active-context.md` for what matters right now.
- Jump to `work-log.md` for day-by-day history.

## Behavior vs. Implementation

This folder intentionally separates two different questions:

- "How should the chatbot behave?"
- "How is that behavior currently implemented in code?"

Keep them separate because they change at different speeds and serve different readers.

Use `chatbot-behavior.md` when the answer is about workflow, customer handling, handoff, quoting, scheduling, or escalation behavior.

Use `implementation-architecture.md` when the answer is about modules, models, adapters, persistence, configuration, or tests.

Use `../configuration.md` when the answer is specifically about runnable TOML shapes, supported config types, or which config file to start from.

## Current Intent

This folder is designed to support future Codex skills that can:

- update the daily work log
- refine topic-specific documentation
- keep the docs modular instead of letting one file grow without bound
