# Day06 · MySQL 深化（上）：B+ 树索引

> 日期：2026-08-20 ｜ 深度目标：L3 ｜ 状态：□ 未完成 □ 已完成

## 1. 核心概念

（用自己的话写 2-3 句——写不出来 = 没学会）

- **B+ 树索引**：MySQL InnoDB 默认索引结构。所有数据在叶子节点、叶子节点用双向链表串联——范围查询只需顺序扫描叶子。
- **聚簇索引 vs 二级索引**：聚簇索引的叶子直接存整行数据（主键默认就是它）；二级索引叶子存"索引列 + 主键值"，查到后要**回表**取整行。
- **最左前缀**：复合索引 `(a, b, c)` 只有从 `a` 开始连续使用才生效；跳过 `b` 直接用 `c` 会失效。
- **覆盖索引**：查询只需要索引列（+主键）就能拿到结果，不需要回表——是优化查询的常用手段。

## 2. 关键代码

```sql
-- 建表（造 10w 条数据做实验）
CREATE DATABASE IF NOT EXISTS test_idx DEFAULT CHARSET utf8mb4;
USE test_idx;

CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(50) NOT NULL,
    age INT NOT NULL,
    email VARCHAR(100),
    city VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 造数据（MySQL 8 用递归 CTE）
INSERT INTO users (name, age, email, city, created_at)
WITH RECURSIVE seq AS (
    SELECT 1 AS n UNION ALL SELECT n+1 FROM seq WHERE n < 100000
)
SELECT CONCAT('user', n), 18 + (n % 50), CONCAT('u', n, '@x.com'),
       ELT(1 + (n % 5), '北京','上海','广州','深圳','杭州'), NOW()
FROM seq;

-- 建立索引
CREATE INDEX idx_age ON users(age);                  -- 单列
CREATE INDEX idx_name_age ON users(name, age);       -- 复合（最左前缀演示）

-- ① 看有没有走索引
EXPLAIN SELECT * FROM users WHERE age = 30;
-- type=ref, key=idx_age, rows≈2000

-- ② 范围查询走索引（B+ 树叶子链表）
EXPLAIN SELECT * FROM users WHERE age BETWEEN 30 AND 35;
-- type=range

-- ③ 最左前缀：用 name 开头 → 走索引
EXPLAIN SELECT * FROM users WHERE name = 'user100' AND age = 30;
-- key=idx_name_age

-- ④ 跳过 name 直接用 age → 复合索引失效（只可能全表扫或走 idx_age）
EXPLAIN SELECT * FROM users WHERE age = 30 AND name LIKE '%x';
-- 注意对比: 第二条件不是前缀

-- ⑤ 覆盖索引：只查索引列 → Using index（不回表）
EXPLAIN SELECT name, age FROM users WHERE name = 'user100';
-- Extra=Using index

-- ⑥ 索引失效典型：对索引列用函数/隐式转换
EXPLAIN SELECT * FROM users WHERE LEFT(name, 5) = 'user1';
-- 失效（函数包裹索引列）
```

## 3. 原理图

```
B+ 树（示意，3 层）：
         [50 | 100]
        /     |     \
   [20|35]  [60|80]  [110|...]      ← 非叶子节点只存键（索引），扇出大
    /  \    /  |  \    ...
  20 35  60  80  110               ← 叶子节点存数据(聚簇)或"键+主键"(二级)
   │   │   │   │   │
   └───┴───┴───┴───┘  ← 叶子间双向链表 → 范围查询顺序扫

为什么快：3 层 B+ 树可容纳千万级数据，查询 = 3 次磁盘 IO（树高 ≈ IO 次数）

回表流程（二级索引 idx_age 查 age=30）：
  1. 沿 idx_age 的 B+ 树找到叶子：age=30 → 主键 id=xxx
  2. 拿 id 再沿聚簇索引 B+ 树找一次 → 取整行数据（这就是"回表"）
```

## 4. 面试问答

**Q1：为什么 MySQL 用 B+ 树不用哈希、红黑树、B 树？**
> - 哈希：O(1) 但**不支持范围查询**和排序，冲突处理复杂
> - 红黑树：平衡二叉树，树高 ≈ log2N，千万级数据树高 20+ 层，**磁盘 IO 次数太多**（每层一次 IO）
> - B 树：非叶子节点也存数据，节点存不了几个键，**扇出小、树高更高**
> - B+ 树：非叶子只存键（扇出大、树高 ≈ 3-4）、叶子有序链表（范围查询友好）——**磁盘 IO 次数少 + 范围查询优**，正好匹配"磁盘顺序读远快于随机读"

**Q2：什么是回表？怎么避免？**
> 二级索引查到主键后再回聚簇索引取整行 = 回表（多一次 IO）。避免：**覆盖索引**（查询列都包含在索引里，`Using index`）、必要时建合适的复合索引。

**Q3：最左前缀原则具体指什么？**
> 复合索引 `(a,b,c)` 生效的组合：`a`、`a,b`、`a,b,c`。`b,c`、`c` 不生效；`a,c` 时 `a` 生效 `c` 部分失效。原则：**从最左列开始连续**。

**Q4：哪些操作会让索引失效？**
> 对索引列用函数/运算（`LEFT(name,5)`）、隐式类型转换（`WHERE phone = 138...` phone 是 varchar）、`LIKE '%xx'` 前置通配、`OR` 连接非索引列、`!=`/`NOT IN`（可能不保证用）、复合索引不满足最左前缀。

**Q5：`EXPLAIN` 怎么看？**
> 重点字段：`type`（const/ref/range/index/ALL，从好到坏）、`key`（实际用的索引）、`rows`（预估扫描行数）、`Extra`（`Using index` 覆盖索引、`Using filesort` 未用索引排序、`Using temporary` 用了临时表——后两者要警惕）。

## 5. 踩坑记录（今天实际遇到 + 常见坑）

| 坑 | 现象 | 解决 |
|------|------|------|
| （待填：今天真实报错） | | |
| 建了索引却不生效 | `EXPLAIN` 显示全表扫 | 检查是否满足最左前缀 / 对索引列用了函数 |
| 低选择性列建索引 | 性别列建索引，区分度太低优化器不用 | 区分度高的列（如 email）才值得建 |
| 只查 1 行但 type=ALL | 表数据量太小，优化器认为全表扫更快 | 小表不纠结，数据量大后再看 |
| 复合索引顺序错了 | `(age, name)` 与查询 `name=?` 不匹配 | 按查询模式排：等值列在前，范围列在后 |

## 6. 待补 / 明日预告

- [ ] 实测：用 `EXPLAIN ANALYZE`（MySQL 8）对比加索引前后真实耗时
- [ ] 记录 3 个真实场景的索引设计（等值+范围+排序）
- 明日：MySQL 深化（下）——SQL 优化 + 事务隔离 + MVCC
