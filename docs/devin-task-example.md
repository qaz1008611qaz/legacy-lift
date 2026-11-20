# 示例：Legacy Lift 自动生成的 Devin 任务

下面是 `python -m legacy_lift tests/fixtures/py2_shop --prompts` 对第 3 批（循环依赖那一批）的真实输出：

```
Batch 3: migrate to Python 3 (depends on batches: #2)

Files:
- tests/fixtures/py2_shop/shop/orders.py (4 risk points)
- tests/fixtures/py2_shop/shop/payments.py (5 risk points)

Known Python 2 constructs:
- xrange -> range x1
- except E, e -> except E as e x1
- print x -> print(x) x1
- renamed stdlib module x1
- str/bytes semantics, needs review x1

Acceptance criteria:
1. Before editing, write characterization tests that pass on the current code.
2. Migrate only the files above; open one PR for this batch.
3. The same tests pass on Python 3.11; no behaviour change.
4. Flag every str/bytes decision in the PR description for human review.

```
