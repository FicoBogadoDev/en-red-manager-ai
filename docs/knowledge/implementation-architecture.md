# Implementation Architecture

This file describes how the current codebase is implemented.

It is the technical companion to `chatbot-behavior.md`:

- `chatbot-behavior.md` explains what the chatbot is supposed to do
- `implementation-architecture.md` explains how the repo currently does it

## Current Technical Shape

The codebase is centered on a persistent contact thread with one or more jobs over time.

Key implementation characteristics:

- Python 3.12 project with FastAPI entry points
- ports-and-adapters structure in `src/manager_ai/`
- persisted thread state in JSON storage by default
- configurable classifier, structured extraction, reply generation, and LLM adapters
- mocked commercial and operational integrations where production integrations do not exist yet

The main runtime entry point is the workflow-oriented `Agent` in `src/manager_ai/agent/workflow_agent.py`.

## Major Code Areas

- `api/`
  FastAPI app and webhook routes
- `src/manager_ai/agent/`
  Main workflow agent and tracking wrapper
- `src/manager_ai/models/`
  Thread, job, quote, appointment, message, and extraction models
- `src/manager_ai/services/`
  Workflow services for ingestion, routing, evidence intake, quote handling, scheduling, escalation, and closure
- `src/manager_ai/ports/`
  Protocols for infrastructure and interpretation boundaries
- `src/manager_ai/adapters/`
  Concrete implementations for classifiers, extraction, LLMs, messaging, storage, scheduling, reminders, and reply generation
- `config/`
  TOML runtime variants
- `nice_gui_app/`
  Local UI for browsing and driving saved conversations

## Runtime Flow

At a high level:

1. `api/main.py` loads configuration and builds the agent.
2. `src/manager_ai/config.py` selects concrete adapters from TOML.
3. `api/routes.py` receives `{ phone, text }` webhook payloads.
4. `workflow_agent.Agent` loads or creates a contact thread.
5. The agent classifies intent, selects or creates a job, updates extracted state, and decides outbound replies or external actions.
6. Messaging and storage adapters persist the result outside the core workflow.

More concretely, `workflow_agent.Agent` currently does this for each incoming message:

1. Load or create a `ContactThreadState`.
2. Normalize and append the inbound message to thread history.
3. Record workflow events such as incoming message, detected intent, and selected route.
4. Reuse the active job or create a new `JobState` through `thread_router`.
5. Disqualify non-service requests early.
6. Run structured extraction on the message.
7. Recompute missing fields and evidence/scoping status.
8. Optionally create quote, scheduling, reminder, escalation, and reply outputs.
9. Persist the updated thread and emit outbound messages.

## Core Persisted Objects

### `ContactThreadState`

The main persisted unit for one phone number.

Contains:

- thread status
- active job reference
- all jobs in the thread
- message history
- workflow events
- escalation flags
- dormant reopen count

### `JobState`

The main unit of work inside a thread.

Contains:

- job status
- title and summary
- contact name and stakeholders
- scope details such as address, city, installation type, and net areas
- evidence inventory
- quotes
- schedule requests and appointments
- missing fields
- escalation and closure markers

Other important persisted structures include:

- `ConversationMessage`
  normalized inbound/outbound chat history
- `ConversationEvent`
  auditable workflow event log
- `QuoteVersion`
  quote history with status and amount
- `ScheduleRequest`
  requested scheduling actions
- `Appointment`
  tracked operational scheduling records

## Configured Modes

Current practical config variants:

- `config/dev.toml`
  PydanticAI LLM, Instructor extractor, JSON storage, log messaging, and MLflow tracking
- `config/dev-no-api.toml`
  Log LLM, JSON storage, log messaging, no extractor config, and no tracking
- `config/dev-ui-llm.toml`
  Additional local variant for UI-oriented work

The config builder in `src/manager_ai/config.py` currently supports:

- LLM adapters: `pydantic_ai`, `claude`, `log`
- storage adapters: `json`, `memory`
- message classifier adapters: `heuristic`, `llm`
- structured extraction adapters: `heuristic`, `llm`
- reply generation adapters: `rules`, `llm`
- tracking modes: `mlflow`, `off`

An older `extractor` path also still exists for Instructor-based extraction support.

## Current Service Rules Reflected In Code

### Job selection

`src/manager_ai/services/thread_router.py` currently opens a new job when:

- there is no active job
- a new inquiry arrives while the active job is terminal
- a new inquiry arrives while there is already an active non-terminal job
- the active job is older than 45 days

Otherwise, the active job is reused.

### Missing fields and scoping

`src/manager_ai/services/evidence_intake.py` currently treats these as required:

- `contact_name`
- `address`
- `city`
- `installation_type`
- `net_areas`

If any are missing, the job becomes `awaiting_evidence`.

If all are present, the job becomes `scoping`.

### Quote handling

`src/manager_ai/services/quote_management.py` currently:

- only prepares quotes for `quote_question` or `negotiation` intents
- requires installation type plus at least one complete net area
- supersedes the previous quote when a new one is created
- marks negotiation as `negotiating`
- marks quote answers as `quote_sent`

### Scheduling handling

`src/manager_ai/services/scheduling_coordinator.py` currently:

- creates a `ScheduleRequest`
- appends an `Appointment`
- sets job status to `scheduled` or `reschedule_needed`
- asks the scheduling adapter to create an external action

### Escalation handling

`src/manager_ai/services/handoff_and_escalation.py` currently raises escalation actions for:

- multiple active jobs in one thread
- multiple stakeholders on one job
- commercial negotiation state

## What Is Still Provisional

Several important pieces are intentionally scaffolded:

- heuristic message classifier remains available and is still useful for deterministic tests
- heuristic structured extraction remains available and is still useful for offline work
- quote drafting is mocked
- scheduling is mocked
- reminders are mocked
- messaging is still log-based rather than a real WhatsApp transport

There is also some intentional architecture overlap from the ongoing transition:

- older linear-flow models and services still exist in parts of the repo
- the maintained docs should treat the thread/job workflow as the current direction
- legacy pieces should only be treated as current when the code path still actively uses them

## Testing Reality

The repo has meaningful coverage around workflow behavior and model logic, especially in:

- `tests/unit/src/agent/`
- `tests/unit/src/services/`
- `tests/unit/src/models/`

There are also integration checks around MLflow and live-model workflows under `tests/integration/`.

Notable behavior covered by tests includes:

- creating a new job inside an existing thread
- reopening dormant threads as new jobs
- collecting scope information into job state
- preserving quote history during negotiation
- saving multiple net areas
- generating scheduling actions
- disqualifying non-service requests

## What Belongs Here

- code structure
- runtime wiring
- persisted models
- adapter/config behavior
- concrete service rules reflected in code
- test and tooling reality

## What Does Not Belong Here

- the intended business conversation flow in prose
- product-level rationale without code implications
- daily status history

Those belong in `chatbot-behavior.md`, `active-context.md`, or `work-log.md`.
