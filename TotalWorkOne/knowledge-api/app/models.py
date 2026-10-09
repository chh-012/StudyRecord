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