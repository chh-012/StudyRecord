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