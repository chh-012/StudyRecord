# Day05 · FastAPI 初体验 + 工程工具链 + Git 规范

> 日期：2026-08-19 ｜ 深度目标：L2 ｜ 状态：□ 未完成 □ 已完成
> ⚠️ 先自己写，写完全部后再对照 `_reference/week01/day05-FastAPI.md`

## 1. 核心概念

用自己的话写 2-3 句（写不出来 = 没学会）：

- FastAPI 靠什么实现自动文档和数据校验？
- 路径参数 vs 查询参数的区别？
- 虚拟环境为什么必要？poetry/pip 各干什么？
- commit message 为什么要规范？`type(scope): 描述` 各段含义？

## 2. 关键代码

自己敲，跑通才算会（提交 git）：

- [ ] 创建 venv 并激活，安装 fastapi/uvicorn，`pip freeze > requirements.txt`
- [ ] todo CRUD：GET(列表+done 过滤)/POST/PUT/DELETE，Pydantic 校验
- [ ] 配 logging（分级日志替代 print）
- [ ] 在 `/docs` Swagger 页面完整测一遍 5 个接口
- [ ] 用 curl 或 postman 再测一遍（不依赖 Swagger UI）
- [ ] 按 `type(scope): 描述` 规范提交当天所有代码

## 3. 原理图

画 FastAPI 请求处理链路：HTTP → 路由 → Pydantic 校验 → 处理函数 → 响应模型 → 返回 + 登记到 /docs

## 4. 面试问答

自己先答，答不出再翻 _reference：

- Q1：FastAPI vs Flask vs Django？
- Q2：Pydantic 模型是干什么的？
- Q3：`response_model` 和直接返回 dict 的区别？
- Q4：路径参数 vs 查询参数？
- Q5：虚拟环境为什么必要？

## 5. 踩坑记录

| 坑 | 现象 | 解决 |
|------|------|------|
| （今天真实报错，逐条记） | | |

## 6. 待补 / 明日预告

- [ ] （学完补自己的待补项）
- 明日：MySQL 深化（上）—— B+ 树索引
