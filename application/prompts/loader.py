# -*- coding: utf-8 -*-
"""PromptLoader

Reads and caches ``app/application/prompts/sourcepilot.yml``. All prompts
in the project are sourced from this single file.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

PROMPTS_PATH = Path(__file__).resolve().parent / "sourcepilot.yml"


@lru_cache(maxsize=1)
def load_prompts() -> dict:
    with open(PROMPTS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)
