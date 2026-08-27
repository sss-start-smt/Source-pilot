# -*- coding: utf-8 -*-
"""SourcePilot Agents (top-level entry points)

This package exposes the multi-agent surface that SourcePilot's PRD calls out:
    - supervisor (MainAgent / ProcurementConcierge)
    - sourcing_agent (SourcingAgent)
    - quote_agent (QuoteAgent)

The actual implementations live under ``app.application.agents`` and follow
the same DDD boundary (Application layer composes Domain + Infrastructure).
These modules are thin, public re-exports so that external scripts and tests
can do ``from app.agents import SourcingAgentFactory`` without depending on
the internal application-layer path.
"""
from app.application.agents.main_agent import MainAgentFactory, SessionRegistry
from app.application.agents.orchestrator import MainAgentOrchestrator
from app.application.agents.quote_agent import QuoteAgentFactory
from app.application.agents.search_agent import SearchAgentFactory
from app.application.agents.sourcing_agent import SourcingAgentFactory
from app.application.agents.trade_agent import TradeAgentFactory

# Backwards-compatible aliases: the PRD uses ``supervisor`` for the
# MainAgent / ProcurementConcierge total-control surface.
SupervisorFactory = MainAgentFactory
SupervisorOrchestrator = MainAgentOrchestrator

__all__ = [
    "MainAgentFactory",
    "MainAgentOrchestrator",
    "SessionRegistry",
    "SearchAgentFactory",
    "SourcingAgentFactory",
    "QuoteAgentFactory",
    "TradeAgentFactory",
    "SupervisorFactory",
    "SupervisorOrchestrator",
]
