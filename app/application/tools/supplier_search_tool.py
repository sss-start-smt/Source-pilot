# -*- coding: utf-8 -*-
"""supplier_search_tool

Structured RFQ slots -> SupplierSearchUseCase -> qualified supplier cards.
The Agent/LLM is responsible for extracting the slots from natural language;
Python validates types and applies every hard constraint deterministically.

Do not add ``from __future__ import annotations`` here: AgentScope inspects the
runtime annotations to generate the tool schema.
"""
import json
from typing import Optional

from agentscope.message import TextBlock, ToolResultState
from agentscope.tool import ToolChunk

from app.application.usecases.supplier_search import SupplierSearchUseCase
from app.application.tools.supplier_search_validation import validate_supplier_search_input
from app.domain.supplier.supplier_search_spec import SupplierSearchSpec
from app.infrastructure.context import ProcurementContext
from app.infrastructure.eventbus import TradeEventBus


def build_supplier_search_tool(usecase: SupplierSearchUseCase, bus: TradeEventBus):
    async def supplier_search_tool(
        product: str,
        normalized_query: str,
        quantity: int | str,
        category: Optional[str] = None,
        price_max_major: float | str | None = None,
        required_certifications: Optional[list[str]] = None,
        max_lead_time_days: int | str | None = None,
        required_customization: Optional[list[str]] = None,
        top_k: int | str = 5,
        currency: str = "USD",
    ) -> ToolChunk:
        """Search suppliers for a structured procurement RFQ.

        Call this tool only after ``product`` and ``quantity`` are known. Never
        invent missing numeric constraints merely to make the call succeed.

        Args:
            product (`str`):
                Product being sourced, e.g. "vacuum flask". Required.
            normalized_query (`str`):
                Normalized retrieval query retaining product and key attributes.
            quantity (`int`):
                Required purchase quantity. This is a hard MOQ gate.
            category (`str | None`):
                Supplier category slot, e.g. "vacuum flask".
            price_max_major (`float | None`):
                Maximum acceptable unit price in ``currency``. Hard gate when present.
            required_certifications (`list[str] | None`):
                All required certifications. Every listed certification must be present.
            max_lead_time_days (`int | None`):
                Maximum acceptable supplier lead time in days. Hard gate when present.
            required_customization (`list[str] | None`):
                Required customization capabilities; all must be supported.
            top_k (`int`):
                Qualified suppliers to return, default 5.
            currency (`str`):
                Currency for the unit-price hard gate, default USD.
        """
        session_id = ProcurementContext.current_session_id()

        try:
            validated = validate_supplier_search_input(
                product=product,
                quantity=quantity,
                price_max_major=price_max_major,
                max_lead_time_days=max_lead_time_days,
                top_k=top_k,
                currency=currency,
            )
        except ValueError as err:
            return ToolChunk(
                content=[TextBlock(type="text", text=f"[error] {err}")],
                state=ToolResultState.ERROR,
            )
        quantity_i = validated.quantity
        price_f = validated.price_max_major
        lead_i = validated.max_lead_time_days
        top_k_i = validated.top_k
        product = validated.product
        currency = validated.currency

        certifications = [item.strip() for item in (required_certifications or []) if item.strip()]
        customization = [item.strip() for item in (required_customization or []) if item.strip()]
        args = {
            "product": product,
            "normalized_query": normalized_query,
            "category": category,
            "quantity": quantity_i,
            "price_max_major": price_f,
            "required_certifications": certifications,
            "max_lead_time_days": lead_i,
            "required_customization": customization,
            "top_k": top_k_i,
            "currency": currency,
        }
        bus.publish(session_id, "tool.invoke", {"tool": "supplier_search_tool", "args": args})
        bus.publish(
            session_id,
            "workflow.progress",
            {"stage": "supplier_retrieval", "message": "正在召回供应商"},
        )

        try:
            spec = SupplierSearchSpec(
                normalized_query=normalized_query,
                category=category or product.strip(),
                quantity=quantity_i,
                price_max_major=price_f,
                required_certifications=certifications,
                max_lead_time_days=lead_i,
                required_customization=customization,
                top_k=top_k_i,
                currency=currency,
            )
            result = await usecase.execute(spec)
        except ValueError as err:
            bus.publish(session_id, "tool.result", {"tool": "supplier_search_tool", "error": str(err)})
            return ToolChunk(
                content=[TextBlock(type="text", text=f"[error] {err}")],
                state=ToolResultState.ERROR,
            )

        # Echo the validated structured extraction so the UI/MainAgent can show
        # what was understood before explaining retrieval results.
        result["rfq"] = {
            "product": product.strip(),
            "quantity": quantity_i,
            "target_price": price_f,
            "currency": currency.upper().strip(),
            "required_certifications": certifications,
            "max_lead_time_days": lead_i,
            "customization": customization,
            "missing_required_fields": [],
        }
        bus.publish(
            session_id,
            "workflow.progress",
            {
                "stage": "hard_filter",
                "message": "硬约束过滤完成",
                "qualified_supplier_count": result["qualified_supplier_count"],
                "filtered_out_count": result["filtered_out_count"],
            },
        )
        bus.publish(
            session_id,
            "tool.result",
            {
                "tool": "supplier_search_tool",
                "hit_count": len(result["hits"]),
                "filtered_out_count": result["filtered_out_count"],
                "recall_strategy": result["recall_strategy"],
                "rfq": result["rfq"],
                "hits": result["hits"],
                "filtered_out": result.get("filtered_out", []),
            },
        )
        return ToolChunk(
            content=[TextBlock(type="text", text=json.dumps(result, ensure_ascii=False))],
            state=ToolResultState.SUCCESS,
        )

    return supplier_search_tool

