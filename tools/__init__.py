# -*- coding: utf-8 -*-
"""SourcePilot Tools (top-level entry points)

This package exposes the deterministic procurement tools that the PRD names
explicitly. Each submodule is a thin re-export over the corresponding
``app.application.usecases`` or ``app.application.tools`` implementation so
that external code can use ``from app.tools.<x> import <y>`` without needing
to know the internal application-layer path.

Mapping:
    supplier_search    -> SupplierSearchUseCase (constraint-aware retrieval +
                          hard-gate filtering + soft rerank)
    quotation_parser   -> quotation extraction + coercion helpers
    constraint_checker -> hard-constraint reason-code rules
    cost_calculator    -> effective unit cost computation
    ranking_engine     -> deterministic supplier ranking
"""
from app.application.usecases import supplier_search
from app.application.usecases import quotation_compare as ranking_engine
from app.application.usecases.supplier_search import (
    REASON_CODES,
    REASON_CUSTOMIZATION_UNSUPPORTED,
    REASON_LEAD_TIME_TOO_LONG,
    REASON_MISSING_CERTIFICATION,
    REASON_MOQ_TOO_HIGH,
    REASON_PRICE_ABOVE_TARGET,
)
from app.application.usecases.quotation_compare import (
    HARD_CURRENCY_MISMATCH,
    HARD_CUSTOMIZATION_UNSUPPORTED,
    HARD_LEAD_TIME_TOO_LONG,
    HARD_MISSING_CERTIFICATION,
    HARD_MOQ_TOO_HIGH,
    HARD_PRICE_ABOVE_TARGET,
    HARD_QUOTE_INCOMPLETE,
    MVP_WEIGHTS,
)
from app.domain.quotation.quotation import Quotation

# ``quotation_parser`` and ``constraint_checker`` are intentionally NOT
# re-exported here. Their submodule names collide with internal
# ``app.application.quotation_parser``; callers should import the submodule
# directly: ``from app.tools.quotation_parser import parse_quotation``.

__all__ = [
    "supplier_search",
    "ranking_engine",
    "REASON_CODES",
    "REASON_MOQ_TOO_HIGH",
    "REASON_PRICE_ABOVE_TARGET",
    "REASON_MISSING_CERTIFICATION",
    "REASON_LEAD_TIME_TOO_LONG",
    "REASON_CUSTOMIZATION_UNSUPPORTED",
    "HARD_CURRENCY_MISMATCH",
    "HARD_QUOTE_INCOMPLETE",
    "MVP_WEIGHTS",
    "Quotation",
]
