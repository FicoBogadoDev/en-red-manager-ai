from __future__ import annotations

import re

from manager_ai.models.conversation import (
    AttachmentKind,
    ContactThreadState,
    ConversationMessage,
    DimensionEstimate,
    JobState,
)
from manager_ai.ports.structured_extraction import StructuredExtractionPort

_DIMENSION_PAIR_RE = re.compile(
    r"(?P<width>\d+(?:[.,]\d+)?)\s*(?:x|por)\s*(?P<height>\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
_SINGLE_DIMENSION_RE = re.compile(
    r"(?P<label>ancho|alto)\s*(?:de|:)?\s*(?P<value>\d+(?:[.,]\d+)?)",
    re.IGNORECASE,
)
_ADDRESS_RE = re.compile(
    r"([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ. ]{4,}\s\d{1,5})"
)
_ADDRESS_WITH_PREP_RE = re.compile(
    r"\ben\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ. ]{2,}\s\d{1,5})"
)
_NAME_RE = re.compile(
    r"(?:me llamo|soy)\s+([A-Za-zÁÉÍÓÚÑáéíóúñ ]{2,}?)(?:,| y |$)",
    re.IGNORECASE,
)
_UNIT_COUNT_RE = re.compile(r"(\d+)\s+(?:unidades|departamentos|deptos|balcones)", re.IGNORECASE)
_MONEY_RE = re.compile(r"\$?\s*(\d{4,9})")


def _clean_text_value(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .,:;")


def _float(value: str) -> float:
    return float(value.replace(",", "."))


class HeuristicStructuredExtractionAdapter(StructuredExtractionPort):
    def extract(
        self,
        thread: ContactThreadState,
        job: JobState,
        message: ConversationMessage,
    ) -> JobState:
        updated_job = job.model_copy(deep=True)
        text = message.content
        lower_text = text.lower()

        name_match = _NAME_RE.search(text)
        if name_match and updated_job.contact_name is None:
            updated_job.contact_name = _clean_text_value(name_match.group(1)).title()

        address_match = _ADDRESS_WITH_PREP_RE.search(text) or _ADDRESS_RE.search(text)
        if address_match:
            updated_job.scope.address = _clean_text_value(address_match.group(1))

        if "rosario" in lower_text:
            updated_job.scope.city = "Rosario"
        elif "funes" in lower_text:
            updated_job.scope.city = "Funes"
        elif "rovira" in lower_text:
            updated_job.scope.city = "Roldan"

        if "balc" in lower_text:
            updated_job.scope.installation_type = "balcony"
            updated_job.scope.area_context = "balcony"
        elif "techo" in lower_text or "terraza" in lower_text:
            updated_job.scope.installation_type = "roof"
            updated_job.scope.area_context = "roof"
        elif "escalera" in lower_text:
            updated_job.scope.installation_type = "stairwell"
            updated_job.scope.area_context = "stairwell"

        dims_matches = list(_DIMENSION_PAIR_RE.finditer(lower_text))
        if len(dims_matches) > 1:
            updated_job.scope.replace_net_areas([
                DimensionEstimate(
                    label=f"Area {index}",
                    width_meters=_float(match.group("width")),
                    height_meters=_float(match.group("height")),
                )
                for index, match in enumerate(dims_matches, start=1)
            ])
        elif dims_matches:
            dims_match = dims_matches[0]
            width = _float(dims_match.group("width"))
            height = _float(dims_match.group("height"))
            if not updated_job.scope.net_areas:
                updated_job.scope.net_areas.append(
                    DimensionEstimate(label="Area 1", width_meters=width, height_meters=height)
                )
            elif all(
                area.width_meters != width or area.height_meters != height
                for area in updated_job.scope.net_areas
            ):
                updated_job.scope.net_areas.append(
                    DimensionEstimate(
                        label=f"Area {len(updated_job.scope.net_areas) + 1}",
                        width_meters=width,
                        height_meters=height,
                    )
                )
        else:
            for match in _SINGLE_DIMENSION_RE.finditer(lower_text):
                value = _float(match.group("value"))
                if not updated_job.scope.net_areas:
                    updated_job.scope.net_areas.append(DimensionEstimate(label="Area 1"))
                primary_area = updated_job.scope.net_areas[0]
                if match.group("label").lower() == "ancho":
                    primary_area.width_meters = value
                else:
                    primary_area.height_meters = value

        updated_job.scope.ensure_area_labels()

        unit_count_match = _UNIT_COUNT_RE.search(lower_text)
        if unit_count_match:
            updated_job.scope.unit_count = int(unit_count_match.group(1))

        if "urgente" in lower_text or "cuanto antes" in lower_text:
            updated_job.scope.urgency = "urgent"
        elif "esta semana" in lower_text or "esta semana" in lower_text:
            updated_job.scope.urgency = "this_week"
        elif "sin apuro" in lower_text or "tranqui" in lower_text:
            updated_job.scope.urgency = "flexible"

        if any(token in lower_text for token in ("consorcio", "reglamento", "administración", "administracion")):
            if "consorcio" not in updated_job.scope.building_constraints:
                updated_job.scope.building_constraints.append("consorcio")
        if any(token in lower_text for token in ("sin perforar", "no perforar", "medianera", "técnico", "tecnico")):
            note = "restriccion_tecnica"
            if note not in updated_job.scope.technical_constraints:
                updated_job.scope.technical_constraints.append(note)

        if any(token in lower_text for token in ("economico", "económico", "barato", "presupuesto ajustado")):
            updated_job.scope.budget_sensitivity = "high"

        for attachment in message.attachments:
            updated_job.evidence.attachments.append(attachment)
            if attachment.kind == AttachmentKind.IMAGE:
                updated_job.evidence.has_photos = True
            elif attachment.kind == AttachmentKind.VIDEO:
                updated_job.evidence.has_video = True
            elif attachment.kind == AttachmentKind.AUDIO:
                updated_job.evidence.has_audio = True
            elif attachment.kind == AttachmentKind.DOCUMENT:
                updated_job.evidence.has_documents = True
        updated_job.evidence.attachment_count = len(updated_job.evidence.attachments)

        money_match = _MONEY_RE.search(lower_text.replace(".", ""))
        if money_match and any(token in lower_text for token in ("presupuesto", "precio", "sale", "costo")):
            updated_job.negotiation_notes.append(f"precio_mencionado:{money_match.group(1)}")

        if updated_job.scope.service_intent is None and any(
            token in lower_text for token in ("red", "proteccion", "protección", "seguridad", "gato", "chico", "mascota")
        ):
            updated_job.scope.service_intent = "safety_net_installation"

        updated_job.updated_at = message.created_at
        return updated_job
