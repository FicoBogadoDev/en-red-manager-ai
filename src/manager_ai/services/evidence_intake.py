from __future__ import annotations

from manager_ai.models.conversation import JobState, JobStatus

_REQUIRED_FIELDS = (
    "contact_name",
    "address",
    "city",
    "installation_type",
    "net_areas",
)


def compute_missing_fields(job: JobState) -> list[str]:
    missing: list[str] = []
    if not job.contact_name:
        missing.append("contact_name")
    if not job.scope.address:
        missing.append("address")
    if not job.scope.city:
        missing.append("city")
    if not job.scope.installation_type:
        missing.append("installation_type")
    if not job.scope.has_complete_net_area():
        missing.append("net_areas")
    return missing


def refresh_evidence_status(job: JobState) -> JobState:
    updated = job.model_copy(deep=True)
    updated.missing_fields = compute_missing_fields(updated)
    if updated.status not in {JobStatus.DISQUALIFIED, JobStatus.CLOSED, JobStatus.COMPLETED}:
        updated.status = (
            JobStatus.AWAITING_EVIDENCE
            if updated.missing_fields
            else JobStatus.SCOPING
        )
    return updated


def next_question(job: JobState) -> str:
    prompts = {
        "contact_name": "Para arrancar bien, ¿me decís tu nombre?",
        "address": "¿En qué dirección sería la instalación?",
        "city": "¿En qué ciudad queda?",
        "installation_type": "¿Es para balcón, techo o escalera?",
        "net_areas": "¿Tenés una o mas medidas aproximadas de las areas a cubrir? Si querés pasamelas como ancho x alto para cada una.",
    }
    if not job.missing_fields:
        return "Ya tengo la base del caso. Lo dejo listo para revisión y presupuesto."
    return prompts[job.missing_fields[0]]
