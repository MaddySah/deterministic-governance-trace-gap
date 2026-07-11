# The Band of Pseudo-Control
### Verifying systems you can't fully know — with arithmetic, not oracles

Most organizations have exactly one reliable method for discovering how their systems are wired: change something, and wait for someone to scream.

Someone ships a patch. A dashboard goes blank. A field stops arriving in a downstream table nobody remembered was downstream. The "minor" config edit turns out to feed three teams. We give this many names — incident, regression, postmortem — but the underlying instrument is always the same. It is the scream test, and it is how we learn our true blast radius: after the fact, at the worst possible time, from the angriest possible source.

This essay is about replacing the scream test with something cheaper, earlier, and — this is the surprising part — almost entirely arithmetic.

## Every system tells a story about itself

Pick any system and you will find, sitting right next to it, a story about what it is supposed to be. A design document describes intended behavior. A lineage graph declares which things depend on which. A dashboard wears a label — "complete," "fair," "validated." A service advertises an SLA. An ingestion pipeline has an expected shape: these fields, this cadence, this volume.

And in every case, quietly, reality walks away from the story. The doc says the patch rejects expired tokens; the code rejects stale ones, mostly. The graph omits the dependency that matters. The "fairness" label rests on nothing anyone can point to. The expected field stops arriving, the average barely moves, and no alarm fires.

This is not drift in the machine-learning sense. Drift — distributions shifting under a model — is one *dialect* of this problem, the statistical one. The general phenomenon is older and dumber and far more universal: the map goes stale, and nobody notices until something breaks. Most systems that suffer from it have no model anywhere in sight. What they have is a gap between a documented story and an implemented reality, and no instrument pointed at that gap except the scream.

## The trap: the omniscient version

The instinct, once you see the gap, is to want to close all of it. Verify everything. Reconcile the map to the territory completely. Know the truth.

That instinct should be resisted, and the reasons define the boundary of anything practical.

First, truth at that resolution is ruinously expensive. Checking everything against everything, continuously, over high volume and velocity, costs more than the failures it prevents. Nobody actually wants omniscience; they want to not get paged at 3 a.m.

Second, the deepest version is not merely expensive but impossible. To verify that an implementation matches its intent, you must know the intent — and intent lives in informal natural language, while the implementation is a formal artifact. There is no algorithm that guarantees a specification faithfully captures what a human meant. Researchers call this the oracle problem, and it does not yield to more compute. Worse: hand the judgment to a language model, and it will often infer the *intended* behavior from a function's name and quietly bless code that contradicts it. The judge can be confidently, plausibly wrong.

So the omniscient verifier is a costume. It looks like rigor; it is a damsel not actually in distress. The practical system is the one that knows precisely how much it cannot know.

## You are not in the truth business

Here is the reframe that makes the problem tractable.

There are three sides to every story: the documented one, the real one, and the one a human must judge. The system's entire job is to place the first two side by side, clearly. It never touches the third. It does not decide whether a discrepancy is a defect; it surfaces the discrepancy and routes it to the person who owns that call.

This dissolves the question *"do we want truth at that resolution?"* — because the thing you are building was never in the truth business. It is in the *here are the two stories, you decide* business.

What you can do, then, is **partition**. Draw a hard line around the slice you can assert with arithmetic — present or absent, matched or unmatched, stable or wobbling. Refuse to claim anything past that line. And in the band between certainty and ignorance, run informed decisions and educated guesses, rather than pretending at proof.

I think of this as a *band of pseudo-control*. You cannot make a non-deterministic system deterministic. You can wrap a deterministic scaffold around the part you can measure, and operate honestly in the margin. Stephen Covey drew a circle of control, a wider circle of influence, and a still wider circle of concern, for human attention. The same partition works for systems. Most engineering effort is squandered out in the circle of concern — fretting at things it cannot assert. The discipline is to spend it in the circle of control, and to be honest about the boundary.

## The engine: one rule

Everything practical that follows reduces to a single rule:

> **Let the soft layer propose. Let counting decide. Rank by structure.**

Fuzzy techniques — similarity, language models, inference — are permitted to *suggest*: these two things might correspond; this answer might be wrong. They are never permitted to *render the verdict*. The verdict belongs to arithmetic: the agreement rate is 0.6; forty-seven of fifty fields arrived; this requirement maps to zero tests. And you never let a single model be both the proposer and the judge — because that is exactly the configuration that an adversary, or simple bad luck, can flatter.

## Why arithmetic, and why it is enough

The reason to insist on counting is not aesthetic. It is that the operations involved are trivial, deterministic, falsifiable, and nearly impossible to game. Consider what a verdict actually requires.

Let **R** be the set of requirements extracted from the document. Let a relation link requirements to implementation evidence — a test that names them, a commit that touches the relevant file. The covered requirements **T** are those with at least one link. Then the gaps are simply the set difference:

```
G = R \ T
```

That is a left anti-join — the most ordinary operation in data engineering. Coverage is a ratio:

```
c = |T| / |R|        (a number in [0, 1])
```

To prioritize the gaps, build the dependency graph and count, for each requirement, how many things sit downstream of it — its descendants. Blast radius is that count; severity is the count times a hand-set criticality weight:

```
severity(r) = |descendants(r)| · weight(r)
```

Sort the gaps by severity, descending. That is your worklist. This is triage: an emergency room cannot run every test on every patient, so it sorts by acuity and spends scarce attention where the stakes are highest. Note what the worklist is *not*: it is not a trained classifier, so there is no AUC-ROC, no labels, no probability to calibrate. Ranking a worklist is a sort key, not a model. The structure you already built hands you the impact for free.

And for requirements shaped like an answer — "must return the balance," "must reject the expired token" — there is a counting test for robustness too. Ask the same question many ways. Collect the answers. A correct, well-grounded system returns a tight cluster; a fragile one wobbles. Measure the wobble as normalized entropy, or more simply as an agreement rate:

```
stability = (count of the most common answer) / (number of phrasings)
```

Low stability is the flag. No model grades another model; you are counting the spread of a distribution.

Every verdict in the system is one of these: a set difference, a ratio, a reachability count, the entropy of a small distribution. None requires inference at decision time. None requires training. Run it twice on the same inputs and you get the same answer, to the bit. Point at any flag and you can show the rows that produced it.

Contrast a language model as judge. Its output is a *sample* from a distribution; run it twice and it may disagree with itself, and a well-crafted input can coax it toward a chosen answer. A count has no such surface. You cannot flatter an anti-join. This is why simplicity here is not a limitation to apologize for — it is the entire source of the system's trustworthiness.

## The decision matrix

Every choice above was made by rejecting a more tempting, more expensive, more fragile alternative. Laid out, the rejections *are* the design.

| Decision | The tempting path | The principled choice | The principle |
|---|---|---|---|
| What to check | Verify everything; find the truth | The gap between a system's stated story and its reality | Truth at full resolution is unaffordable and unwanted; the gap is cheap and universal |
| What kind of problem | Treat it as drift / statistical monitoring | Map versus territory, mostly non-statistical | Drift is only the ML dialect of a more general staleness |
| Linking intent to reality | Embeddings everywhere | Deterministic joins on keys; similarity only at the language seam, as suggestions | Most links have clean keys; similarity that *judges* is gameable, similarity that *proposes* is safe |
| Rendering the verdict | A model as judge | Arithmetic decides; the soft layer only proposes | A count cannot be flattered; never let one model both propose and judge |
| How deep to look | Prove the path from input to output | Check endpoints and touchpoints — presence and correspondence | Path-proof is the formal-methods rabbit hole; an opaque path is a hand raised for a human |
| Ranking the work | Score a classifier (AUC-ROC) | Sort by blast radius, computed from the dependency graph | With no labels there is no classifier; ranking is a sort key, and structure supplies impact for free |

Read down the third column and the engine rule reappears: soft proposes, counting decides, structure ranks.

## What it must refuse to say

A system built this way earns trust less by what it claims than by what it declines to claim.

It *can* say: here are the requirements with no corresponding implementation; here are the expected-but-missing fields; here are the declared-but-unused dependencies; here are the answers that wobble under rephrasing — ranked by computed blast radius. All falsifiable, all cheap, all reproducible.

It *must refuse* to say: that a flagged item is definitely a defect — it is a candidate for human eyes. That an unflagged item is safe — absence of evidence is not evidence of correctness. That the internal path is correct — it does not read paths. And any semantic verdict in which a model would be both proposer and judge — forbidden by construction.

Most systems sold in this space overclaim exactly those four things. A system that *structurally cannot* is the rarer, and the more credible, artifact.

## Verification is partition, not certainty

The scream test endures because the alternative is usually framed as omniscience — and omniscience is expensive, unwanted, and in its deepest form impossible. But that was always the wrong alternative. The real one is humbler and entirely buildable: partition the knowable from the unknowable, assert only the knowable with arithmetic you can show your work for, and spend your limited attention on the knowable part with the largest blast radius.

You cannot control a non-deterministic system. You can draw a clean line around the band where your guesses are educated, make informed decisions inside it, and stop pretending about the rest.

That band — not certainty — is the whole of the job. And it is enough to retire the scream.
