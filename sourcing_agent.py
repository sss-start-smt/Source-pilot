# -*- coding: utf-8 -*-
"""SourcingAgent: RFQ -> supplier retrieval -> deterministic hard filters."""
from __future__ import annotations

from agentscope.agent import Agent, ReActConfig
from agentscope.tool import FunctionTool, Toolkit

from app.application.agents.context_policy import build_context_config
from app.application.prompts.loader import load_prompts
from app.application.tools.supplier_search_tool import build_supplier_search_tool
from app.application.usecases.supplier_search import SupplierSearchUseCase
from app.infrastructure.eventbus import TradeEventBus
from app.infrastructure.llm import create_chat_model
from app.infrastructure.resilience import CircuitBreakerRegistry, ToolResilienceMiddleware
from app.infrastructure.settings import Settings
from app.infrastructure.throttle import GatewayThrottle
from app.infrastructure.tracing import build_agent_middlewares


class SourcingAgentFactory:
    def __init__(
        self,
        settings: Settings,
        supplier_search: SupplierSearchUseCase,
        bus: TradeEventBus,
        circuit_registry: CircuitBreakerRegistry,
        throttle: GatewayThrottle,
    ) -> None:
        self._settings = settings
        self._supplier_search = supplier_search
        self._bus = bus
        self._circuit_registry = circuit_registry
        self._throttle = throttle

    def _resilience(self) -> list:
        return [ToolResilienceMiddleware(self._circuit_registry, self._bus)]

    def build_tools(self) -> list[FunctionTool]:
        return [
            FunctionTool(
                build_supplier_search_tool(self._supplier_search, self._bus),
                is_read_only=True,
                middlewares=self._resilience(),
            ),
        ]

    def build(self) -> Agent:
        prompts = load_prompts()["sub_agents"]["sourcing"]
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
            react_config=ReActConfig(max_iters=6),
        )
