"""
trace-gap end to end, in one command.

Part A -- static conformance on a code change (the anti-join that is the whole
detector: coverage, gaps ranked by blast radius, orphan implementations).

Part B -- the same engine pointed at an AGENT ORCHESTRATION RUN. Deterministic
gates for contract breaches, a graded trust reading for everything else, and an
auditable risk record at the end.

Synthetic data, planted faults, deterministic output. Run it twice, get the same
answer to the bit.
"""

from __future__ import annotations
import json
from .claims import claims, evidence_refs, implementations
from .conformance import coverage, gaps, orphans
from .agent_assess import evaluate
from .verdict import compose, trust_model

L = "=" * 78


def rule(t: str) -> None:
    print("\n" + L + "\n" + t + "\n" + L)


def part_a() -> None:
    rule("PART A  -  STATIC CONFORMANCE   (a code change: docs vs. diff)")
    reqs, ev = claims(), evidence_refs()
    print(f"\n  Coverage  c = |T| / |R| = {len(ev)}/{len(reqs)} = {coverage(reqs, ev):.0%}\n")
    print("  Gaps  (G = R \\ T), ranked by blast radius x criticality:\n")
    print(f"    {'SEV':>5}  {'REQ':<9} {'MODULE':<12} {'BLAST':>5}  DECLARED BEHAVIOR")
    for g in gaps(reqs, ev):
        print(f"    {g.severity:>5.0f}  {g.req.id:<9} {g.req.module:<12} "
              f"{g.blast:>5.0f}  \"{g.req.text}\"")
    print("\n  Orphan implementations (O = impl \\ claimed) -- code answering to no requirement:")
    for name in orphans(implementations(), reqs):
        print(f"    - {name}")


def part_b() -> None:
    rule("PART B  -  AGENT ORCHESTRATION   (the plan vs. what the agent did)")
    print("""
  The agent says: "I completed the loan pre-screening."
  The governor checks. Every verdict below is a set difference or a count.
""")
    findings = evaluate()

    crit = [f for f in findings if f.critical]
    qual = [f for f in findings if not f.critical]

    print("  CRITICAL GATE  (contract breaches -- binary, absolute)\n")
    print(f"    {'SEV':>5}  {'CHECK':<18} {'REF':<16} {'BLAST':>5}  DETAIL")
    for f in crit:
        mark = "?" if f.kind == "cannot_attest" else "x"
        print(f"  {mark} {f.severity:>5.0f}  {f.kind:<18} {f.ref:<16} {f.blast:>5.0f}  {f.reason}")

    if qual:
        print("\n  QUALITY MEASURES  (graded -- informs, never gates)\n")
        for f in qual:
            print(f"    - {f.kind:<18} {f.ref:<16} {f.reason}")

    print("\n  TRUST MODEL  (graded reading per consumer -- a count, not a probability)\n")
    for t in trust_model(findings):
        print(f"    {t.consumer:<18} trust={t.ratio:>4.0%}  {t.state}")
        for ar in t.failed:
            print(f"          x {ar} unmet")
        for ar in t.unattested:
            print(f"          ? {ar} cannot attest -> human")

    rule("THE AUDITABLE RISK RECORD")
    print()
    print(json.dumps(compose(findings), indent=2))

    rule("THE BOTTOM LINE")
    print("""
  Deterministic governance for a probabilistic system.

  The gate is binary and deterministic. The trust reading is graded and still
  deterministic. A soft layer may cluster these findings and propose links, but
  it never renders the verdict -- delete it and every line above is identical.

  The soft layer explains. The arithmetic decides.
""" + L)


def main() -> None:
    part_a()
    part_b()


if __name__ == "__main__":
    main()
