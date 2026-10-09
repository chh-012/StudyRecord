# 项目1：知识管理系统（knowledge-api）设计文档

> 日期：2026-10-09
> 阶段：Week2 学习计划 Day6-7「项目1：知识管理系统」综合串联

## 1. 背景与目标

将 Week1（Python 进阶 / pytest / FastAPI / MySQL 索引）+ Week2（Redis 缓存 / Linux 部署 / LLM 首接触）所学拼装为一个可运行的 Web 后端系统。完成定义：CRUD 全通 + 搜索走缓存 + pytest 跑绿 + Swagger 可演示 + 可部署 Linux。

## 2. 技术栈

| 组件 | 选型 | 说明 |
|------|------|------|
| Web 框架 | FastAPI + uvicorn | def 路由，同步方案 |
| ORM | SQLAlchemy 2.x（sync）+ PyMySQL | M:N 关系、索引建在海量文本外层 |
| 数据库 | MySQL 8.0 | utf8mb4，ORM 自动建表 |
| 缓存 | redis-py + Redis 7 | 搜索缓存 + 空结果短缓存防穿透 |
| 校验 | Pydantic v2 | 请求/响应双校验 |
| 配置 | python-dotenv | 全部敏感配置走 .env |
| 测试 | pytest + httpx + unittest.mock | SQLite 内存库隔离 MySQL、mock 隔离 Redis |
| 可选 | httpx 调 DeepSeek（OpenAI 兼容） | LLM 摘要接口，Key 不硬编码 |

## 3. 目录结构

```
knowledge-api/
├── app/
│   ├── main.py       # FastAPI 入口、路由、依赖注入、统一响应
│   ├── models.py     # SQLAlchemy 模型
│   ├── schemas.py    # Pydantic schema
│   ├── crud.py       # 数据库操作
│   ├── cache.py      # Redis 缓存封装（含故障降级）
│   └── config.py     # 读取 .env 配置
├── tests/
│   ├── conftest.py   # fixtures：SQLite 引擎、mock Redis、TestClient
│   └── test_notes.py # 用例：CRUD 主流程 / 缓存命中 / 缓存穿透 / LLM 摘要
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 4. 数据模型

- `notes`：id、title（varchar(200)，索引）、content（Text，可空）、created_at、updated_at
- `tags`：id、name（varchar(50)，unique 索引）
- `note_tags`：note_id + tag_id 复合主键，外键级联删除

建库后 `Base.metadata.create_all` 自动建表；README 附建库 SQL。

## 5. API 设计（统一响应 {code, message, data}）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/notes | 创建笔记（title 必填、content 可空、tags 列表，标签不存在自动建） |
| GET | /api/notes | 列表分页（page/page_size），支持 ?tag= 筛选 |
| GET | /api/notes/{id} | 详情（含标签） |
| PUT | /api/notes/{id} | 更新标题/内容/标签，失效搜索缓存 |
| DELETE | /api/notes/{id} | 删除（级联删关联），失效搜索缓存 |
| GET | /api/notes/search?q=&tag= | 搜索：q 对标题/内容 LIKE 模糊；tag 精确筛选（AND）；q/tag 至少传一个 |
| POST | /api/notes/{id}/summary | LLM 摘要（加分项） |

- 分页响应：`{items, total, page, page_size}`
- 成功 `code=0`；参数/校验错误 422；不存在 404；LLM 失败 502，错误信息入 message

## 6. 缓存设计（Redis）

- key：`notes:search:{q}:{tag}`，TTL 300s
- 未命中 → 查 MySQL → 写回。命中直接返回
- **缓存穿透防护**：查不到的空结果写哨兵值 `EMPTY`，TTL 60s
- **失效策略**：创建/更新/删除时 SCAN 清理 `notes:search:*` 前缀
- **优雅降级**：Redis 连接异常只记 warning 日志，业务直查 MySQL 不报错（本机仅有 MySQL 8 时的实测方案）

## 7. 日志与错误处理

- `logging`：uvicorn 统一日志，cache 层异常走 `logger.warning`
- 全局兜底：未捕获异常返回 `{code: 1, message: "internal server error"}` + 500

## 8. 测试策略（mock 隔离，独立可跑）

- DB：SQLite 内存库（`StaticPool`），不依赖 MySQL；依赖注入覆盖 `get_db`
- Redis：`unittest.mock` patch `RedisCache` 的方法，不依赖 Redis 进程
- 用例（≥4）：① CRUD 主流程（建→列→标签筛选→详情→改→删）② 缓存命中不查库 ③ 空结果穿透哨兵缓存 ④ LLM 摘要成功/失败

## 9. 部署

README 写明：本地启动（建库 → pip install → uvicorn）→ Swagger `/docs` → Linux 部署命令序列（venv + systemd 服务单元 + nohup 备选方案）。

## 10. 验收标准

- [x] 目录结构严格符合要求
- [ ] uvicorn 启动后 Swagger 可访问（有 MySQL 8 可实测）
- [ ] pytest 全部用例通过（mock 隔离，独立运行）
- [ ] 笔记标题、标签名建索引
- [ ] .env 配置外置、.gitignore 忽略敏感文件
- [ ] LLM 摘要接口 Key 不硬编码