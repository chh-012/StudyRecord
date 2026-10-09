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