# Day03 · 上下文管理器 + 类型提示 + dataclass

> 日期：2026-08-17 ｜ 深度目标：L2→L3 ｜ 状态：□ 未完成 □ 已完成（周中综合测验：____/10）
> ⚠️ 先自己写，写完全部后再对照 `_reference/week01/day03-上下文类型dataclass.md`

## 1. 核心概念

用自己的话写 2-3 句（写不出来 = 没学会）：

- 上下文管理器保证什么？`with` 的执行流程？
- `contextlib.contextmanager` 和手写类式有什么区别？
- 类型提示在运行时生效吗？它服务谁？
- dataclass 帮你自动生成了什么？

## 2. 关键代码

自己敲，跑通才算会（提交 git）：

- [ ] 类式上下文管理器：数据库连接自动关闭（含异常时也要关闭）
- [ ] `contextmanager` 装饰器版：锁/资源守卫
- [ ] dataclass：User 类（id/name/tags），`frozen=True` + `default_factory`
- [ ] 复现可变默认值陷阱：`= []` 时多个实例共享列表
- [ ] Protocol：定义 Greetable 协议并让任意有 `greeting()` 的类通过

## 3. 原理图

画 `with` 执行流程图：`__enter__` → 块 → `__exit__`（正常/异常两条路径，True/False 分支）

## 4. 面试问答

自己先答，答不出再翻 _reference：

- Q1：`__exit__` 返回 True/False 的区别？
- Q2：`contextmanager` vs 手写类的适用场景？
- Q3：dataclass vs namedtuple vs dict？
- Q4：为什么可变默认值要 `field(default_factory=list)`？
- Q5：类型提示强制吗？运行时会校验吗？

## 5. 踩坑记录

| 坑 | 现象 | 解决 |
|------|------|------|
| （今天真实报错，逐条记） | | |

## 6. 待补 / 明日预告

- [ ] 周中综合测验订正（10 题，目标 ≥8/10）
- [ ] （学完补自己的待补项）
- 明日：Python 异步（asyncio/aiohttp）+ pytest
