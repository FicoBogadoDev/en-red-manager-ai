import pytest
from pydantic import ValidationError

from manager_ai.models.extraction import ExtractedClientData, ExtractedNetArea


class TestExtractedClientData:
    def test_all_fields_populated(self) -> None:
        data = ExtractedClientData(
            name="Federico",
            street="Tucumán 1464",
            city="Rosario",
            floor_or_apartment="6B",
            installation_type="balcony",
            net_areas=[ExtractedNetArea(label="Balcon", width_meters=4.0, height_meters=1.2)],
            urgency="urgente",
        )
        dumped = data.model_dump()
        assert set(dumped.keys()) == {
            "name", "street", "city", "floor_or_apartment",
            "installation_type", "net_areas", "urgency",
        }
        assert dumped["name"] == "Federico"
        assert dumped["net_areas"][0]["width_meters"] == 4.0

    def test_none_values_included_in_dump(self) -> None:
        data = ExtractedClientData()
        dumped = data.model_dump()
        assert len(dumped) == 7
        assert dumped["net_areas"] == []
        assert all(v is None for k, v in dumped.items() if k != "net_areas")

    def test_installation_type_literal_rejects_invalid(self) -> None:
        with pytest.raises(ValidationError):
            ExtractedClientData(installation_type="basement")
