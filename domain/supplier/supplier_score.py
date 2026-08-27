# -*- coding: utf-8 -*-
"""Deterministic supplier decision score for the B2B sourcing workflow."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SupplierScore:
    supplier_id: str
    hard_constraints_passed: bool
    hard_constraint_failures: list[str] = field(default_factory=list)
    component_scores: dict[str, float | None] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    final_score: float = 0.0
    strengths: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    next_action: str = ""
    needs_human_approval: bool = True

    def __post_init__(self) -> None:
        if not self.supplier_id or not self.supplier_id.strip():
            raise ValueError("SupplierScore.supplier_id required")
        if not 0.0 <= self.final_score <= 100.0:
            raise ValueError("SupplierScore.final_score 必须位于 [0, 100]")
        if self.hard_constraints_passed and self.hard_constraint_failures:
            raise ValueError("passed supplier 不能同时包含 hard_constraint_failures")
        for name, score in self.component_scores.items():
            if score is not None and not 0.0 <= score <= 1.0:
                raise ValueError(f"component score {name} 必须位于 [0, 1]")
        if self.weights:
            total = sum(self.weights.values())
            if abs(total - 1.0) > 1e-9:
                raise ValueError("SupplierScore.weights 权重和必须为 1")

    def to_dict(self) -> dict:
        return {
            "supplier_id": self.supplier_id,
            "hard_constraints_passed": self.hard_constraints_passed,
            "hard_constraint_failures": list(self.hard_constraint_failures),
            "component_scores": dict(self.component_scores),
            "weights": dict(self.weights),
            "final_score": round(self.final_score, 2),
            "strengths": list(self.strengths),
            "risks": list(self.risks),
            "next_action": self.next_action,
            "needs_human_approval": self.needs_human_approval,
        }
