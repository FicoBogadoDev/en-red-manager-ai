# Manager AI — En Red Rosario

AI-powered WhatsApp agent that handles first contact with new clients for **En Red Rosario**, an Argentine company that installs safety nets on balconies, rooftops, and stairwells. The agent qualifies leads, collects structured installation data, and hands off complete client profiles to human advisors. All conversations happen in Spanish (Argentine register).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Project Layout](#project-layout)
3. [Data Models](#data-models)
4. [Conversation Stages](#conversation-stages)
5. [How LLM Responses Update Client Data](#how-llm-responses-update-client-data)
6. [Agent Orchestration](#agent-orchestration)
7. [Ports & Adapters](#ports--adapters)
8. [System Prompts](#system-prompts)
9. [API Endpoint](#api-endpoint)
10. [Configuration](#configuration)
11. [Setup & Running](#setup--running)
12. [Running Tests](#running-tests)
13. [Inspecting Saved Conversations](#inspecting-saved-conversations)
14. [Extension Points](#extension-points)

---

## Architecture Overview

The system follows a **hexagonal (ports & adapters)** architecture. The core business logic knows nothing about HTTP, WhatsApp, file systems, or the specific LLM provider. Each infrastructure concern is hidden behind an abstract interface (a `Protocol`), and concrete implementations are injected at startup via a TOML config file.

```
┌──────────────────────────────────────────────────────────┐
│                        API Layer                          │
│          FastAPI  POST /webhook  (api/routes.py)          │
└─────────────────────────┬────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────┐
│                    Agent (Orchestrator)                    │
│               src/manager_ai/agent/agent.py               │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ qualification│  │  collection  │  │    handoff      │  │
│  │  service    │  │   service    │  │    service      │  │
│  └─────────────┘  └──────────────┘  └─────────────────┘  │
└──────┬──────────────────┬──────────────────┬─────────────┘
       │                  │                  │
  LLMPort           StoragePort        MessagingPort
  (Protocol)         (Protocol)         (Protocol)
       │                  │                  │
  ClaudeAdapter    JsonFileAdapter     LogAdapter
  (or LogStub)     (or InMemory)       (or WhatsApp*)
```

> `*` planned, not yet implemented

---

## Project Layout

```
manager-ai/
├── api/
│   ├── main.py              # FastAPI app factory, loads config, wires agent
│   └── routes.py            # POST /webhook endpoint
│
├── src/manager_ai/
│   ├── agent/
│   │   ├── agent.py         # Agent class — main orchestrator
│   │   └── prompts.py       # All Spanish system prompts and canned messages
│   │
│   ├── models/
│   │   ├── client.py        # ClientChart, Address, Dimensions, InstallationType
│   │   └── conversation.py  # ConversationState, ConversationStage, Message
│   │
│   ├── ports/
│   │   ├── llm.py           # LLMPort interface
│   │   ├── messaging.py     # MessagingPort interface
│   │   └── storage.py       # StoragePort interface
│   │
│   ├── adapters/
│   │   ├── llm/
│   │   │   ├── claude.py    # Calls Anthropic Claude API
│   │   │   └── log.py       # Prints to stdout (dev/testing stub)
│   │   ├── messaging/
│   │   │   └── log.py       # Prints to stdout (dev/testing stub)
│   │   └── storage/
│   │       ├── json_file.py # One JSON file per phone in data/conversations/
│   │       └── memory.py    # In-memory dict (unit testing only)
│   │
│   ├── services/
│   │   ├── qualification.py # Stage 1: Is this lead relevant?
│   │   ├── collection.py    # Stage 2: Collect client fields via LLM JSON
│   │   └── handoff.py       # Stage 3: Close conversation, notify advisor
│   │
│   └── config.py            # Reads TOML, builds and injects adapters into Agent
│
├── config/
│   ├── dev.toml             # Development wiring (Claude LLM, log messaging, JSON storage)
│   └── prod.toml.example    # Production template
│
├── data/conversations/      # Persisted ConversationState JSON files
├── tests/                   # pytest unit tests
├── .env.example             # Environment variables template
└── pyproject.toml
```

---

## Data Models

### `ClientChart` — [src/manager_ai/models/client.py](src/manager_ai/models/client.py)

The structured data profile built up during the conversation. Starts empty (all `None`) and is incrementally filled as the client answers questions.

```python
class ClientChart(BaseModel):
    name: str | None                     # Client's full name
    phone: str                           # Primary key — WhatsApp number
    address: Address                     # Nested address fields
    installation_type: InstallationType | None  # "balcony" | "roof" | "stairwell"
    dimensions: Dimensions | None        # Width and height in metres
    urgency: str | None                  # Timeline / preferred date

class Address(BaseModel):
    street: str | None                   # Street name and number
    city: str | None
    floor_or_apartment: str | None       # Optional — e.g. "6B", "PB"

class Dimensions(BaseModel):
    width_meters: float | None
    height_meters: float | None

class InstallationType(str, Enum):
    BALCONY   = "balcony"
    ROOF      = "roof"
    STAIRWELL = "stairwell"
```

**Required fields for a complete profile** (checked by `required_fields_complete()`):
- `name`
- `address.street`
- `address.city`
- `installation_type`
- `dimensions.width_meters`
- `dimensions.height_meters`

`urgency` and `address.floor_or_apartment` are collected but not required to trigger handoff.

---

### `ConversationState` — [src/manager_ai/models/conversation.py](src/manager_ai/models/conversation.py)

Everything that is persisted for a single phone number.

```python
class ConversationState(BaseModel):
    phone: str
    stage: ConversationStage = ConversationStage.QUALIFYING
    client: ClientChart           # The growing client profile
    history: list[Message] = []   # Full message log (user + assistant turns)
    handoff_reason: str | None    # Populated when the conversation closes

class Message(BaseModel):
    role: str     # "user" or "assistant"
    content: str
```

---

## Conversation Stages

```
New contact arrives
        │
        ▼
  ┌──────────────┐
  │  QUALIFYING  │  Does this person need safety net installation?
  └──────┬───────┘
         │ QUALIFIED keyword in LLM response
         ▼
  ┌──────────────┐
  │  COLLECTING  │  Gather name, address, type, dimensions, urgency
  └──────┬───────┘
         │ required_fields_complete() → True
         ▼
  ┌────────────────────┐
  │  HANDOFF_PENDING   │  Send closing message, notify advisor
  └──────┬─────────────┘
         │ (same turn — no extra message needed)
         ▼
  ┌──────────────┐
  │     DONE     │  Conversation closed, further messages ignored
  └──────────────┘

         ┌─── NOT_QUALIFIED keyword ──────────────────► DONE
         │    (standard rejection message sent)
```

Stage transitions are **immutable**: each service function receives the current `ConversationState` and returns a new one via Pydantic's `model_copy(update={...})`. Nothing is mutated in place.

---

## How LLM Responses Update Client Data

This is the core mechanism. The LLM is the source of truth for what the client has communicated; it is also responsible for parsing that natural language into structured fields. The system uses two different extraction protocols depending on the stage.

### Stage 1 — Qualification: keyword in plain text

The qualification prompt instructs Claude to append exactly one of two tokens at the end of its response:

```
QUALIFIED      → lead matches the service
NOT_QUALIFIED  → lead does not match
```

`qualification.run_qualification()` ([src/manager_ai/services/qualification.py](src/manager_ai/services/qualification.py)):

1. Appends the user message to `state.history`.
2. Sends `[system_prompt] + history` to the LLM.
3. Calls `is_qualified(llm_response)` — checks for `"QUALIFIED"` while excluding `"NOT_QUALIFIED"`.
4. Strips both keywords from the reply before sending it to the client.
5. Sets `stage = COLLECTING` if qualified, `stage = DONE` if not.
6. Returns the updated state. **`ClientChart` is not touched here.**

```python
def is_qualified(llm_response: str) -> bool:
    return "QUALIFIED" in llm_response and "NOT_QUALIFIED" not in llm_response
```

If the stage becomes `DONE`, the `Agent` overrides the LLM's reply with a hardcoded `NOT_QUALIFIED_MESSAGE` so the rejection wording is always consistent and never varies by LLM output.

---

### Stage 2 — Collection: embedded JSON block

This is where the `ClientChart` is progressively built. The collection prompt instructs Claude to always append a fenced JSON block at the end of every response:

```
```json
{
  "name": "...",
  "street": "...",
  "city": "...",
  "floor_or_apartment": "...",
  "installation_type": "balcony|roof|stairwell|null",
  "width_meters": null,
  "height_meters": null,
  "urgency": "..."
}
```
```

The LLM fills in fields it has confirmed from the conversation and leaves the rest `null`. **Crucially, it carries forward all previously confirmed fields on every turn**, so the JSON always represents the complete picture of what is known at that moment.

`collection.run_collection()` ([src/manager_ai/services/collection.py](src/manager_ai/services/collection.py)) processes each turn in five steps:

#### Step 1 — Get LLM response
```python
updated_history = state.history + [Message(role="user", content=user_message)]
messages_for_llm = [Message(role="system", content=system_prompt)] + updated_history
llm_response = llm.complete(messages_for_llm)
```

#### Step 2 — Extract the JSON block
```python
def extract_json_block(text: str) -> dict | None:
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        return None
    return json.loads(match.group(1))
```
A regex finds the first fenced JSON block and parses it. If the LLM fails to include one (or produces malformed JSON), `extract_json_block` returns `None` and `extracted` defaults to `{}` — the chart is simply left unchanged for that turn.

#### Step 3 — Merge non-null values into the existing chart
```python
def merge_extracted_data(chart: ClientChart, extracted: dict) -> ClientChart:
    updates: dict = {}

    if extracted.get("name"):
        updates["name"] = extracted["name"]

    # Address fields merged individually
    address_updates = {}
    if extracted.get("street"):        address_updates["street"] = extracted["street"]
    if extracted.get("city"):          address_updates["city"] = extracted["city"]
    if extracted.get("floor_or_apartment"): address_updates["floor_or_apartment"] = ...
    if address_updates:
        updates["address"] = chart.address.model_copy(update=address_updates)

    # installation_type mapped from string → enum
    raw_type = extracted.get("installation_type")
    if raw_type and raw_type != "null":
        updates["installation_type"] = _INSTALLATION_TYPE_MAP.get(raw_type)

    # Dimensions merged at the sub-field level
    width, height = extracted.get("width_meters"), extracted.get("height_meters")
    if width or height:
        existing = chart.dimensions or Dimensions()
        updates["dimensions"] = existing.model_copy(update={
            k: v for k, v in {"width_meters": width, "height_meters": height}.items()
            if v is not None
        })

    if extracted.get("urgency"):
        updates["urgency"] = extracted["urgency"]

    return chart.model_copy(update=updates)
```

Key properties of this merge:
- **Only non-null values overwrite existing ones.** A field already set in the chart is never erased by a subsequent `null` in the JSON.
- **Address and Dimensions are merged at the sub-field level**, not replaced wholesale. If `street` was already known and the LLM only provides `city` this turn, both are preserved.
- **`installation_type` is normalised** from the raw string (`"balcony"`) to the `InstallationType` enum via `_INSTALLATION_TYPE_MAP`.

#### Step 4 — Validate dimensions
```python
_MIN_DIMENSION_METERS = 0.5
_MAX_DIMENSION_METERS = 50.0

def is_plausible_dimension(value: float | None) -> bool:
    if value is None:
        return True
    return _MIN_DIMENSION_METERS <= value <= _MAX_DIMENSION_METERS
```

After merging, the updated chart's dimensions are sanity-checked. If either dimension falls outside the 0.5 m – 50 m range, the entire `Dimensions` object is reset to `None`:

```python
dims = updated_chart.dimensions
if dims and (
    not is_plausible_dimension(dims.width_meters)
    or not is_plausible_dimension(dims.height_meters)
):
    updated_chart = updated_chart.model_copy(update={"dimensions": None})
```

This forces the agent to ask for dimensions again on the next turn rather than silently accepting an obviously wrong value (e.g. the client typed "400" meaning centimetres).

#### Step 5 — Determine stage transition
```python
new_stage = (
    ConversationStage.HANDOFF_PENDING
    if required_fields_complete(updated_chart)
    else ConversationStage.COLLECTING
)
```

`required_fields_complete()` checks that all six mandatory fields are non-null. The moment the last required field is confirmed, the stage advances to `HANDOFF_PENDING` and the handoff fires **within the same message handling turn**.

#### What the client receives

Before the reply is sent, the JSON block is stripped out so the client only sees the conversational text:

```python
reply = re.sub(r"```json.*?```", "", llm_response, flags=re.DOTALL).strip()
```

---

### Stage 3 — Handoff: canned message, no LLM call

`handoff.run_handoff()` ([src/manager_ai/services/handoff.py](src/manager_ai/services/handoff.py)) does not call the LLM. It sends a fixed closing message and marks the conversation `DONE`:

```python
def run_handoff(state, closing_message, messaging) -> ConversationState:
    messaging.send(to=state.phone, text=closing_message)
    return state.model_copy(update={
        "stage": ConversationStage.DONE,
        "handoff_reason": "all_fields_collected",
    })
```

---

### End-to-end example of a collection turn

```
Client says: "Son 4 metros de ancho por 1.20 de alto"

LLM responds:
  "Bárbaro, anotado: 4 m de ancho × 1,20 m de alto. ¿Tenés alguna urgencia
   o fecha tentativa para la instalación?

   ```json
   {
     "name": "Federico",
     "street": "Tucumán 1464",
     "city": "Rosario",
     "floor_or_apartment": "6B",
     "installation_type": "balcony",
     "width_meters": 4.0,
     "height_meters": 1.2,
     "urgency": null
   }
   ```"

collection.run_collection():
  1. extract_json_block() → {"name": "Federico", "street": "Tucumán 1464", ...,
                              "width_meters": 4.0, "height_meters": 1.2, "urgency": null}
  2. merge_extracted_data() → chart now has dimensions (4.0 × 1.2), all previous fields kept
  3. is_plausible_dimension(4.0) → True, is_plausible_dimension(1.2) → True
  4. required_fields_complete() → False (urgency missing but not required; all 6 required
     fields ARE present → actually True here → stage = HANDOFF_PENDING)
  5. reply sent = "Bárbaro, anotado: 4 m de ancho × 1,20 m de alto. ¿Tenés alguna urgencia
     o fecha tentativa para la instalación?"   (JSON stripped)
```

---

## Agent Orchestration

`Agent.handle_message()` ([src/manager_ai/agent/agent.py](src/manager_ai/agent/agent.py)) is the single entry point for every incoming message. It uses `if` statements (not `elif`) so that a stage transition within a single turn is immediately acted upon:

```python
def handle_message(self, phone: str, text: str) -> None:
    state = self._load_or_create(phone)

    # Closed conversations are silently ignored
    if state.stage == ConversationStage.DONE:
        return

    # ── Stage: QUALIFYING ──────────────────────────────────────────────
    if state.stage == ConversationStage.QUALIFYING:
        state, reply = qualification.run_qualification(
            state, text, self._llm, QUALIFICATION_SYSTEM_PROMPT
        )
        if state.stage == ConversationStage.DONE:
            # Rejected — send standard message and stop
            self._messaging.send(to=phone, text=NOT_QUALIFIED_MESSAGE)
            self._storage.save(phone, state)
            return
        self._messaging.send(to=phone, text=reply)
    # state.stage may now be COLLECTING

    # ── Stage: COLLECTING ──────────────────────────────────────────────
    if state.stage == ConversationStage.COLLECTING:
        state, reply = collection.run_collection(
            state, text, self._llm, COLLECTION_SYSTEM_PROMPT
        )
        self._messaging.send(to=phone, text=reply)
    # state.stage may now be HANDOFF_PENDING

    # ── Stage: HANDOFF_PENDING ─────────────────────────────────────────
    if state.stage == ConversationStage.HANDOFF_PENDING:
        state = handoff.run_handoff(state, HANDOFF_MESSAGE, self._messaging)
    # state.stage is now DONE

    self._storage.save(phone, state)
```

**Important:** because the stage check after qualification uses `if state.stage == COLLECTING` (not `elif`), a first message that immediately qualifies will continue into the collection step in the same turn. Similarly, a collection turn that completes the chart will immediately trigger handoff in the same turn — no extra round-trip from the client is needed.

---

## Ports & Adapters

### Interfaces (`src/manager_ai/ports/`)

All three ports are `typing.Protocol` classes — no inheritance required.

| Port | Method | Purpose |
|------|--------|---------|
| `LLMPort` | `complete(messages) -> str` | Send a message list, receive a string response |
| `MessagingPort` | `send(to, text) -> None` | Deliver a message to a phone number |
| `StoragePort` | `load(phone) -> ConversationState \| None` | Retrieve persisted state |
| | `save(phone, state) -> None` | Persist updated state |

### Concrete Adapters (`src/manager_ai/adapters/`)

| Adapter | Config key | Notes |
|---------|-----------|-------|
| `ClaudeAdapter` | `llm = "claude"` | Calls `anthropic.Anthropic().messages.create()` |
| `LogLLMAdapter` | `llm = "log"` | Prints prompt, returns placeholder — no API key needed |
| `LogMessagingAdapter` | `messaging = "log"` | Prints outgoing message to stdout |
| `JsonFileStorageAdapter` | `storage = "json"` | `data/conversations/<phone>.json` |
| `InMemoryStorageAdapter` | *(test only)* | Plain dict, no file I/O |

### Wiring (`src/manager_ai/config.py`)

```python
def build_agent(config_path: Path) -> Agent:
    config = toml.loads(config_path.read_text())
    llm       = _build_llm(config)        # selects adapter by config key
    messaging = _build_messaging(config)
    storage   = _build_storage(config)
    return Agent(llm=llm, messaging=messaging, storage=storage)
```

`api/main.py` calls `build_agent` at startup and attaches the resulting `Agent` instance to the FastAPI app state.

---

## System Prompts

All prompts live in [src/manager_ai/agent/prompts.py](src/manager_ai/agent/prompts.py). They are plain strings injected as the first `system` message in every LLM call.

### `QUALIFICATION_SYSTEM_PROMPT`
Instructs the LLM to:
- Confirm whether the query is about safety net installation for balconies, rooftops, or stairwells.
- Respond in Argentine Spanish (tuteo, local vocabulary).
- Append `QUALIFIED` or `NOT_QUALIFIED` as the final line — the only machine-readable signal in this stage.

### `COLLECTION_SYSTEM_PROMPT`
Instructs the LLM to:
- Collect the five data categories (name, address, type, dimensions, urgency) one at a time, in natural order.
- Respond in Argentine Spanish.
- Always append a fenced `json` block listing all confirmed fields and `null` for the rest — the structured payload the service layer extracts.

### Canned messages (no LLM call)

| Constant | Used when |
|----------|-----------|
| `HANDOFF_MESSAGE` | All required fields collected — closing message to client |
| `NOT_QUALIFIED_MESSAGE` | Lead does not match the service — replaces LLM rejection reply |

Using hardcoded canned messages for these cases ensures consistent wording regardless of LLM variation.

---

## API Endpoint

`POST /webhook` ([api/routes.py](api/routes.py))

```
Request body:
{
  "phone": "+5493411234567",   // WhatsApp number
  "text":  "Hola, quiero instalar una red en mi balcón"
}

Response:
{
  "status": "ok"
}
```

The endpoint delegates entirely to `Agent.handle_message()`. All replies are sent asynchronously via the messaging adapter (currently printed to stdout).

Example:
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"phone": "+5493411234567", "text": "Hola, quiero una red para mi balcón"}'
```

---

## Configuration

### `config/dev.toml`
```toml
[adapters]
llm       = "claude"   # "claude" | "log"
messaging = "log"      # "log"    | (whatsapp — not yet implemented)
storage   = "json"     # "json"   | "memory"

[json_storage]
path = "data/conversations"

[claude]
model        = "claude-sonnet-4-6"
api_key_env  = "ANTHROPIC_API_KEY"   # name of the env var to read the key from
```

### `.env`
```
ANTHROPIC_API_KEY=sk-ant-...
```

Set `llm = "log"` to run without an API key — useful for checking request routing without spending tokens.

---

## Setup & Running

```bash
# 1. Create the virtual environment (WSL: keep it outside /mnt/c/ to avoid Windows venv issues)
UV_PROJECT_ENVIRONMENT=~/.venvs/manager-ai uv sync --extra dev

# 2. Configure the API key
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...

# 3. Start the server
UV_PROJECT_ENVIRONMENT=~/.venvs/manager-ai uv run uvicorn api.main:app --reload
```

> **WSL note:** prefix every `uv` command with `UV_PROJECT_ENVIRONMENT=~/.venvs/manager-ai`, or add `export UV_PROJECT_ENVIRONMENT=~/.venvs/manager-ai` to `~/.bashrc`.

Simulate messages with curl (see [API Endpoint](#api-endpoint) above). Send multiple messages with the same phone number to walk through the full flow; the state is persisted between requests.

---

## Running Tests

```bash
UV_PROJECT_ENVIRONMENT=~/.venvs/manager-ai uv run pytest tests/ -v
```

Unit tests use `InMemoryStorageAdapter` and a `StubLLM` that returns preset strings, so no API key or network access is needed.

---

## Inspecting Saved Conversations

Each conversation is saved as `data/conversations/<phone>.json`. Example of a completed conversation:

```json
{
  "phone": "+5493411234567",
  "stage": "done",
  "client": {
    "name": "Federico Bogado",
    "phone": "+5493411234567",
    "address": {
      "street": "Tucumán 1464",
      "city": "Rosario",
      "floor_or_apartment": "6B"
    },
    "installation_type": "balcony",
    "dimensions": { "width_meters": 4.0, "height_meters": 1.2 },
    "urgency": "La semana que viene por la tarde"
  },
  "history": [
    {"role": "user",      "content": "Hola, quiero instalar una red en mi balcón"},
    {"role": "assistant", "content": "¡Hola! Con gusto te ayudo..."},
    ...
  ],
  "handoff_reason": "all_fields_collected"
}
```

To reset a conversation and start fresh:
```bash
rm data/conversations/+5493411234567.json
```

---

## Extension Points

| Component | Current | Future |
|-----------|---------|--------|
| Messaging | `LogMessagingAdapter` (stdout) | `WhatsAppAdapter` (Meta Cloud API) |
| Storage | `JsonFileStorageAdapter` | `PostgresStorageAdapter` |
| LLM | `ClaudeAdapter` | Any provider implementing `LLMPort` |
| Handoff | Send closing message only | Notify CRM / human team via webhook |
| Validation | Dimension range check | NLP address validation, duplicate detection |
