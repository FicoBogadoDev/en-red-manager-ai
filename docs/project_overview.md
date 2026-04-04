# Manager AI Project Overview

Update note:
If this document conflicts with the newer thread-and-job workflow, prefer the thread-and-job model. The current codebase is centered on persistent contact threads, multiple jobs per thread, and modular workflow services rather than the older single linear conversation flow.

## Purpose

Manager AI is a Python application for handling the first WhatsApp conversation with prospective clients of En Red Rosario, a company that installs safety nets for balconies, roofs, and stairwells. The assistant speaks in Spanish, decides whether the inquiry matches the business, gathers the minimum installation details needed for a quote, and then closes the chat so a human advisor can take over.

This document is meant to be a current-state reference for future onboarding and maintenance. It describes the code as it exists now and intentionally ignores `source_data/`.

## Core workflow

Each incoming message is processed against a persisted `ConversationState` keyed by phone number.

1. `QUALIFYING`
   The agent checks whether the person is actually asking about En Red Rosario's service.
2. `COLLECTING`
   The agent gathers structured lead data one turn at a time.
3. `HANDOFF_PENDING`
   Once all required fields are present, the agent sends a closing message.
4. `DONE`
   The conversation is treated as closed and later messages are ignored.

The required fields for handoff are:

- client name
- street
- city
- installation type
- width in meters
- height in meters

Urgency and apartment/floor are optional enrichments.

## Main architecture

The project still follows a ports-and-adapters shape:

- `api/`
  FastAPI entry point exposing `POST /webhook`.
- `src/manager_ai/agent/`
  Conversation orchestration, prompts, and optional MLflow tracking wrapper.
- `src/manager_ai/services/`
  Stage-specific business logic for qualification, collection, and handoff.
- `src/manager_ai/models/`
  Pydantic models for conversation state, client data, and extracted structured fields.
- `src/manager_ai/ports/`
  Protocol-style interfaces for LLM, storage, messaging, and extractor behavior.
- `src/manager_ai/adapters/`
  Concrete implementations for Anthropic/PydanticAI LLM calls, Instructor extraction, JSON-file storage, memory storage, and log-based messaging.
- `nice_gui_app/`
  A local chat UI for browsing saved conversations and manually driving the agent.

The important design choice is that the `Agent` depends on abstractions, not infrastructure details. Startup wiring in `src/manager_ai/config.py` decides which concrete adapters are used.

## Runtime flow

At startup:

- `api/main.py` loads environment variables from `.env`
- `manager_ai.config.build_agent()` reads a TOML config file
- the selected adapters are instantiated
- tracking may wrap the base agent before the router is created

For each webhook call:

1. `api/routes.py` receives `{ phone, text }`
2. `Agent.handle_message()` loads or creates the conversation state
3. the current stage decides which service runs
4. the selected messaging adapter sends the assistant response
5. the selected storage adapter persists the updated state

## Extraction strategy

The project currently supports two collection modes:

- Regex/JSON-block mode
  The collection prompt asks the model to append a fenced JSON block. `services/collection.py` parses the block, strips it from the reply, and merges any non-null fields into `ClientChart`.
- Instructor mode
  `adapters/extractor/instructor_extractor.py` makes a single Anthropic call that returns both the conversational reply and validated `ExtractedClientData`.

The extractor is optional. If none is configured, the older JSON-block parsing path is used.

After extraction, dimensions are sanity-checked. Values outside the accepted range are discarded so the agent asks again.

## Models and persistence

The main persisted object is `ConversationState`:

- `phone`
- `stage`
- `client`
- `history`
- `handoff_reason`

`ClientChart` stores the lead information being built up over time. JSON-file storage writes one conversation per phone number under `data/conversations/`.

This means the system is stateful across runs as long as the JSON files remain available.

## Configurations

The repo currently contains two practical config variants:

- `config/dev.toml`
  Uses PydanticAI for LLM calls, Instructor for extraction, JSON-file storage, log messaging, and MLflow tracking.
- `config/dev-no-api.toml`
  Uses log-based LLM output, JSON-file storage, log messaging, no extractor, and no tracking. This is the cheapest local path because it avoids external API calls.

`config.py` also still supports:

- direct Anthropic access through `ClaudeAdapter`
- in-memory storage for tests
- tracking disabled entirely

## Observability and tooling

A newer part of the project is the MLflow instrumentation layer:

- `src/manager_ai/agent/tracked_agent.py` wraps the base agent
- each handled message creates an MLflow run and an agent trace span
- LLM and extractor calls are wrapped so prompts, responses, and business metrics can be inspected

The repository also includes:

- `nice_gui_app/main.py` for a lightweight operator/developer UI
- integration scripts in `tests/integration/` for manually checking MLflow traces with real API calls

## Testing posture

The test suite is mostly focused on the collection and qualification services:

- qualification keyword handling and stage transitions
- JSON extraction and merge behavior
- extractor-vs-LLM branching
- required-field completion
- dimension validation
- extraction model validation

This gives reasonable coverage of the core business rules, but there is less automated coverage around the FastAPI layer, NiceGUI app, and end-to-end production wiring.

## Current strengths

- Clear staged workflow for a narrow business problem
- Good separation between domain logic and infrastructure
- Flexible extraction path: prompt-based parsing or validated structured extraction
- Simple persistence model that is easy to inspect manually
- Useful local tools for debugging conversations and model behavior

## Current limitations and drift notes

- The README describes the project well at a high level, but it lags behind the current code in a few places.
- `config/prod.toml.example` is referenced in older docs but is no longer present.
- The system still uses a log-only messaging adapter; a real WhatsApp transport is not implemented in this repo.
- The qualification stage relies on string keywords in model output, which is simple but brittle compared with schema-based classification.
- Some manual integration checks live as runnable scripts under `tests/integration/` rather than as fully automated tests.

## Suggested mental model for future work

Think of the project as four layers:

1. transport layer
   FastAPI webhook and local GUI entry points
2. orchestration layer
   `Agent` and optional `MLFlowTrackedAgent`
3. domain layer
   services plus Pydantic state models
4. infrastructure layer
   storage, LLM, extraction, messaging, and tracking adapters selected from TOML config

If you need to change behavior, most business changes should land in the services, prompts, or models. If you need a new provider or environment-specific integration, it probably belongs in an adapter plus config wiring.
