"""Render each batch as a Devin Bot task with explicit acceptance criteria."""
from __future__ import annotations

from collections import Counter


def devin_prompt(batch, reports: dict) -> str:
    rules = Counter(f.hint for m in batch.modules for f in reports[m].findings)
    files = "\n".join(f"- {reports[m].path} ({reports[m].risk} risk points)" for m in batch.modules)
    hints = "\n".join(f"- {hint} x{n}" for hint, n in rules.most_common())
    after = ", ".join(f"#{d}" for d in sorted(batch.depends_on)) or "none"
    return (
        f"Batch {batch.index}: migrate to Python 3 (depends on batches: {after})\n\n"
        f"Files:\n{files}\n\nKnown Python 2 constructs:\n{hints or '- none detected'}\n\n"
        "Acceptance criteria:\n"
        "1. Before editing, write characterization tests that pass on the current code.\n"
        "2. Migrate only the files above; open one PR for this batch.\n"
        "3. The same tests pass on Python 3.11; no behaviour change.\n"
        "4. Flag every str/bytes decision in the PR description for human review.\n"
    )


def markdown_plan(batches, reports: dict) -> str:
    total = sum(r.risk for r in reports.values())
    out = [f"# Migration plan: {len(reports)} modules, {len(batches)} batches, {total} risk points", ""]
    for b in batches:
        after = ", ".join(f"#{d}" for d in sorted(b.depends_on)) or "-"
        out.append(f"## Batch {b.index} (risk {b.risk}, after {after})")
        out.extend(f"- `{m}`" for m in b.modules)
        out.append("")
    return "\n".join(out)
