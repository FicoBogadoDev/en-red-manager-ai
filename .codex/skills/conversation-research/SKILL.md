---
name: conversation-research
description: Use this skill when working on WhatsApp conversation analysis for this repository, especially when the task involves `source_data/`, the normalized conversation corpus, per-conversation research dossiers, aggregate research, or updating the HTML/JSON research pack in `docs/research/`. This skill is for the En Red Rosario conversation-research workflow in this project only.
---

# Conversation Research

Use this skill for this repository's conversation-analysis workflow.

The goal is to keep a hybrid method:

1. deterministic parsing and report generation
2. qualitative analysis grounded in the real transcripts
3. updated HTML research outputs that preserve both layers

## Project-Specific Paths

- Source corpus: `source_data/`
- Reorganization manifest: `source_data/reorganization_manifest.json`
- Deterministic + hybrid generator: `scripts/generate_conversation_research.py`
- Output reports: `docs/research/`
- Per-conversation HTML: `docs/research/conversations/`
- Structured data: `docs/research/data/`

## Workflow

### 1. Confirm corpus shape

Before analysis:

- inspect `source_data/`
- assume the normalized structure is one conversation folder per export plus `unassigned/`
- do not use `Para fico.rar`
- treat `unassigned/` as supplemental evidence, not as a normal conversation

If the corpus is not normalized, first fix the structure before doing research work.

### 2. Run the deterministic layer first

Use `scripts/generate_conversation_research.py` as the baseline pipeline.

That script is the factual layer for:

- parsed timelines
- message counts
- attachment inventories
- extracted prices
- extracted dimension-like patterns
- long-gap heuristics
- generated HTML/JSON scaffolding

When updating the research pack, prefer improving this script rather than hand-editing generated HTML.

### 3. Read the real transcripts

Do not rely only on generated HTML.

For qualitative analysis, read:

- the original transcripts in each conversation folder under `source_data/.../transcript/*.txt`
- the generated JSON in `docs/research/data/`
- the HTML only as a navigation/view layer

The qualitative layer must be grounded in the transcript itself.

### 4. Add the qualitative layer

For each conversation, look for:

- what the customer actually wants
- whether the thread is one job or multiple jobs
- who the stakeholders are
- what EnRed does well in the sale
- what creates friction or delay
- what should become structured product state

Important recurring lenses for this project:

- thread vs job separation
- negotiated price vs quoted price
- attachment-dependent qualification
- scheduling/rescheduling clarity
- material recommendation rationale
- multi-stakeholder flows
- post-install/payment/follow-up behavior

Separate facts from interpretation. If a conclusion is uncertain, say so explicitly.

### 5. Update reports in place

Preferred behavior:

- update the existing HTML pack in `docs/research/`
- keep per-conversation and aggregate reports in the same locations
- preserve the deterministic data layer in `docs/research/data/`

Do not create duplicate parallel report trees unless explicitly asked.

## Output Expectations

Per-conversation reports should usually include:

- executive summary
- qualitative read
- repeated patterns
- workflow risks
- product implications
- evidence snippets
- timeline
- attachment inventory

Aggregate research should usually include:

- corpus-level synthesis
- thread-vs-job modeling insight
- recurring EnRed behaviors
- recurring customer behaviors
- key product/design implications
- comparison table across conversations
- unassigned evidence appendix

## Guardrails

- Treat one WhatsApp thread as potentially containing multiple jobs.
- Do not erase the deterministic layer when adding qualitative insights.
- Avoid overclaiming from attachment placeholders if the media was not interpreted.
- Keep project-specific advice tied to EnRed Rosario's real workflow, not generic chatbot advice.
- When refining the workflow, improve the generator script and regenerate outputs rather than manually patching generated HTML.
