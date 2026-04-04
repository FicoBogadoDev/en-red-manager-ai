import pytest

pytest.skip("Legacy collection tests replaced by workflow tests.", allow_module_level=True)

from manager_ai.models.client import Address, ClientChart, Dimensions, InstallationType
from manager_ai.models.conversation import (
    ConversationStage,
    ConversationState,
    Message,
)
from manager_ai.models.extraction import ExtractedClientData
from manager_ai.services.collection import (
    _dict_to_extracted,
    extract_json_block,
    merge_extracted_data,
    required_fields_complete,
    run_collection,
)


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class StubLLM:
    """LLM stub that returns a preset response and tracks call count."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.call_count = 0

    def complete(self, messages: list[Message]) -> str:
        self.call_count += 1
        return self._response


class StubExtractor:
    """Extractor stub that returns preset reply and data."""

    def __init__(self, reply: str, data: ExtractedClientData) -> None:
        self._reply = reply
        self._data = data
        self.call_count = 0

    def collect(self, messages: list[Message]) -> tuple[str, ExtractedClientData]:
        self.call_count += 1
        return self._reply, self._data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PHONE = "+5493411234567"


def make_state(phone: str = PHONE) -> ConversationState:
    return ConversationState(
        phone=phone,
        stage=ConversationStage.COLLECTING,
        client=ClientChart(phone=phone),
    )


def make_complete_chart(phone: str = PHONE) -> ClientChart:
    return ClientChart(
        phone=phone,
        name="Federico Bogado",
        address=Address(street="Tucumán 1464", city="Rosario"),
        installation_type=InstallationType.BALCONY,
        dimensions=Dimensions(width_meters=4.0, height_meters=1.2),
    )


# ---------------------------------------------------------------------------
# TestExtractJsonBlock
# ---------------------------------------------------------------------------

class TestExtractJsonBlock:
    def test_valid_json_block(self) -> None:
        text = 'Hola!\n```json\n{"name": "Ana"}\n```\nBye.'
        result = extract_json_block(text)
        assert result == {"name": "Ana"}

    def test_no_json_block_returns_none(self) -> None:
        result = extract_json_block("No hay bloque aquí.")
        assert result is None

    def test_malformed_json_returns_none(self) -> None:
        text = '```json\n{invalid json}\n```'
        result = extract_json_block(text)
        assert result is None


# ---------------------------------------------------------------------------
# TestDictToExtracted
# ---------------------------------------------------------------------------

class TestDictToExtracted:
    def test_all_keys_mapped(self) -> None:
        raw = {
            "name": "Carlos",
            "street": "San Martín 100",
            "city": "Rosario",
            "floor_or_apartment": "3B",
            "installation_type": "balcony",
            "width_meters": 3.0,
            "height_meters": 1.5,
            "urgency": "urgente",
        }
        result = _dict_to_extracted(raw)
        assert result.name == "Carlos"
        assert result.street == "San Martín 100"
        assert result.city == "Rosario"
        assert result.floor_or_apartment == "3B"
        assert result.installation_type == "balcony"
        assert result.width_meters == 3.0
        assert result.height_meters == 1.5
        assert result.urgency == "urgente"

    def test_missing_keys_become_none(self) -> None:
        result = _dict_to_extracted({})
        assert result.name is None
        assert result.street is None
        assert result.city is None
        assert result.floor_or_apartment is None
        assert result.installation_type is None
        assert result.width_meters is None
        assert result.height_meters is None
        assert result.urgency is None


# ---------------------------------------------------------------------------
# TestMergeExtractedData
# ---------------------------------------------------------------------------

class TestMergeExtractedData:
    def test_name_only(self) -> None:
        chart = ClientChart(phone=PHONE)
        result = merge_extracted_data(chart, {"name": "María"})
        assert result.name == "María"

    def test_address_fields_merged_individually(self) -> None:
        chart = ClientChart(
            phone=PHONE,
            address=Address(street="Corrientes 1000", city=None),
        )
        result = merge_extracted_data(chart, {"city": "Rosario"})
        assert result.address.street == "Corrientes 1000"
        assert result.address.city == "Rosario"

    def test_installation_type_string_mapped_to_enum(self) -> None:
        chart = ClientChart(phone=PHONE)
        result = merge_extracted_data(chart, {"installation_type": "roof"})
        assert result.installation_type == InstallationType.ROOF

    def test_dimensions_partial_merge(self) -> None:
        chart = ClientChart(
            phone=PHONE,
            dimensions=Dimensions(width_meters=3.0, height_meters=None),
        )
        result = merge_extracted_data(chart, {"height_meters": 1.5})
        assert result.dimensions.width_meters == 3.0
        assert result.dimensions.height_meters == 1.5

    def test_null_does_not_overwrite_existing_value(self) -> None:
        chart = ClientChart(phone=PHONE, name="Pedro")
        result = merge_extracted_data(chart, {"name": None})
        assert result.name == "Pedro"


# ---------------------------------------------------------------------------
# TestRequiredFieldsComplete
# ---------------------------------------------------------------------------

class TestRequiredFieldsComplete:
    def test_true_when_all_required_fields_present(self) -> None:
        chart = make_complete_chart()
        assert required_fields_complete(chart) is True

    def test_false_when_name_missing(self) -> None:
        chart = make_complete_chart()
        chart = chart.model_copy(update={"name": None})
        assert required_fields_complete(chart) is False

    def test_false_when_street_missing(self) -> None:
        chart = make_complete_chart()
        chart = chart.model_copy(
            update={"address": chart.address.model_copy(update={"street": None})}
        )
        assert required_fields_complete(chart) is False

    def test_false_when_city_missing(self) -> None:
        chart = make_complete_chart()
        chart = chart.model_copy(
            update={"address": chart.address.model_copy(update={"city": None})}
        )
        assert required_fields_complete(chart) is False

    def test_false_when_installation_type_missing(self) -> None:
        chart = make_complete_chart()
        chart = chart.model_copy(update={"installation_type": None})
        assert required_fields_complete(chart) is False

    def test_false_when_dimensions_missing(self) -> None:
        chart = make_complete_chart()
        chart = chart.model_copy(update={"dimensions": None})
        assert required_fields_complete(chart) is False

    def test_false_when_width_missing(self) -> None:
        chart = make_complete_chart()
        chart = chart.model_copy(
            update={"dimensions": Dimensions(width_meters=None, height_meters=1.2)}
        )
        assert required_fields_complete(chart) is False

    def test_false_when_height_missing(self) -> None:
        chart = make_complete_chart()
        chart = chart.model_copy(
            update={"dimensions": Dimensions(width_meters=4.0, height_meters=None)}
        )
        assert required_fields_complete(chart) is False


# ---------------------------------------------------------------------------
# TestRunCollection
# ---------------------------------------------------------------------------

COLLECTION_PROMPT = "<system>"

_FULL_JSON_REPLY = (
    'Anotado, gracias.\n'
    '```json\n'
    '{"name": "Federico Bogado", "street": "Tucumán 1464", "city": "Rosario",'
    ' "floor_or_apartment": null, "installation_type": "balcony",'
    ' "width_meters": 4.0, "height_meters": 1.2, "urgency": null}\n'
    '```'
)

_PARTIAL_JSON_REPLY = (
    '¿Cuál es tu nombre?\n'
    '```json\n'
    '{"name": "Federico", "street": null, "city": null,'
    ' "floor_or_apartment": null, "installation_type": null,'
    ' "width_meters": null, "height_meters": null, "urgency": null}\n'
    '```'
)


class TestRunCollection:
    def test_regex_path_updates_chart(self) -> None:
        llm = StubLLM(_FULL_JSON_REPLY)
        state = make_state()

        new_state, _ = run_collection(
            state=state,
            user_message="Me llamo Federico, vivo en Tucumán 1464, Rosario.",
            llm=llm,
            system_prompt=COLLECTION_PROMPT,
        )

        assert new_state.client.name == "Federico Bogado"
        assert new_state.client.address.city == "Rosario"
        assert new_state.client.installation_type == InstallationType.BALCONY
        assert new_state.client.dimensions.width_meters == 4.0

    def test_extractor_path_calls_collect_not_llm(self) -> None:
        llm = StubLLM("should not be called")
        extracted = ExtractedClientData(name="Ana")
        extractor = StubExtractor(reply="Perfecto, anotado.", data=extracted)
        state = make_state()

        run_collection(
            state=state,
            user_message="Hola",
            llm=llm,
            system_prompt=COLLECTION_PROMPT,
            extractor=extractor,
        )

        assert extractor.call_count == 1
        assert llm.call_count == 0

    def test_invalid_dimension_resets_dimensions(self) -> None:
        bad_json = (
            '```json\n'
            '{"name": null, "street": null, "city": null,'
            ' "floor_or_apartment": null, "installation_type": null,'
            ' "width_meters": 400.0, "height_meters": 1.2, "urgency": null}\n'
            '```'
        )
        llm = StubLLM(bad_json)
        state = make_state()

        new_state, _ = run_collection(
            state=state,
            user_message="El balcón mide 400 metros.",
            llm=llm,
            system_prompt=COLLECTION_PROMPT,
        )

        assert new_state.client.dimensions is None

    def test_all_fields_complete_sets_handoff_pending(self) -> None:
        llm = StubLLM(_FULL_JSON_REPLY)
        state = make_state()

        new_state, _ = run_collection(
            state=state,
            user_message="Todo listo.",
            llm=llm,
            system_prompt=COLLECTION_PROMPT,
        )

        assert new_state.stage == ConversationStage.HANDOFF_PENDING

    def test_incomplete_fields_stays_collecting(self) -> None:
        llm = StubLLM(_PARTIAL_JSON_REPLY)
        state = make_state()

        new_state, _ = run_collection(
            state=state,
            user_message="Me llamo Federico.",
            llm=llm,
            system_prompt=COLLECTION_PROMPT,
        )

        assert new_state.stage == ConversationStage.COLLECTING

    def test_json_block_stripped_from_reply(self) -> None:
        llm = StubLLM(_PARTIAL_JSON_REPLY)
        state = make_state()

        _, reply = run_collection(
            state=state,
            user_message="Hola",
            llm=llm,
            system_prompt=COLLECTION_PROMPT,
        )

        assert "```json" not in reply
        assert "```" not in reply
