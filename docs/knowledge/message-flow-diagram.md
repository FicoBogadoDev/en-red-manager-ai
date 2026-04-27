# Message Flow Diagram

This diagram shows the rough runtime path of one inbound message until the app decides on outbound replies and persistence.

It is intentionally simplified, but it follows the current `workflow_agent.Agent` flow closely enough to use as an orientation map.

## End-To-End Flow

```mermaid
flowchart TD
    A["Inbound message<br/>phone + text"] --> B["FastAPI route<br/>api/routes.py"]
    B --> C["App wiring builds agent from TOML config<br/>api/main.py + src/manager_ai/wiring"]
    C --> D["Agent.handle_message()<br/>creates IncomingMessage"]
    D --> E["Load or create thread<br/>ContactThreadState"]
    E --> F["Normalize and append inbound message<br/>record incoming_message event"]
    F --> G["Classify intent<br/>MessageClassifierPort"]
    G --> H["Select route<br/>record intent_detected and route_selected"]
    H --> I{"Reuse active job<br/>or create new job?"}
    I -->|Reuse| J["Use existing JobState<br/>record job_selected"]
    I -->|Create| K["Create new JobState via thread_router<br/>record job_created"]
    J --> L{"Is this an En Red service request?"}
    K --> L
    L -->|No| M["Mark job disqualified<br/>append not-qualified reply"]
    L -->|Yes| N["Run structured extraction<br/>update job data"]
    N --> O["Recompute missing fields and evidence status<br/>record extraction/missing-field events"]
    O --> P["Quote handling<br/>ensure_quote()"]
    P --> Q["Scheduling handling<br/>handle_scheduling()"]
    Q --> R["Closure and follow-up handling<br/>apply_closure_updates()"]
    R --> S{"Any outbound reply already prepared?"}
    M --> T["Append outbound message(s) to history<br/>record outbound/status events"]
    S -->|Yes| T
    S -->|No| U{"Job status after processing?"}
    U -->|scoping| V["Promote to estimate_ready<br/>reply: ready for quote/review"]
    U -->|awaiting_evidence| W["Reply with next missing-field question"]
    U -->|Other| X["Generate fallback conversational reply"]
    V --> T
    W --> T
    X --> T
    T --> Y["Create escalation actions if needed"]
    Y --> Z["Persist updated thread/job<br/>via repository or storage adapter"]
    Z --> AA["Send outbound message(s)<br/>via messaging adapter"]
    Z --> AB["Return workflow result<br/>with thread, outbound messages, external actions"]
```

## Main Decision Points

- Intent classification decides the route the message should take.
- Job selection decides whether the message continues an existing case or starts a new one.
- Service qualification can stop the normal flow early.
- Structured extraction determines whether enough information exists to move toward quoting.
- Quote, scheduling, reminder, and closure services may each add reply text or external actions.
- If nothing else created a reply, the agent falls back to a next-question or general conversational response.

## Rough Mental Model

You can think of the flow in four layers:

1. transport and wiring
   FastAPI route plus config-driven app assembly
2. thread/job orchestration
   load thread, classify message, pick job, record events
3. workflow services
   extraction, evidence status, quoting, scheduling, closure, escalation
4. side effects
   persist state, send replies, request external actions

## Related Docs

- `chatbot-behavior.md`
  for what the chatbot is supposed to do
- `implementation-architecture.md`
  for the surrounding technical structure
