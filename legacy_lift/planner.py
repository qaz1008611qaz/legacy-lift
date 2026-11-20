"""Turn a scan into an ordered list of migration batches.

Rules:
1. Modules in an import cycle must move together (strongly connected components).
2. A batch may only depend on batches that were already migrated
   (dependencies first, so every PR is testable on its own).
3. Batches are capped by risk so one PR stays reviewable.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Batch:
    index: int
    modules: list
    risk: int
    depends_on: set = field(default_factory=set)


def strongly_connected(graph: dict) -> list:
    """Tarjan's algorithm, iterative so large repos do not hit the recursion limit."""
    index, low, on_stack, stack, result, counter = {}, {}, set(), [], [], [0]
    for start in sorted(graph):
        if start in index:
            continue
        work = [(start, iter(sorted(graph[start])))]
        index[start] = low[start] = counter[0]; counter[0] += 1
        stack.append(start); on_stack.add(start)
        while work:
            node, children = work[-1]
            child = next(children, None)
            if child is None:
                work.pop()
                if work:
                    low[work[-1][0]] = min(low[work[-1][0]], low[node])
                if low[node] == index[node]:
                    comp = []
                    while True:
                        top = stack.pop(); on_stack.discard(top); comp.append(top)
                        if top == node:
                            break
                    result.append(sorted(comp))
            elif child not in index:
                index[child] = low[child] = counter[0]; counter[0] += 1
                stack.append(child); on_stack.add(child)
                work.append((child, iter(sorted(graph[child]))))
            elif child in on_stack:
                low[node] = min(low[node], index[child])
    return result


def plan(reports: dict, max_risk: int = 20) -> list:
    graph = {name: set(rep.imports) for name, rep in reports.items()}
    comps = strongly_connected(graph)
    comp_of = {m: i for i, comp in enumerate(comps) for m in comp}
    deps = {i: {comp_of[d] for m in comp for d in graph[m]} - {i} for i, comp in enumerate(comps)}

    # Kahn layering on the condensed DAG: a component is ready once all its deps are done.
    done, layers = set(), []
    while len(done) < len(comps):
        ready = sorted((i for i in deps if i not in done and deps[i] <= done),
                       key=lambda i: comps[i])
        if not ready:  # cannot happen on a DAG; guard against bad input
            raise RuntimeError("dependency graph is not acyclic after condensation")
        layers.append(ready)
        done.update(ready)

    batches, batch_of_comp = [], {}
    for layer in layers:
        current, risk = [], 0
        for ci in layer:
            comp_risk = sum(reports[m].risk for m in comps[ci])
            if current and risk + comp_risk > max_risk:
                batches.append((current, risk)); current, risk = [], 0
            current.append(ci); risk += comp_risk
        if current:
            batches.append((current, risk))

    result = []
    for bi, (cis, risk) in enumerate(batches, 1):
        for ci in cis:
            batch_of_comp[ci] = bi
        mods = [m for ci in cis for m in comps[ci]]
        dep_batches = {batch_of_comp[d] for ci in cis for d in deps[ci]}
        result.append(Batch(bi, mods, risk, dep_batches))
    return result
