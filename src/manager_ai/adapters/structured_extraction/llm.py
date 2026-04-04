from __future__ import annotations

import os

from pydantic import BaseModel, Field
from pydantic_ai import Agent as PydanticAgent

from manager_ai.adapters.llm._runner import run_coro_sync
from manager_ai.models.conversation import ContactThreadState, ConversationMessage, DimensionEstimate, JobState
from manager_ai.ports.structured_extraction import StructuredExtractionPort


class _StructuredJobUpdate(BaseModel):
    class NetAreaUpdate(BaseModel):
        label: str | None = Field(default=None)
        width_meters: float | None = Field(default=None)
        height_meters: float | None = Field(default=None)

    contact_name: str | None = Field(default=None)
    service_intent: str | None = Field(default=None)
    property_type: str | None = Field(default=None)
    address: str | None = Field(default=None)
    city: str | None = Field(default=None)
    installation_type: str | None = Field(default=None)
    area_context: str | None = Field(default=None)
    net_areas: list[NetAreaUpdate] = Field(default_factory=list)
    unit_count: int | None = Field(default=None)
    urgency: str | None = Field(default=None)
    budget_sensitivity: str | None = Field(default=None)
    technical_constraints: list[str] = Field(default_factory=list)
    building_constraints: list[str] = Field(default_factory=list)


class LLMStructuredExtractionAdapter(StructuredExtractionPort):
    def __init__(self, model: str, api_key_env: str) -> None:
        api_key = os.environ.get(api_key_env)
        if api_key:
            os.environ["ANTHROPIC_API_KEY"] = api_key
        self._model_id = f"anthropic:{model}"

    def extract(
        self,
        thread: ContactThreadState,
        job: JobState,
        message: ConversationMessage,
    ) -> JobState:
        agent: PydanticAgent[None, _StructuredJobUpdate] = PydanticAgent(
            model=self._model_id,
            output_type=_StructuredJobUpdate,
            instructions=(
                "Extraé datos estructurados del último mensaje del cliente para En Red Rosario. "
                "Solo devolvé datos explícitos o muy confiables. "
                "Si el mensaje parece ser solamente el nombre de la persona, cargalo en contact_name. "
                "installation_type debe ser balcony, roof o stairwell cuando corresponda. "
                "service_intent puede ser safety_net_installation si queda claro que busca redes de seguridad. "
                "Si menciona medidas, devolvelas en net_areas como una lista de areas con ancho y alto."
            ),
        )
        context = (
            f"Areas actuales={self._net_area_summary(job)}. "
            f"Trabajo actual: nombre={job.contact_name}, direccion={job.scope.address}, ciudad={job.scope.city}, "
            f"tipo={job.scope.installation_type}, "
            f"faltantes={', '.join(job.missing_fields) if job.missing_fields else 'ninguno'}.\n"
            f"Ultimo mensaje del cliente: {message.content}"
        )
        result = run_coro_sync(agent.run(context))
        update = result.output

        updated_job = job.model_copy(deep=True)
        if update.contact_name:
            updated_job.contact_name = update.contact_name
        if update.service_intent:
            updated_job.scope.service_intent = update.service_intent
        if update.property_type:
            updated_job.scope.property_type = update.property_type
        if update.address:
            updated_job.scope.address = update.address
        if update.city:
            updated_job.scope.city = update.city
        if update.installation_type:
            updated_job.scope.installation_type = update.installation_type
        if update.area_context:
            updated_job.scope.area_context = update.area_context
        if update.net_areas:
            updated_job.scope.replace_net_areas([
                DimensionEstimate(
                    label=area.label or f"Area {index}",
                    width_meters=area.width_meters,
                    height_meters=area.height_meters,
                )
                for index, area in enumerate(update.net_areas, start=1)
            ])
        if update.unit_count is not None:
            updated_job.scope.unit_count = update.unit_count
        if update.urgency:
            updated_job.scope.urgency = update.urgency
        if update.budget_sensitivity:
            updated_job.scope.budget_sensitivity = update.budget_sensitivity
        for item in update.technical_constraints:
            if item not in updated_job.scope.technical_constraints:
                updated_job.scope.technical_constraints.append(item)
        for item in update.building_constraints:
            if item not in updated_job.scope.building_constraints:
                updated_job.scope.building_constraints.append(item)

        updated_job.scope.ensure_area_labels()
        updated_job.updated_at = message.created_at
        return updated_job

    def _net_area_summary(self, job: JobState) -> str:
        if not job.scope.net_areas:
            return "ninguna"
        return ", ".join(
            f"{area.label or f'Area {index}'}={area.width_meters}x{area.height_meters}"
            for index, area in enumerate(job.scope.net_areas, start=1)
        )
