# -*- coding: utf-8 -*-
"""quotation_normalize_tool

LLM-extracted quotation slots -> validated Quotation -> deterministic effective cost.
No ``from __future__ import annotations``: AgentScope inspects runtime annotations.
"""
import json
from typing import Optional

from agentscope.message import TextBlock, ToolResultState
from agentscope.tool import ToolChunk

from app.application.quotation_parser import normalize_structured_quotation, parse_quotation_text
from app.infrastructure.context import ProcurementContext
from app.infrastructure.eventbus import TradeEventBus


def build_quotation_normalize_tool(bus: TradeEventBus):
    async def quotation_normalize_tool(
        quote_id: str,
        supplier_id: str,
        quantity: int | str,
        unit_price: float | str | None = None,
        currency: Optional[str] = None,
        incoterm: Optional[str] = None,
        logo_fee_per_unit: float | str | None = None,
        packaging_fee_per_unit: float | str | None = None,
        fixed_fee: float | str | None = None,
        fixed_fee_description: Optional[str] = None,
        lead_time_days: int | str | None = None,
        lead_time_min_days: int | str | None = None,
        lead_time_max_days: int | str | None = None,
        payment_terms: Optional[str] = None,
        certifications_confirmed: Optional[list[str]] = None,
        raw_text: Optional[str] = None,
    ) -> ToolChunk:
        """Normalize one supplier quotation into a deterministic schema.

        Prefer passing explicitly extracted fields. Use ``raw_text`` only as a
        conservative fallback; ambiguous/missing fields remain null.

        Args:
            quote_id (`str`): Stable quote identifier.
            supplier_id (`str`): Supplier id from sourcing results; never invent one.
            quantity (`int`): RFQ quantity used for fixed-fee allocation.
            unit_price (`float | None`): Explicit quoted unit price.
            currency (`str | None`): Explicit quote currency, e.g. USD.
            incoterm (`str | None`): EXW/FOB/CIF/etc when stated.
            logo_fee_per_unit (`float | None`): Per-unit logo fee when stated.
            packaging_fee_per_unit (`float | None`): Per-unit packaging fee when stated.
            fixed_fee (`float | None`): Fixed fee allocated over quantity when stated.
            fixed_fee_description (`str | None`): e.g. sample_fee/setup_fee.
            lead_time_days (`int | None`): Single-value lead time.
            lead_time_min_days (`int | None`): Lower bound when quote gives a range.
            lead_time_max_days (`int | None`): Upper bound when quote gives a range.
            payment_terms (`str | None`): Payment terms verbatim/normalized.
            certifications_confirmed (`list[str] | None`): Certifications explicitly confirmed in quote.
            raw_text (`str | None`): Optional raw quote for limited regex fallback.
        """
        session_id = ProcurementContext.current_session_id()
        bus.publish(session_id, "tool.invoke", {"tool": "quotation_normalize_tool", "supplier_id": supplier_id})
        bus.publish(
            session_id,
            "workflow.progress",
            {"stage": "quote_parse", "message": "正在解析报价", "supplier_id": supplier_id},
        )
        try:
            has_structured_payload = any(
                value is not None
                for value in (
                    unit_price,
                    currency,
                    incoterm,
                    logo_fee_per_unit,
                    packaging_fee_per_unit,
                    fixed_fee,
                    lead_time_days,
                    lead_time_min_days,
                    lead_time_max_days,
                    payment_terms,
                    certifications_confirmed,
                )
            )
            if has_structured_payload:
                result = normalize_structured_quotation(
                    quote_id=quote_id,
                    supplier_id=supplier_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    currency=currency,
                    incoterm=incoterm,
                    logo_fee_per_unit=logo_fee_per_unit,
                    packaging_fee_per_unit=packaging_fee_per_unit,
                    fixed_fee=fixed_fee,
                    fixed_fee_description=fixed_fee_description,
                    lead_time_days=lead_time_days,
                    lead_time_min_days=lead_time_min_days,
                    lead_time_max_days=lead_time_max_days,
                    payment_terms=payment_terms,
                    certifications_confirmed=certifications_confirmed,
                    assume_missing_fees_zero=False,
                )
            elif raw_text:
                result = parse_quotation_text(
                    raw_text,
                    quote_id=quote_id,
                    supplier_id=supplier_id,
                    quantity=int(quantity),
                )
            else:
                raise ValueError("至少提供结构化报价字段或 raw_text")
        except (TypeError, ValueError) as err:
            bus.publish(session_id, "tool.result", {"tool": "quotation_normalize_tool", "error": str(err)})
            return ToolChunk(
                content=[TextBlock(type="text", text=f"[error] {err}")],
                state=ToolResultState.ERROR,
            )

        payload = result.to_dict()
        bus.publish(
            session_id,
            "tool.result",
            {
                "tool": "quotation_normalize_tool",
                "supplier_id": supplier_id,
                "effective_unit_cost": payload.get("effective_unit_cost"),
                "warnings": payload.get("warnings", []),
            },
        )
        return ToolChunk(
            content=[TextBlock(type="text", text=json.dumps(payload, ensure_ascii=False))],
            state=ToolResultState.SUCCESS,
        )

    return quotation_normalize_tool
