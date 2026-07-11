# trace-gap for agent orchestration layers

### Attesting to what an agent *did*, not what it was *supposed* to do — with arithmetic

---

## Why this is the same problem

An orchestration layer is a plan: a DAG of agent steps, each with a contract — the
tools it is allowed to call, the sub-goals it is meant to satisfy, the outputs it
should produce. The plan is a *story the system tells about itself*. The run trace —
the tools actually called, the steps actually executed, the outputs actually
produced — is the *implemented reality*.

That is exactly the gap trace-gap was built for. Nothing in the engine changes. The
claim source is the orchestration plan instead of a design doc; the evidence source
is the run trace instead of a diff. Everything downstream — anti-join, coverage,
blast-radius ranking, the cannot-attest route, the arithmetic verdict — is
identical. The design doc's use-case map already names this wedge: *approved action
spec vs. what the agent did — "agents act; nobody attests to what they actually
did."* This note makes that row concrete.

The reason it matters now: agentic orchestration is moving into regulated and
high-consequence workflows faster than anyone has built the assurance layer for it.
An LLM-judge grading whether an agent "did the right thing" is the same trap the
essay warns about — a sample from a distribution, non-reproducible and game-able. A
run trace, by contrast, is a set of facts you can count.

---

## The rule, unchanged

> **Soft proposes. Counting decides. Structure ranks.**

A model may *propose* whether a free-text step met its intent. It never renders the
verdict. The verdict is a set difference, a coverage ratio, a reachability count.
What cannot be checked deterministically is not guessed — it is routed to a human as
*cannot attest*.

---

## The four checks (all arithmetic)

Let the plan declare, per step, an allow-list of tools and the requirements it
satisfies. Let the trace record, per executed step, the tools it used and its
status.

```
tool-scope violation   used(step) \ allowed(step)          # per step, a set difference
skipped step           planned \ executed
unplanned step         executed \ planned                  # orphan execution
unmet requirement      AR \ met                            # met needs a successful,
                                                           # deterministically-verifiable step
severity               |descendants(step)| x criticality   # the worklist sort key
```

Each is a set operation or a reachability count on a graph you already have. No
inference at decision time, reproducible to the bit, falsifiable by pointing at the
rows.

**What each catches, and why it is not a nuisance:**

- **Tool-scope violation.** An agent that calls a tool outside its contract is the
  clearest, cheapest signal of misbehavior there is — an unauthorized data source, a
  side-effecting action it was never granted. `used \ allowed` finds it with a set
  difference. In a permissioned domain (a credit pull that reaches for `web.search`)
  this is a compliance event, not a style nit.
- **Skipped and unplanned steps.** `planned \ executed` catches a required step the
  agent silently dropped; `executed \ planned` catches a step it invented. Both are
  plan-conformance, both are set differences.
- **Unmet requirement.** A declared sub-goal that no successful, checkable step
  satisfied. The anti-join again — this time between the orchestration's requirements
  and the steps that actually delivered them.
- **Cannot attest.** A step whose success is not deterministically checkable — a
  free-text rationale, a judgment call — is *not* passed and *not* failed. It is
  routed to a human. A soft judge may annotate it; it never decides it.

The worklist is ranked by blast radius over the orchestration DAG: a violation on a
step that many later steps and consumers depend on outranks one on a near-terminal
step. Structure supplies the impact for free.

---

## The verdict

The output is not "the agent misbehaved." It is a **trust ratio per consumer** — of
the severity-weighted requirements protecting what each downstream consumer depends
on, how many held — plus the explicit cannot-attest list. A compliance-audit
consumer can read `trust = 33%, AR-03 and AR-05 unmet` and know precisely what failed and why;
an applicant-comms consumer sees a different ratio because it depends on different
requirements. Deterministic, auditable, and legible to a risk reviewer as-is.

See `src/agent_assess.py` and `src/verdict.py` for the implementation, and run
`python -m src.demo` for a worked loan-pre-screening example with four planted
faults — one of each kind above.

---

## Where it plugs into an orchestration stack

- **Post-run gate.** After each orchestration run, emit the ranked findings and the
  per-consumer trust verdict. Non-blocking by default; blocking on a tunable
  severity threshold for high-criticality flows.
- **Offline evaluation harness.** Run it across a suite of recorded traces to score
  an orchestration's conformance over time — the same discipline as frontier-model
  evaluation, where a golden reference and a deterministic rubric decide, not a
  judge grading a judge.
- **Governance evidence.** The coverage and violation artifacts map directly to the
  "prove the system did what its spec says" demand that conformity assessment places
  on high-risk automated decisioning.

---

## What it still refuses to claim

The refusal list carries over intact. trace-gap does **not** assert that an agent's
output is *correct*, only that a step ran, stayed in scope, and satisfied a declared
requirement for which deterministic evidence exists. It does not read the agent's
reasoning path. It does not let a model be both proposer and judge. Whether the
adverse-action notice was *well-written* is a human's call; whether it was *sent at
all* is an anti-join. trace-gap answers only the second, and says so.
