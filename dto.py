# -*- coding: utf-8 -*-
"""presentation DTO

REST 请求 / 响应模型。procurement_session_id 缺省时由服务端生成。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SubmitIntentRequest(BaseModel):
    procurement_session_id: Optional[str] = Field(default=None, description="会话 ID，缺省则新建会话")
    buyer_id: str = Field(min_length=1, description="采购方 / buyer ID")
    locale: str = Field(default="zh-CN")
    currency: str = Field(default="CNY")
    raw_query: str = Field(min_length=1, description="采购方自然语言采购需求")


class SubmitIntentResponse(BaseModel):
    procurement_session_id: str
    final_text: str
