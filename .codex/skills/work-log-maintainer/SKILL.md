---
name: work-log-maintainer
description: Use this skill when updating the maintained daily work log for this repository. It helps append clear day-by-day entries to `docs/knowledge/work-log.md` based on the current conversation, the repo state, and any explicit user notes.
---

# Work Log Maintainer

Use this skill when the task is to update the project's maintained work log.

## Primary Target

- `docs/knowledge/work-log.md`

## Goal

Append a useful daily entry that helps future work continue smoothly.

The work log should capture:

- what changed
- why it changed
- important decisions or tradeoffs
- concrete follow-up items

## Workflow

### 1. Ground the entry

Before editing the log:

- inspect the current date
- read the latest section of `docs/knowledge/work-log.md`
- inspect relevant changed files if they matter
- use the current conversation as the primary narrative source

If the user asks for a broader day summary across multiple conversations, infer only from available repo evidence and the existing log. Do not invent work that is not visible.

### 2. Append, do not rewrite history

- add a new dated section if one does not exist for the day
- otherwise append to the existing date section
- preserve prior entries unless the user explicitly asks to clean them up

### 3. Keep entries high signal

Prefer concise bullets or short subsections covering:

- completed work
- reasoning
- follow-up

Avoid:

- raw terminal transcripts
- vague statements like "misc fixes"
- duplicated detail already obvious from the file list alone

## Guardrails

- The log is a project memory aid, not a polished release note.
- Mark uncertainty clearly.
- If the repo state and the conversation disagree, say so in the log rather than silently choosing one.
