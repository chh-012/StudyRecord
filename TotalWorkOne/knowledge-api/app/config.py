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