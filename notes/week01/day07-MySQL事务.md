# Day07 · MySQL 深化（下）：SQL 优化 + 事务 + MVCC

> 日期：2026-08-21 ｜ 深度目标：L3 ｜ 状态：□ 未完成 □ 已完成（周复盘：____）

## 1. 核心概念

（用自己的话写 2-3 句——写不出来 = 没学会）

- **事务 ACID**：原子性（全做或全不做）、一致性（数据约束不破）、隔离性（并发互不干扰）、持久性（提交即落盘）。
- **隔离级别与异常**：读未提交（脏读）→ 读已提交（不可重复读）→ 可重复读（幻读，InnoDB 默认级别）→ 串行化（无并发问题但最慢）。
- **MVCC（多版本并发控制）**：靠"隐藏列（事务ID/回滚指针）+ undo log + ReadView"实现——读不加锁，写不加读锁，读写不互斥，这是 InnoDB 高并发的核心。
- **慢查询优化流程**：找到慢 SQL（慢查询日志）→ EXPLAIN 分析 → 建索引/改 SQL → 对比验证。

## 2. 关键代码

```sql
-- ① 慢查询日志开启（临时）
SET GLOBAL slow_query_log = ON;
SET GLOBAL long_query_time = 1;   -- 超过 1 秒记录

-- ② 事务与隔离级别验证
START TRANSACTION;
UPDATE users SET age = age + 1 WHERE id = 1;
-- 未提交：其他会话看不到修改（可重复读下）
COMMIT;   -- 或 ROLLBACK;

-- 查看/设置隔离级别
SELECT @@transaction_isolation;            -- REPEATABLE-READ（默认）
SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;

-- ③ 锁演示（行锁）
START TRANSACTION;
SELECT * FROM users WHERE id = 1 FOR UPDATE;   -- 加行级排他锁
-- 另一个会话更新同 id 会阻塞，直到本会话 COMMIT
COMMIT;

-- ④ 慢查询优化前后对比（构造一个需要优化的查询）
-- 优化前（无合适索引，全表扫 10w 行）
EXPLAIN SELECT * FROM users WHERE email = 'u50000@x.com';

-- 加索引后
CREATE INDEX idx_email ON users(email);
EXPLAIN SELECT * FROM users WHERE email = 'u50000@x.com';
-- type 从 ALL → ref，rows 从 100000 → 1

-- ⑤ 分页深翻页优化（大 OFFSET 的坑）
-- 慢：OFFSET 100000 要扫过前 10w 行
EXPLAIN SELECT * FROM users ORDER BY id LIMIT 100000, 20;
-- 优：用上次位置（游标分页，id 是主键）
EXPLAIN SELECT * FROM users WHERE id > 100000 ORDER BY id LIMIT 20;
```

## 3. 原理图

```
隔离级别 × 并发异常：
                 脏读    不可重复读    幻读
读未提交         可能     可能        可能
读已提交         —       可能        可能
可重复读(默认)   —       —           InnoDB 靠 Next-Key Lock 解决
串行化           —       —           —

MVCC 读流程（可重复读下的快照读）：
SELECT 时生成 ReadView（记录活跃事务 ID 集合）
  → 沿 undo log 版本链找"创建事务ID < ReadView 最小值 且 未删除"的版本
  → 保证同一事务内多次读看到同一快照 → 可重复读

为什么读写不互斥：
  写：只加行锁 + 生成新版本（undo log 记旧值）
  读：快照读，走 MVCC 读旧版本，不用等写锁
```

## 4. 面试问答

**Q1：ACID 分别怎么保证的？**
> 原子性 → undo log（失败回滚）；持久性 → redo log（崩溃恢复）+ doublewrite；隔离性 → 锁 + MVCC；一致性 → 前三者共同保证 + 约束。

**Q2：脏读 / 不可重复读 / 幻读的区别？**
> 脏读：读到**未提交**的数据（回滚了就白读）；不可重复读：同一条记录两次读**值不同**（被其他事务修改/提交）；幻读：两次**范围查询**结果行数不同（其他事务插入/删除）。

**Q3：InnoDB 怎么解决幻读？**
> 默认可重复读下，用 **Next-Key Lock**（记录锁 + 间隙锁）：范围查询时锁住"记录及前后间隙"，防止其他事务在区间内插入——实际上 InnoDB 在 RR 级别下已经基本杜绝幻读（但仍不是串行化语义，面试可说"快照读天然无幻读，当前读靠 Next-Key Lock"）。

**Q4：MVCC 和锁的关系？**
> 快照读（普通 SELECT）走 MVCC，不加锁；当前读（`SELECT ... FOR UPDATE`、UPDATE、DELETE）走锁。二者配合实现"读写不阻塞、写写互斥"。

**Q5：深分页为什么慢？怎么优化？**
> `LIMIT 100000, 20` 要扫描并丢弃前 10w 行。优化：①游标分页（`WHERE id > 上次值`）②延迟关联（先只查主键再 join 回原表）③覆盖索引。

## 5. 踩坑记录（今天实际遇到 + 常见坑）

| 坑 | 现象 | 解决 |
|------|------|------|
| （待填：今天真实报错） | | |
| 忘记 `COMMIT` | 数据"改了"但别处查不到，锁一直被占 | 事务结束显式 COMMIT/ROLLBACK，用 try/finally 包裹 |
| 长事务 | undo log 膨胀、锁持有过久 | 事务里只做必要操作，别把网络请求/大循环放里面 |
| `SELECT ... FOR UPDATE` 忘提交 | 其他会话卡死（行锁未释放） | 排查 `SHOW PROCESSLIST` / `information_schema.innodb_trx` |
| 事务里查了又改 | 同一事务内看到"自己的修改"却疑惑 | 记住：事务内修改对自身可见 |

## 6. 待补 / 周复盘（8/21 晚上完成）

**第 1 周复盘表（对照 Week1 执行表填写）：**

- [ ] 主线完成率（7 天 × 8.5h）：____%
- [ ] 验收项通过：____ / 7
- [ ] 欠账清单 + 处理（→ 8/30 机动日补 / 降级 / 放弃）
- [ ] 8.5h/天实际能达到吗？哪个环节超时？
- [ ] 执行表格式反馈（影响是否继续生成后续周）
- [ ] 下周继续吗？Y / 调整后继续 / N
- [ ] 本周 3 个最深印象的收获：1. 2. 3.

**待补：**
- [ ] 事务的隔离级别实验：开 2 个会话实测脏读/不可重复读/幻读（用 READ UNCOMMITTED 复现）
- [ ] `EXPLAIN ANALYZE` 实测慢查询优化前后耗时
