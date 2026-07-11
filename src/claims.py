"""
The documented story vs. the implemented reality -- static case (a code change).

`claims` are requirements pulled from a design doc / tickets (the story).
`evidence` are references found in code and tests (the reality).

Both are synthetic here so the demo is reproducible, but they mirror what real
connectors would emit: rows in a common schema. Two faults are planted:

  - a REQUIREMENT WITH NO EVIDENCE  (REQ-003): a declared behavior nothing
    implements or tests. The anti-join catches it.
  - an ORPHAN IMPLEMENTATION        (FN-legacy_export): code that answers to no
    requirement. The *reverse* anti-join catches it -- this is how spec staleness
    surfaces from the other direction.

Each requirement is attached to a module, and modules form a dependency graph,
so a gap on a high-fan-out module outranks a gap on a leaf.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Set
from .graph import DAG


@dataclass
class Requirement:
    id: str
    text: str
    module: str
    criticality: float          # 1 = nice-to-have ... 5 = revenue / regulatory


def claims() -> List[Requirement]:
    return [
        Requirement("REQ-001", "reject expired auth tokens",        "auth",        5.0),
        Requirement("REQ-002", "log a request id on every call",    "logging",     2.0),
        Requirement("REQ-003", "refresh account balance hourly",    "billing",     5.0),  # planted gap (high blast)
        Requirement("REQ-004", "paginate the transactions endpoint","api",         3.0),
        Requirement("REQ-005", "mask PII in exported reports",      "export",      4.0),
        Requirement("REQ-006", "retry the bureau call three times", "bureau",      3.0),
        Requirement("REQ-007", "pad currency strings to 2 decimals","util_format", 1.0),  # planted gap (leaf)
    ]


# References discovered in code/tests. REQ-003 and REQ-007 are deliberately absent.
def evidence_refs() -> Set[str]:
    return {"REQ-001", "REQ-002", "REQ-004", "REQ-005", "REQ-006"}


# Implementation units found in the codebase, and the requirement each names.
# `FN-legacy_export` names nothing declared -> orphan implementation.
def implementations() -> List[tuple[str, str | None]]:
    return [
        ("FN-check_token",     "REQ-001"),
        ("FN-request_logger",  "REQ-002"),
        ("FN-paginate",        "REQ-004"),
        ("FN-mask_pii",        "REQ-005"),
        ("FN-bureau_retry",    "REQ-006"),
        ("FN-legacy_export",   None),        # orphan: code with no requirement behind it
    ]


def module_graph() -> DAG:
    """Which modules depend on which. Downstream reach becomes blast radius."""
    g = DAG()
    # auth and logging are foundational: many things sit downstream of them.
    for dep in ["api", "billing", "export", "bureau"]:
        g.add("auth", dep)
        g.add("logging", dep)
    g.add("api", "export")       # the reports endpoint feeds exports
    g.add("bureau", "billing")   # bureau data feeds billing
    # billing feeds the money-facing surfaces -> a gap here is wide.
    for sink in ["revenue_dashboard", "exec_report", "finance_ledger"]:
        g.add("billing", sink)
    g.add("export", "partner_feed")
    g.node("util_format")        # a leaf: nothing depends on it -> blast 0
    return g
