# Conversation Workflow Roadmap

## Purpose

This document captures the next implementation steps after the thread-and-job workflow refactor.

It is meant to answer two questions clearly:

- what is already structurally implemented
- what still needs to change before the En Red Rosario conversation workflow is production-ready

## Current Baseline

The codebase now supports a more realistic conversation model:

- a persistent contact thread per phone
- multiple jobs within one thread
- decoupled workflow modules for ingestion, routing, evidence intake, quote handling, scheduling, escalation, and closure
- mocked external operations behind ports
- behavior tests for the main workflow cases

Important current limitation:

- several modules are still heuristic or mocked and should be treated as scaffolding, not final production intelligence

## What Is Still Provisional

These are the main pieces that should evolve next:

- `MessageClassifierPort`
  Current implementation is heuristic. This is good for deterministic testing and architecture validation, but not robust enough for real ambiguous WhatsApp traffic.

- `StructuredExtractionPort`
  Current implementation is also heuristic. It can extract simple names, addresses, dimensions, and some constraints, but it will miss nuance in real conversations.

- `QuoteDraftingPort`
  Current implementation is mocked. It provides placeholder estimates and quote history structure, but not real business pricing logic.

- `SchedulingPort`
  Current implementation is mocked. It correctly marks where scheduling should trigger, but does not integrate with a calendar or operations workflow.

- `ReminderPort`
  Current implementation is mocked. It marks follow-up points, but does not create real reminders or reminders-backed automations.

## Future Phases

### Phase 2: LLM Intelligence Layer

Goal: replace the most brittle heuristics with configurable LLM-backed adapters while keeping deterministic guardrails.

Add:

- `LLMMessageClassifier` behind `MessageClassifierPort`
- `LLMStructuredExtractionAdapter` behind `StructuredExtractionPort`
- TOML config selection between heuristic and LLM implementations
- explicit confidence output from classifier/extractor adapters

Keep deterministic rules for:

- final state transitions
- escalation thresholds
- thread reopening rules
- unsupported-service rejection
- quote/scheduling side-effect authorization

Success criteria:

- ambiguous messages are routed more accurately
- reused threads and multi-job messages are handled more reliably
- structured extraction captures richer operational details from real language

### Phase 3: Commercial Workflow

Goal: make quote and negotiation behavior match the research corpus more closely.

Add:

- real quote lifecycle rules
- rough estimate vs final quote distinction
- negotiated price tracking with explicit override reasons
- recommendation rationale persistence
- approval / rejection / objection capture
- human review checkpoints for commercial exceptions

Likely design direction:

- deterministic state changes
- business-rule pricing or human-entered pricing source of truth
- optional LLM support for quote wording and explanation, not for authoritative price storage

Success criteria:

- quote history is reliable and auditable
- negotiation does not overwrite prior quote context
- handoff includes commercial rationale, not just raw collected fields

### Phase 4: Operational Integrations

Goal: replace mocked operational ports with real integrations while preserving decoupling.

Add real adapters for:

- scheduling/calendar
- reminders/follow-up
- optional CRM or internal ops sync

Requirements:

- integrations remain behind protocols
- failures are represented explicitly in workflow results
- conversation flow can continue safely if an external operation fails

Success criteria:

- scheduling requests create real operational records
- reschedules and follow-ups become traceable actions, not placeholders

### Phase 5: Operator Experience

Goal: expose the new thread/job model properly in the app surfaces.

Update:

- FastAPI request/response models to support attachments and richer message metadata
- NiceGUI to show threads, jobs, events, quote history, schedule actions, and escalation state
- any future admin/review views around human handoff and job selection

Success criteria:

- operators can inspect multiple jobs in one thread
- active job selection and escalation reasons are visible
- conversation context is understandable without reading raw JSON

### Phase 6: Cleanup and Retirement of Legacy Flow

Goal: remove the remaining pieces of the old one-thread/one-job linear design once all consumers are fully migrated.

Clean up:

- old qualification/collection/handoff flow dependencies
- compatibility assumptions that exist only to ease the refactor
- outdated docs describing the previous lifecycle

Success criteria:

- the repo has one clear conversation architecture
- tests reflect the new model only
- onboarding docs match the actual code

## Recommended Order

Recommended implementation order from here:

1. LLM classifier and LLM structured extraction
2. commercial workflow depth
3. operational integrations
4. UI/API/operator improvements
5. legacy cleanup and documentation refresh

## Design Rules To Preserve

As the next phases are implemented, keep these rules intact:

- a thread is not a job
- business state transitions stay explicit in Python
- external dependencies stay behind ports/protocols
- LLMs assist interpretation, not authoritative persistence
- mocked adapters should be replaceable without changing core workflow logic
- thread history, job history, and event history remain inspectable and auditable

## Suggested Immediate Next Task

The highest-value next step is:

- implement `LLMMessageClassifier` and `LLMStructuredExtractionAdapter`
- wire both through TOML config
- keep the heuristic adapters for tests and offline fallback

That gives the project a much stronger real-world conversation layer without undoing the decoupled architecture that is now in place.
