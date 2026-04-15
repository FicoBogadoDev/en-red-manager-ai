# Chatbot Behavior

This file describes how the chatbot is supposed to behave from a product and workflow point of view.

It is the behavioral companion to `implementation-architecture.md`:

- `chatbot-behavior.md` explains intended workflow behavior
- `implementation-architecture.md` explains how the repo currently implements that behavior

## Product Scope

Manager AI supports En Red Rosario's WhatsApp conversations for safety-net inquiries.

The chatbot should help with:

- first contact with prospective customers
- identifying whether the request matches En Red's service
- gathering enough structured information to move the case forward
- supporting quote, scheduling, and follow-up transitions
- surfacing cases that need human intervention

## Core Behavioral Model

The current project direction treats:

- one contact thread as the long-lived WhatsApp relationship with a phone number
- one job as a specific installation or commercial case inside that thread

That distinction matters because a single person may come back later with:

- another property
- another installation area
- quote follow-up
- rescheduling
- post-installation questions

In practice, the workflow assumes that the same phone number may represent an ongoing relationship rather than a single one-off chat.

## Main Workflow Expectations

### 1. Qualification

The chatbot should determine whether the message is actually about En Red Rosario's service.

Non-service requests should be politely closed out or redirected rather than entering the normal workflow.

Current operational meaning:

- requests outside En Red's service are disqualified
- the thread remains visible rather than deleted
- the customer still gets a reply instead of silent failure

### 2. Scope and evidence intake

For relevant jobs, the chatbot should gather the information needed to understand the case:

- who the customer is
- where the work is
- what kind of installation is needed
- dimensions or net areas
- urgency and constraints
- whether attachments or evidence are available

Current minimum information for a scoping-ready case:

- contact name
- address
- city
- installation type
- at least one complete net area with width and height

If these are incomplete, the chatbot should keep asking for the next missing piece instead of pretending the case is ready.

### 3. Quote and negotiation support

Once the case is clear enough, the workflow should support:

- rough estimate generation
- quote history instead of overwriting prior offers
- negotiation tracking
- rationale for recommendations or overrides

Current intended behavior:

- a first pricing answer may be a rough estimate
- later quote responses should preserve history by superseding prior quotes rather than replacing them invisibly
- negotiation is a special state that should remain traceable and reviewable

### 4. Scheduling and follow-up

Once a job is commercially ready, the workflow should support:

- scheduling requests
- appointment tracking
- rescheduling
- reminders and follow-up

Current intended behavior:

- customer scheduling requests should create an explicit operational request
- rescheduling should be represented differently from a first scheduling request
- follow-up should remain visible as workflow state, not just free text in chat history

### 5. Escalation and closure

The chatbot should escalate when the conversation is ambiguous, commercially sensitive, or operationally risky.

Cases should be closable with explicit reasons instead of disappearing into ambiguous end states.

Current automatic escalation conditions include:

- more than one active job in the same thread
- multiple stakeholders on the same job
- commercial negotiation state

These are good examples of behavior that should remain visible even if the exact implementation changes.

## Current Lifecycle Picture

At a high level, a relevant inquiry tends to move through this pattern:

1. A message arrives on an existing or new contact thread.
2. The system decides whether it belongs to the active job or should start a new one.
3. The chatbot qualifies the request as in-scope or not.
4. The chatbot gathers scope information and evidence until the job is sufficiently understood.
5. The workflow can produce a quote or estimate when enough information exists.
6. Scheduling, rescheduling, escalation, negotiation, and closure happen as explicit workflow states.

## Job Reuse vs. New Job

The current behavioral intent is:

- reuse the active job when the customer is still talking about the same case
- open a new job when the customer starts a genuinely new inquiry
- reopen a dormant relationship as a new job rather than mutating old closed work

This matters because mixing multiple installations into one job would make quoting, scheduling, and follow-up harder to audit.

## What The Chatbot Should Not Do

- silently merge distinct jobs into one case when the customer is clearly talking about another project
- act as if a quote is authoritative when it is still pending human review
- treat attachments as irrelevant when they may change scoping or operations
- hide the need for human review during negotiation or ambiguity

## Behavioral Rules To Preserve

- a thread is not the same thing as a job
- the chatbot can assist interpretation, but critical workflow state should remain explicit
- quote history should stay traceable
- human escalation should be visible and intentional
- evidence and attachments matter operationally, not just as chat decoration

## Real-World Notes

This file should capture durable workflow understanding.

If a conclusion comes from conversation research:

- keep the detailed evidence in `docs/research/`
- summarize only the reusable behavioral conclusion here

## What Belongs Here

- expected conversation flow
- business-level workflow rules
- thread vs. job semantics
- scoping and handoff expectations
- handoff, escalation, and operational expectations

## What Does Not Belong Here

- module-by-module code descriptions
- adapter wiring details
- detailed test coverage notes
- chronological project updates

Those belong in `implementation-architecture.md`, `active-context.md`, or `work-log.md`.
