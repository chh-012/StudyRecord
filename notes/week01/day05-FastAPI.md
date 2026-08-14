# Day05 · FastAPI 初体验 + 工程工具链 + Git 规范

> 日期：2026-08-19 ｜ 深度目标：L2 ｜ 状态：□ 未完成 □ 已完成

## 1. 核心概念

（用自己的话写 2-3 句——写不出来 = 没学会）

- **FastAPI**：基于类型提示的 Python Web 框架，自动生成 OpenAPI/Swagger 文档，自带 Pydantic 数据校验，天然支持异步。核心：路径参数、查询参数、请求体（Pydantic 模型）、响应模型。
- **工程工具链**：venv（环境隔离）→ pip/poetry（依赖管理）→ logging（日志分级，替代 print）。这些是"每天每个项目都用"的肌肉记忆。
- **Git 规范**：分支策略 + commit message 规范 + `.gitignore` + PR 流程——团队协作的底线，一个人也要按规范练。

## 2. 关键代码

```python
# main.py —— todo CRUD（内存版，先跑通接口）
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(title="Todo API", version="0.1.0")

class Todo(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    done: bool = False

class TodoCreate(Todo):
    pass

class TodoOut(Todo):
    id: int

todos: dict[int, Todo] = {}
next_id = 1

@app.get("/todos", response_model=list[TodoOut])      # 查询参数: ?done=true
def list_todos(done: Optional[bool] = None):
    items = [(i, t) for i, t in todos.items() if done is None or t.done == done]
    return [TodoOut(id=i, **t.model_dump()) for i, t in items]

@app.post("/todos", response_model=TodoOut, status_code=201)
def create_todo(body: TodoCreate):
    global next_id
    todos[next_id] = Todo(**body.model_dump())
    out = TodoOut(id=next_id, **body.model_dump())
    next_id += 1
    return out

@app.get("/todos/{todo_id}", response_model=TodoOut)
def get_todo(todo_id: int):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo 不存在")
    return TodoOut(id=todo_id, **todos[todo_id].model_dump())

@app.put("/todos/{todo_id}", response_model=TodoOut)
def update_todo(todo_id: int, body: TodoCreate):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo 不存在")
    todos[todo_id] = Todo(**body.model_dump())
    return TodoOut(id=todo_id, **body.model_dump())

@app.delete("/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
    todos.pop(todo_id, None)

# 启动: uvicorn main:app --reload
# 文档: http://127.0.0.1:8000/docs  (自动 Swagger UI)
```

```bash
# 工具链（每天用）
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install fastapi uvicorn pydantic
pip freeze > requirements.txt    # 锁定依赖
```

```python
# logging 替代 print（settings.py）
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
logger.info("服务启动")
```

## 3. 原理图

```
浏览器/curl ──HTTP──► FastAPI
                        │
                        ├─ 路由匹配 (路径+方法)
                        ├─ Pydantic 校验请求体 ──失败──► 422 自动报错
                        ├─ 执行处理函数
                        ├─ Pydantic 校验响应模型
                        └─ 返回 JSON + 自动登记到 /docs (OpenAPI)

Git 提交流程（单人也要规范）：
工作区 → git add → 暂存区 → git commit → 本地仓库 → git push → 远程
```

## 4. 面试问答

**Q1：FastAPI vs Flask vs Django？**
> FastAPI：类型提示驱动、自动文档、异步支持、性能高（uvicorn），现代首选；Flask：轻量灵活但要自己拼校验/文档；Django：全家桶（ORM/Admin/认证内置），适合大项目，学习曲线陡。

**Q2：Pydantic 模型是干什么的？**
> 请求/响应数据的声明式校验和序列化：自动类型转换、范围校验（Field）、嵌套模型、错误信息自动返回 422。基于类型提示，IDE 友好。

**Q3：`response_model` 和直接返回 dict 的区别？**
> `response_model` 声明返回结构：自动过滤多余字段（如密码）、类型转换、生成 OpenAPI 文档。返回的数据会"按声明裁剪"。

**Q4：路径参数 vs 查询参数？**
> 路径参数 `/todos/{id}` 用于定位资源（必须传）；查询参数 `?done=true&page=2` 用于筛选/分页（可缺省，配默认值）。

**Q5：虚拟环境为什么必要？**
> 隔离不同项目的依赖版本（A 项目要 requests 2.x，B 项目要 3.x），避免污染系统 Python，也保证"换台机器 pip install -r requirements.txt 能复现"。

## 5. 踩坑记录（今天实际遇到 + 常见坑）

| 坑 | 现象 | 解决 |
|------|------|------|
| （待填：今天真实报错） | | |
| 没激活 venv 就 pip install | 包装到系统 Python，项目里 import 不到 | 先 `source .venv/bin/activate`，`which pip` 确认路径 |
| 路径参数写错顺序 | `/todos/{id}` 和 `/todos/me` 冲突 | 静态路由写在动态路由前面 |
| 忘记 `response_model` | 返回里带了多余字段 | 接口一律声明 `response_model` |
| commit message 随意 | 几个月后看不懂"update"改了什么 | 用 `type(scope): 描述`，type 见下方规范 |

## 6. 待补 / 明日预告

- [ ] 用 curl/postman 完整测一遍 5 个接口（GET/POST/PUT/DELETE/过滤）
- [ ] 给 todo 接口加 CORS 中间件（后面 Vue3 前端联调用）
- 明日：MySQL 深化（上）——B+ 树索引
