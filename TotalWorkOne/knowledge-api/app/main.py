"""FastAPI 入口：路由、依赖注入、统一响应与异常处理。"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse
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
    # 关闭默认文档页：其静态资源默认走 jsdelivr CDN，国内网络常超时导致白屏，
    # 下面自定义 /docs 与 /redoc，改用可访问的 unpkg 源
    docs_url=None,
    redoc_url=None,
)

# 文档页静态资源地址（unpkg 在本机实测可达，jsdelivr 不可达）
SWAGGER_JS_URL = "https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"
SWAGGER_CSS_URL = "https://unpkg.com/swagger-ui-dist@5/swagger-ui.css"
SWAGGER_FAVICON_URL = "https://unpkg.com/swagger-ui-dist@5/favicon-32x32.png"
REDOC_JS_URL = "https://unpkg.com/redoc@next/bundles/redoc.standalone.js"


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Swagger UI 文档页（静态资源走 unpkg，避免默认 CDN 不可达导致白屏）。"""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        swagger_js_url=SWAGGER_JS_URL,
        swagger_css_url=SWAGGER_CSS_URL,
        swagger_favicon_url=SWAGGER_FAVICON_URL,
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc_html():
    """ReDoc 文档页（同样改走 unpkg 源）。"""
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url=REDOC_JS_URL,
        redoc_favicon_url=SWAGGER_FAVICON_URL,
    )


# 教学用前端页面：单文件 HTML，样式与脚本全部内联，不依赖任何外部 CDN
STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
async def index_page():
    """返回教学演示页面（可直观看到请求经过的每一层）。"""
    return FileResponse(STATIC_DIR / "index.html")


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
    response: Response,
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
        # 教学用：告诉前端这次是命中了缓存（没查数据库）
        response.headers["X-Cache"] = "HIT"
        return ApiResponse(data=cached)

    notes = crud.search_notes(db, q, tag)
    results = [NoteOut.model_validate(n).model_dump(mode="json") for n in notes]
    cache.set_search(q or "", tag, results)
    response.headers["X-Cache"] = "MISS"
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