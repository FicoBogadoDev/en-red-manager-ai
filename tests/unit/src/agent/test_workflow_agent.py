from datetime import UTC, datetime
from typing import Any

from manager_ai.adapters.storage.memory import InMemoryStorageAdapter
from manager_ai.agent.workflow_agent import Agent
from manager_ai.models.conversation import IncomingMessage, JobStatus, ThreadStatus
from manager_ai.ports.qualification import QualificationDecision, ServiceQualification


class StubLLM:
    def complete(self, system_prompt: str, messages: Any) -> str:
        return "stub"


class SpyMessaging:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send(self, to: str, text: str) -> None:
        self.sent.append((to, text))


class StubQualifier:
    def __init__(self, result: ServiceQualification) -> None:
        self.result = result

    def qualify(self, *args: Any, **kwargs: Any) -> ServiceQualification:
        return self.result


def build_agent() -> tuple[Agent, InMemoryStorageAdapter, SpyMessaging]:
    storage = InMemoryStorageAdapter()
    messaging = SpyMessaging()
    agent = Agent(
        llm=StubLLM(),
        messaging=messaging,
        storage=storage,
    )
    return agent, storage, messaging


def build_agent_with_qualifier(
    qualifier: StubQualifier,
) -> tuple[Agent, InMemoryStorageAdapter, SpyMessaging]:
    storage = InMemoryStorageAdapter()
    messaging = SpyMessaging()
    agent = Agent(
        llm=StubLLM(),
        messaging=messaging,
        storage=storage,
        qualifier=qualifier,
    )
    return agent, storage, messaging


def test_creates_new_job_when_same_thread_starts_another_project() -> None:
    agent, storage, _ = build_agent()
    phone = "+5493410000001"

    agent.handle_message(phone, "Hola, necesito red para un balcon en Rosario")
    agent.handle_message(phone, "Ademas necesito otra red para otro depto")

    thread = storage.load_thread(phone)
    assert thread is not None
    assert len(thread.jobs) == 2
    assert thread.active_job_id == thread.jobs[-1].id
    assert thread.status == ThreadStatus.ESCALATED


def test_reopens_dormant_thread_as_new_job() -> None:
    agent, storage, _ = build_agent()
    phone = "+5493410000002"

    old_message = IncomingMessage(
        phone=phone,
        text="Necesito red para balcon en Rosario",
        received_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    new_message = IncomingMessage(
        phone=phone,
        text="Hola, ahora necesito otra red para otra direccion",
        received_at=datetime(2025, 4, 1, tzinfo=UTC),
    )

    agent.handle_incoming_message(old_message)
    agent.handle_incoming_message(new_message)

    thread = storage.load_thread(phone)
    assert thread is not None
    assert len(thread.jobs) == 2
    assert thread.dormant_reopen_count >= 1


def test_collects_scope_and_prepares_estimate_ready() -> None:
    agent, storage, messaging = build_agent()
    phone = "+5493410000003"

    agent.handle_message(phone, "Hola, me llamo Ana y necesito red para balcon en Rioja 1234 Rosario")
    agent.handle_message(phone, "Mide 4 x 2")

    thread = storage.load_thread(phone)
    assert thread is not None
    job = thread.get_job(thread.active_job_id)
    assert job is not None
    assert job.contact_name == "Ana"
    assert job.scope.address == "Rioja 1234"
    assert job.scope.city == "Rosario"
    assert len(job.scope.net_areas) == 1
    assert job.scope.net_areas[0].width_meters == 4.0
    assert job.scope.net_areas[0].height_meters == 2.0
    assert job.status == JobStatus.ESTIMATE_READY
    assert messaging.sent[-1][1].startswith("Ya tengo la base del caso")
    event_kinds = [event.kind for event in thread.events]
    assert "intent_detected" in event_kinds
    assert "route_selected" in event_kinds
    assert "extracted_data_updated" in event_kinds
    assert "missing_fields_updated" in event_kinds
    assert "job_status_changed" in event_kinds


def test_quote_negotiation_keeps_history() -> None:
    agent, storage, _ = build_agent()
    phone = "+5493410000004"

    agent.handle_message(phone, "Hola, me llamo Ana, necesito red para balcon en Rioja 1234 Rosario")
    agent.handle_message(phone, "Mide 4 x 2")
    agent.handle_message(phone, "Cuanto sale?")
    agent.handle_message(phone, "Se puede mejorar el precio?")

    thread = storage.load_thread(phone)
    assert thread is not None
    job = thread.get_job(thread.active_job_id)
    assert job is not None
    assert len(job.quotes) == 2
    assert job.quotes[0].status.value == "superseded"
    assert job.status == JobStatus.NEGOTIATING
    quote_events = [event for event in thread.events if event.kind in {"quote_generated", "quote_superseded"}]
    assert len(quote_events) >= 3


def test_multiple_net_areas_are_saved_and_used_for_quote() -> None:
    agent, storage, _ = build_agent()
    phone = "+5493410000008"

    agent.handle_message(phone, "Hola, me llamo Ana y necesito red para balcon en Rioja 1234 Rosario")
    agent.handle_message(phone, "Mide 4 x 2 y otra parte 3 x 1,5")
    agent.handle_message(phone, "Cuanto sale?")

    thread = storage.load_thread(phone)
    assert thread is not None
    job = thread.get_job(thread.active_job_id)
    assert job is not None
    assert len(job.scope.net_areas) == 2
    assert [(area.width_meters, area.height_meters) for area in job.scope.net_areas] == [
        (4.0, 2.0),
        (3.0, 1.5),
    ]
    assert job.quotes
    assert job.quotes[-1].amount_ars == 525000


def test_scheduling_creates_external_action_and_appointment() -> None:
    agent, storage, _ = build_agent()
    phone = "+5493410000005"

    agent.handle_message(phone, "Hola, necesito red para balcon en Rosario")
    result = agent.handle_incoming_message(
        IncomingMessage(phone=phone, text="Podemos coordinar visita el viernes?")
    )

    thread = storage.load_thread(phone)
    assert thread is not None
    job = thread.get_job(thread.active_job_id)
    assert job is not None
    assert result.external_actions
    assert result.external_actions[0].kind == "schedule"
    assert len(job.appointments) == 1
    assert job.status == JobStatus.SCHEDULED
    scheduling_events = [event.kind for event in thread.events]
    assert "intent_detected" in scheduling_events
    assert "route_selected" in scheduling_events
    assert "scheduling_requested" in scheduling_events
    assert "external_action_created" in scheduling_events


def test_non_service_request_is_disqualified() -> None:
    agent, storage, messaging = build_agent()
    phone = "+5493410000006"

    agent.handle_message(phone, "Hola, quiero una red de pesca")

    thread = storage.load_thread(phone)
    assert thread is not None
    job = thread.get_job(thread.active_job_id)
    assert job is not None
    assert job.status == JobStatus.DISQUALIFIED
    assert thread.status == ThreadStatus.WAITING_ON_INTERNAL
    assert messaging.sent
    disqualify_event = next(event for event in thread.events if event.kind == "service_disqualified")
    assert disqualify_event.payload["route"] == "disqualify"


def test_mixed_supported_and_unsupported_request_preserves_job() -> None:
    agent, storage, messaging = build_agent()
    phone = "+5493410000014"

    agent.handle_message(phone, "Hola, necesito red para balcon y tambien un mosquitero")

    thread = storage.load_thread(phone)
    assert thread is not None
    job = thread.get_job(thread.active_job_id)
    assert job is not None
    assert job.status == JobStatus.AWAITING_EVIDENCE
    assert job.scope.installation_type == "balcony"
    assert "No instalamos mosquiteros" in messaging.sent[-1][1]
    assert "nombre" in messaging.sent[-1][1]
    event = next(
        event
        for event in thread.events
        if event.kind == "unsupported_service_extra_detected"
    )
    assert event.payload["unsupported_items"]


def test_unsupported_extra_during_active_job_keeps_collecting() -> None:
    agent, storage, messaging = build_agent()
    phone = "+5493410000015"

    agent.handle_message(phone, "Hola, necesito red para balcon en Rosario")
    agent.handle_message(phone, "Tambien arreglan barandas?")

    thread = storage.load_thread(phone)
    assert thread is not None
    assert len(thread.jobs) == 1
    job = thread.get_job(thread.active_job_id)
    assert job is not None
    assert job.status != JobStatus.DISQUALIFIED
    assert job.scope.installation_type == "balcony"
    assert "No hacemos arreglos de barandas" in messaging.sent[-1][1]
    assert "nombre" in messaging.sent[-1][1]


def test_greeting_first_message_asks_for_clarification_without_disqualifying() -> None:
    agent, storage, messaging = build_agent()
    phone = "+5493410000009"

    agent.handle_message(phone, "hola")

    thread = storage.load_thread(phone)
    assert thread is not None
    job = thread.get_job(thread.active_job_id)
    assert job is not None
    assert job.status == JobStatus.QUALIFYING
    assert thread.status == ThreadStatus.WAITING_ON_CUSTOMER
    assert "redes de seguridad" in messaging.sent[-1][1]
    event_kinds = [event.kind for event in thread.events]
    assert "service_clarification_requested" in event_kinds
    assert "service_disqualified" not in event_kinds


def test_injected_qualifier_can_drive_unclear_reply() -> None:
    qualifier = StubQualifier(
        ServiceQualification(
            decision=QualificationDecision.UNCLEAR,
            reason="fake unclear",
            reply="Es por redes de seguridad?",
        )
    )
    agent, storage, messaging = build_agent_with_qualifier(qualifier)
    phone = "+5493410000012"

    agent.handle_message(phone, "hola")

    thread = storage.load_thread(phone)
    assert thread is not None
    job = thread.get_job(thread.active_job_id)
    assert job is not None
    assert job.status == JobStatus.QUALIFYING
    assert messaging.sent[-1][1] == "Es por redes de seguridad?"


def test_injected_qualifier_can_drive_disqualification_reply() -> None:
    qualifier = StubQualifier(
        ServiceQualification(
            decision=QualificationDecision.NOT_SERVICE,
            reason="fake not service",
            reply="No trabajamos ese tipo de red.",
        )
    )
    agent, storage, messaging = build_agent_with_qualifier(qualifier)
    phone = "+5493410000013"

    agent.handle_message(phone, "hola")

    thread = storage.load_thread(phone)
    assert thread is not None
    job = thread.get_job(thread.active_job_id)
    assert job is not None
    assert job.status == JobStatus.DISQUALIFIED
    assert messaging.sent[-1][1] == "No trabajamos ese tipo de red."


def test_service_request_after_greeting_reuses_qualifying_job() -> None:
    agent, storage, _ = build_agent()
    phone = "+5493410000010"

    agent.handle_message(phone, "hola")
    agent.handle_message(phone, "Necesito una red para balcon")

    thread = storage.load_thread(phone)
    assert thread is not None
    assert len(thread.jobs) == 1
    job = thread.get_job(thread.active_job_id)
    assert job is not None
    assert job.status == JobStatus.AWAITING_EVIDENCE
    assert job.scope.installation_type == "balcony"


def test_chitchat_during_open_service_job_does_not_disqualify() -> None:
    agent, storage, _ = build_agent()
    phone = "+5493410000011"

    agent.handle_message(phone, "Hola, necesito red para balcon en Rosario")
    agent.handle_message(phone, "jaja perfecto")

    thread = storage.load_thread(phone)
    assert thread is not None
    assert len(thread.jobs) == 1
    job = thread.get_job(thread.active_job_id)
    assert job is not None
    assert job.status != JobStatus.DISQUALIFIED
    assert job.scope.installation_type == "balcony"
    event_kinds = [event.kind for event in thread.events]
    assert "service_disqualified" not in event_kinds


def test_reused_job_emits_job_selected_event() -> None:
    agent, storage, _ = build_agent()
    phone = "+5493410000007"

    agent.handle_message(phone, "Hola, necesito red para balcon en Rosario")
    agent.handle_message(phone, "Mide 3 x 2")

    thread = storage.load_thread(phone)
    assert thread is not None
    selected_events = [event for event in thread.events if event.kind == "job_selected"]
    assert selected_events
    assert all(event.payload["route"] == "evidence_intake" for event in selected_events)
