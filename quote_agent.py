# -*- coding: utf-8 -*-
"""QuoteAgent: quote extraction/normalization and deterministic comparison."""
from __future__ import annotations

from agentscope.agent import Agent, ReActConfig
from agentscope.tool import FunctionTool, Toolkit

from app.application.agents.context_policy import build_context_config
from app.application.prompts.loader import load_prompts
from app.application.tools.quotation_compare_tool import build_quotation_compare_tool
from app.application.tools.quotation_normalize_tool import build_quotation_normalize_tool
from app.application.usecases.quotation_compare import QuotationCompareUseCase
from app.domain.supplier.ports.supplier_repository import SupplierRepository
from app.infrastructure.eventbus import TradeEventBus
from app.infrastructure.llm import create_chat_model
from app.infrastructure.resilience import CircuitBreakerRegistry, ToolResilienceMiddleware
from app.infrastructure.settings import Settings
from app.infrastructure.throttle import GatewayThrottle
from app.infrastructure.tracing import build_agent_middlewares


class QuoteAgentFactory:
    def __init__(
        self,
        settings: Settings,
        supplier_repo: SupplierRepository,
        quotation_compare: QuotationCompareUseCase,
        bus: TradeEventBus,
        circuit_registry: CircuitBreakerRegistry,
        throttle: GatewayThrottle,
    ) -> None:
        self._settings = settings
        self._supplier_repo = supplier_repo
        self._quotation_compare = quotation_compare
        self._bus = bus
        self._circuit_registry = circuit_registry
        self._throttle = throttle

    def _resilience(self) -> list:
        return [ToolResilienceMiddleware(self._circuit_registry, self._bus)]

    def build_tools(self) -> list[FunctionTool]:
        return [
            FunctionTool(
                build_quotation_normalize_tool(self._bus),
                is_read_only=True,
                middlewares=self._resilience(),
            ),
            FunctionTool(
                build_quotation_compare_tool(
                    self._supplier_repo,
                    self._quotation_compare,
                    self._bus,
                ),
                is_read_only=True,
                middlewares=self._resilience(),
            ),
        ]

    def build(self) -> Agent:
        prompts = load_prompts()["sub_agents"]["quote"]
        return Agent(
            name=prompts["name"],
            system_prompt=prompts["system_prompt"],
            model=create_chat_model(self._settings, throttle=self._throttle, bus=self._bus),
            toolkit=Toolkit(tools=list(self.build_tools())),
            middlewares=build_agent_middlewares(self._settings),
            context_config=build_context_config(
                self._settings.context_size,
                self._settings.tool_result_limit,
            ),
            react_config=ReActConfig(max_iters=8),
        )
