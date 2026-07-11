"""
The arithmetic core (static conformance).

Every verdict here is a set difference, a ratio, or a reachability count. No
inference at decision time, no training, reproducible to the bit. You cannot
flatter an anti-join.

    G   = R \\ T                            gaps: requirements with no evidence
    c   = |T| / |R|                         coverage
    sev = blast_radius(module) x weight     the worklist sort key (triage)
    O   = impl \\ claimed                    orphans: code with no requirement
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Set
from .claims import Requirement, module_graph


@dataclass
class Gap:
    req: Requirement
    severity: float
    blast: float
    reason: str


def coverage(reqs: List[Requirement], evidence: Set[str]) -> float:
    covered = {r.id for r in reqs} & evidence
    return len(covered) / len(reqs) if reqs else 1.0


def gaps(reqs: List[Requirement], evidence: Set[str]) -> List[Gap]:
    """Left anti-join: requirements minus covered, ranked by blast radius."""
    g = module_graph()
    out: List[Gap] = []
    for r in reqs:
        if r.id in evidence:
            continue
        blast = float(len(g.descendants(r.module)))     # |descendants(r)|
        out.append(Gap(
            req=r,
            blast=blast,
            severity=blast * r.criticality,             # severity = |descendants| x weight
            reason="no test or code references this requirement",
        ))
    return sorted(out, key=lambda x: x.severity, reverse=True)


def orphans(implementations: List[tuple], reqs: List[Requirement]) -> List[str]:
    """Reverse anti-join: implementation units that answer to no requirement."""
    declared = {r.id for r in reqs}
    return [name for (name, req_id) in implementations
            if req_id is None or req_id not in declared]
