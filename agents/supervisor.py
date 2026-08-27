# -*- coding: utf-8 -*-
"""SourcePilot supervisor (ProcurementConcierge).

This is a thin facade over ``app.application.agents.main_agent.MainAgentFactory``,
which is the actual primary surface of the Cross-border Sourcing Copilot.
"""
from app.application.agents.main_agent import MainAgentFactory, SessionRegistry

Supervisor = MainAgentFactory
SupervisorSessions = SessionRegistry

__all__ = ["MainAgentFactory", "SessionRegistry", "Supervisor", "SupervisorSessions"]
