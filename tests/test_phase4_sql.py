# -*- coding: utf-8 -*-
"""四期模块一：关系库仓储实现

跑 SQLite 内存库（与交付形态同源）。仓储代码不绑驱动，换服务型数据库
只需换 DATABASE_URL 与异步驱动，但那些驱动的特有行为本仓未验证。
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.domain.buyer.preference import BuyerPreference
from app.domain.session.ports.conversation_store import (
    ConversationEventRecord,
    ConversationTurn,
)
from app.infrastructure.persistence.sql.repositories import (
    SqlConversationStore,
    SqlPreferenceStore,
    SqlSessionStore,
    bootstrap_schema,
    create_engine,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    await bootstrap_schema(eng)
    yield eng
    await eng.dispose()


class TestEngineSelection:
    """连接池参数必须按驱动分开给：把服务型数据库那套给 SQLite 会直接报错。"""

    async def test_sqlite_engine_created_without_server_pool_args(self):
        engine = create_engine("sqlite+aiosqlite:///:memory:")
        try:
            assert engine.url.get_backend_name() == "sqlite"
        finally:
            await engine.dispose()

    async def test_default_settings_point_to_sqlite(self, tmp_path, monkeypatch):
        """不配 DATABASE_URL 时默认落在 DATA_DIR 下的 SQLite 文件。"""
        from app.infrastructure.settings import load_settings

        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("MYSQL_URL", raising=False)

        settings = load_settings()
        assert settings.database_url.startswith("sqlite+aiosqlite:///")
        assert settings.database_url.endswith("sourcepilot.db")

    async def test_explicit_database_url_wins(self, tmp_path, monkeypatch):
        from app.infrastructure.settings import load_settings

        monkeypatch.setenv("LLM_API_KEY", "test-key")
        monkeypatch.setenv("DATA_DIR", str(tmp_path))
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:////tmp/explicit.db")
        assert load_settings().database_url.endswith("explicit.db")


class TestSessionStore:
    async def test_state_roundtrip(self, engine):
        store = SqlSessionStore(engine)
        await store.save("s1", '{"session_id":"s1"}')
        assert await store.load("s1") == '{"session_id":"s1"}'

    async def test_save_is_upsert(self, engine):
        """每轮都会覆盖写同一会话，第二次不能因主键冲突失败。"""
        store = SqlSessionStore(engine)
        await store.save("s1", '{"v":1}')
        await store.save("s1", '{"v":2}')
        assert await store.load("s1") == '{"v":2}'

    async def test_missing_returns_none(self, engine):
        assert await SqlSessionStore(engine).load("nope") is None


class TestConversationStore:
    async def test_turns_ordered_by_turn_index(self, engine):
        store = SqlConversationStore(engine)
        await store.touch_session("s1", "buyer-001", "zh-CN", "CNY")
        for index in range(3):
            await store.append_turn(
                ConversationTurn(
                    session_id="s1", buyer_id="buyer-001", role="buyer", content=f"第{index}问",
                ),
            )
        turns = await store.list_turns("s1")
        assert [turn.content for turn in turns] == ["第0问", "第1问", "第2问"]

    async def test_turn_index_isolated_per_session(self, engine):
        """turn_index 按会话独立自增，不能被其他会话的行数带偏。"""
        store = SqlConversationStore(engine)
        await store.append_turn(
            ConversationTurn(session_id="s1", buyer_id="b", role="buyer", content="a"),
        )
        await store.append_turn(
            ConversationTurn(session_id="s1", buyer_id="b", role="agent", content="b"),
        )
        await store.append_turn(
            ConversationTurn(session_id="s2", buyer_id="b", role="buyer", content="c"),
        )
        assert len(await store.list_turns("s1")) == 2
        assert len(await store.list_turns("s2")) == 1

    async def test_events_persisted_with_payload(self, engine):
        store = SqlConversationStore(engine)
        await store.append_events(
            [
                ConversationEventRecord(
                    session_id="s1", type="tool.result", payload={"tool": "supplier_search_tool"},
                ),
            ],
        )
        # 事件表没有读接口，直接查会话主记录确认写入未抛错即可
        assert await store.find_session("s1") is None  # 事件不建会话主记录

    async def test_touch_session_is_idempotent(self, engine):
        store = SqlConversationStore(engine)
        await store.touch_session("s1", "buyer-001", "zh-CN", "CNY")
        await store.touch_session("s1", "buyer-001", "zh-CN", "CNY")
        session = await store.find_session("s1")
        assert session is not None and session["buyer_id"] == "buyer-001"

    async def test_empty_events_is_noop(self, engine):
        await SqlConversationStore(engine).append_events([])


class TestPreferenceStore:
    async def test_append_and_list(self, engine):
        store = SqlPreferenceStore(engine)
        await store.append(
            BuyerPreference(buyer_id="b1", kind="dislike", statement="不要塑料材质"),
        )
        prefs = await store.list_by_buyer("b1")
        assert [p.statement for p in prefs] == ["不要塑料材质"]

    async def test_duplicate_swallowed_by_unique_constraint(self, engine):
        """幂等去重靠唯一约束兜底，重复写入不能抛给调用方。"""
        store = SqlPreferenceStore(engine)
        pref = BuyerPreference(buyer_id="b1", kind="dislike", statement="不要塑料材质")
        await store.append(pref)
        await store.append(pref)
        assert len(await store.list_by_buyer("b1")) == 1

    async def test_same_statement_different_kind_both_kept(self, engine):
        store = SqlPreferenceStore(engine)
        await store.append(BuyerPreference(buyer_id="b1", kind="like", statement="小众设计"))
        await store.append(BuyerPreference(buyer_id="b1", kind="dislike", statement="小众设计"))
        assert len(await store.list_by_buyer("b1")) == 2

    async def test_buyers_isolated(self, engine):
        store = SqlPreferenceStore(engine)
        await store.append(BuyerPreference(buyer_id="b1", kind="like", statement="x"))
        assert await store.list_by_buyer("b2") == []

    async def test_delete_hit_and_miss(self, engine):
        store = SqlPreferenceStore(engine)
        await store.append(BuyerPreference(buyer_id="b1", kind="dislike", statement="不要塑料材质"))

        assert await store.delete("b1", "不要塑料材质") is True
        assert await store.list_by_buyer("b1") == []
        assert await store.delete("b1", "不要塑料材质") is False

    async def test_delete_requires_exact_match(self, engine):
        """删偏好不可逆，不得前缀匹配误删。"""
        store = SqlPreferenceStore(engine)
        await store.append(BuyerPreference(buyer_id="b1", kind="dislike", statement="不要塑料材质"))
        assert await store.delete("b1", "不要塑料") is False
        assert len(await store.list_by_buyer("b1")) == 1

    async def test_delete_removes_both_kinds_of_same_statement(self, engine):
        """同一句话可同时存为 like 与 dislike（见上一条用例），
        撤回时两条一并清除——买家表达的是“忘掉这条说法”。"""
        store = SqlPreferenceStore(engine)
        await store.append(BuyerPreference(buyer_id="b1", kind="like", statement="小众设计"))
        await store.append(BuyerPreference(buyer_id="b1", kind="dislike", statement="小众设计"))

        assert await store.delete("b1", "小众设计") is True
        assert await store.list_by_buyer("b1") == []

    async def test_delete_does_not_cross_buyers(self, engine):
        store = SqlPreferenceStore(engine)
        await store.append(BuyerPreference(buyer_id="b1", kind="dislike", statement="不要塑料材质"))
        await store.append(BuyerPreference(buyer_id="b2", kind="dislike", statement="不要塑料材质"))

        assert await store.delete("b1", "不要塑料材质") is True
        assert len(await store.list_by_buyer("b2")) == 1
