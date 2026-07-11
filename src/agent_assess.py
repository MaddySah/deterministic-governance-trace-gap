"""
The Evidence Evaluator -- the arithmetic core.

Every finding here is a set difference, a ratio, or a reachability count. There is
no model in this file, by construction. This is the block the judge cannot reach.

    tool scope       used(step) \\ allowed(step)
    delegation       delegated_to \\ may_delegate_to     (privilege escalation)
    plan conformance planned \\ executed  and  executed \\ planned
    budgets          cost > cost_budget, latency > latency_budget
    residency/PII    region not in allowed_regions; handled_pii and not pii_allowed
    coverage         AR \\ met
    provenance       evidence without established lineage cannot substantiate
    severity         |descendants(step)| x criticality   (the sort key, not a gate)

Retries are counted, not collapsed: a breach on ANY attempt is a breach, even if a
later attempt was clean. The agent's own self-critique and reported confidence are
carried into the record but never counted as evidence that a requirement was met --
an agent grading itself is the forbidden configuration.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from .policy import Contract, is_critical, lane
from .evidence import StepRun
from .orchestration import (
    declared_plan, orchestration_dag, orchestration_requirements, run_trace,
)


@dataclass
class Finding:
    kind: str                 # keys into policy.CHECK_LANES
    ref: str                  # step id or requirement id
    severity: float
    blast: float
    reason: str
    route: str                # "human" | "cannot_attest" | "digest"
    evidence_ids: List[str] = field(default_factory=list)
    policy_ids:   List[str] = field(default_factory=list)
    confidence: float = 1.0   # 1.0 = pure arithmetic. Lower only if soft-informed.

    @property
    def critical(self) -> bool:
        return is_critical(self.kind)

    @property
    def lane(self) -> str:
        return lane(self.kind)


def _blast(dag, plan) -> Dict[str, float]:
    return {sid: float(len(dag.descendants(sid))) for sid in plan}


def evaluate() -> List[Finding]:
    plan = declared_plan()
    dag = orchestration_dag()
    reqs = {r.id: r for r in orchestration_requirements()}
    trace = run_trace()

    executed = {s.id for s in trace}
    planned = set(plan)
    blast = _blast(dag, plan)
    step_crit = {sid: max((reqs[a].criticality for a in c.satisfies if a in reqs), default=1.0)
                 for sid, c in plan.items()}

    F: List[Finding] = []

    def add(kind, ref, reason, route="human", conf=1.0, ev=None, pol=None):
        b = blast.get(ref, 0.0)
        F.append(Finding(kind, ref, b * step_crit.get(ref, 1.0), b, reason, route,
                         evidence_ids=ev or [], policy_ids=pol or [], confidence=conf))

    # ---- per-observation checks (retries counted individually) -------------
    for s in trace:
        c: Optional[Contract] = plan.get(s.id)
        eid = f"{s.id}#a{s.attempt}"
        if c is None:
            continue  # unplanned; handled below
        pol = [c.step_id]

        out_of_scope = s.tools_used - c.allowed_tools
        if out_of_scope:
            add("tool_scope", s.id,
                f"attempt {s.attempt} called out-of-scope tool(s): {', '.join(sorted(out_of_scope))}",
                ev=[eid], pol=pol)

        bad_deleg = s.delegated_to - c.may_delegate_to
        if bad_deleg:
            add("delegation_scope", s.id,
                f"delegated to {', '.join(sorted(bad_deleg))} outside its permitted set "
                f"(privilege escalation by proxy)", ev=[eid], pol=pol)

        if s.cost > c.cost_budget:
            add("cost_budget", s.id,
                f"attempt {s.attempt} cost {s.cost} exceeds budget {c.cost_budget}",
                ev=[eid], pol=pol)

        if s.latency_ms > c.latency_budget_ms:
            add("latency_budget", s.id,
                f"attempt {s.attempt} took {s.latency_ms}ms, budget {c.latency_budget_ms}ms",
                ev=[eid], pol=pol)

        if s.region not in c.allowed_regions:
            add("region", s.id, f"ran in region '{s.region}', outside {sorted(c.allowed_regions)}",
                ev=[eid], pol=pol)

        if s.handled_pii and not c.pii_allowed:
            add("pii", s.id, "handled PII without permission in its contract", ev=[eid], pol=pol)

        if s.provenance is None or not s.provenance.established:
            add("cannot_attest", s.id,
                "evidence has no establishable provenance, so it cannot substantiate its claim",
                route="cannot_attest", ev=[eid], pol=pol)

    # ---- plan conformance --------------------------------------------------
    for sid in planned - executed:
        add("skipped", sid,
            f"planned step never executed (satisfies {', '.join(sorted(plan[sid].satisfies))})",
            pol=[sid])
    for sid in executed - planned:
        used = next(s.tools_used for s in trace if s.id == sid)
        F.append(Finding("unplanned", sid, 1.0, 0.0,
                         f"executed but absent from the plan; tools {', '.join(sorted(used))}",
                         "human", evidence_ids=[sid], policy_ids=[]))

    # ---- coverage: AR \ met -------------------------------------------------
    # A step satisfies its requirement only if it ran ok, stayed in scope, and
    # produced provenanced, deterministically-checkable evidence.
    # A breach fails the requirement. Missing provenance does NOT fail it -- we
    # simply cannot attest to it, which is a different, more honest outcome.
    breached = {f.ref for f in F
                if f.critical and f.kind not in ("skipped", "unplanned", "cannot_attest")}
    unattestable_steps = {f.ref for f in F if f.kind == "cannot_attest"}

    for ar_id, r in reqs.items():
        steps_for = [sid for sid, c in plan.items() if ar_id in c.satisfies]
        status, why, conf = None, "no step was declared to satisfy it", 1.0
        for sid in steps_for:
            runs = [s for s in trace if s.id == sid]
            ok = [s for s in runs if s.status == "ok"]
            if not ok:
                why = f"step '{sid}' never completed successfully"; continue
            if sid in breached:
                why = f"step '{sid}' ran, but breached its contract"; continue
            if sid in unattestable_steps:
                status = status or "cannot_attest"
                why = f"step '{sid}' ran, but its evidence has no provenance"
                continue
            s = ok[-1]
            if plan[sid].verifiable and s.produced_checkable_evidence:
                status = "met"; break
            status = status or "cannot_attest"
            why = f"only a non-verifiable step ('{sid}') covers it"
            conf = s.reported_confidence      # carry the agent's uncertainty, don't collapse it
        if status == "met":
            continue
        b = max((blast.get(sid, 0.0) for sid in steps_for), default=0.0)
        kind = "cannot_attest" if status == "cannot_attest" else "unmet"
        F.append(Finding(kind, ar_id, b * r.criticality, b, f"'{r.text}' -- {why}",
                         "cannot_attest" if kind == "cannot_attest" else "human",
                         evidence_ids=steps_for, policy_ids=[r.contract_ref], confidence=conf))

    # Risk Scorer: rank by severity. It sorts; it never gates.
    return sorted(F, key=lambda f: (not f.critical, -f.severity))
