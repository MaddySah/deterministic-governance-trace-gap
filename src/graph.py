"""
Blast radius, with no dependencies.

Importance is inherited, not intrinsic: a node matters because of what sits
downstream of it. Blast radius = the criticality-weighted count of everything a
node can reach. It is a reachability count on a graph you already have (imports,
lineage, an orchestration DAG) -- not a trained score. Structure supplies impact
for free; we only sort by it.

networkx would do this in one call; a dozen lines of BFS keeps the repo
zero-dependency and the arithmetic legible.
"""

from __future__ import annotations
from typing import Dict, List, Set


class DAG:
    """Directed graph. edges[node] = nodes that depend on / follow `node`."""

    def __init__(self) -> None:
        self.edges: Dict[str, Set[str]] = {}

    def add(self, src: str, dst: str) -> None:
        self.edges.setdefault(src, set()).add(dst)
        self.edges.setdefault(dst, set())

    def node(self, n: str) -> None:
        self.edges.setdefault(n, set())

    def descendants(self, start: str) -> Set[str]:
        """Everything reachable downstream of `start` (excluding itself)."""
        seen: Set[str] = set()
        stack: List[str] = list(self.edges.get(start, set()))
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(self.edges.get(n, set()) - seen)
        return seen

    def blast_radius(self, start: str, weight: Dict[str, float] | None = None) -> float:
        """Criticality-weighted downstream reach. weight defaults to 1 per node."""
        w = weight or {}
        return sum(w.get(d, 1.0) for d in self.descendants(start))
