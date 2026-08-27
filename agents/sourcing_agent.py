# -*- coding: utf-8 -*-
"""SourcePilot SourcingAgent facade.

Wraps ``app.application.agents.sourcing_agent.SourcingAgentFactory`` so that
callers can ``from app.agents.sourcing_agent import SourcingAgentFactory``.
"""
from app.application.agents.sourcing_agent import SourcingAgentFactory

__all__ = ["SourcingAgentFactory"]
