import json
import re

from manager_ai.models.client import Address, ClientChart, Dimensions, InstallationType
from manager_ai.models.conversation import ConversationStage, ConversationState, Message
from manager_ai.ports.llm import LLMPort


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

    width = extracted.get("width_meters")
    height = extracted.get("height_meters")
    if width or height:
        existing = chart.dimensions or Dimensions()
        updates["dimensions"] = existing.model_copy(
            update={
                k: v
                for k, v in {"width_meters": width, "height_meters": height}.items()
                if v is not None
            }
        )

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
        chart.dimensions is not None,
        chart.dimensions.width_meters is not None if chart.dimensions else False,
        chart.dimensions.height_meters is not None if chart.dimensions else False,
    ])


def run_collection(
    state: ConversationState,
    user_message: str,
    llm: LLMPort,
    system_prompt: str,
) -> tuple[ConversationState, str]:
    """
    Run one data-collection turn.

    Returns the updated state and the assistant reply.
    """
    updated_history = state.history + [Message(role="user", content=user_message)]
    messages_for_llm = [Message(role="system", content=system_prompt)] + updated_history
    llm_response = llm.complete(messages_for_llm)

    # Extract and validate structured data
    extracted = extract_json_block(llm_response) or {}
    updated_chart = merge_extracted_data(state.client, extracted)

    # Sanity-check dimensions
    dims = updated_chart.dimensions
    if dims and (
        not is_plausible_dimension(dims.width_meters)
        or not is_plausible_dimension(dims.height_meters)
    ):
        # Reset the bad dimensions so the agent asks again
        updated_chart = updated_chart.model_copy(update={"dimensions": None})

    # Strip the JSON block from the reply before sending it to the client
    reply = re.sub(r"```json.*?```", "", llm_response, flags=re.DOTALL).strip()

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
