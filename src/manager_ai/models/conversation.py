from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from manager_ai.models.client import Address, ClientChart, InstallationType, NetArea


def utc_now() -> datetime:
    return datetime.now(UTC)


class ThreadStatus(str, Enum):
    ACTIVE = "active"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    WAITING_ON_INTERNAL = "waiting_on_internal"
    ESCALATED = "escalated"
    DORMANT = "dormant"


class JobStatus(str, Enum):
    NEW = "new"
    QUALIFYING = "qualifying"
    AWAITING_EVIDENCE = "awaiting_evidence"
    SCOPING = "scoping"
    ESTIMATE_READY = "estimate_ready"
    QUOTE_SENT = "quote_sent"
    NEGOTIATING = "negotiating"
    APPROVED = "approved"
    READY_TO_SCHEDULE = "ready_to_schedule"
    SCHEDULED = "scheduled"
    RESCHEDULE_NEEDED = "reschedule_needed"
    COMPLETED = "completed"
    PAYMENT_PENDING = "payment_pending"
    CLOSED = "closed"
    DISQUALIFIED = "disqualified"
    ABANDONED = "abandoned"


class ConversationStage(str, Enum):
    QUALIFYING = "qualifying"
    COLLECTING = "collecting"
    HANDOFF_PENDING = "handoff_pending"
    DONE = "done"


class AppointmentStatus(str, Enum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    RESCHEDULE_REQUESTED = "reschedule_requested"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class QuoteKind(str, Enum):
    ROUGH = "rough"
    FINAL = "final"
    NEGOTIATED = "negotiated"


class QuoteStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class IntentType(str, Enum):
    NEW_INQUIRY = "new_inquiry"
    PROVIDE_EVIDENCE = "provide_evidence"
    QUOTE_QUESTION = "quote_question"
    NEGOTIATION = "negotiation"
    SCHEDULING = "scheduling"
    RESCHEDULING = "rescheduling"
    PAYMENT = "payment"
    POST_INSTALL = "post_install"
    FOLLOW_UP = "follow_up"
    CHIT_CHAT = "chit_chat"
    UNKNOWN = "unknown"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AttachmentKind(str, Enum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    CONTACT = "contact"
    OTHER = "other"


class EscalationReason(str, Enum):
    LOW_CONFIDENCE = "low_confidence"
    MULTIPLE_ACTIVE_JOBS = "multiple_active_jobs"
    COMMERCIAL_OVERRIDE = "commercial_override"
    STAKEHOLDER_CONFLICT = "stakeholder_conflict"
    AMBIGUOUS_THREAD = "ambiguous_thread"


class Message(BaseModel):
    role: str
    content: str


class AttachmentRef(BaseModel):
    kind: AttachmentKind = AttachmentKind.OTHER
    name: str | None = None
    source: str | None = None


class IncomingMessage(BaseModel):
    phone: str
    text: str
    received_at: datetime = Field(default_factory=utc_now)
    source: str = "whatsapp"
    attachments: list[AttachmentRef] = Field(default_factory=list)


class ConversationMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: MessageRole
    content: str
    created_at: datetime = Field(default_factory=utc_now)
    attachments: list[AttachmentRef] = Field(default_factory=list)
    source: str = "workflow"


class Stakeholder(BaseModel):
    role: str
    label: str
    relationship: str | None = None


class DimensionEstimate(BaseModel):
    label: str | None = None
    width_meters: float | None = None
    height_meters: float | None = None


class JobScope(BaseModel):
    service_intent: str | None = None
    property_type: str | None = None
    address: str | None = None
    city: str | None = None
    installation_type: str | None = None
    area_context: str | None = None
    net_areas: list[DimensionEstimate] = Field(default_factory=list)
    unit_count: int | None = None
    technical_constraints: list[str] = Field(default_factory=list)
    building_constraints: list[str] = Field(default_factory=list)
    urgency: str | None = None
    budget_sensitivity: str | None = None

    def replace_net_areas(self, areas: list[DimensionEstimate]) -> None:
        self.net_areas = []
        for index, area in enumerate(areas, start=1):
            self.net_areas.append(
                area.model_copy(
                    update={"label": area.label or f"Area {index}"}
                )
            )
        self.ensure_area_labels()

    def ensure_area_labels(self) -> None:
        for index, area in enumerate(self.net_areas, start=1):
            if area.label is None:
                area.label = f"Area {index}"

    def has_complete_net_area(self) -> bool:
        return any(
            area.width_meters is not None and area.height_meters is not None
            for area in self.net_areas
        )

    def complete_net_areas(self) -> list[DimensionEstimate]:
        return [
            area
            for area in self.net_areas
            if area.width_meters is not None and area.height_meters is not None
        ]


class JobEvidence(BaseModel):
    attachments: list[AttachmentRef] = Field(default_factory=list)
    attachment_count: int = 0
    has_photos: bool = False
    has_video: bool = False
    has_audio: bool = False
    has_documents: bool = False
    notes: list[str] = Field(default_factory=list)


class QuoteVersion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    kind: QuoteKind
    status: QuoteStatus = QuoteStatus.DRAFT
    amount_ars: int | None = None
    rationale: str | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ScheduleRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    requested_window: str | None = None
    reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class Appointment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: AppointmentStatus = AppointmentStatus.REQUESTED
    scheduled_for: str | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ConversationEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    kind: str
    occurred_at: datetime = Field(default_factory=utc_now)
    job_id: str | None = None
    summary: str
    payload: dict[str, object | None] = Field(default_factory=dict)


class JobState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: JobStatus = JobStatus.NEW
    title: str = "Nueva consulta"
    summary: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    dormant_since: datetime | None = None
    contact_name: str | None = None
    stakeholders: list[Stakeholder] = Field(default_factory=list)
    scope: JobScope = Field(default_factory=JobScope)
    evidence: JobEvidence = Field(default_factory=JobEvidence)
    quotes: list[QuoteVersion] = Field(default_factory=list)
    schedule_requests: list[ScheduleRequest] = Field(default_factory=list)
    appointments: list[Appointment] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    recommendation_rationale: str | None = None
    negotiation_notes: list[str] = Field(default_factory=list)
    objections: list[str] = Field(default_factory=list)
    closure_reason: str | None = None
    escalated: bool = False


class ContactThreadState(BaseModel):
    phone: str
    display_name: str | None = None
    status: ThreadStatus = ThreadStatus.ACTIVE
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    active_job_id: str | None = None
    jobs: list[JobState] = Field(default_factory=list)
    history: list[ConversationMessage] = Field(default_factory=list)
    events: list[ConversationEvent] = Field(default_factory=list)
    escalation_flags: list[EscalationReason] = Field(default_factory=list)
    dormant_reopen_count: int = 0

    def get_job(self, job_id: str | None) -> JobState | None:
        if job_id is None:
            return None
        for job in self.jobs:
            if job.id == job_id:
                return job
        return None

    @property
    def stage(self) -> ConversationStage:
        active_job = self.get_job(self.active_job_id)
        if active_job is None:
            return ConversationStage.QUALIFYING
        if active_job.status in {JobStatus.NEW, JobStatus.QUALIFYING}:
            return ConversationStage.QUALIFYING
        if active_job.status in {JobStatus.AWAITING_EVIDENCE, JobStatus.SCOPING}:
            return ConversationStage.COLLECTING
        if active_job.status in {JobStatus.ESTIMATE_READY, JobStatus.QUOTE_SENT, JobStatus.NEGOTIATING}:
            return ConversationStage.HANDOFF_PENDING
        return ConversationStage.DONE

    @property
    def client(self) -> ClientChart:
        active_job = self.get_job(self.active_job_id)
        installation_type: InstallationType | None = None
        address = Address()
        phone = self.phone
        if active_job is not None:
            active_job.scope.ensure_area_labels()
            raw_type = active_job.scope.installation_type
            if raw_type == "balcony":
                installation_type = InstallationType.BALCONY
            elif raw_type == "roof":
                installation_type = InstallationType.ROOF
            elif raw_type == "stairwell":
                installation_type = InstallationType.STAIRWELL
            address = Address(
                street=active_job.scope.address,
                city=active_job.scope.city,
            )
        return ClientChart(
            phone=phone,
            name=active_job.contact_name if active_job is not None else None,
            address=address,
            installation_type=installation_type,
            net_areas=[
                NetArea(
                    label=area.label,
                    width_meters=area.width_meters,
                    height_meters=area.height_meters,
                )
                for area in (active_job.scope.net_areas if active_job is not None else [])
            ],
            urgency=active_job.scope.urgency if active_job is not None else None,
        )


class ConversationState(BaseModel):
    phone: str
    stage: ConversationStage = ConversationStage.QUALIFYING
    client: ClientChart | None = None
    history: list[Message] = Field(default_factory=list)
    handoff_reason: str | None = None


class OutboundMessage(BaseModel):
    to: str
    text: str


class EscalationAction(BaseModel):
    reason: EscalationReason
    message: str
    job_id: str | None = None


class ExternalActionRequest(BaseModel):
    kind: Literal["schedule", "reminder"]
    job_id: str | None = None
    summary: str
    payload: dict[str, object | None] = Field(default_factory=dict)


class WorkflowResult(BaseModel):
    thread: ContactThreadState
    outbound_messages: list[OutboundMessage] = Field(default_factory=list)
    external_actions: list[ExternalActionRequest] = Field(default_factory=list)
    escalations: list[EscalationAction] = Field(default_factory=list)
