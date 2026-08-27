# -*- coding: utf-8 -*-
"""SourcePilot Pydantic / dataclass schemas (top-level entry points).

This module is a single import surface for the data shapes that travel
across the SourcePilot API. The authoritative classes still live in their
domain modules under ``app.domain.*``; this file re-exports them so that
external callers (frontend typing, integration tests, OpenAPI generators)
can do ``from app.models.schemas import RFQ, Supplier, Quotation``.

Symbol names are kept stable; if the underlying class name differs, we
alias it here so that downstream imports do not break.
"""
from __future__ import annotations

from app.domain.procurement.rfq import RFQ
from app.domain.supplier.supplier import Supplier
from app.domain.supplier.supplier_score import SupplierScore
from app.domain.supplier.supplier_search_spec import SupplierSearchSpec
from app.domain.quotation.quotation import Quotation
from app.domain.buyer.preference import BuyerPreference, PreferenceStore
from app.domain.order.order import Order, OrderStatus
from app.domain.order.order_line import OrderLine
from app.domain.catalog.product import Product, ProductHighlight
from app.domain.catalog.product_search_spec import ProductSearchSpec
from app.domain.catalog.sku import Sku
from app.domain.catalog.money import Money
from app.domain.shipping.tariff_schedule import TariffSchedule, ShippingQuote
from app.application.usecases.supplier_search import SupplierCandidate
from app.application.usecases.quotation_compare import SupplierQuoteInput

# Backwards-compatible aliases (older callers / docs use the spelled-out form)
PreferenceRecord = BuyerPreference
SKU = Sku

__all__ = [
    "RFQ",
    "Supplier",
    "SupplierScore",
    "SupplierSearchSpec",
    "SupplierCandidate",
    "SupplierQuoteInput",
    "Quotation",
    "BuyerPreference",
    "PreferenceRecord",
    "PreferenceStore",
    "Order",
    "OrderLine",
    "OrderStatus",
    "Product",
    "ProductHighlight",
    "ProductSearchSpec",
    "SKU",
    "Sku",
    "Money",
    "TariffSchedule",
    "ShippingQuote",
]
