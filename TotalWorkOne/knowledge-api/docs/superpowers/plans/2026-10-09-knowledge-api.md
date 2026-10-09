# 知识管理系统（knowledge-api）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现一个笔记管理后端：笔记 CRUD + 多标签 + Redis 缓存搜索（含防穿透）+ LLM 摘要，可部署 Linux。

**Architecture:** FastAPI 同步方案。`main.py` 路由 + 依赖注入 → `crud.py` SQL 层 → `models.py` ORM；`cache.py` 封装 Redis（故障优雅降级）；`config.py` 统一读 .env；Pydantic v2 统一 `{code, message, data}` 响应。测试用 SQLite 内存库 + FakeRedis 完全隔离 MySQL/Redis。

**Tech Stack:** Python 3.10+ / FastAPI / SQLAlchemy 2.x + PyMySQL / redis-py / Pydantic v2 / pytest + httpx / python-dotenv

**Spec:** `docs/superpowers/specs/2026-10-09-knowledge-api-design.md`

---

## 约束与约定

- 项目根目录：`D:\AstudyRecord\TotalWorkOne\knowledge-api`
- git 仓库根在 `D:\AstudyRecord`（项目位于已有仓库内，提交路径带 `TotalWorkOne/knowledge-api/` 前缀）
- 环境：本机 Python 3.13.5；MySQL 8 已装（库名 `knowledge_db`）；**Redis 未装** → 测试必须隔离 Redis，运行时靠优雅降级
- TDD：先写失败测试 → 最小实现 → 跑绿 → 提交
- 所有命令在项目根目录执行；Windows PowerShell 环境

## 文件结构

| 文件 | 职责 |
|------|------|
| Create `app/config.py` | dotenv 读配置 + Settings 单例 |
| Create `app/models.py` | Note/Tag/note_tags，索引与级联 |
| Create `app/schemas.py` | ApiResponse/NoteCreate/NoteUpdate/NoteOut/SummaryOut |
| Create `app/cache.py` | RedisCache：命中/回填/哨兵防穿透/降级 |
| Create `app/crud.py` | create/list/get/update/delete/search_notes |
| Create `app/main.py` | 路由、get_db、异常处理、LLM 调用 |
| Create `app/__init__.py` | 空包标记 |
| Create `tests/__init__.py` | 空包标记 |
| Create `tests/conftest.py` | SQLite 引擎 + FakeRedis + client fixture |
| Create `tests/test_notes.py` | 6 个测试用例 |
| Create `requirements.txt` / `.env.example` / `.gitignore` / `README.md` | 依赖与部署文档 |

---

## Task 1: 环境准备 + 编写全部失败测试（红）

**Files:**
- Create `requirements.txt`
- Create `tests/__init__.py`
- Create `tests/conftest.py`
- Create `tests/test_notes.py`

- [ ] **Step 1.1: 创建虚拟环境并写 requirements.txt**

```text
fastapi>=0.115
uvicorn[standard]>=0.30
SQLAlchemy>=2.0
PyMySQL>=1.1
cryptography>=42.0
redis>=5.0
pydantic>=2.6
python-dotenv>=1.0
httpx>=0.27
pytest>=8.0
```

运行：`python -m venv .venv && .venv\Scripts\python -m pip install -U pip && .venv\Scripts\python -m pip install -r requirements.txt`

- [ ] **Step 1.2: 编写 tests/conftest.py**

```python
"""pytest fixtures：SQLite 内存库 + FakeRedis + TestClient，完全隔离 MySQL/Redis。"""
import os

# 必须在导入 app.main 之前设置，保证测试环境 LLM 配置可预期
os.environ.setdefault("LLM_API_KEY", "test-key")
os.environ.setdefault("LLM_API_BASE", "https://llm.example.com/v1")
os.environ.setdefault("LLM_MODEL", "test-model")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_app
from app.cache import RedisCache
from app.main import app, get_db
from app.models import Base


class FakeRedis:
    """极简内存版 Redis 客户端，供 RedisCache 注入，验证缓存行为无需真 Redis。"""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self.store[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                self.ttls.pop(key, None)
                count += 1
        return count

    def scan_iter(self, match: str | None = None, count: int = 100):
        prefix = match.rstrip("*") if match else ""
        for key in list(self.store.keys()):
            if key.startswith(prefix):
                yield key


@pytest.fixture()
def test_engine():
    """SQLite 内存引擎：StaticPool 保证所有请求共享同一内存库。"""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def db_session(test_engine):
    testing_session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    session = testing_session()
    yield session
    session.close()


@pytest.fixture()
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest.fixture()
def client(db_session, fake_redis, monkeypatch):
    """TestClient：DB 覆盖为 SQLite、缓存覆盖为 FakeRedis。"""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    test_cache = RedisCache(host="unused", port=0, db=0, client=fake_redis)
    monkeypatch.setattr(main_app, "cache", test_cache)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

- [ ] **Step 1.3: 编写 tests/test_notes.py**

```python
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
```

- [ ] **Step 1.4: 运行测试确认失败（红）**

运行：`.venv\Scripts\python -m pytest tests -v`
Expected: 收集失败 `ModuleNotFoundError: No module named 'app'`

---

## Task 2: config / models / schemas / cache / crud（实现到测试可导入）

**Files:**
- Create `app/__init__.py`
- Create `app/config.py`
- Create `app/models.py`
- Create `app/schemas.py`
- Create `app/cache.py`
- Create `app/crud.py`

- [ ] **Step 2.1: app/__init__.py（空文件）**

- [ ] **Step 2.2: app/config.py**

```python
"""读取 .env 配置。所有连接信息与密钥统一从环境变量读取，不硬编码。"""
import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

# 项目根目录：app/ 的上一层
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """全局配置对象，字段与 .env.example 一一对应。"""

    # MySQL
    mysql_host: str
    mysql_port: int
    mysql_user: str
    mysql_password: str
    mysql_db: str
    # Redis
    redis_host: str
    redis_port: int
    redis_db: int
    # 缓存 TTL（秒）
    search_cache_ttl: int
    empty_cache_ttl: int
    # LLM（OpenAI 兼容接口）
    llm_api_base: str
    llm_api_key: str
    llm_model: str
    llm_timeout: float

    @property
    def database_url(self) -> str:
        """SQLAlchemy 连接串（utf8mb4 支持中文与 emoji）。"""
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    """配置单例：进程内只解析一次 .env。"""
    return Settings(
        mysql_host=_env("MYSQL_HOST", "127.0.0.1"),
        mysql_port=_env_int("MYSQL_PORT", 3306),
        mysql_user=_env("MYSQL_USER", "root"),
        mysql_password=_env("MYSQL_PASSWORD", ""),
        mysql_db=_env("MYSQL_DB", "knowledge_db"),
        redis_host=_env("REDIS_HOST", "127.0.0.1"),
        redis_port=_env_int("REDIS_PORT", 6379),
        redis_db=_env_int("REDIS_DB", 0),
        search_cache_ttl=_env_int("SEARCH_CACHE_TTL", 300),
        empty_cache_ttl=_env_int("EMPTY_CACHE_TTL", 60),
        llm_api_base=_env("LLM_API_BASE", "https://api.deepseek.com/v1"),
        llm_api_key=_env("LLM_API_KEY", ""),
        llm_model=_env("LLM_MODEL", "deepseek-chat"),
        llm_timeout=_env_float("LLM_TIMEOUT", 30.0),
    )
```

- [ ] **Step 2.3: app/models.py**

```python
"""SQLAlchemy ORM 模型：笔记（Note）与标签（Tag）多对多。"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    """naive UTC 时间：MySQL DATETIME 无时区信息，统一按 UTC 存储。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


# 笔记-标签关联表：复合主键 + 双方级联删除
note_tags = Table(
    "note_tags",
    Base.metadata,
    Column("note_id", Integer, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Note(Base):
    """笔记：标题必填（索引），内容可空。"""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )

    tags: Mapped[list["Tag"]] = relationship(
        secondary=note_tags, back_populates="notes", lazy="selectin"
    )


class Tag(Base):
    """标签：名称唯一（唯一索引），创建笔记时自动创建。"""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)

    notes: Mapped[list[Note]] = relationship(
        secondary=note_tags, back_populates="tags", lazy="selectin"
    )
```

- [ ] **Step 2.4: app/schemas.py**

```python
"""Pydantic v2 请求/响应模型。统一响应结构：{code, message, data}。"""
from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应外壳：code=0 成功，非 0 失败。"""

    code: int = 0
    message: str = "ok"
    data: T | None = None


class PageData(BaseModel, Generic[T]):
    """分页数据载荷。"""

    items: list[T]
    total: int
    page: int
    page_size: int


def _clean_tags(tags: list[str]) -> list[str]:
    """标签清理：去空白、去重、丢弃空串。"""
    seen: set[str] = set()
    result: list[str] = []
    for raw in tags:
        name = raw.strip()
        if name and name not in seen:
            seen.add(name)
            result.append(name)
    return result


class NoteCreate(BaseModel):
    """创建笔记：标题必填，内容可空，标签缺省为空列表。"""

    title: str = Field(..., min_length=1, max_length=200, description="笔记标题")
    content: str | None = Field(None, description="笔记内容，可空")
    tags: list[str] = Field(default_factory=list, description="标签列表；不存在的标签自动创建")

    @field_validator("title")
    @classmethod
    def strip_title(cls, title: str) -> str:
        title = title.strip()
        if not title:
            raise ValueError("标题不能为空白")
        return title

    @field_validator("tags")
    @classmethod
    def straighten_tags(cls, tags: list[str]) -> list[str]:
        return _clean_tags(tags)


class NoteUpdate(BaseModel):
    """更新笔记：字段全部可选，只更新传入的字段。"""

    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = None
    tags: list[str] | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, title: str | None) -> str | None:
        if title is None:
            return None
        title = title.strip()
        if not title:
            raise ValueError("标题不能为空白")
        return title

    @field_validator("tags")
    @classmethod
    def straighten_tags(cls, tags: list[str] | None) -> list[str] | None:
        if tags is None:
            return None
        return _clean_tags(tags)


class NoteOut(BaseModel):
    """笔记响应：tags 直接输出名称列表。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str | None
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def tag_names(cls, tags: list) -> list[str]:
        """ORM Tag 对象列表 → 名称列表；已是字符串则原样保留。"""
        return [t.name if isinstance(t, str) is False and hasattr(t, "name") else t for t in tags]


class SummaryOut(BaseModel):
    """LLM 摘要响应。"""

    summary: str
```

> 注意 `tag_names` 写法为兼容「Tag 对象」与「缓存反序列化后的 str」两种输入。

- [ ] **Step 2.5: app/cache.py**

```python
"""Redis 缓存封装：搜索缓存读写 + 空结果哨兵防穿透 + 故障优雅降级。"""
import json
import logging

import redis

logger = logging.getLogger(__name__)


class RedisCache:
    """搜索缓存。

    - key：notes:search:{q}:{tag}，正常结果 TTL search_ttl 秒（默认 300）
    - 空结果写哨兵值 EMPTY，TTL empty_ttl 秒（默认 60），防止缓存穿透
    - Redis 故障（RedisError）只记 warning 日志，业务自动降级直查 MySQL
    """

    KEY_PREFIX = "notes:search:"
    EMPTY = "EMPTY"

    def __init__(
        self,
        host: str,
        port: int,
        db: int,
        search_ttl: int = 300,
        empty_ttl: int = 60,
        client: redis.Redis | None = None,
    ):
        # client 参数用于测试注入 FakeRedis；生产环境为 None 时惰性连接真 Redis
        self._client = client or redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self._search_ttl = search_ttl
        self._empty_ttl = empty_ttl

    def _key(self, q: str, tag: str | None) -> str:
        return f"{self.KEY_PREFIX}{q}:{tag or ''}"

    def get_search(self, q: str, tag: str | None) -> list[dict] | None:
        """读取搜索缓存。

        返回 None = 未命中（需查库回填）；返回 [] = 命中空结果哨兵（无需查库）；
        返回 list[dict] = 命中正常结果。
        """
        try:
            raw = self._client.get(self._key(q, tag))
        except redis.RedisError as exc:
            logger.warning("Redis 读取失败，降级直查数据库: %s", exc)
            return None
        if raw is None:
            return None
        if raw == self.EMPTY:
            return []
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("缓存内容损坏，忽略: %s", self._key(q, tag))
            return None

    def set_search(self, q: str, tag: str | None, results: list[dict]) -> None:
        """回填搜索缓存；空结果写哨兵 + 短 TTL。"""
        payload = self.EMPTY if not results else json.dumps(results, ensure_ascii=False, default=str)
        ttl = self._empty_ttl if not results else self._search_ttl
        try:
            self._client.set(self._key(q, tag), payload, ex=ttl)
        except redis.RedisError as exc:
            logger.warning("Redis 写入失败，跳过缓存回填: %s", exc)

    def invalidate_all(self) -> None:
        """清除全部搜索缓存（笔记增删改后调用）。"""
        try:
            keys = list(self._client.scan_iter(match=f"{self.KEY_PREFIX}*", count=100))
            if keys:
                self._client.delete(*keys)
        except redis.RedisError as exc:
            logger.warning("Redis 缓存清理失败，跳过: %s", exc)
```

- [ ] **Step 2.6: app/crud.py**

```python
"""数据库操作层：全部 SQL 集中在此，路由层不写 SQL。"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Note, Tag
from app.schemas import NoteCreate, NoteUpdate


def _get_or_create_tags(db: Session, tag_names: list[str]) -> list[Tag]:
    """按名称查找标签，不存在则创建；flush 保证新增标签先拿到主键。"""
    tags: list[Tag] = []
    for name in tag_names:
        tag = db.execute(select(Tag).where(Tag.name == name)).scalar_one_or_none()
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


def create_note(db: Session, data: NoteCreate) -> Note:
    """创建笔记：标题/内容 + 自动创建不存在的标签。"""
    note = Note(title=data.title, content=data.content)
    note.tags = _get_or_create_tags(db, data.tags)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_notes(db: Session, page: int, page_size: int, tag: str | None = None) -> tuple[int, list[Note]]:
    """分页列表；tag 非空时按标签名精确筛选。"""
    stmt = select(Note)
    count_stmt = select(func.count(Note.id))
    if tag:
        stmt = stmt.join(Note.tags).where(Tag.name == tag)
        count_stmt = count_stmt.join(Note.tags).where(Tag.name == tag)
    total = db.execute(count_stmt).scalar_one()
    stmt = (
        stmt.order_by(Note.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    notes = db.execute(stmt).scalars().unique().all()
    return total, list(notes)


def get_note(db: Session, note_id: int) -> Note | None:
    return db.execute(select(Note).where(Note.id == note_id)).scalar_one_or_none()


def update_note(db: Session, note: Note, data: NoteUpdate) -> Note:
    """更新笔记：只更新传入的字段；传了 tags 则整体替换标签集合。"""
    if data.title is not None:
        note.title = data.title
    if data.content is not None:
        note.content = data.content
    if data.tags is not None:
        note.tags = _get_or_create_tags(db, data.tags)
    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, note: Note) -> None:
    """删除笔记；note_tags 关联由外键 ondelete CASCADE 清理。"""
    db.delete(note)
    db.commit()


def search_notes(db: Session, q: str | None, tag: str | None) -> list[Note]:
    """搜索：q 对标题/内容 LIKE 模糊匹配，tag 精确筛选，两者 AND 关系。"""
    stmt = select(Note)
    if tag:
        stmt = stmt.join(Note.tags).where(Tag.name == tag)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Note.title.like(pattern), Note.content.like(pattern)))
    stmt = stmt.order_by(Note.updated_at.desc())
    return list(db.execute(stmt).scalars().unique().all())
```

- [ ] **Step 2.7: 运行测试确认仍有失败（红色保持在路由缺失）**

运行：`.venv\Scripts\python -m pytest tests -v`
Expected: `ModuleNotFoundError: No module named 'app.main'`（conftest 导入失败）

---

## Task 3: main.py 路由层（绿）

**Files:**
- Create `app/main.py`

- [ ] **Step 3.1: app/main.py**

```python
"""FastAPI 入口：路由、依赖注入、统一响应与异常处理。"""
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import crud
from app.cache import RedisCache
from app.config import get_settings
from app.models import Base
from app.schemas import ApiResponse, NoteCreate, NoteOut, NoteUpdate, PageData, SummaryOut

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

# 全局引擎与缓存实例；engine 为惰性连接，MySQL 不可用不影响进程启动
engine = create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
cache = RedisCache(
    host=settings.redis_host,
    port=settings.redis_port,
    db=settings.redis_db,
    search_ttl=settings.search_cache_ttl,
    empty_ttl=settings.empty_cache_ttl,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时自动建表；失败只告警，不阻断启动（便于先启动服务再补数据库）。"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表结构检查完成")
    except Exception as exc:  # 数据库未就绪时降级告警
        logger.warning("自动建表失败（请确认 MySQL 已启动且已建库）: %s", exc)
    yield


app = FastAPI(
    title="知识管理系统 API",
    description="Week2 项目1：FastAPI + SQLAlchemy + MySQL + Redis",
    version="1.0.0",
    lifespan=lifespan,
)


def get_db():
    """请求级数据库会话依赖。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTPException 统一包装为 {code, message, data}。"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail), "data": None},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic 校验错误统一包装，细节放入 data。"""
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "请求参数校验失败", "data": exc.errors()},
    )


# ---------- 笔记 CRUD ----------

@app.post("/api/notes", response_model=ApiResponse[NoteOut], status_code=201)
def create_note(payload: NoteCreate, db: Session = Depends(get_db)):
    note = crud.create_note(db, payload)
    cache.invalidate_all()
    return ApiResponse(message="创建成功", data=NoteOut.model_validate(note))


@app.get("/api/notes", response_model=ApiResponse[PageData[NoteOut]])
def list_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    tag: str | None = Query(None, max_length=50),
    db: Session = Depends(get_db),
):
    total, notes = crud.list_notes(db, page, page_size, tag)
    data = PageData(
        items=[NoteOut.model_validate(n) for n in notes],
        total=total,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=data)


# 注意：/search 路径必须先于 /{note_id} 声明
@app.get("/api/notes/search", response_model=ApiResponse[list[NoteOut]])
def search_notes(
    q: str | None = Query(None, max_length=100),
    tag: str | None = Query(None, max_length=50),
    db: Session = Depends(get_db),
):
    q = q.strip() if q else None
    tag = tag.strip() if tag else None
    if not q and not tag:
        raise HTTPException(422, "q 与 tag 至少传一个")

    cached = cache.get_search(q or "", tag)
    if cached is not None:
        return ApiResponse(data=cached)

    notes = crud.search_notes(db, q, tag)
    results = [NoteOut.model_validate(n).model_dump(mode="json") for n in notes]
    cache.set_search(q or "", tag, results)
    return ApiResponse(data=results)


@app.get("/api/notes/{note_id}", response_model=ApiResponse[NoteOut])
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = crud.get_note(db, note_id)
    if note is None:
        raise HTTPException(404, f"笔记 {note_id} 不存在")
    return ApiResponse(data=NoteOut.model_validate(note))


@app.put("/api/notes/{note_id}", response_model=ApiResponse[NoteOut])
def update_note(note_id: int, payload: NoteUpdate, db: Session = Depends(get_db)):
    note = crud.get_note(db, note_id)
    if note is None:
        raise HTTPException(404, f"笔记 {note_id} 不存在")
    note = crud.update_note(db, note, payload)
    cache.invalidate_all()
    return ApiResponse(message="更新成功", data=NoteOut.model_validate(note))


@app.delete("/api/notes/{note_id}", response_model=ApiResponse[None])
def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = crud.get_note(db, note_id)
    if note is None:
        raise HTTPException(404, f"笔记 {note_id} 不存在")
    crud.delete_note(db, note)
    cache.invalidate_all()
    return ApiResponse(message="删除成功")


# ---------- LLM 摘要（加分项） ----------

def _call_llm(title: str, content: str) -> str:
    """调用 OpenAI 兼容 LLM 接口生成摘要；API Key 从配置读取，绝不硬编码。"""
    if not settings.llm_api_key:
        raise HTTPException(502, "未配置 LLM_API_KEY，无法生成摘要")
    prompt = f"请用不超过 100 字的中文总结以下笔记：\n标题：{title}\n内容：{content}"
    try:
        resp = httpx.post(
            f"{settings.llm_api_base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
            },
            timeout=settings.llm_timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except httpx.HTTPError as exc:
        logger.error("LLM 调用失败: %s", exc)
        raise HTTPException(502, f"LLM 调用失败: {exc}")


@app.post("/api/notes/{note_id}/summary", response_model=ApiResponse[SummaryOut])
def generate_summary(note_id: int, db: Session = Depends(get_db)):
    note = crud.get_note(db, note_id)
    if note is None:
        raise HTTPException(404, f"笔记 {note_id} 不存在")
    summary = _call_llm(note.title, note.content or "")
    return ApiResponse(data=SummaryOut(summary=summary))
```

- [ ] **Step 3.2: 运行全部测试，逐个修复直至全绿**

运行：`.venv\Scripts\python -m pytest tests -v`
Expected: `6 passed`

**可能的坑（实施时核对）：**
- `NoteOut.tag_names` 的 `isinstance(t, str) is False` 写法：若写成 `isinstance(t, str)` 会导致 str 分支返回 `t.name`（不存在）→ AttributeError。必须是「非 str 且有 name 属性 → 取 name」
- conftest 中 `os.environ.setdefault` 必须在 `import app.main` 之前（已满足）
- 缓存 key 断言 `notes:search:缓存:`：q 为中文不转小写，直接拼接（与 cache._key 一致）
- sqlite 中 `unique=True` 的标签写入依赖 crud flush → 已处理

- [ ] **Step 3.3: 提交**

```bash
git add TotalWorkOne/knowledge-api/app TotalWorkOne/knowledge-api/tests TotalWorkOne/knowledge-api/requirements.txt
git commit -m "feat(knowledge-api): FastAPI 笔记 CRUD + Redis 搜索缓存 + LLM 摘要，pytest 6 用例全绿"
```

---

## Task 4: 工程配套文件 + 全量验证 + 最终提交

**Files:**
- Create `.env.example`
- Create `.gitignore`
- Create `README.md`

- [ ] **Step 4.1: .env.example**

```ini
# ========== MySQL ==========
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=knowledge_db

# ========== Redis ==========
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0

# ========== 搜索缓存 TTL（秒） ==========
SEARCH_CACHE_TTL=300
EMPTY_CACHE_TTL=60

# ========== LLM（OpenAI 兼容接口，可选） ==========
# 例如 DeepSeek：base=https://api.deepseek.com/v1 model=deepseek-chat
LLM_API_BASE=https://api.deepseek.com/v1
LLM_API_KEY=
LLM_MODEL=deepseek-chat
LLM_TIMEOUT=30.0
```

- [ ] **Step 4.2: .gitignore**

```gitignore
# 环境变量（含密钥，严禁提交）
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
.venv/
venv/

# 测试与缓存
.pytest_cache/
.cache/
htmlcov/
.coverage

# IDE
.idea/
.vscode/
*.log
```

- [ ] **Step 4.3: README.md**

```markdown
# 知识管理系统（knowledge-api）

Week2 项目1：FastAPI + SQLAlchemy 2.x + MySQL 8 + Redis 7 + Pydantic v2 + pytest。

## 功能

- 笔记 CRUD（标题必填、内容可空、多标签，标签自动创建）
- 列表分页 + 按标签筛选
- 搜索接口：Redis 缓存加速，空结果短缓存防穿透，Redis 故障自动降级
- LLM 摘要接口（OpenAI 兼容，Key 放 .env）
- 统一响应结构 `{code, message, data}`

## 接口速览（启动后访问 /docs 查看 Swagger）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/notes | 创建笔记 |
| GET | /api/notes?page=1&page_size=10&tag=xx | 列表分页/标签筛选 |
| GET | /api/notes/{id} | 详情 |
| PUT | /api/notes/{id} | 更新 |
| DELETE | /api/notes/{id} | 删除 |
| GET | /api/notes/search?q=xx&tag=xx | 搜索（q/tag 至少一个） |
| POST | /api/notes/{id}/summary | LLM 摘要（需配 LLM_API_KEY） |

## 本地启动

```bash
# 1. 建库（MySQL 8）
mysql -uroot -p -e "CREATE DATABASE IF NOT EXISTS knowledge_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. 虚拟环境 + 依赖
python -m venv .venv
.venv\Scripts\activate        # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# 3. 配置
copy .env.example .env        # 修改其中的数据库密码

# 4. 启动（Redis 未安装也可启动，缓存自动降级）
uvicorn app.main:app --reload
```

Swagger 文档：http://127.0.0.1:8000/docs

## 运行测试（无需 MySQL/Redis，全 mock 隔离）

```bash
pytest tests -v
```

## Linux 部署

前置：已安装 MySQL 8、Redis 7（`apt install redis-server`）、Python 3.10+。

```bash
# 1. 上传代码
scp -r knowledge-api user@server:/opt/
cd /opt/knowledge-api

# 2. 建库与虚拟环境
mysql -uroot -p -e "CREATE DATABASE IF NOT EXISTS knowledge_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. 配置并启动（方式一：systemd，推荐）
cp .env.example .env && vi .env   # 填数据库密码等
sudo tee /etc/systemd/system/knowledge-api.service > /dev/null <<'EOF'
[Unit]
Description=Knowledge API
After=network.target mysql.service redis-server.service

[Service]
User=www-data
WorkingDirectory=/opt/knowledge-api
ExecStart=/opt/knowledge-api/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
EnvironmentFile=/opt/knowledge-api/.env

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now knowledge-api
journalctl -u knowledge-api -f          # 看日志
curl http://127.0.0.1:8000/docs         # 验证

# 方式二：nohup 后台启动（无 systemd 权限时）
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &
```

## 配置项（.env）

| 变量 | 默认 | 说明 |
|------|------|------|
| MYSQL_HOST/PORT/USER/PASSWORD/DB | 127.0.0.1/3306/root/空/knowledge_db | MySQL 连接 |
| REDIS_HOST/PORT/DB | 127.0.0.1/6379/0 | Redis 连接 |
| SEARCH_CACHE_TTL | 300 | 搜索缓存秒数 |
| EMPTY_CACHE_TTL | 60 | 空结果短缓存（防穿透） |
| LLM_API_BASE / LLM_API_KEY / LLM_MODEL / LLM_TIMEOUT | DeepSeek 默认 | LLM 摘要（可选） |
```

- [ ] **Step 4.4: 全量验证**

运行：`.venv\Scripts\python -m pytest tests -v`
Expected: `6 passed in <时间>s`

- [ ] **Step 4.5: 最终提交**

```bash
git add TotalWorkOne/knowledge-api
git commit -m "docs(knowledge-api): 补充 README 部署文档、.env.example 与 .gitignore"
```

---

## 自审记录

1. **Spec 覆盖**：CRUD（Task3 路由+Task2 crud）✓；标签自动创建（crud._get_or_create_tags）✓；搜索缓存+穿透（cache.py + 测试2/3）✓；统一响应（schemas.ApiResponse + 异常处理器）✓；Pydantic 校验 ✓；索引（models title index/tag unique index）✓；.env 配置 ✓；pytest mock 隔离 ✓；LLM 摘要 ✓；README 本地+Linux 部署 ✓
2. **占位符**：无 TBD/TODO
3. **类型一致性**：`RedisCache(host, port, db, search_ttl, empty_ttl, client)` 在 main.py、conftest.py 两处调用签名一致；`crud.search_notes(db, q, tag)` 签名与 main 调用一致；`cache.get_search(q or "", tag)` 三处（get/set/_key）一致