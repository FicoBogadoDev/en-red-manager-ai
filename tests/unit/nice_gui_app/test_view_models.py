from datetime import UTC, datetime

from manager_ai.models.conversation import (
    Appointment,
    ContactThreadState,
    ConversationEvent,
    JobScope,
    JobState,
    JobStatus,
    QuoteKind,
    QuoteStatus,
    QuoteVersion,
    ThreadStatus,
)
from nice_gui_app.view_models import (
    active_job,
    filtered_events,
    job_options,
    latest_appointment,
    latest_quote,
    make_thread_summary,
    open_job_count,
)


def build_thread() -> ContactThreadState:
    job_one = JobState(
        id="job-1",
        title="Balcony job",
        status=JobStatus.ESTIMATE_READY,
        contact_name="Ana",
        scope=JobScope(service_intent="balcony protection", city="Rosario"),
        quotes=[
            QuoteVersion(kind=QuoteKind.ROUGH, status=QuoteStatus.SENT, amount_ars=120000),
            QuoteVersion(kind=QuoteKind.NEGOTIATED, status=QuoteStatus.SENT, amount_ars=110000),
        ],
        appointments=[
            Appointment(status="confirmed", scheduled_for="viernes 10hs"),
        ],
    )
    job_two = JobState(
        id="job-2",
        title="Second unit",
        status=JobStatus.CLOSED,
    )
    return ContactThreadState(
        phone="+5493410000010",
        display_name="Ana",
        status=ThreadStatus.ESCALATED,
        updated_at=datetime(2026, 4, 2, 12, 30, tzinfo=UTC),
        active_job_id="job-1",
        jobs=[job_one, job_two],
        events=[
            ConversationEvent(kind="intent_detected", job_id="job-1", summary="intent", payload={"intent": "provide_evidence"}),
            ConversationEvent(kind="route_selected", job_id="job-1", summary="route", payload={"route": "evidence_intake"}),
            ConversationEvent(kind="quote_generated", job_id="job-1", summary="quote", payload={"amount": 120000}),
            ConversationEvent(kind="thread_status_changed", summary="active->escalated", payload={"thread_status_after": "escalated"}),
        ],
    )


def test_make_thread_summary_uses_thread_state() -> None:
    thread = build_thread()

    summary = make_thread_summary(thread)

    assert summary.phone == thread.phone
    assert summary.status == "escalated"
    assert summary.active_job_count == 1
    assert summary.last_activity == "2026-04-02T12:30:00+00:00"


def test_active_job_and_job_options_follow_selection() -> None:
    thread = build_thread()

    assert active_job(thread).id == "job-1"
    assert active_job(thread, "job-2").id == "job-2"
    assert job_options(thread) == {
        "job-1": "Balcony job [estimate_ready]",
        "job-2": "Second unit [closed]",
    }


def test_latest_quote_and_appointment_pick_last_item() -> None:
    thread = build_thread()
    job = thread.get_job("job-1")
    assert job is not None

    quote = latest_quote(job)
    appointment = latest_appointment(job)

    assert quote is not None
    assert quote.amount_ars == 110000
    assert appointment is not None
    assert appointment.scheduled_for == "viernes 10hs"


def test_filtered_events_support_job_and_trace_filters() -> None:
    thread = build_thread()

    quote_events = filtered_events(thread, "job-1", include_thread_wide=False, trace_group="quote")
    all_with_thread = filtered_events(thread, "job-1", include_thread_wide=True, trace_group="all")

    assert [event.kind for event in quote_events] == ["quote_generated"]
    assert [event.kind for event in all_with_thread] == [
        "intent_detected",
        "route_selected",
        "quote_generated",
        "thread_status_changed",
    ]


def test_open_job_count_only_counts_active_statuses() -> None:
    thread = build_thread()

    assert open_job_count(thread) == 1
