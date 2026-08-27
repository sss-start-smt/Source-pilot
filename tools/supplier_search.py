# -*- coding: utf-8 -*-
"""SourcePilot supplier_search tool facade.

Wraps the constraint-aware ``SupplierSearchUseCase`` so that
``from app.tools.supplier_search import SupplierSearchUseCase`` works and
the module is addressable by the PRD's "supplier_search" tool name.
"""
from app.application.usecases.supplier_search import (
    REASON_CODES,
    SupplierCandidate,
    SupplierSearchUseCase,
)
from app.application.usecases.supplier_retrieval import SupplierRetrievalUseCase
from app.application.tools.supplier_search_tool import build_supplier_search_tool
from app.application.tools.supplier_search_validation import (
    validate_supplier_search_input,
)

validate_hard_constraint_payload = validate_supplier_search_input

__all__ = [
    "SupplierSearchUseCase",
    "SupplierRetrievalUseCase",
    "SupplierCandidate",
    "REASON_CODES",
    "build_supplier_search_tool",
    "validate_supplier_search_input",
    "validate_hard_constraint_payload",
]
