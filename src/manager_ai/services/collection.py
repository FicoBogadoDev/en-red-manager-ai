from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from manager_ai.models.client import Address, ClientChart, InstallationType, NetArea
from manager_ai.models.conversation import ConversationStage, ConversationState, Message
from manager_ai.models.extraction import ExtractedClientData
from manager_ai.ports.llm import LLMPort

if TYPE_CHECKING:
    from manager_ai.ports.extractor import ExtractorPort


_INSTALLATION_TYPE_MAP: dict[str, InstallationType] = {
    "balcony": InstallationType.BALCONY,
    "roof": InstallationType.ROOF,
    "stairwell": InstallationType.STAIRWELL,
}

_MIN_DIMENSION_METERS = 0.5
_MAX_DIMENSION_METERS = 50.0


def extract_json_block(text: str) -> dict | None:
    """Pull the first ```json ... ``` block out of the LLM response."""
    match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def is_plausible_dimension(value: float | None) -> bool:
    """Return True if the dimension is within a reasonable range for a net installation."""
    if value is None:
        return True
    return _MIN_DIMENSION_METERS <= value <= _MAX_DIMENSION_METERS


def merge_extracted_data(chart: ClientChart, extracted: dict) -> ClientChart:
    """Merge non-null LLM-extracted fields into the existing ClientChart."""
    updates: dict = {}

    if extracted.get("name"):
        updates["name"] = extracted["name"]

    address_updates: dict = {}
    if extracted.get("street"):
        address_updates["street"] = extracted["street"]
    if extracted.get("city"):
        address_updates["city"] = extracted["city"]
    if extracted.get("floor_or_apartment"):
        address_updates["floor_or_apartment"] = extracted["floor_or_apartment"]
    if address_updates:
        updates["address"] = chart.address.model_copy(update=address_updates)

    raw_type = extracted.get("installation_type")
    if raw_type and raw_type != "null":
        updates["installation_type"] = _INSTALLATION_TYPE_MAP.get(raw_type)

    raw_net_areas = extracted.get("net_areas") or []
    if raw_net_areas:
        updates["net_areas"] = [
            NetArea(
                label=area.get("label") or f"Area {index}",
                width_meters=area.get("width_meters"),
                height_meters=area.get("height_meters"),
            )
            for index, area in enumerate(raw_net_areas, start=1)
        ]

    if extracted.get("urgency"):
        updates["urgency"] = extracted["urgency"]

    return chart.model_copy(update=updates)


def required_fields_complete(chart: ClientChart) -> bool:
    """Return True when all mandatory fields are collected."""
    return all([
        chart.name,
        chart.address.street,
        chart.address.city,
        chart.installation_type is not None,
        any(
            area.width_meters is not None and area.height_meters is not None
            for area in chart.net_areas
        ),
    ])


def _dict_to_extracted(raw: dict) -> "ExtractedClientData":
    return ExtractedClientData(
        name=raw.get("name"),
        street=raw.get("street"),
        city=raw.get("city"),
        floor_or_apartment=raw.get("floor_or_apartment"),
        installation_type=raw.get("installation_type"),
        net_areas=raw.get("net_areas") or [],
        urgency=raw.get("urgency"),
    )


def run_collection(
    state: ConversationState,
    user_message: str,
    llm: LLMPort,
    system_prompt: str,
    extractor: "ExtractorPort | None" = None,
) -> tuple[ConversationState, str]:
    """
    Run one data-collection turn.

    Returns the updated state and the assistant reply.
    """
    updated_history = state.history + [Message(role="user", content=user_message)]

    if extractor is not None:
        messages_for_llm = [Message(role="system", content=system_prompt)] + updated_history
        reply, extracted_data = extractor.collect(messages_for_llm)
    else:
        llm_response = llm.complete(system_prompt, updated_history)
        raw = extract_json_block(llm_response) or {}
        extracted_data = _dict_to_extracted(raw)
        reply = re.sub(r"```json.*?```", "", llm_response, flags=re.DOTALL).strip()

    updated_chart = merge_extracted_data(state.client, extracted_data.model_dump())

    # Sanity-check areas
    if any(
        not is_plausible_dimension(area.width_meters)
        or not is_plausible_dimension(area.height_meters)
        for area in updated_chart.net_areas
    ):
        updated_chart = updated_chart.model_copy(update={"net_areas": []})

    updated_history = updated_history + [Message(role="assistant", content=reply)]

    new_stage = (
        ConversationStage.HANDOFF_PENDING
        if required_fields_complete(updated_chart)
        else ConversationStage.COLLECTING
    )

    new_state = state.model_copy(
        update={
            "stage": new_stage,
            "client": updated_chart,
            "history": updated_history,
        }
    )
    return new_state, reply
