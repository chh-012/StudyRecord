# Day03 · 上下文管理器 + 类型提示 + dataclass

> 日期：2026-08-17 ｜ 深度目标：L2→L3 ｜ 状态：□ 未完成 □ 已完成（含周中综合测验：____/10）

## 1. 核心概念

（用自己的话写 2-3 句——写不出来 = 没学会）

- **上下文管理器**：实现 `__enter__`/`__exit__` 的对象，配合 `with` 保证资源"用完必还"（关文件、关连接、释放锁），异常也会走到 `__exit__`。
- **`contextlib.contextmanager`**：用生成器把"进入逻辑 / yield / 退出逻辑"写在一起，少写一个类。
- **类型提示（typing）**：运行时不影响性能，作用是：IDE 补全、静态检查（mypy）、文档自解释。`Optional[X]` = `X | None`。
- **dataclass**：`@dataclass` 自动生成 `__init__`/`__repr__`/`__eq__`，是"用类装数据"的现代方式，替代手写样板代码。

## 2. 关键代码

```python
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, Protocol

# ① 类式上下文管理器：数据库连接
class DBConnection:
    def __enter__(self):
        print("连接数据库...")
        return self                      # with ... as conn 拿到的是这个
    def __exit__(self, exc_type, exc_val, exc_tb):
        print("关闭连接")
        return False                     # False = 不吞异常，让它继续抛
    def query(self, sql: str) -> str:
        return f"结果: {sql}"

with DBConnection() as conn:
    print(conn.query("SELECT 1"))
    # 即使这里抛异常，__exit__ 也会执行（连接保证关闭）

# ② 生成器式：用 contextmanager 少写一个类
@contextmanager
def lock_guard(name: str):
    print(f"加锁 {name}")
    try:
        yield                        # with 块执行到这里暂停
    finally:
        print(f"解锁 {name}")        # 无论正常/异常都会执行

with lock_guard("user_lock"):
    print("临界区代码")

# ③ dataclass：数据容器
@dataclass(frozen=True)              # frozen: 不可变
class User:
    id: int
    name: str
    tags: list[str] = field(default_factory=list)   # 关键：不能写 = []
    def greeting(self) -> str:
        return f"Hi {self.name}"

u = User(1, "阿豪")
print(u)                             # User(id=1, name='阿豪', tags=[])
print(u == User(1, "阿豪"))          # True（自动生成 __eq__）

# ④ Protocol：结构化子类型（鸭子类型 + 静态检查）
class Greetable(Protocol):
    def greeting(self) -> str: ...
def say_hi(g: Greetable) -> str:
    return g.greeting()              # 任何有 greeting() 的对象都能传
```

## 3. 原理图

```
with EXPR as VAR:
    BLOCK
    ├─ 1. VAR = EXPR.__enter__()
    ├─ 2. 执行 BLOCK
    │      ├─ 正常结束 → 跳到 3
    │      └─ 抛异常  → 跳到 3（带异常信息）
    └─ 3. EXPR.__exit__(exc_type, exc_val, exc_tb)
           └─ 返回 True → 吞掉异常；False → 继续抛
```

## 4. 面试问答

**Q1：`__exit__` 返回 `True`/`False` 的区别？**
> `True` = 吞掉异常（with 块内异常不向外抛，调用方无感知）；`False` = 异常继续向上传播。默认应返回 `False`，只有明确"我处理了这个异常"才返回 `True`。

**Q2：`contextmanager` 和手写类的区别？**
> 语法糖，等价实现。生成器版把 enter/exit 逻辑写在一个函数里更紧凑；类版适合需要保存状态、需要多个 `with` 复用场景。

**Q3：dataclass 和普通类、namedtuple、dict 的区别？**
> - dict：无类型、无属性访问，键拼错才发现
> - namedtuple：不可变、无类型提示、不能加方法
> - dataclass：可变/不可变可选、类型提示、可加方法、可默认值——数据容器的现代默认选择

**Q4：为什么 dataclass 里可变默认值要用 `field(default_factory=list)`？**
> Python 默认参数只求值一次，`= []` 会导致所有实例共享同一个 list（经典可变默认值陷阱）。

**Q5：类型提示是强制的吗？运行时会校验吗？**
> 不强制、运行时不校验。它服务于 IDE/mypy 和可读性。团队规范通常要求公共接口必须写。

## 5. 踩坑记录（今天实际遇到 + 常见坑）

| 坑 | 现象 | 解决 |
|------|------|------|
| （待填：今天真实报错） | | |
| dataclass 可变默认值 | 多个实例共享同一个列表，互相污染 | `field(default_factory=list)` |
| `__exit__` 忘记 return | 异常被吞/被传播不符合预期 | 明确写 `return False` |
| `Optional[str]` 误用 | 新手以为 Optional = 可选参数 | `Optional[str]` = `str | None`，不是"参数可以不传" |
| 类型提示里写 `list` 而不是 `list[int]` | mypy 报错/提示不全 | 泛型参数化 `list[int]`、`dict[str, int]` |

## 6. 待补 / 明日预告

- [ ] 周中综合测验订正（10 题，目标 ≥8/10）
- [ ] `contextlib.ExitStack`（动态管理多个上下文）看一眼概念
- 明日：Python 异步（asyncio/aiohttp）+ pytest
