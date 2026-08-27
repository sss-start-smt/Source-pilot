# -*- coding: utf-8 -*-
"""SourcePilot configuration entry point.

Thin re-export over ``app.infrastructure.settings`` so that scripts and
external tools can do ``from app.config.settings import load_settings,
Settings`` without depending on the internal infrastructure path.
"""
from app.infrastructure.settings import PROJECT_ROOT, Settings, load_settings

__all__ = ["Settings", "load_settings", "PROJECT_ROOT"]
