"""Redis 缓存封装：搜索缓存读写 + 空结果哨兵防穿透 + 故障优雅降级。"""
import json
import logging

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

logger = logging.getLogger(__name__)


class RedisCache:
    """搜索缓存。

    - key：notes:search:{q}:{tag}，正常结果 TTL search_ttl 秒（默认 300）
    - 空结果写哨兵值 EMPTY，TTL empty_ttl 秒（默认 60），防止缓存穿透
    - Redis 故障（RedisError）只记 warning 日志，业务自动降级直查 MySQL
    """

    KEY_PREFIX = "notes:search:"
    EMPTY = "EMPTY"

    # 连接/读写超时（秒），并关闭自动重试。
    # 必须显式设置：redis-py 默认既无超时、又会自动重试 3 次，
    # Redis 未启动时单次操作要卡 10 秒以上（本机实测 9~15 秒），
    # 接口会直接超时——那样"故障降级"就形同虚设。
    # 本机实测：超时 1 秒 + 不重试 → 约 1 秒内失败并降级，请求不受影响。
    SOCKET_TIMEOUT = 1.0
    NO_RETRY = Retry(NoBackoff(), 0)

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
        self._client = client or redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            socket_connect_timeout=self.SOCKET_TIMEOUT,
            socket_timeout=self.SOCKET_TIMEOUT,
            retry=self.NO_RETRY,
        )
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