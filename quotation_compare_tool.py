# -*- coding: utf-8 -*-
"""quotation_compare_tool

Validated quote payloads -> deterministic hard gate -> ranked Top-3.
No ``from __future__ import annotations``: AgentScope inspects runtime annotations.
"""
import json
from typing import Any, Optional

from agentscope.message import TextBlock, ToolResultState
from agentscope.tool import ToolChunk

from app.application.quotation_parser import normalize_structured_quotation
from app.application.usecases.quotation_compare import QuotationCompareUseCase, SupplierQuoteInput
from app.domain.procurement.rfq import RFQ
from app.domain.supplier.ports.supplier_repository import SupplierRepository
from app.infrastructure.context import ProcurementContext
from app.infrastructure.eventbus import TradeEventBus


def build_quotation_compare_tool(
    supplier_repo: SupplierRepository,
    usecase: QuotationCompareUseCase,
    bus: TradeEventBus,
):
    async def quotation_compare_tool(
        product: str,
        quantity: int | str,
        quotes: list[dict[str, Any]],
        target_price: float | str | None = None,
        currency: str = "USD",
        material: Optional[list[str]] = None,
        specifications: Optional[dict[str, Any]] = None,
        required_certifications: Optional[list[str]] = None,
        max_lead_time_days: int | str | None = None,
        customization: Optional[list[str]] = None,
        destination: Optional[str] = None,
        preferred_incoterm: Optional[str] = None,
        top_k: int | str = 3,
    ) -> ToolChunk:
        """Compare structured supplier quotes and return a qualified shortlist.

        ``quotes`` must contain supplier_id plus normalized quote fields. Numeric
        scores are always recalculated by Python; do not pass or invent scores.
        """
        session_id = ProcurementContext.current_session_id()
        bus.publish(session_id, "tool.invoke", {"tool": "quotation_compare_tool", "quote_count": len(quotes)})
        bus.publish(
            session_id,
            "workflow.progress",
            {"stage": "shortlist", "message": "正在生成 Shortlist"},
        )
        try:
            quantity_i = int(quantity)
            top_k_i = int(top_k)
            target_f = None if target_price is None else float(target_price)
            lead_i = None if max_lead_time_days is None else int(max_lead_time_days)
            rfq = RFQ(
                request_id="RFQ-QUOTE-COMPARE",
                product=product,
                quantity=quantity_i,
                target_price=target_f,
                currency=currency,
                material=material or [],
                specifications=specifications or {},
                customization=customization or [],
                required_certifications=required_certifications or [],
                max_lead_time_days=lead_i,
                destination=destination,
                preferred_incoterm=preferred_incoterm,
            )

            supplier_ids = [str(row.get("supplier_id", "")).strip() for row in quotes]
            if any(not supplier_id for supplier_id in supplier_ids):
                raise ValueError("每条 quote 必须包含 supplier_id")
            suppliers = await supplier_repo.find_by_ids(supplier_ids)
            by_id = {supplier.supplier_id: supplier for supplier in suppliers}
            missing = [supplier_id for supplier_id in supplier_ids if supplier_id not in by_id]
            if missing:
                raise ValueError(f"unknown supplier_id: {', '.join(missing)}")

            items = []
            for index, row in enumerate(quotes, start=1):
                supplier_id = str(row["supplier_id"])
                extraction = normalize_structured_quotation(
                    quote_id=str(row.get("quote_id") or f"Q-{index:03d}"),
                    supplier_id=supplier_id,
                    quantity=row.get("quantity", quantity_i),
                    unit_price=row.get("unit_price"),
                    currency=row.get("currency", currency),
                    incoterm=row.get("incoterm"),
                    logo_fee_per_unit=row.get("logo_fee_per_unit"),
                    packaging_fee_per_unit=row.get("packaging_fee_per_unit"),
                    fixed_fee=row.get("fixed_fee"),
                    fixed_fee_description=row.get("fixed_fee_description"),
                    lead_time_days=row.get("lead_time_days"),
                    lead_time_min_days=row.get("lead_time_min_days"),
                    lead_time_max_days=row.get("lead_time_max_days"),
                    payment_terms=row.get("payment_terms"),
                    certifications_confirmed=row.get("certifications_confirmed"),
                    assume_missing_fees_zero=False,
                )
                items.append(SupplierQuoteInput(by_id[supplier_id], extraction.quotation))

            result = usecase.execute(rfq, items, top_k=top_k_i)
        except (TypeError, ValueError) as err:
            bus.publish(session_id, "tool.result", {"tool": "quotation_compare_tool", "error": str(err)})
            return ToolChunk(
                content=[TextBlock(type="text", text=f"[error] {err}")],
                state=ToolResultState.ERROR,
            )

        bus.publish(
            session_id,
            "tool.result",
            {
                "tool": "quotation_compare_tool",
                "qualified_supplier_count": result["qualified_supplier_count"],
                "shortlist": result["shortlist"],
                "disqualified_count": len(result["disqualified"]),
            },
        )
        return ToolChunk(
            content=[TextBlock(type="text", text=json.dumps(result, ensure_ascii=False))],
            state=ToolResultState.SUCCESS,
        )

    return quotation_compare_tool
