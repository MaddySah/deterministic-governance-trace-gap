"""
The Decision Composer -- two lanes in, one auditable risk record out.

    CRITICAL GATE   contract breaches only.  Binary, absolute, deterministic.
                    One failed critical check is enough -> HALT.
    TRUST MODEL     coverage, stability, freshness over the window. Graded.
                    It informs; it never gates.

Graded is not probabilistic: 86% coverage is a *count*, not a model's opinion. So
both lanes stay deterministic, and "you cannot flatter an anti-join" survives in
each of them.

The output is not a boolean. It is a record that carries its own evidence: the
exact evidence and policy ids that produced it, the measured confidence, the
graded risk, a remediation, and a hash so the record itself is tamper-evident.
"""

from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List
from .policy import DEFAULT_THRESHOLDS, Thresholds
from .agent_assess import Finding
from .orchestration import orchestration_requirements

PROCEED       = "PROCEED"
HALT          = "HALT"
CANNOT_ATTEST = "CANNOT_ATTEST"

REMEDIATION = {
    "tool_scope":       "revoke the out-of-scope tool or widen the contract, then re-run",
    "delegation_scope": "deny the delegation or add the sub-agent to may_delegate_to",
    "skipped":          "re-run the missing step before the decision is released",
    "unplanned":        "remove the step or add it to the declared plan",
    "cost_budget":      "raise the budget deliberately, or fix the retry loop",
    "latency_budget":   "raise the budget deliberately, or profile the step",
    "region":           "re-run in an allowed region; check data-residency policy",
    "pii":              "grant pii_allowed explicitly, or stop handling PII here",
    "unmet":            "deliver the requirement, then re-run the gate",
    "cannot_attest":    "route to a named human owner for manual attestation",
}


@dataclass
class Trust:
    """The graded reading. A count, not a probability."""
    consumer: str
    ratio: float
    state: str
    failed: List[str] = field(default_factory=list)
    unattested: List[str] = field(default_factory=list)


def trust_model(findings: List[Finding], th: Thresholds = DEFAULT_THRESHOLDS) -> List[Trust]:
    reqs = orchestration_requirements()
    protect: Dict[str, list] = {}
    for r in reqs:
        for c in r.consumers:
            protect.setdefault(c, []).append(r)

    failed = {f.ref for f in findings if f.kind == "unmet"}
    unattested = {f.ref for f in findings if f.kind == "cannot_attest"}

    out: List[Trust] = []
    for consumer, rs in sorted(protect.items()):
        total = sum(r.criticality for r in rs)
        held = sum(r.criticality for r in rs
                   if r.id not in failed and r.id not in unattested)
        ratio = held / total if total else 1.0
        state = "TRUSTED" if ratio >= 0.999 else (
            "DEGRADED" if ratio < th.min_trust_to_proceed else "REDUCED")
        out.append(Trust(consumer, ratio, state,
                         [r.id for r in rs if r.id in failed],
                         [r.id for r in rs if r.id in unattested]))
    return sorted(out, key=lambda t: t.ratio)


def compose(findings: List[Finding], th: Thresholds = DEFAULT_THRESHOLDS) -> dict:
    """The auditable risk record. Any critical breach forces HALT."""
    critical = [f for f in findings if f.critical and f.kind != "cannot_attest"]
    unattestable = [f for f in findings if f.kind == "cannot_attest"]
    trust = trust_model(findings, th)

    if critical and th.halt_on_any_critical:
        verdict = HALT
        reasoning = (f"{len(critical)} critical contract breach(es). "
                     f"Highest: {critical[0].kind} on {critical[0].ref}. "
                     "One failed critical check is enough.")
    elif unattestable:
        verdict = CANNOT_ATTEST
        reasoning = (f"No breach, but {len(unattestable)} item(s) cannot be "
                     "deterministically attested. Refused, not guessed.")
    else:
        verdict = PROCEED
        reasoning = "No critical breach; all attestable requirements held."

    # confidence: pure arithmetic = 1.0; soft-informed findings drag it down.
    conf = min([f.confidence for f in findings], default=1.0)
    risk = round(1.0 - (min(t.ratio for t in trust) if trust else 1.0), 2)

    record = {
        "decision": "orchestration_run:run-8f31",
        "verdict": verdict,
        "reasoning": reasoning,
        "evidence_ids": sorted({e for f in findings for e in f.evidence_ids}),
        "policy_ids": sorted({p for f in findings for p in f.policy_ids}),
        "confidence": round(conf, 2),
        "risk": risk,
        "suggested_remediation": [
            f"{f.ref}: {REMEDIATION.get(f.kind, 'review')}"
            for f in findings if f.critical
        ][:4],
        "trust": {t.consumer: round(t.ratio, 2) for t in trust},
    }
    # audit_hash last: it seals everything above it.
    payload = json.dumps(record, sort_keys=True, separators=(",", ":"))
    record["audit_hash"] = "sha256:" + hashlib.sha256(payload.encode()).hexdigest()[:16]
    return record
