from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from manager_ai.adapters.classifier.heuristic import HeuristicMessageClassifier
from manager_ai.adapters.qualification.heuristic import HeuristicQualificationAdapter
from manager_ai.adapters.quote_drafting.mock import MockQuoteDraftingAdapter
from manager_ai.adapters.reminder.mock import MockReminderAdapter
from manager_ai.adapters.reply_generation.rules import RulesConversationReplyAdapter
from manager_ai.adapters.scheduling.mock import MockSchedulingAdapter
from manager_ai.adapters.structured_extraction.heuristic import (
    HeuristicStructuredExtractionAdapter,
)
from manager_ai.agent.prompts import NOT_QUALIFIED_MESSAGE
from manager_ai.models.conversation import (
    ContactThreadState,
    ConversationMessage,
    ConversationEvent,
    ExternalActionRequest,
    IncomingMessage,
    IntentType,
    JobState,
    JobStatus,
    MessageRole,
    OutboundMessage,
    ThreadStatus,
    WorkflowResult,
    utc_now,
)
from manager_ai.ports.conversation_repository import ConversationRepositoryPort
from manager_ai.ports.conversation_reply import ConversationReplyPort
from manager_ai.adapters.llm.text_generation.wiring import LLMTextGenerationPort
from manager_ai.ports.message_classifier import MessageClassifierPort
from manager_ai.ports.messaging import MessagingPort
from manager_ai.ports.qualification import (
    QualifiedServiceItem,
    QualificationDecision,
    QualificationPort,
)
from manager_ai.ports.quote_drafting import QuoteDraftingPort
from manager_ai.ports.reminder import ReminderPort
from manager_ai.ports.scheduling import SchedulingPort
from manager_ai.ports.structured_extraction import StructuredExtractionPort
from manager_ai.services.closure_and_followup import apply_closure_updates
from manager_ai.services.evidence_intake import next_question, refresh_evidence_status
from manager_ai.services.handoff_and_escalation import maybe_escalate
from manager_ai.services.message_ingestion import ingest_message
from manager_ai.services.quote_management import ensure_quote
from manager_ai.services.scheduling_coordinator import handle_scheduling
from manager_ai.services.thread_router import add_job, select_job

if TYPE_CHECKING:
    from manager_ai.ports.extractor import ExtractorPort

SERVICE_CLARIFICATION_MESSAGE = (
    "Hola! Gracias por escribirnos. En Red Rosario instalamos redes de seguridad "
    "para balcones, techos y escaleras. Es por ese tipo de instalacion?"
)


class Agent:
    def __init__(
        self,
        llm: LLMTextGenerationPort,
        messaging: MessagingPort,
        storage: ConversationRepositoryPort,
        extractor: "ExtractorPort | None" = None,
        classifier: MessageClassifierPort | None = None,
        qualifier: QualificationPort | None = None,
        structured_extractor: StructuredExtractionPort | None = None,
        reply_generator: ConversationReplyPort | None = None,
        quote_drafter: QuoteDraftingPort | None = None,
        scheduler: SchedulingPort | None = None,
        reminders: ReminderPort | None = None,
    ) -> None:
        self._llm = llm
        self._messaging = messaging
        self._storage = storage
        self._extractor = extractor
        self._classifier = classifier or HeuristicMessageClassifier()
        self._qualifier = qualifier or HeuristicQualificationAdapter()
        self._structured_extractor = (
            structured_extractor or HeuristicStructuredExtractionAdapter()
        )
        self._reply_generator = reply_generator or RulesConversationReplyAdapter()
        self._quote_drafter = quote_drafter or MockQuoteDraftingAdapter()
        self._scheduler = scheduler or MockSchedulingAdapter()
        self._reminders = reminders or MockReminderAdapter()

    def handle_message(self, phone: str, text: str) -> None:
        result = self.handle_incoming_message(IncomingMessage(phone=phone, text=text))
        for outbound in result.outbound_messages:
            self._messaging.send(to=outbound.to, text=outbound.text)

    def handle_incoming_message(self, message: IncomingMessage) -> WorkflowResult:
        thread = self._load_or_create(message.phone)
        normalized_message = ingest_message(message)
        thread_status_before = thread.status.value
        thread.history.append(normalized_message)
        thread.updated_at = normalized_message.created_at
        thread.events.append(
            ConversationEvent(
                kind="incoming_message",
                summary="Inbound message received",
                payload={
                    "text": normalized_message.content,
                    "attachments": len(normalized_message.attachments),
                    "source": normalized_message.source,
                },
            )
        )

        current_job = select_job(thread, IntentType.NEW_INQUIRY)
        intent = self._classifier.classify(
            thread=thread,
            job=current_job,
            message=normalized_message,
        )
        thread.events.append(
            ConversationEvent(
                kind="intent_detected",
                job_id=current_job.id if current_job is not None else None,
                summary=intent.value,
                payload={
                    "intent": intent.value,
                    "message_id": normalized_message.id,
                    "message_text": normalized_message.content,
                },
            )
        )

        route = self._route_for_intent(intent)
        thread.events.append(
            ConversationEvent(
                kind="route_selected",
                job_id=current_job.id if current_job is not None else None,
                summary=route,
                payload={
                    "route": route,
                    "intent": intent.value,
                    "message_id": normalized_message.id,
                },
            )
        )

        job = select_job(thread, intent)
        if job is None:
            title = "Consulta nueva" if not thread.jobs else "Nuevo trabajo en hilo existente"
            job = add_job(thread, title=title)
            thread.events.append(
                ConversationEvent(
                    kind="job_created",
                    job_id=job.id,
                    summary=title,
                    payload={
                        "route": route,
                        "intent": intent.value,
                    },
                )
            )
            if thread.jobs[:-1]:
                thread.dormant_reopen_count += 1
                thread.events.append(
                    ConversationEvent(
                        kind="dormant_thread_reopened",
                        job_id=job.id,
                        summary="Thread reopened into a new job",
                        payload={"reopen_count": thread.dormant_reopen_count},
                    )
                )
        else:
            thread.events.append(
                ConversationEvent(
                    kind="job_selected",
                    job_id=job.id,
                    summary=job.title,
                    payload={
                        "route": route,
                        "intent": intent.value,
                        "created": False,
                    },
                )
            )
        thread.active_job_id = job.id

        outbound_messages: list[OutboundMessage] = []
        external_actions: list[ExternalActionRequest] = []
        job_status_before = job.status.value
        before_missing_fields = list(job.missing_fields)
        before_job_snapshot = job.model_dump(mode="json")

        service_qualification = self._qualifier.qualify(
            thread=thread,
            job=job,
            message=normalized_message,
        )
        if service_qualification.decision == QualificationDecision.NOT_SERVICE:
            job.status = JobStatus.DISQUALIFIED
            job.closure_reason = "not_enred_service"
            thread.status = ThreadStatus.WAITING_ON_INTERNAL
            thread.events.append(
                ConversationEvent(
                    kind="service_disqualified",
                    job_id=job.id,
                    summary="Message is not an En Red service request",
                    payload={
                        "route": "disqualify",
                        "intent": intent.value,
                        "thread_status_before": thread_status_before,
                        "thread_status_after": thread.status.value,
                        "job_status_before": job_status_before,
                        "job_status_after": job.status.value,
                        "qualification_reason": service_qualification.reason,
                    },
                )
            )
            outbound_messages.append(
                OutboundMessage(
                    to=thread.phone,
                    text=service_qualification.reply or NOT_QUALIFIED_MESSAGE,
                )
            )
            self._replace_job(thread, job)
            self._append_outbound_messages_to_history(thread, outbound_messages)
            self._record_outbound_events(thread, job, outbound_messages, route, intent)
            self._record_status_change_events(
                thread=thread,
                job=job,
                thread_status_before=thread_status_before,
                job_status_before=job_status_before,
            )
            self._persist(thread, job, "job_disqualified")
            return WorkflowResult(thread=thread, outbound_messages=outbound_messages)
        if service_qualification.decision == QualificationDecision.UNCLEAR:
            thread.status = ThreadStatus.WAITING_ON_CUSTOMER
            thread.events.append(
                ConversationEvent(
                    kind="service_clarification_requested",
                    job_id=job.id,
                    summary="Message did not contain enough service-fit evidence",
                    payload={
                        "route": route,
                        "intent": intent.value,
                        "thread_status_before": thread_status_before,
                        "thread_status_after": thread.status.value,
                        "job_status": job.status.value,
                        "qualification_reason": service_qualification.reason,
                    },
                )
            )
            outbound_messages.append(
                OutboundMessage(
                    to=thread.phone,
                    text=service_qualification.reply or SERVICE_CLARIFICATION_MESSAGE,
                )
            )
            self._replace_job(thread, job)
            self._append_outbound_messages_to_history(thread, outbound_messages)
            self._record_outbound_events(thread, job, outbound_messages, route, intent)
            self._record_status_change_events(
                thread=thread,
                job=job,
                thread_status_before=thread_status_before,
                job_status_before=job_status_before,
            )
            self._persist(thread, job, "service_clarification_requested")
            return WorkflowResult(thread=thread, outbound_messages=outbound_messages)

        qualification_side_reply: str | None = None
        if service_qualification.unsupported_items:
            qualification_side_reply = (
                service_qualification.side_reply
                or self._qualification_side_reply(
                    service_qualification.service_items,
                    service_qualification.unsupported_items,
                )
            )
            thread.events.append(
                ConversationEvent(
                    kind="unsupported_service_extra_detected",
                    job_id=job.id,
                    summary="Message included unsupported extras while preserving the active job",
                    payload={
                        "route": route,
                        "intent": intent.value,
                        "unsupported_items": [
                            item.model_dump(mode="json")
                            for item in service_qualification.unsupported_items
                        ],
                        "service_items": [
                            item.model_dump(mode="json")
                            for item in service_qualification.service_items
                        ],
                        "qualification_reason": service_qualification.reason,
                    },
                )
            )

        job = self._structured_extractor.extract(
            thread=thread,
            job=job,
            message=normalized_message,
        )
        extraction_changes = self._diff_job_snapshot(before_job_snapshot, job.model_dump(mode="json"))
        if extraction_changes:
            thread.events.append(
                ConversationEvent(
                    kind="extracted_data_updated",
                    job_id=job.id,
                    summary="Structured data updated",
                    payload={
                        "intent": intent.value,
                        "route": route,
                        "changed_fields": extraction_changes,
                    },
                )
            )
        job = refresh_evidence_status(job)
        if before_missing_fields != job.missing_fields:
            thread.events.append(
                ConversationEvent(
                    kind="missing_fields_updated",
                    job_id=job.id,
                    summary="Missing fields recalculated",
                    payload={
                        "before": before_missing_fields,
                        "after": list(job.missing_fields),
                    },
                )
            )

        job, quote_reply = ensure_quote(
            job=job,
            intent=intent,
            drafter=self._quote_drafter,
        )
        if quote_reply:
            latest_quote = job.quotes[-1]
            thread.events.append(
                ConversationEvent(
                    kind="quote_generated",
                    job_id=job.id,
                    summary=latest_quote.kind.value,
                    payload={
                        "route": route,
                        "intent": intent.value,
                        "quote_kind": latest_quote.kind.value,
                        "quote_status": latest_quote.status.value,
                        "amount_ars": latest_quote.amount_ars,
                    },
                )
            )
            if len(job.quotes) > 1:
                thread.events.append(
                    ConversationEvent(
                        kind="quote_superseded",
                        job_id=job.id,
                        summary="Previous quote superseded",
                        payload={
                            "quote_count": len(job.quotes),
                            "current_quote_id": latest_quote.id,
                        },
                    )
                )
            outbound_messages.append(OutboundMessage(to=thread.phone, text=quote_reply))

        job, schedule_action, schedule_reply = handle_scheduling(
            job=job,
            intent=intent,
            scheduler=self._scheduler,
        )
        if schedule_action is not None:
            external_actions.append(schedule_action)
            thread.events.append(
                ConversationEvent(
                    kind="scheduling_requested",
                    job_id=job.id,
                    summary=schedule_action.summary,
                    payload={
                        "route": route,
                        "intent": intent.value,
                        "external_action_type": schedule_action.kind,
                        "details": schedule_action.payload,
                    },
                )
            )
        if schedule_reply:
            outbound_messages.append(OutboundMessage(to=thread.phone, text=schedule_reply))

        job, closure_reply, reminder_action = apply_closure_updates(
            job=job,
            intent=intent,
            reminders=self._reminders,
        )
        if closure_reply:
            thread.events.append(
                ConversationEvent(
                    kind="closure_transition",
                    job_id=job.id,
                    summary=job.status.value,
                    payload={
                        "route": route,
                        "intent": intent.value,
                        "job_status": job.status.value,
                        "closure_reason": job.closure_reason,
                    },
                )
            )
            outbound_messages.append(OutboundMessage(to=thread.phone, text=closure_reply))
        if reminder_action is not None:
            external_actions.append(reminder_action)
            thread.events.append(
                ConversationEvent(
                    kind="reminder_requested",
                    job_id=job.id,
                    summary=reminder_action.summary,
                    payload={
                        "route": route,
                        "intent": intent.value,
                        "external_action_type": reminder_action.kind,
                        "details": reminder_action.payload,
                    },
                )
            )

        if not outbound_messages:
            if job.status == JobStatus.SCOPING:
                job.status = JobStatus.ESTIMATE_READY
                thread.status = ThreadStatus.WAITING_ON_INTERNAL
                outbound_messages.append(
                    OutboundMessage(
                        to=thread.phone,
                        text=self._reply_generator.draft_reply(
                            thread=thread,
                            job=job,
                            intent=intent,
                            route=route,
                            fallback_text="Ya tengo la base del caso. Lo dejo preparado para cotización y seguimiento del equipo.",
                        ),
                    )
                )
            elif job.status == JobStatus.AWAITING_EVIDENCE:
                thread.status = ThreadStatus.WAITING_ON_CUSTOMER
                outbound_messages.append(
                    OutboundMessage(
                        to=thread.phone,
                        text=self._reply_generator.draft_reply(
                            thread=thread,
                            job=job,
                            intent=intent,
                            route=route,
                            fallback_text=next_question(job),
                        ),
                    )
                )
            else:
                thread.status = ThreadStatus.ACTIVE

        if qualification_side_reply and outbound_messages:
            outbound_messages[0] = outbound_messages[0].model_copy(
                update={"text": f"{qualification_side_reply} {outbound_messages[0].text}"}
            )
        elif qualification_side_reply:
            outbound_messages.append(
                OutboundMessage(to=thread.phone, text=qualification_side_reply)
            )

        escalations = maybe_escalate(thread=thread, job=job)
        if escalations:
            thread.status = ThreadStatus.ESCALATED
            thread.escalation_flags.extend(action.reason for action in escalations)
            job.escalated = True
            thread.events.extend(
                ConversationEvent(
                    kind="escalation_triggered",
                    job_id=action.job_id,
                    summary=action.reason.value,
                    payload={
                        "route": route,
                        "intent": intent.value,
                        "reason": action.reason.value,
                        "message": action.message,
                    },
                )
                for action in escalations
            )

        self._replace_job(thread, job)
        self._append_outbound_messages_to_history(thread, outbound_messages)
        self._record_outbound_events(thread, job, outbound_messages, route, intent)
        self._record_external_action_events(thread, job, external_actions, route, intent)
        self._record_status_change_events(
            thread=thread,
            job=job,
            thread_status_before=thread_status_before,
            job_status_before=job_status_before,
        )
        self._persist(thread, job, f"intent:{intent.value}")

        return WorkflowResult(
            thread=thread,
            outbound_messages=outbound_messages,
            external_actions=external_actions,
            escalations=escalations,
        )

    def _load_or_create(self, phone: str) -> ContactThreadState:
        existing = self._storage.load_thread(phone)
        if existing is not None:
            return existing
        return ContactThreadState(phone=phone)

    def _replace_job(self, thread: ContactThreadState, job: JobState) -> None:
        for index, existing in enumerate(thread.jobs):
            if existing.id == job.id:
                thread.jobs[index] = job
                break
        else:
            thread.jobs.append(job)
        thread.active_job_id = job.id
        thread.updated_at = utc_now()

    def _persist(self, thread: ContactThreadState, job: JobState, event_kind: str) -> None:
        thread.events.append(
            ConversationEvent(
                kind=event_kind,
                job_id=job.id,
                summary=job.status.value,
                payload={
                    "thread_status": thread.status.value,
                    "missing_fields": ",".join(job.missing_fields),
                    "active_job_id": thread.active_job_id,
                },
            )
        )
        self._storage.save_thread(thread)

    def _is_service_request(self, text: str, job: JobState) -> bool:
        if job.scope.service_intent or job.scope.installation_type:
            return True
        lower = text.lower()
        if any(token in lower for token in ("pesca", "volley", "futbol", "fútbol", "red lan")):
            return False
        return any(
            token in lower
            for token in (
                "red",
                "balcon",
                "balcón",
                "techo",
                "escalera",
                "proteccion",
                "protección",
                "seguridad",
                "gato",
                "mascota",
            )
        )

    def _route_for_intent(self, intent: IntentType) -> str:
        if intent in {IntentType.QUOTE_QUESTION, IntentType.NEGOTIATION}:
            return "quote_management"
        if intent in {IntentType.SCHEDULING, IntentType.RESCHEDULING}:
            return "scheduling"
        if intent in {IntentType.PAYMENT, IntentType.POST_INSTALL, IntentType.FOLLOW_UP}:
            return "closure_followup"
        if intent in {IntentType.PROVIDE_EVIDENCE, IntentType.NEW_INQUIRY, IntentType.UNKNOWN, IntentType.CHIT_CHAT}:
            return "evidence_intake"
        return "mixed"

    def _qualification_side_reply(
        self,
        service_items: list[QualifiedServiceItem],
        unsupported_items: list[QualifiedServiceItem],
    ) -> str:
        accepted_labels = [
            item.reply_label or item.normalized_service
            for item in service_items
        ]
        unsupported_phrases = [
            item.rejection_phrase
            for item in unsupported_items
            if item.rejection_phrase
        ]
        if not unsupported_phrases:
            unsupported_labels = [
                item.reply_label or item.normalized_service
                for item in unsupported_items
            ]
            unsupported_phrases = [
                f"No trabajamos {', '.join(dict.fromkeys(unsupported_labels))}."
            ]
        accepted_part = (
            f"Podemos ayudarte con {', '.join(dict.fromkeys(accepted_labels))}."
            if accepted_labels
            else "Seguimos con la red de seguridad."
        )
        rejected_part = " ".join(dict.fromkeys(unsupported_phrases))
        return f"{accepted_part} {rejected_part}"

    def _record_outbound_events(
        self,
        thread: ContactThreadState,
        job: JobState,
        outbound_messages: Iterable[OutboundMessage],
        route: str,
        intent: IntentType,
    ) -> None:
        for outbound in outbound_messages:
            thread.events.append(
                ConversationEvent(
                    kind="outbound_message_prepared",
                    job_id=job.id,
                    summary=outbound.to,
                    payload={
                        "route": route,
                        "intent": intent.value,
                        "text": outbound.text,
                    },
                )
            )

    def _record_external_action_events(
        self,
        thread: ContactThreadState,
        job: JobState,
        external_actions: Iterable[ExternalActionRequest],
        route: str,
        intent: IntentType,
    ) -> None:
        for action in external_actions:
            thread.events.append(
                ConversationEvent(
                    kind="external_action_created",
                    job_id=job.id,
                    summary=action.kind,
                    payload={
                        "route": route,
                        "intent": intent.value,
                        "external_action_type": action.kind,
                        "details": action.payload,
                    },
                )
            )

    def _record_status_change_events(
        self,
        thread: ContactThreadState,
        job: JobState,
        thread_status_before: str,
        job_status_before: str,
    ) -> None:
        if thread_status_before != thread.status.value:
            thread.events.append(
                ConversationEvent(
                    kind="thread_status_changed",
                    job_id=job.id,
                    summary=f"{thread_status_before}->{thread.status.value}",
                    payload={
                        "thread_status_before": thread_status_before,
                        "thread_status_after": thread.status.value,
                    },
                )
            )
        if job_status_before != job.status.value:
            thread.events.append(
                ConversationEvent(
                    kind="job_status_changed",
                    job_id=job.id,
                    summary=f"{job_status_before}->{job.status.value}",
                    payload={
                        "job_status_before": job_status_before,
                        "job_status_after": job.status.value,
                    },
                    )
                )

    def _append_outbound_messages_to_history(
        self,
        thread: ContactThreadState,
        outbound_messages: Iterable[OutboundMessage],
    ) -> None:
        for outbound in outbound_messages:
            thread.history.append(
                ConversationMessage(
                    role=MessageRole.ASSISTANT,
                    content=outbound.text,
                    source="workflow",
                )
            )
        if thread.history:
            thread.updated_at = thread.history[-1].created_at

    def _diff_job_snapshot(self, before: dict, after: dict) -> list[str]:
        changed: list[str] = []
        self._collect_changed_paths(before, after, "", changed)
        return changed

    def _collect_changed_paths(
        self,
        before: object,
        after: object,
        prefix: str,
        changed: list[str],
    ) -> None:
        if isinstance(before, dict) and isinstance(after, dict):
            for key in sorted(set(before.keys()) | set(after.keys())):
                path = f"{prefix}.{key}" if prefix else key
                if key not in before or key not in after:
                    changed.append(path)
                    continue
                self._collect_changed_paths(before[key], after[key], path, changed)
            return
        if isinstance(before, list) and isinstance(after, list):
            if before != after:
                changed.append(prefix)
            return
        if before != after and prefix:
            changed.append(prefix)
