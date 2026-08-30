# -*- coding: utf-8 -*-
"""permissions

2.0 权限系统适配：DEFAULT 模式下非只读工具会触发 RequireUserConfirmEvent 挂起等确认。
SourcePilot 当前 MVP 不执行外部写操作；这里只放行计划、调度与本地偏好记忆工具。

不用 BYPASS/DONT_ASK 全局模式：保持权限引擎生效，只精准放行已知工具，
未来接入 Bash/文件类危险工具时仍受默认策略保护。
"""
from __future__ import annotations

from agentscope.agent import Agent
from agentscope.permission import PermissionBehavior, PermissionRule

# 内置计划工具 + 调度/本地记忆工具
_AUTO_ALLOWED_TOOLS = (
    "task_dispatch",
    "remember_preference_tool",
    # 撤回偏好与记住偏好对称：买家已在对话里明确说“以后不用避开塑料了”，
    # 再弹一次工具层确认卡是重复询问；且误删风险由精确匹配兜底
    "forget_preference_tool",
    "TaskCreate",
    "TaskUpdate",
    "TaskList",
    "TaskGet",
)


def allow_business_tools(agent: Agent) -> Agent:
    """给 Agent 的权限上下文追加业务工具 allow 规则（幂等，兼容恢复的持久化状态）。"""
    allow_rules = agent.state.permission_context.allow_rules
    for tool_name in _AUTO_ALLOWED_TOOLS:
        rules = allow_rules.setdefault(tool_name, [])
        if any(rule.source == "projectSettings" for rule in rules):
            continue
        rules.append(
            PermissionRule(
                tool_name=tool_name,
                rule_content=None,
                behavior=PermissionBehavior.ALLOW,
                source="projectSettings",
            ),
        )
    return agent
