"""
The Policy Engine -- owns the rules, not the run.

It holds two things and does one job.

It holds the CONTRACT (the risk envelope): not just an allow-list, but the full
operating boundary of an agent step -- tools, delegation rule, cost and latency
budgets, data-residency region, PII handling, and the *expected* quality and
confidence.

Its one job is the classification everything else hinges on: each check is either
a CRITICAL GATE (a breach -> HALT, binary and absolute) or a QUALITY MEASURE (a
graded reading that informs, never gates). The Policy Engine defines what
"out-of-bound" means; it does not detect it. Detection is the Evaluator's job.

Note which fields land in which lane. Tool permissions, delegated scope, region,
PII, and the budgets are gates: exceed them and it is a contract breach. Expected
quality and expected confidence are measures: fall below them and the trust
reading degrades, but the line does not stop. Same engine, same arithmetic --
policy decides what is fatal and what is merely a compromise.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Set


# Which lane a check reports to. This is the whole two-lane split.
CRITICAL = "critical"   # breach -> HALT / CANNOT-ATTEST. Binary, absolute.
QUALITY  = "quality"    # graded -> feeds the trust reading. Never gates.

CHECK_LANES: Dict[str, str] = {
    "tool_scope":       CRITICAL,   # used \ allowed
    "delegation_scope": CRITICAL,   # delegated \ delegator  (privilege escalation)
    "skipped":          CRITICAL,   # planned \ executed
    "unplanned":        CRITICAL,   # executed \ planned
    "region":           CRITICAL,   # data residency / jurisdiction
    "pii":              CRITICAL,   # PII handling breach
    "cost_budget":      CRITICAL,   # exceeded the envelope
    "latency_budget":   CRITICAL,
    "unmet":            CRITICAL,   # a required outcome nothing delivered
    "cannot_attest":    CRITICAL,   # refused, not guessed -> routed to a human
    "coverage":         QUALITY,    # graded: how much is covered
    "confidence":       QUALITY,    # graded: measured judge/agent confidence
    "freshness":        QUALITY,    # graded: is the evidence current
}


def lane(kind: str) -> str:
    """Which lane does this finding report to? Policy decides, not the check."""
    return CHECK_LANES.get(kind, QUALITY)


def is_critical(kind: str) -> bool:
    return lane(kind) == CRITICAL


@dataclass
class Contract:
    """
    The risk envelope for one agent step. The bound the agent may not cross.

    Out-of-bound == a breach of this contract == a deterministic failure.
    """
    step_id: str
    # --- gate fields: crossing these is a breach -------------------------
    allowed_tools: Set[str]
    satisfies: Set[str]                     # requirements this step must meet
    may_delegate_to: Set[str] = field(default_factory=set)
    cost_budget: float = 1.0                # arbitrary units, per step
    latency_budget_ms: int = 5_000
    allowed_regions: Set[str] = field(default_factory=lambda: {"ca", "us"})
    pii_allowed: bool = False               # may this step handle PII at all?
    # --- measure fields: falling short degrades the reading, never halts --
    expected_quality: float = 0.90
    expected_confidence: float = 0.70
    # --- attestability ---------------------------------------------------
    verifiable: bool = True                 # can success be checked deterministically?


# Thresholds are policy, not scoring. The Risk Scorer ranks; policy gates.
@dataclass
class Thresholds:
    min_trust_to_proceed: float = 0.80      # below this, the trust reading is DEGRADED
    halt_on_any_critical: bool = True       # one failed critical check is enough


DEFAULT_THRESHOLDS = Thresholds()
