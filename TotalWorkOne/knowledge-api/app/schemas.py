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
        """ORM Tag 对象列表 → 名称列表；已是字符串则原样保留（缓存反序列化场景）。"""
        return [t.name if not isinstance(t, str) and hasattr(t, "name") else t for t in tags]


class SummaryOut(BaseModel):
    """LLM 摘要响应。"""

    summary: str