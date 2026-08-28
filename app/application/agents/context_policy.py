# -*- coding: utf-8 -*-
"""context_policy

Context 工程策略：把 2.0 内置的上下文压缩配置成 B2B 采购场景的口径
（即教程 Cache Breakpoint 章节要解决的问题——长对话不爆 token 且关键事实不丢）。

压缩触发：上下文占用达 context_size * trigger_ratio 时，Agent 自动把早期消息
压缩成摘要写入 AgentState.summary，保留末段 reserve_ratio 的原始消息。

关键取舍：摘要提示词显式列出必须保留的 RFQ、供应商、报价与人工确认边界。

注意：summary_template 的占位符必须与 2.0 内置 summary_schema 的五个字段一致
（task_overview / current_state / important_discoveries / next_steps / context_to_preserve），
否则压缩时渲染摘要会抛 KeyError。
"""
from __future__ import annotations

from agentscope.agent import ContextConfig

_COMPRESSION_PROMPT = """<system-hint>当前对话上下文即将超出窗口，请把此前的工作压缩成一份中文摘要，
供你后续继续为这位买家服务。当前时间：{current_time}。

必须逐字保留的事实（丢失会导致后续回答出错）：
1. 结构化 RFQ：品类、数量、目标价、认证、交期与定制要求；
2. 已通过硬约束的供应商：supplier_id、匹配证据与过滤原因；
3. 报价事实：币种、贸易条款、费用项、有效单价与缺失字段；
4. 当前需要人工确认的动作和下一步。

可以压缩或丢弃的内容：工具返回的完整候选列表（只留 shortlist）、寒暄、重复表述、
已被更新覆盖的中间结论。

摘要中的所有数字必须来自此前的工具返回，不得重新估算。</system-hint>"""

_SUMMARY_TEMPLATE = """<system-info>以下是你此前为该买家服务的工作摘要，视作事实基准继续服务。
# 买家诉求与约束
{task_overview}

# 当前进展（召回 / 筛选 / 报价比较）
{current_state}

# 关键事实（supplier_id / 报价 / 过滤原因）
{important_discoveries}

# 下一步与待确认事项
{next_steps}

# 买家偏好与必须保留的上下文
{context_to_preserve}</system-info>"""


def build_context_config(context_size: int, tool_result_limit: int) -> ContextConfig:
    """构造 SourcePilot 的上下文压缩策略。

    Args:
        context_size (`int`):
            模型上下文窗口大小（与 create_chat_model 保持一致）。
        tool_result_limit (`int`):
            单个工具结果的字符上限，超出会被截断，防止候选列表挤爆上下文。
    """
    del context_size  # 窗口由 model 侧提供，这里仅保留参数以标明配套关系
    return ContextConfig(
        trigger_ratio=0.75,
        reserve_ratio=0.15,
        compression_prompt=_COMPRESSION_PROMPT,
        summary_template=_SUMMARY_TEMPLATE,
        tool_result_limit=tool_result_limit,
    )
