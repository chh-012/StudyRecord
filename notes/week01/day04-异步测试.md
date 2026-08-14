# Day04 · Python 异步 + pytest

> 日期：2026-08-18 ｜ 深度目标：L2 ｜ 状态：□ 未完成 □ 已完成

## 1. 核心概念

（用自己的话写 2-3 句——写不出来 = 没学会）

- **异步的本质**：单线程内，遇到 I/O 等待（网络/磁盘）就"挂起当前任务、切去执行别的任务"，把等待时间利用起来。**协程是协作式调度**——自己让出（await），不是被抢占。
- **事件循环**：一个循环不断从就绪队列取协程执行；`await` 一个 I/O 操作时，该协程挂起、事件循环去跑别的协程，I/O 完成回调唤醒它。
- **pytest**：测试即函数；`assert` 失败即用例失败。`fixture` 提供测试前置/后置资源，`mock` 替换依赖，参数化一套逻辑测多组数据。
- **GIL 与异步的关系**：GIL 限制的是 CPU 并行；异步解决的是 I/O 等待——所以**异步不加速 CPU 密集型代码，只加速 I/O 密集**。

## 2. 关键代码

```python
import asyncio
import time

# ① 协程与并发执行
async def fetch(url: str, delay: float) -> str:
    await asyncio.sleep(delay)          # 模拟网络 I/O
    return f"{url} 完成"

async def main():
    tasks = [fetch(f"url-{i}", 1) for i in range(5)]
    results = await asyncio.gather(*tasks)   # 并发跑，总耗时 ~1s 而非 5s
    return results

async def main2():
    t1 = asyncio.create_task(fetch("a", 1))
    t2 = asyncio.create_task(fetch("b", 1))
    return await t1, await t2           # create_task 立即调度，可细粒度控制

# 同步 vs 异步对比（串行 3 个 1s 请求）
async def serial():
    for i in range(3):
        await fetch(str(i), 1)          # 3s

async def parallel():
    await asyncio.gather(*(fetch(str(i), 1) for i in range(3)))  # 1s

# ② aiohttp 真实并发请求（需 pip install aiohttp）
import aiohttp

async def fetch_url(session: aiohttp.ClientSession, url: str) -> tuple[str, int]:
    async with session.get(url) as resp:
        return url, resp.status

async def fetch_all(urls: list[str]) -> list[tuple[str, int]]:
    async with aiohttp.ClientSession() as session:
        return await asyncio.gather(*(fetch_url(session, u) for u in urls))

# ③ pytest 基础（test_ 开头文件/函数才会被收集）
# test_utils.py:
#   import pytest
#
#   @pytest.fixture
#   def conn():
#       c = DBConnection()      # 复用 Day03 的类
#       yield c                 # 测试后自动关闭
#
#   @pytest.mark.parametrize("a,b,expected", [(1,2,3), (0,0,0), (-1,1,0)])
#   def test_add(a, b, expected):
#       assert a + b == expected
#
#   from unittest.mock import patch
#   @patch("module.get_data", return_value=[1,2,3])
#   def test_with_mock(mock_get):
#       assert process() == [1,2,3]
```

## 3. 原理图

```
事件循环调度：
            ┌──────────────────────────────┐
task A ───► │ await 网络IO → 挂起 A        │
task B ───► │ 执行 B → await → 挂起 B      │
task C ───► │ 执行 C ...                   │
            │ IO 完成 → 唤醒 A → 继续       │
            └──────────────────────────────┘
单线程内交替执行，无线程切换开销，无锁竞争。

协程 vs 线程 vs 进程：
  协程: 单线程内切换，开销最小，I/O 密集最优
  线程: 受 GIL 限制，切换有开销，I/O 密集可用
  进程: 多核并行，CPU 密集最优，通信成本高
```

## 4. 面试问答

**Q1：协程和线程的区别？**
> 线程由操作系统抢占式调度（可能随时被打断，需加锁）；协程由事件循环协作式调度（只有 await 时让出，无需锁）。协程切换开销远小于线程。

**Q2：事件循环怎么知道 I/O 完成了？**
> 底层用操作系统的 I/O 多路复用（select/poll/epoll/kqueue）监听 socket 就绪，就绪后把对应的协程放回就绪队列。

**Q3：`gather` 和 `create_task` 的区别？**
> `gather` 批量并发并聚合结果（一个 await 拿全部）；`create_task` 把协程包装成 Task 立即调度，可单独管理、单独 await。`gather` 内部就是创建 Task。

**Q4：为什么 async 不能加速 CPU 密集型代码？**
> 协程切换不解决 CPU 计算本身，且受 GIL 限制单进程只能用一个核。CPU 密集应该用多进程（`multiprocessing`/`ProcessPoolExecutor`）。

**Q5：pytest 里怎么测异步函数？**
> 装 `pytest-asyncio`，加 `@pytest.mark.asyncio` 装饰器（或用 asyncio 的 `asyncio.run()` 包装在同步测试里）。

## 5. 踩坑记录（今天实际遇到 + 常见坑）

| 坑 | 现象 | 解决 |
|------|------|------|
| （待填：今天真实报错） | | |
| 在同步函数里直接调 async | `RuntimeWarning: coroutine was never awaited` | 用 `asyncio.run(coro())` 或在 async 函数里 `await` |
| 忘了 `await asyncio.sleep` | 函数瞬间"跑完"，行为不对 | async 函数里的耗时调用都要 await，否则事件循环不会让出 |
| aiohttp 每请求新建 session | 连接没复用，反而更慢 | 一个 `ClientSession` 复用所有请求（`async with`） |
| pytest 断言失败却不报错 | 用了 `assert` 之外的方式（如 `print` 检查） | 一律用 `assert`，失败信息才被收集 |

## 6. 待补 / 明日预告

- [ ] 用 `asyncio.Semaphore` 限制并发数（防止打爆目标服务）
- [ ] 实测串行 vs `gather` 的耗时差异并记录数字
- 明日：FastAPI 初体验 + 工程工具链 + Git 规范
