from __future__ import annotations

from manager_ai.models.conversation import JobState, QuoteKind, QuoteStatus, QuoteVersion
from manager_ai.ports.quote_drafting import QuoteDraftingPort


class MockQuoteDraftingAdapter(QuoteDraftingPort):
    def draft_quote(self, job: JobState, rough: bool) -> QuoteVersion:
        complete_areas = job.scope.complete_net_areas()
        if complete_areas:
            area = sum(
                (net_area.width_meters or 0.0) * (net_area.height_meters or 0.0)
                for net_area in complete_areas
            )
        else:
            area = 2.0 * 1.2
        units = job.scope.unit_count or 1
        amount = int(round(area * 42000 * units, -3))
        kind = QuoteKind.ROUGH if rough else QuoteKind.FINAL
        rationale = (
            "Estimacion mock basada en medidas y cantidad de unidades."
            if rough
            else "Cotizacion mock lista para revision humana."
        )
        return QuoteVersion(
            kind=kind,
            status=QuoteStatus.SENT,
            amount_ars=max(amount, 75000),
            rationale=rationale,
            notes="mock_quote",
        )
