from __future__ import annotations

import unicodedata

from manager_ai.adapters.qualification.catalog import (
    CatalogBullet,
    DEFAULT_SERVICE_CATALOG_PATH,
    ServiceCatalog,
    load_service_catalog,
    normalized_text,
    searchable_terms,
)
from manager_ai.models.conversation import ContactThreadState, ConversationMessage, JobState
from manager_ai.ports.qualification import (
    QualifiedServiceItem,
    QualificationDecision,
    QualificationPort,
    QualificationScopeStatus,
    ServiceQualification,
)


def _normalized_text(text: str) -> str:
    without_accents = unicodedata.normalize("NFKD", text)
    ascii_text = without_accents.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.lower().split())


def _has_existing_service_evidence(job: JobState) -> bool:
    return bool(job.scope.service_intent or job.scope.installation_type)


def _matched_items(
    text: str,
    entries: list[CatalogBullet],
    scope_status: QualificationScopeStatus,
) -> list[QualifiedServiceItem]:
    matches: list[QualifiedServiceItem] = []
    text_terms = searchable_terms(text)
    for entry in entries:
        matched_text = _matched_text(text, text_terms, entry)
        if matched_text is None:
            continue
        matches.append(
            QualifiedServiceItem(
                raw_text=matched_text,
                normalized_service=_service_slug(entry.label),
                scope_status=scope_status,
                reply_label=entry.label,
                rejection_phrase=entry.response,
            )
        )
    return matches


def _matched_text(
    text: str,
    text_terms: set[str],
    entry: CatalogBullet,
) -> str | None:
    for alias in entry.aliases:
        normalized_alias = normalized_text(alias)
        if len(normalized_alias) >= 4 and normalized_alias in text:
            return alias
    shared_terms = text_terms & searchable_terms(entry.text)
    if shared_terms:
        return sorted(shared_terms)[0]
    return None


def _service_slug(label: str) -> str:
    slug = "_".join(sorted(searchable_terms(label)))
    return slug or normalized_text(label).replace(" ", "_")


class HeuristicQualificationAdapter:
    def __init__(self, catalog: ServiceCatalog | None = None) -> None:
        self._catalog = catalog or load_service_catalog(DEFAULT_SERVICE_CATALOG_PATH)

    def qualify(
        self,
        thread: ContactThreadState,
        job: JobState,
        message: ConversationMessage,
    ) -> ServiceQualification:
        text = _normalized_text(message.content)
        service_items = _matched_items(
            text,
            self._catalog.offered,
            QualificationScopeStatus.IN_SCOPE,
        )
        unsupported_items = [
            *_matched_items(
                text,
                self._catalog.adjacent_unsupported,
                QualificationScopeStatus.ADJACENT_UNSUPPORTED,
            ),
            *_matched_items(
                text,
                self._catalog.clearly_not_service,
                QualificationScopeStatus.ADJACENT_UNSUPPORTED,
            ),
        ]
        unknown_items = _matched_items(
            text,
            self._catalog.ambiguous,
            QualificationScopeStatus.UNKNOWN,
        )

        if service_items or _has_existing_service_evidence(job):
            reason = (
                "Message includes catalog service items."
                if service_items
                else "Existing job already has service-fit evidence."
            )
            return ServiceQualification(
                decision=QualificationDecision.SERVICE,
                reason=reason,
                service_items=service_items,
                unsupported_items=unsupported_items,
                unknown_items=unknown_items,
            )

        if unsupported_items:
            return ServiceQualification(
                decision=QualificationDecision.NOT_SERVICE,
                reason="Message only mentions catalog services En Red does not offer.",
                unsupported_items=unsupported_items,
                unknown_items=unknown_items,
                reply=_unsupported_only_reply(unsupported_items),
            )

        if unknown_items:
            return ServiceQualification(
                decision=QualificationDecision.UNCLEAR,
                reason="Message includes ambiguous catalog terms.",
                unknown_items=unknown_items,
            )

        return ServiceQualification(
            decision=QualificationDecision.UNCLEAR,
            reason="Message does not contain enough service-fit evidence.",
        )


def _unsupported_only_reply(items: list[QualifiedServiceItem]) -> str | None:
    phrases = [item.rejection_phrase for item in items if item.rejection_phrase]
    if phrases:
        return " ".join(dict.fromkeys(phrases))
    labels = [item.reply_label or item.normalized_service for item in items]
    if not labels:
        return None
    return f"No trabajamos {', '.join(dict.fromkeys(labels))}."
