"""知识管理系统测试：CRUD 主流程 / 缓存命中 / 缓存穿透 / LLM 摘要 / 统一响应。"""
import httpx

import app.main as main_app


def test_note_crud_full_flow(client):
    """CRUD 主流程：创建（自动建标签）→ 列表/标签筛选 → 详情 → 更新 → 删除。"""
    resp = client.post(
        "/api/notes",
        json={"title": "FastAPI 学习", "content": "路由与依赖注入", "tags": ["python", "web"]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["code"] == 0
    note_id = body["data"]["id"]
    assert sorted(body["data"]["tags"]) == ["python", "web"]

    # 列表分页
    resp = client.get("/api/notes", params={"page": 1, "page_size": 10})
    page = resp.json()["data"]
    assert page["total"] == 1
    assert len(page["items"]) == 1

    # 按标签筛选
    resp = client.get("/api/notes", params={"tag": "python"})
    page = resp.json()["data"]
    assert page["total"] == 1
    assert page["items"][0]["id"] == note_id

    # 详情
    resp = client.get(f"/api/notes/{note_id}")
    assert resp.json()["data"]["title"] == "FastAPI 学习"

    # 更新：标题修改 + 标签替换（backend 自动创建）
    resp = client.put(f"/api/notes/{note_id}", json={"title": "FastAPI 进阶", "tags": ["python", "backend"]})
    assert resp.json()["data"]["title"] == "FastAPI 进阶"
    assert sorted(resp.json()["data"]["tags"]) == ["backend", "python"]

    # 删除后详情 404
    assert client.delete(f"/api/notes/{note_id}").json()["code"] == 0
    resp = client.get(f"/api/notes/{note_id}")
    assert resp.status_code == 404
    assert resp.json()["code"] == 404


def test_search_cache_hit_skips_database(client, fake_redis, monkeypatch):
    """缓存命中：首次搜索写缓存，第二次同条件搜索不再查库。"""
    client.post("/api/notes", json={"title": "Redis 缓存实战", "content": "穿透 击穿 雪崩", "tags": ["redis"]})

    calls = {"n": 0}
    original = main_app.crud.search_notes

    def counted_search(db, q, tag):
        calls["n"] += 1
        return original(db, q, tag)

    monkeypatch.setattr(main_app.crud, "search_notes", counted_search)

    first = client.get("/api/notes/search", params={"q": "缓存"})
    assert first.status_code == 200
    assert len(first.json()["data"]) == 1
    assert calls["n"] == 1
    assert "notes:search:缓存:" in fake_redis.store  # 首次搜索已回填缓存

    second = client.get("/api/notes/search", params={"q": "缓存"})
    assert second.status_code == 200
    assert len(second.json()["data"]) == 1
    assert calls["n"] == 1  # 命中了缓存，未再查库


def test_search_empty_result_cached_penetration(client, fake_redis, monkeypatch):
    """缓存穿透防护：查不到的空结果写哨兵值 + 短 TTL，第二次不再穿透到库。"""
    calls = {"n": 0}
    original = main_app.crud.search_notes

    def counted_search(db, q, tag):
        calls["n"] += 1
        return original(db, q, tag)

    monkeypatch.setattr(main_app.crud, "search_notes", counted_search)

    first = client.get("/api/notes/search", params={"q": "不存在的关键词xyz"})
    assert first.status_code == 200
    assert first.json()["data"] == []

    key = "notes:search:不存在的关键词xyz:"
    assert fake_redis.store[key] == "EMPTY"  # 空结果哨兵
    assert fake_redis.ttls[key] == 60  # 短 TTL，防穿透

    second = client.get("/api/notes/search", params={"q": "不存在的关键词xyz"})
    assert second.json()["data"] == []
    assert calls["n"] == 1  # 哨兵命中，未再查库


def test_search_requires_q_or_tag(client):
    """q 与 tag 都缺省时返回统一结构的 422。"""
    resp = client.get("/api/notes/search")
    assert resp.status_code == 422
    assert resp.json()["code"] == 422


def test_llm_summary_success(client, monkeypatch):
    """LLM 摘要：调用成功返回摘要文本。"""
    note_id = client.post(
        "/api/notes", json={"title": "测试笔记", "content": "这是一段需要摘要的内容", "tags": []}
    ).json()["data"]["id"]

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "这是一段摘要"}}]}

    monkeypatch.setattr(main_app.httpx, "post", lambda *a, **k: FakeResponse())
    resp = client.post(f"/api/notes/{note_id}/summary")
    assert resp.status_code == 200
    assert resp.json()["data"]["summary"] == "这是一段摘要"


def test_llm_summary_call_failure(client, monkeypatch):
    """LLM 摘要：下游调用失败返回 502 统一结构，不影响主流程。"""
    note_id = client.post(
        "/api/notes", json={"title": "测试笔记2", "content": "内容", "tags": []}
    ).json()["data"]["id"]

    def boom(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(main_app.httpx, "post", boom)
    resp = client.post(f"/api/notes/{note_id}/summary")
    assert resp.status_code == 502
    assert resp.json()["code"] == 502