"""公开产品边界回归：确保 Portfolio Edition 始终保持 1+2 Agent 架构。"""

import os
os.environ.setdefault("LLM_API_KEY", "test-placeholder")

from app.application.prompts.loader import load_prompts
from app.presentation.server import build_app


def test_only_two_specialist_agents_are_configured() -> None:
    sub_agents = load_prompts()["sub_agents"]
    assert set(sub_agents) == {"sourcing", "quote"}
def test_public_api_stays_inside_procurement_mvp() -> None:
    paths = {route.path for route in build_app().routes}
    assert "/procurement/intents" in paths
    assert "/procurement/events" in paths
    assert not any("/orders" in path for path in paths)
