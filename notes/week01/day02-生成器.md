# Day02 · 生成器与迭代器

> 日期：2026-08-16 ｜ 深度目标：L3 ｜ 状态：□ 未完成 □ 已完成

## 1. 核心概念

（用自己的话写 2-3 句——写不出来 = 没学会）

- **迭代器协议**：实现 `__iter__`（返回自身）和 `__next__`（返回下一个值，耗尽抛 `StopIteration`）的对象。
- **可迭代对象 vs 迭代器**：`list`/`str`/`range` 是可迭代对象（能 `iter()`）；迭代器是一次性的（能 `next()`）。`for` 循环内部就是"取 iter → 反复 next → 捕获 StopIteration"。
- **生成器**：含 `yield` 的函数。调用不执行，返回生成器对象；每次 `next()` 执行到下一个 `yield` 暂停。
- **惰性求值**：值用到一个算一个，不一次性进内存——这是大文件/无限序列的解法。

## 2. 关键代码

```python
# ① 斐波那契生成器
def fib():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

f = fib()
print([next(f) for _ in range(8)])      # [0, 1, 1, 2, 3, 5, 8, 13]

# ② 无限序列 take 前 N 个（itertools.islice 更专业，这里手写演示）
def take(n, gen):
    return [next(gen) for _ in range(n)]

# ③ 大文件流式逐行读取（对比 read() 一次性载入）
def read_lines(path):
    with open(path, encoding="utf-8") as fp:
        for line in fp:                 # 文件对象本身可迭代
            yield line.rstrip("\n")

# ④ send()：向生成器内部传值（协程雏形）
def echo():
    while True:
        received = yield                 # yield 表达式，可以接收 send 的值
        print(f"收到: {received}")

e = echo()
next(e)                                  # 启动到第一个 yield
e.send("hello")                          # 打印 收到: hello

# ⑤ yield from：委托给子生成器
def sub():
    yield 1
    yield 2
def main():
    yield from sub()                     # 相当于逐个 yield sub() 的值
    yield 3
print(list(main()))                      # [1, 2, 3]
```

## 3. 原理图

```
生成器生命周期：
创建 gen() → 未开始
  next() ──► 执行到第一个 yield，暂停，返回值
  next() ──► 执行到下一个 yield，暂停
  next() ──► 函数体跑完，抛 StopIteration → 结束

内存对比（1000 万个数）：
list:     [0,1,2,...,10^7]  一次性占 ~320MB
generator: 每次只生产 1 个，常驻内存几乎为 0
```

## 4. 面试问答

**Q1：`range(10)` 和 `list(range(10))` 有什么区别？**
> `range` 是惰性可迭代对象（只存 start/stop/step，迭代时现算）；`list` 一次性把 10 个元素装进内存。大范围时 `range` 内存优势巨大。

**Q2：生成器为什么只能迭代一次？**
> 生成器内部状态（当前执行位置、局部变量）只保留一份，迭代完即耗尽（抛 StopIteration）。想复用就重新调用函数。

**Q3：`send()` 有什么用？什么时候用？**
> `send(value)` 把值传回 `yield` 表达式处，实现"生成器与外部双向通信"——是协程/管道模式的基础（如生产者-消费者、流水线处理）。

**Q4：`yield` 和 `return` 能同时用吗？**
> 可以。`return` 在生成器中表示结束并抛 StopIteration（`return x` 的值在 Python3.3+ 存入 StopIteration.value，用 `yield from` 可拿到）。

**Q5：迭代器协议里为什么需要 `__iter__` 返回自身？**
> 为了让迭代器也能被 `for`/`iter()` 直接使用（协议要求 `iter(obj)` 返回的对象必须可迭代）。同时支持"同一迭代器多次 for"语义的区分。

## 5. 踩坑记录（今天实际遇到 + 常见坑）

| 坑 | 现象 | 解决 |
|------|------|------|
| （待填：今天真实报错） | | |
| 生成器只消费一次 | 第二次 `for` 循环结果为空 | 需要复用就重新创建生成器 |
| 在 `yield` 前调 `send` | `TypeError: can't send non-None value to a just-started generator` | 先 `next(g)` 启动到第一个 `yield` 再 `send` |
| 误把 `yield` 当 `return` | 函数"返回"的是生成器对象而不是值 | 记住：调用含 `yield` 的函数不执行函数体 |

## 6. 待补 / 明日预告

- [ ] `itertools`（islice/chain/groupby）在项目中的组合用法
- [ ] 生成器表达式 `(x*x for x in range(10))` 与列表推导的内存对比实测
- 明日：上下文管理器 + 类型提示 + dataclass
