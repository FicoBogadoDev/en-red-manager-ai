# Manager AI — En Red Rosario

## What this is

An AI agent that handles the **first contact with new clients** over WhatsApp for [En Red Rosario](https://enredrosario.com.ar), a company based in Rosario, Argentina that installs safety nets (protección para chicos y mascotas) in balconies, roofs, and stairwells of residential buildings.

## What the agent does (MVP)

1. **Qualifies the lead** — decides whether the incoming query matches the company's service (safety nets for balconies/roofs/stairwells). If not, it politely redirects the person.
2. **Collects client information** — name, address, type of installation, dimensions, urgency.
3. **Hands off to a human** — sends a closing message and flags the conversation as ready for a human advisor.

The agent communicates in **Spanish (Argentine register)**.

## Architecture

```
src/manager_ai/
  agent/          — orchestrates the conversation loop
  models/         — Pydantic models (ClientChart, ConversationState, …)
  ports/          — typing.Protocol interfaces (LLMPort, MessagingPort, StoragePort)
  adapters/       — concrete implementations (Claude, log stubs, JSON file, in-memory)
  services/       — pure business logic (qualification, collection, handoff)
  config.py       — TOML-driven dependency wiring

api/              — FastAPI webhook (POST /webhook receives WhatsApp messages)
config/           — dev.toml and prod.toml.example
tests/            — unit and integration tests
```

## Running locally (no API key)

```bash
uv sync --extra dev
uv run uvicorn api.main:app --reload
```

`config/dev.toml` defaults `adapters.llm = "log"`, so the agent prints its LLM calls to stdout instead of hitting the Anthropic API.

## Running with Claude

1. Copy `.env.example` → `.env` and set `ANTHROPIC_API_KEY`.
2. Edit `config/dev.toml`: change `llm = "log"` → `llm = "claude"`.
3. Restart the server.

## Testing

```bash
uv run pytest tests/
```
