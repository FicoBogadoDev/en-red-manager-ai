"""NiceGUI operator console for the thread/job workflow."""

from __future__ import annotations

import os
from pathlib import Path
import traceback

import dotenv
from nicegui import Client, ui

from manager_ai.adapters.storage.json_file import JsonFileStorageAdapter
from manager_ai.config import build_agent
from manager_ai.models.conversation import ContactThreadState, IncomingMessage, MessageRole
from nice_gui_app.view_models import (
    active_job,
    filtered_events,
    job_options,
    latest_appointment,
    latest_quote,
    make_thread_summary,
)

dotenv.load_dotenv()

CONFIG_PATH = Path(
    os.environ.get(
        "MANAGER_AI_CONFIG",
        str(Path(__file__).parent.parent / "config" / "dev-ui-llm.toml"),
    )
)
DEBUG_LOG_PATH = Path(__file__).parent.parent / "data" / "nice_gui_app_debug.log"

agent = build_agent(CONFIG_PATH)
_inner = agent._agent if hasattr(agent, "_agent") else agent  # type: ignore[attr-defined]
storage: JsonFileStorageAdapter = _inner._storage  # type: ignore[attr-defined]

_THREAD_STATUS_COLOR = {
    "active": "blue",
    "waiting_on_customer": "orange",
    "waiting_on_internal": "amber",
    "escalated": "red",
    "dormant": "grey",
}

_JOB_STATUS_COLOR = {
    "new": "blue",
    "qualifying": "blue",
    "awaiting_evidence": "orange",
    "scoping": "orange",
    "estimate_ready": "teal",
    "quote_sent": "indigo",
    "negotiating": "purple",
    "approved": "green",
    "ready_to_schedule": "green",
    "scheduled": "green",
    "reschedule_needed": "deep-orange",
    "completed": "green",
    "payment_pending": "amber",
    "closed": "grey",
    "disqualified": "red",
    "abandoned": "grey",
}


def _format_value(value: object | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(_format_value(item) for item in value) if value else "-"
    if isinstance(value, dict):
        return ", ".join(f"{key}={_format_value(item)}" for key, item in value.items()) if value else "-"
    return str(value)


def _field_row(label: str, value: object | None) -> None:
    with ui.row().classes("w-full items-start gap-2"):
        ui.label(label).classes("text-xs uppercase tracking-wide text-gray-500 w-28 shrink-0")
        ui.label(_format_value(value)).classes("text-sm text-gray-800 whitespace-pre-wrap")


def _format_net_areas(net_areas: list[object]) -> list[str]:
    formatted: list[str] = []
    for index, area in enumerate(net_areas, start=1):
        label = getattr(area, "label", None) or f"Area {index}"
        width = getattr(area, "width_meters", None)
        height = getattr(area, "height_meters", None)
        formatted.append(f"{label}: {width or '-'} x {height or '-'} m")
    return formatted


def _status_badge(label: str, color_map: dict[str, str]) -> None:
    color = color_map.get(label, "grey")
    ui.badge(label.replace("_", " ").upper()).props(f"color={color} rounded")


def _thread_snapshot(phone: str | None) -> ContactThreadState | None:
    if not phone:
        return None
    return storage.load_thread(phone)


def _log_ui_error(context: str, exc: Exception) -> None:
    DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DEBUG_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"[{context}] {exc}\n")
        handle.write(traceback.format_exc())
        handle.write("\n")


def _log_ui_step(message: str) -> None:
    DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DEBUG_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(f"[step] {message}\n")


@ui.page("/")
async def index(client: Client) -> None:
    current_phone: list[str | None] = [None]
    selected_job_id: list[str | None] = [None]
    pending_user_message: list[str | None] = [None]
    latest_trace_summary: list[str | None] = [None]
    chat_div: list = [None]
    job_select: list = [None]
    trace_group: list[str] = ["all"]
    include_thread_wide: list[bool] = [True]

    def _select_default_phone() -> None:
        phones = sorted(storage.list_thread_phones())
        if current_phone[0] not in phones:
            current_phone[0] = phones[0] if phones else None

    def _scroll_to_bottom() -> None:
        div = chat_div[0]
        if div is None:
            return
        client.run_javascript(
            f"var el = document.getElementById('c{div.id}');"
            " if (el) el.scrollTop = el.scrollHeight;"
        )

    def _sync_job_selector() -> None:
        select = job_select[0]
        if select is None:
            return
        state = _thread_snapshot(current_phone[0])
        options = job_options(state) if state is not None else {}
        select.options = options
        if state is None or not options:
            select.value = None
            selected_job_id[0] = None
            select.update()
            return
        if selected_job_id[0] not in options:
            selected_job_id[0] = state.active_job_id or next(iter(options))
        select.value = selected_job_id[0]
        select.update()

    def _refresh_all() -> None:
        state = _thread_snapshot(current_phone[0])
        if state is not None and selected_job_id[0] is None:
            selected_job_id[0] = state.active_job_id
        show_sidebar.refresh()
        show_thread_header.refresh()
        show_chat.refresh()
        show_job_panel.refresh()
        show_trace_panel.refresh()
        _sync_job_selector()
        _scroll_to_bottom()

    def select_conversation(phone: str) -> None:
        current_phone[0] = phone
        state = _thread_snapshot(phone)
        selected_job_id[0] = state.active_job_id if state is not None else None
        latest_trace_summary[0] = None
        _refresh_all()

    def select_job(job_id: str | None) -> None:
        selected_job_id[0] = job_id
        show_job_panel.refresh()
        show_trace_panel.refresh()

    @ui.refreshable
    def show_sidebar() -> None:
        phones = sorted(storage.list_thread_phones())
        if not phones:
            ui.label("No threads yet").classes("text-sm text-gray-400 mt-3")
            return
        for phone in phones:
            thread = storage.load_thread(phone)
            if thread is None:
                continue
            summary = make_thread_summary(thread)
            is_active = phone == current_phone[0]

            def make_handler(target_phone: str):
                def handler() -> None:
                    select_conversation(target_phone)
                return handler

            with ui.card().classes(
                "w-full cursor-pointer gap-2 border "
                + ("bg-blue-50 border-blue-200" if is_active else "border-gray-200")
            ).on("click", make_handler(phone)):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label(thread.display_name or phone).classes("text-sm font-semibold truncate")
                    if summary.escalation_count:
                        ui.badge(f"{summary.escalation_count} escalations").props("color=red")
                ui.label(phone).classes("text-xs font-mono text-gray-500")
                with ui.row().classes("w-full items-center justify-between"):
                    _status_badge(summary.status, _THREAD_STATUS_COLOR)
                    ui.label(f"{summary.active_job_count} open jobs").classes("text-xs text-gray-500")
                ui.label(f"Updated {summary.last_activity}").classes("text-xs text-gray-400")

    @ui.refreshable
    def show_thread_header() -> None:
        thread = _thread_snapshot(current_phone[0])
        if thread is None:
            ui.label("Select or create a thread to start.").classes("text-sm text-gray-400")
            return
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column().classes("gap-0"):
                ui.label(thread.display_name or thread.phone).classes("text-xl font-semibold")
                ui.label(thread.phone).classes("text-sm font-mono text-gray-500")
            with ui.row().classes("items-center gap-2"):
                _status_badge(thread.status.value, _THREAD_STATUS_COLOR)
                ui.badge(f"{len(thread.jobs)} jobs").props("color=blue-grey")
                if thread.dormant_reopen_count:
                    ui.badge(f"reopened {thread.dormant_reopen_count}x").props("color=amber")
        if latest_trace_summary[0]:
            ui.label(latest_trace_summary[0]).classes("text-sm text-blue-700")

    @ui.refreshable
    def show_chat() -> None:
        thread = _thread_snapshot(current_phone[0])
        if thread is None:
            ui.label("No conversation selected").classes("text-sm text-gray-400")
            return
        if not thread.history and not pending_user_message[0]:
            ui.label("No messages yet").classes("text-sm text-gray-400")
            return
        for message in thread.history:
            is_user = message.role == MessageRole.USER
            is_system = message.role == MessageRole.SYSTEM
            align = "justify-end" if is_user else "justify-start"
            card_classes = "max-w-2xl px-4 py-3 "
            if is_user:
                card_classes += "bg-blue-600 text-white"
            elif is_system:
                card_classes += "bg-amber-50 text-amber-900 border border-amber-200"
            else:
                card_classes += "bg-gray-100 text-gray-900"
            with ui.row().classes(f"w-full {align}"):
                with ui.card().classes(card_classes):
                    ui.label(message.content).classes("text-sm whitespace-pre-wrap")
                    with ui.row().classes("w-full items-center justify-between mt-2"):
                        ui.label(message.role.value).classes("text-xs opacity-70")
                        ui.label(message.created_at.isoformat(timespec='seconds')).classes("text-xs opacity-70")
                    if message.attachments:
                        ui.separator().classes("my-2")
                        ui.label(
                            ", ".join(
                                f"{attachment.kind.value}:{attachment.name or attachment.source or 'attachment'}"
                                for attachment in message.attachments
                            )
                        ).classes("text-xs opacity-80")
        if pending_user_message[0]:
            with ui.row().classes("w-full justify-end"):
                with ui.card().classes("max-w-2xl px-4 py-3 bg-blue-300 text-white"):
                    ui.label(pending_user_message[0]).classes("text-sm whitespace-pre-wrap")

    @ui.refreshable
    def show_job_panel() -> None:
        thread = _thread_snapshot(current_phone[0])
        if thread is None:
            ui.label("Thread details will appear here.").classes("text-sm text-gray-400")
            return
        job = active_job(thread, selected_job_id[0])
        if job is None:
            ui.label("This thread has no jobs yet.").classes("text-sm text-gray-400")
            return

        with ui.row().classes("w-full items-center justify-between"):
            ui.label(job.title).classes("text-lg font-semibold")
            _status_badge(job.status.value, _JOB_STATUS_COLOR)
        if job.summary:
            ui.label(job.summary).classes("text-sm text-gray-600")

        with ui.card().classes("w-full"):
            ui.label("Missing fields").classes("text-sm font-semibold")
            if job.missing_fields:
                for field_name in job.missing_fields:
                    ui.badge(field_name.replace("_", " ")).props("outline color=orange")
            else:
                ui.label("No missing fields").classes("text-sm text-gray-500")

        with ui.card().classes("w-full"):
            ui.label("Contact").classes("text-sm font-semibold")
            _field_row("Display name", thread.display_name)
            _field_row("Phone", thread.phone)
            _field_row("Contact name", job.contact_name)
            _field_row(
                "Stakeholders",
                [
                    f"{stakeholder.role}: {stakeholder.label}"
                    + (f" ({stakeholder.relationship})" if stakeholder.relationship else "")
                    for stakeholder in job.stakeholders
                ],
            )

        with ui.card().classes("w-full"):
            ui.label("Location and scope").classes("text-sm font-semibold")
            _field_row("Service intent", job.scope.service_intent)
            _field_row("Property type", job.scope.property_type)
            _field_row("Address", job.scope.address)
            _field_row("City", job.scope.city)
            _field_row("Installation type", job.scope.installation_type)
            _field_row("Area context", job.scope.area_context)
            _field_row("Net areas", _format_net_areas(job.scope.net_areas))
            _field_row("Units", job.scope.unit_count)
            _field_row("Urgency", job.scope.urgency)
            _field_row("Budget sensitivity", job.scope.budget_sensitivity)
            _field_row("Technical constraints", job.scope.technical_constraints)
            _field_row("Building constraints", job.scope.building_constraints)
            _field_row("Recommendation", job.recommendation_rationale)

        with ui.card().classes("w-full"):
            ui.label("Evidence").classes("text-sm font-semibold")
            _field_row("Attachment count", job.evidence.attachment_count)
            _field_row("Has photos", job.evidence.has_photos)
            _field_row("Has video", job.evidence.has_video)
            _field_row("Has audio", job.evidence.has_audio)
            _field_row("Has documents", job.evidence.has_documents)
            _field_row(
                "Attachments",
                [
                    attachment.name or attachment.source or attachment.kind.value
                    for attachment in job.evidence.attachments
                ],
            )
            _field_row("Evidence notes", job.evidence.notes)

        with ui.card().classes("w-full"):
            ui.label("Quote history").classes("text-sm font-semibold")
            if not job.quotes:
                ui.label("No quotes yet").classes("text-sm text-gray-500")
            else:
                for quote in reversed(job.quotes):
                    with ui.row().classes("w-full justify-between items-start gap-2"):
                        with ui.column().classes("gap-0"):
                            ui.label(f"{quote.kind.value} [{quote.status.value}]").classes("text-sm font-medium")
                            ui.label(quote.created_at.isoformat(timespec="seconds")).classes("text-xs text-gray-500")
                            if quote.rationale:
                                ui.label(quote.rationale).classes("text-xs text-gray-600")
                            if quote.notes:
                                ui.label(quote.notes).classes("text-xs text-gray-600")
                        ui.label(f"ARS {_format_value(quote.amount_ars)}").classes("text-sm font-semibold")
            current_quote = latest_quote(job)
            if current_quote is not None:
                ui.separator().classes("my-2")
                _field_row("Latest amount", current_quote.amount_ars)

        with ui.card().classes("w-full"):
            ui.label("Scheduling").classes("text-sm font-semibold")
            if not job.schedule_requests and not job.appointments:
                ui.label("No scheduling activity yet").classes("text-sm text-gray-500")
            for request in reversed(job.schedule_requests):
                with ui.column().classes("gap-0 mb-2"):
                    ui.label(f"Request: {request.requested_window or '-'}").classes("text-sm font-medium")
                    ui.label(request.reason or "-").classes("text-xs text-gray-600")
            for appointment in reversed(job.appointments):
                with ui.column().classes("gap-0 mb-2"):
                    ui.label(f"Appointment [{appointment.status.value}]").classes("text-sm font-medium")
                    ui.label(appointment.scheduled_for or "-").classes("text-xs text-gray-600")
                    if appointment.notes:
                        ui.label(appointment.notes).classes("text-xs text-gray-600")
            current_appointment = latest_appointment(job)
            if current_appointment is not None:
                ui.separator().classes("my-2")
                _field_row("Latest appointment", current_appointment.scheduled_for)

        with ui.card().classes("w-full"):
            ui.label("Escalations and closure").classes("text-sm font-semibold")
            _field_row("Escalated", job.escalated)
            _field_row("Thread flags", [flag.value for flag in thread.escalation_flags])
            _field_row("Objections", job.objections)
            _field_row("Negotiation notes", job.negotiation_notes)
            _field_row("Closure reason", job.closure_reason)

    @ui.refreshable
    def show_trace_panel() -> None:
        thread = _thread_snapshot(current_phone[0])
        if thread is None:
            ui.label("Workflow trace will appear here.").classes("text-sm text-gray-400")
            return
        events = filtered_events(
            thread=thread,
            selected_job_id=selected_job_id[0],
            include_thread_wide=include_thread_wide[0],
            trace_group=trace_group[0],
        )
        if not events:
            ui.label("No events for the current filter.").classes("text-sm text-gray-400")
            return
        for event in reversed(events):
            with ui.card().classes("w-full border border-gray-200"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label(event.kind).classes("text-sm font-semibold")
                    ui.label(event.occurred_at.isoformat(timespec="seconds")).classes("text-xs text-gray-500")
                ui.label(event.summary).classes("text-sm text-gray-700")
                payload = event.payload or {}
                if payload:
                    for key, value in payload.items():
                        if value in (None, "", [], {}):
                            continue
                        _field_row(key.replace("_", " "), value)

    async def send_message() -> None:
        text = msg_input.value.strip()
        phone = current_phone[0]
        if not text or not phone:
            return

        _log_ui_step(f"send start phone={phone} text={text!r}")
        msg_input.value = ""
        send_btn.disable()
        spinner.visible = True
        pending_user_message[0] = text
        show_chat.refresh()
        _scroll_to_bottom()
        try:
            _log_ui_step("before agent.handle_incoming_message")
            result = agent.handle_incoming_message(
                IncomingMessage(phone=phone, text=text),
            )
            _log_ui_step("after agent.handle_incoming_message")

            selected_job_id[0] = result.thread.active_job_id
            latest_route = next(
                (
                    event.payload.get("route")
                    for event in reversed(result.thread.events)
                    if event.kind == "route_selected" and isinstance(event.payload, dict)
                ),
                None,
            )
            latest_intent = next(
                (
                    event.payload.get("intent")
                    for event in reversed(result.thread.events)
                    if event.kind == "intent_detected" and isinstance(event.payload, dict)
                ),
                None,
            )
            latest_trace_summary[0] = (
                f"Last intent {latest_intent} routed to {latest_route}"
                if latest_route or latest_intent
                else None
            )
            _log_ui_step("before _refresh_all")
            _refresh_all()
            _log_ui_step("after _refresh_all")
        except Exception as exc:
            _log_ui_error("send_message", exc)
            ui.notify(f"Send failed: {exc}", type="negative")
            raise
        finally:
            _log_ui_step("send finally")
            pending_user_message[0] = None
            spinner.visible = False
            send_btn.enable()

    with ui.element("div").style(
        "display:flex; width:100vw; height:100vh; overflow:hidden; background:#f8fafc;"
    ):
        with ui.element("div").style(
            "width:260px; flex-shrink:0; border-right:1px solid #e5e7eb; padding:12px;"
            " display:flex; flex-direction:column; gap:8px; overflow-y:auto; background:white;"
        ):
            ui.label("Threads").classes("text-lg font-semibold")
            ui.button("New thread", on_click=lambda: dialog.open()).classes("w-full")
            show_sidebar()

        with ui.element("div").style(
            "flex:1; min-width:0; display:flex; flex-direction:column; gap:10px; padding:16px;"
        ):
            with ui.card().classes("w-full"):
                show_thread_header()

            with ui.element("div").style(
                "flex:1; min-height:0; display:flex; flex-direction:column; background:white;"
                " border:1px solid #e5e7eb; border-radius:12px; overflow:hidden;"
            ):
                with ui.element("div").style(
                    "flex:1; min-height:0; overflow-y:auto; padding:16px; display:flex; flex-direction:column; gap:12px;"
                ) as _chat_div:
                    show_chat()
                chat_div[0] = _chat_div

                spinner = ui.spinner(size="lg").classes("mx-auto my-2")
                spinner.visible = False

                with ui.element("div").style(
                    "display:flex; gap:8px; align-items:center; padding:12px; border-top:1px solid #e5e7eb;"
                ):
                    msg_input = ui.input(placeholder="Type an inbound WhatsApp message...").style("flex:1;")
                    msg_input.on("keydown.enter", send_message)
                    send_btn = ui.button("Send", on_click=send_message)

        with ui.element("div").style(
            "width:440px; flex-shrink:0; border-left:1px solid #e5e7eb; padding:12px;"
            " display:flex; flex-direction:column; gap:10px; overflow-y:auto; background:#fcfcfd;"
        ):
            ui.label("Workflow console").classes("text-lg font-semibold")
            job_select[0] = ui.select(options={}, label="Active job").classes("w-full")
            job_select[0].on_value_change(lambda event: select_job(event.value))

            show_job_panel()

            with ui.expansion("Technical trace", value=True).classes("w-full"):
                with ui.row().classes("w-full items-center gap-2"):
                    ui.select(
                        options={
                            "all": "All",
                            "intent": "Intent",
                            "extraction": "Extraction",
                            "quote": "Quote",
                            "scheduling": "Scheduling",
                            "escalation": "Escalation",
                            "closure": "Closure",
                        },
                        value=trace_group[0],
                        label="Trace filter",
                        on_change=lambda event: (
                            trace_group.__setitem__(0, event.value),
                            show_trace_panel.refresh(),
                        ),
                    ).classes("flex-1")
                    ui.switch(
                        "Include thread-wide",
                        value=include_thread_wide[0],
                        on_change=lambda event: (
                            include_thread_wide.__setitem__(0, bool(event.value)),
                            show_trace_panel.refresh(),
                        ),
                    )
                show_trace_panel()

    with ui.dialog() as dialog, ui.card():
        ui.label("New thread").classes("text-lg font-semibold")
        phone_input = ui.input(label="Phone", placeholder="+5493411234567").classes("w-full")
        name_input = ui.input(label="Display name (optional)").classes("w-full")

        def confirm_new() -> None:
            phone = phone_input.value.strip()
            display_name = name_input.value.strip()
            if not phone:
                ui.notify("Please enter a phone number", type="warning")
                return
            dialog.close()
            phone_input.value = ""
            name_input.value = ""
            current_phone[0] = phone
            latest_trace_summary[0] = None
            if display_name:
                thread = storage.load_thread(phone) or ContactThreadState(phone=phone, display_name=display_name)
                thread.display_name = display_name
                storage.save_thread(thread)
            selected_job_id[0] = None
            _refresh_all()

        phone_input.on("keydown.enter", confirm_new)
        with ui.row().classes("justify-end w-full"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Open", on_click=confirm_new).props("color=primary")

    _select_default_phone()
    _refresh_all()


if __name__ == "__main__":
    ui.run(title="Manager AI Workflow Console", port=8080, reload=False)
