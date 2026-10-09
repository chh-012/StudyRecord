# 知识管理系统（knowledge-api）

Week2 项目1：FastAPI + SQLAlchemy 2.x + MySQL 8 + Redis 7 + Pydantic v2 + pytest。

## 功能

- 笔记 CRUD（标题必填、内容可空、多标签，标签不存在自动创建）
- 列表分页 + 按标签筛选
- 搜索接口：Redis 缓存加速，空结果短缓存防穿透，Redis 故障自动降级
- LLM 摘要接口（OpenAI 兼容，Key 放 .env 不硬编码）
- 统一响应结构 `{code, message, data}`

## 项目结构

```
knowledge-api/
├── app/
│   ├── main.py       # FastAPI 入口：路由、依赖注入、异常处理
│   ├── models.py     # SQLAlchemy 模型（notes / tags / note_tags）
│   ├── schemas.py    # Pydantic v2 请求/响应模型
│   ├── crud.py       # 数据库操作
│   ├── cache.py      # Redis 缓存封装（防穿透 + 故障降级）
│   └── config.py     # 读取 .env 配置
├── tests/
│   ├── conftest.py   # SQLite 内存库 + FakeRedis，mock 隔离 MySQL/Redis
│   └── test_notes.py # 6 个用例：CRUD / 缓存命中 / 缓存穿透 / LLM 摘要
├── requirements.txt
├── .env.example
└── .gitignore
```

## 接口速览（启动后访问 /docs 查看 Swagger）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/notes | 创建笔记（title 必填、content 可空、tags 列表） |
| GET | /api/notes?page=1&page_size=10&tag=xx | 列表分页 / 按标签筛选 |
| GET | /api/notes/{id} | 详情（含标签） |
| PUT | /api/notes/{id} | 更新标题/内容/标签 |
| DELETE | /api/notes/{id} | 删除 |
| GET | /api/notes/search?q=xx&tag=xx | 搜索（q/tag 至少传一个，走 Redis 缓存） |
| POST | /api/notes/{id}/summary | LLM 摘要（需配置 LLM_API_KEY） |

## 本地启动

```bash
# 1. 建库（MySQL 8）
mysql -uroot -p -e "CREATE DATABASE IF NOT EXISTS knowledge_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 2. 虚拟环境 + 依赖
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

# 3. 配置
copy .env.example .env          # 修改 MYSQL_PASSWORD 等项目实际值

# 4. 启动（Redis 未安装也可启动，缓存自动降级直查 MySQL）
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
journalctl -u knowledge-api -f          # 查看日志
curl http://127.0.0.1:8000/docs         # 验证

# 方式二：nohup 后台启动（无 systemd 权限时）
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &
```

## 配置项（.env）

| 变量 | 默认 | 说明 |
|------|------|------|
| MYSQL_HOST / MYSQL_PORT | 127.0.0.1 / 3306 | MySQL 地址 |
| MYSQL_USER / MYSQL_PASSWORD | root / 空 | MySQL 账号 |
| MYSQL_DB | knowledge_db | 数据库名 |
| REDIS_HOST / REDIS_PORT / REDIS_DB | 127.0.0.1 / 6379 / 0 | Redis 连接 |
| SEARCH_CACHE_TTL | 300 | 搜索缓存秒数 |
| EMPTY_CACHE_TTL | 60 | 空结果短缓存（防穿透） |
| LLM_API_BASE / LLM_API_KEY / LLM_MODEL / LLM_TIMEOUT | DeepSeek 默认 | LLM 摘要（可选） |