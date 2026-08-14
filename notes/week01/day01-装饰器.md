# Day01 · Python 装饰器与函数进阶

> 日期：2026-08-15 ｜ 深度目标：L3 ｜ 状态：□ 未完成 □ 已完成

## 1. 核心概念

（用自己的话写 2-3 句——写不出来 = 没学会）

- **函数是一等公民**：函数可以像变量一样被赋值、传参、返回。这是装饰器能存在的前提。
- **闭包（closure）**：内层函数引用外层函数的变量，且外层函数已经返回后，这个变量依然存活——靠"闭包环境"保存。
- **装饰器**：本质是"接收一个函数、返回一个新函数"的高阶函数。`@deco` 只是 `func = deco(func)` 的语法糖。
- **`functools.wraps`**：把被装饰函数的元信息（`__name__`、`__doc__`）复制到 wrapper 上，否则调试和文档会"找错函数"。

## 2. 关键代码

```python
from functools import wraps
import time

# ① 最简日志装饰器（无参）
def log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[LOG] 调用 {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log
def hello(name: str) -> str:
    return f"Hello, {name}"

# ② 带参装饰器 = 外面多包一层"装饰器工厂"
def retry(max_times: int = 3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_times):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"第 {i+1} 次失败: {e}")
            raise RuntimeError(f"{func.__name__} 重试 {max_times} 次仍失败")
        return wrapper
    return decorator

@retry(max_times=3)
def flaky():
    import random
    if random.random() < 0.5:
        raise ValueError("模拟失败")
    return "成功"

# ③ functools 缓存（练习用，实际项目用 @functools.lru_cache）
@log
def add(a: int, b: int) -> int:
    return a + b

print(hello("Python"))      # [LOG] 调用 hello
print(flaky())              # 可能打印失败信息，最多重试 3 次
```

## 3. 原理图

```
@deco
def f(): ...

  ≡ 等价于

f = deco(f)

调用链（无参装饰器）：
调用 f(x)
  → wrapper(x)（print 日志）
    → f(x)（原函数）
      → 返回结果
    ← 返回结果
  ← 返回结果

带参装饰器结构（三层）：
retry(max_times=3)  → 返回 decorator（装饰器工厂）
  decorator(f)      → 返回 wrapper（真正的"新函数"）
    wrapper(*args)  → 重试逻辑 + 调用 f
```

## 4. 面试问答

**Q1：装饰器执行顺序？**
> 装饰器从下往上"应用"（离函数最近的先执行），调用时从上往下"包装"。多个装饰器 `@a @b` 等价于 `f = a(b(f))`。

**Q2：`@wraps` 为什么必要？**
> 不加的话 wrapper 会顶替原函数的 `__name__`/`__doc__`，导致调试、文档生成（如 FastAPI 的 OpenAPI）、日志全显示 `wrapper`，难以定位。

**Q3：装饰器 vs 装饰器工厂？**
> 无参装饰器直接接收函数；有参装饰器（`@retry(3)`）返回一个"接收函数的装饰器"。区别在于外层是否还有一层接收参数的函数。

**Q4：闭包为什么能记住外层变量？**
> Python 在函数定义时把被引用的外层变量绑定到 `__closure__` 单元里，即使外层函数已返回，单元仍持有引用。

## 5. 踩坑记录（今天实际遇到 + 常见坑）

| 坑 | 现象 | 解决 |
|------|------|------|
| （待填：今天真实报错） | | |
| 忘加 `@wraps` | `f.__name__` 变成 `wrapper` | 补 `@wraps(func)` |
| 带参装饰器少包一层 | `TypeError: decorator() missing 1 required positional argument` | 记住三层结构：工厂→装饰器→wrapper |
| 闭包变量用错 | 循环里 `lambda` 都返回最后一个值 | 用默认参数绑定 `lambda i=i: i` 或 `functools.partial` |

## 6. 待补 / 明日预告

- [ ] 类装饰器（`__call__`）写法
- [ ] 装饰器与上下文管理器的组合（`contextlib` 的 `ContextDecorator`）
- 明日：生成器与迭代器
