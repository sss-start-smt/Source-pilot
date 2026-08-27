# -*- coding: utf-8 -*-
"""SourcePilot QuoteAgent facade.

Wraps ``app.application.agents.quote_agent.QuoteAgentFactory`` so that
callers can ``from app.agents.quote_agent import QuoteAgentFactory``.
"""
from app.application.agents.quote_agent import QuoteAgentFactory

__all__ = ["QuoteAgentFactory"]
