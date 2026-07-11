"""
Evidence -- observed, and provenanced.

Claims and evidence are not two instances of one thing. A claim is *declared*: it
carries intent, a requirement, a priority, a criticality, a contract reference.
Its trust question is authority and staleness -- who declared this, and is it
still binding?

Evidence is *observed*: it carries a source, a timestamp, a lineage, and the run
that produced it. Its trust question is authenticity and freshness -- where did
this come from, and can its lineage be established?

That asymmetry has a hard consequence, and it is a real check, not a slogan:

    EVIDENCE WITH NO PROVENANCE CANNOT SUBSTANTIATE A CLAIM.

Unprovenanced evidence is not counted as passing and not counted as failing. It
is routed to CANNOT-ATTEST, because we cannot say where it came from. Absence of
provenance is an integrity problem, distinct from a stale claim, which is a
governance problem.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Set


@dataclass
class Provenance:
    """Where a piece of evidence came from. Absent -> it cannot substantiate."""
    source: str                  # e.g. "orchestrator.runlog"
    run_ref: str                 # which run produced it
    timestamp: str               # ISO-ish; freshness is a quality measure
    lineage: str                 # upstream chain, if any

    @property
    def established(self) -> bool:
        return bool(self.source and self.run_ref and self.timestamp)


@dataclass
class StepRun:
    """
    One observed execution of a step. This is evidence, so it is provenanced.

    Retries matter: the same step may appear more than once. A clean third
    attempt does NOT paper over an out-of-scope first attempt -- a breach on any
    attempt is still a breach. `attempt` makes that explicit and countable.
    """
    id: str
    tools_used: Set[str]
    status: str                              # "ok" | "error"
    attempt: int = 1
    delegated_to: Set[str] = field(default_factory=set)
    cost: float = 0.1
    latency_ms: int = 400
    region: str = "ca"
    handled_pii: bool = False
    produced_checkable_evidence: bool = True
    self_critique_passed: Optional[bool] = None   # the agent's own opinion. Never counted.
    reported_confidence: float = 0.95             # the agent's own uncertainty. Carried, not trusted.
    provenance: Optional[Provenance] = None       # None -> cannot substantiate
