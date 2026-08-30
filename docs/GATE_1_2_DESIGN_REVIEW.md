# Gate 1.2 Design Review and Decision Record

> **Status:** Final candidate for Craig review; not committed, pushed, tagged, or effective.
>
> **Scientific boundary:** Gate 1.1 primary outcome-generating runs remain zero. This review uses no Gate 1.1 or Gate 1.2 outcome.

## Purpose

This record explains the outcome-independent choices in `preregistrations/GATE_1_2_PREREGISTRATION.md`. Gate 1.2 is designed before Gate 1.1 execution so later robustness choices cannot be selected to rescue, amplify, or reinterpret the Gate 1.1 result.

Gate 1.2 has two roles:

1. independently replicate the exact Gate 1.1 scripted topology contrast under fresh randomness;
2. test whether its direction survives a compact, prespecified set of nearby mechanism and design changes.

It is not a broad parameter search and does not introduce an LLM.

## Frozen-authority boundary

| Authority | Identity |
|---|---|
| Gate 1.1 preregistration commit | `cc1ab868a7401099751030580649e49258654fe2` |
| Gate 1.1 preregistration tag | `gate1.1-prereg-v1` |
| Gate 1.1 preregistration SHA-256 | `e6b7d28870c773c4ad7897349b74acfb99775a83905eaf66dcad2602a639c706` |
| Gate 1.1 implementation commit | `4c8bb4d3f88a38469a6edcb770b1b0a037a73ae7` |
| Gate 1.1 implementation tag | `gate1.1-impl-v1` |
| Gate 1.1 source-bundle SHA-256 | `c8b8dd93b72711eec699cc1fc8981f20beef2c3daed3f3394263c8175dc35b09` |
| Gate 1.1 campaign canonical hash | `sha256:76ceaf1e182b5b6ecbe8214a694b4000d47d495165ab025f15112901e71600f2` |

Gate 1.1 protocol, code, primary decision, and public tags remain unchanged. Gate 1.2 receives its own future protocol, implementation, manifests, artifacts, analysis, and Passport.

The local review branch `gate-1.2-preregistration` begins exactly at `gate1.1-impl-v1`, commit `4c8bb4d3f88a38469a6edcb770b1b0a037a73ae7`.

## Design principles

The panel follows five rules:

- use the exact Gate 1.1 replication as the sole Gate 1.2 primary test;
- vary one dimension at a time in standard robustness cells;
- use simple fractions, counts, or swaps-per-edge values rather than fitted levels;
- keep every treatment comparison matched and condition-blind;
- require the entire robustness family, not a favorable subset, for a robust claim.

## Exact replication decision

The fresh replication keeps all Gate 1.1 scientific semantics, uses root `20260831`, and runs 3,000 matched pairs. This is the calendar successor to the Gate 1.1 root `20260830`, selected without outcome information. Because the generator is stateless SHA-256 over the complete seed and namespace tuple, adjacent numeric roots do not share mutable PRNG state.

The replication uses Gate 1.1's endpoint, paired estimator, 95 percent Student interval, practical five-percentage-point flag, and separate Hoeffding statistic. Its directional hypothesis is supported only when the fresh-replication interval lower bound is greater than zero.

An independently seeded replication should agree in direction if the effect is stable, but it is not required to reproduce an identical point estimate. A conservative two-one-sided equivalence assessment with a fixed plus-or-minus five-percentage-point margin separately labels magnitude consistency.

## Robustness panel rationale

| Dimension | Off-anchor values | Outcome-independent rationale |
|---|---|---|
| Transmission | `1/8`, `3/8` | Exact binary fractions equally spaced by one eighth around the `1/4` anchor |
| Seed count | `3`, `12` | One half and twice the six-seed anchor; exact 5 and 20 percent fractions |
| Horizon | `4`, `12` rounds | Four rounds below and above the eight-round anchor |
| Rewiring | `360`, `840` swaps | Three and seven accepted swaps per 120-edge graph around the five-per-edge anchor |
| Seed dispersion | six consecutive; six every tenth label | Deterministic ring-coordinate concentration and maximal regular spacing without reading treatment topology |
| Alternate topology | three rewired realizations per cluster | Compact within-cluster estimate of sensitivity to treatment-topology realization variance |

The exact-replication anchor supplies `1/4`, six seeds, eight rounds, 600 swaps, uniform placement, and one rewired realization. No anchor condition is redundantly rerun inside each panel.

### Transmission

One eighth and three eighths are exactly representable by integer u64 thresholds. The panel is deliberately three points including the anchor, not a curve-fitting grid.

### Seed count

Counts 3, 6, and 12 create exact 5, 10, and 20 percent seed fractions. The initially unseeded denominators are frozen at 57, 54, and 48, so incidence remains comparable as a fraction.

### Horizon

Four and 12 are simple finite windows around eight. No run may continue to an observed peak or stop when a desired contrast appears.

### Rewiring

The graph has exactly 120 undirected edges. Values 360, 600, and 840 therefore equal three, five, and seven accepted swaps per original edge. The attempt cap remains 60,000; invalid construction is never replaced by a partial graph or another seed.

### Seed dispersion

Both placement rules use the canonical pre-rewiring ring labels and then reuse the identical six labels in both matched conditions. They never optimize on realized ring or rewired centrality, distance, propagation draws, or outcomes. The design intentionally tests whether the topology contrast depends on initial concentration while avoiding condition-specific seed selection.

### Alternate topology

Gate 1.1 already generates an independently rewired treatment graph for every matched pair, so it does not rely on one global rewired realization. Gate 1.2 instead holds seeds and propagation draws fixed within a cluster while sampling three independent treatment topologies. The analysis averages the three treatment incidences before subtracting the single ring incidence, directly testing sensitivity to topology-realization variance while leaving one independent contrast per cluster. The 1,000 clusters, not the 3,000 nested rewired outcomes, are the independent analysis units.

## Sample-size decision

The exact replication retains 3,000 pairs and Gate 1.1's distribution-free half-width below five percentage points.

Every robustness contrast uses 1,000 independent units. Its unadjusted two-sided Hoeffding half-width is approximately 8.59 percentage points; the 11-cell Bonferroni simultaneous reference is approximately 11.03 points. These are deliberately weaker than exact-replication precision but strong enough to identify gross sign instability without a computationally excessive dense sweep.

Projected totals are:

- 3,000 exact-replication pairs and 6,000 condition runs;
- 10,000 standard robustness pairs and 20,000 condition runs;
- 1,000 alternate-topology clusters and 4,000 condition runs;
- 14,000 independent units, 30,000 condition runs, and 1,800,000 scripted agent-runs overall.

No Gate 1.1 observed variance, effect size, interval, or significance enters these choices.

## Inference hierarchy

Gate 1.2 has exactly one primary test: the 3,000-pair exact replication. It is not multiplicity-adjusted because it is the only primary contrast.

The 11 robustness contrasts form one family. Each receives an unadjusted 95 percent interval and a Bonferroni simultaneous 95 percent interval using a frozen family size of 11. Strong robustness requires every simultaneous lower bound to exceed zero. All-positive point estimates are reported separately as descriptive directional stability.

This hierarchy avoids both extremes: it does not treat 11 cells as independent discovery opportunities, and it does not let one significant cell rescue null or adverse results elsewhere.

## Frozen classification logic

The preregistration supplies an ordered algorithm for:

- replicated and robust;
- replicated but specification-sensitive;
- replicated with directionally consistent but imprecise robustness;
- directionally consistent but imprecise exact replication;
- failed replication;
- heterogeneous/inconclusive;
- concordant non-support;
- invalid/inconclusive.

Magnitude consistency is an independent modifier. Strong directional reversal is also separately flagged when any simultaneous robustness interval lies wholly below zero.

A later positive Gate 1.2 result cannot turn a Gate 1.1 null into support. A Gate 1.1 null also cannot cancel the requirement to execute the frozen Gate 1.2 suite.

## Researcher-degree-of-freedom closure

The following are fixed before Gate 1.1 outcome generation:

- three root seeds and every RNG namespace;
- every cell ID and value;
- placement construction and tie elimination;
- alternate-topology realization count and nesting;
- unit IDs, sample sizes, and projected artifact counts;
- endpoint and denominators;
- primary, equivalence, and simultaneous-interval formulas;
- family size and critical probabilities;
- classification order;
- validity, interruption, corruption, and topology-failure behavior;
- execution and analysis isolation.

After public freeze, implementation may test these rules only with nonproduction fixture identities. Any outcome-sensitive change requires a preserved amendment and is prohibited after either gate's outcomes exist.

## Repository plan

This review pass adds only:

```text
preregistrations/GATE_1_2_PREREGISTRATION.md
docs/GATE_1_2_DESIGN_REVIEW.md
```

The existing research agenda already prospectively names all seven Gate 1.2 dimensions and the before-unblinding requirement, so no historical roadmap text needs rewriting.

Future implementation, under separate authorization, should use a structure such as:

```text
manifests/gate1_2_suite_v1.json
pasko_agent_society/gate12_*.py
tests/test_gate12_*.py
artifacts/gate1_2_v1/             # ignored, generated only when authorized
results/gate1_2/                  # compact frozen evidence
docs/GATE_1_2_IMPLEMENTATION_CERTIFICATION.md
docs/GATE_1_2_REPORT.md
docs/REPRODUCING_GATE_1_2.md
```

No manifest, implementation, artifact directory, seed realization, topology, treatment outcome, or analysis is created in this preregistration pass.

## Proposed freeze sequence

1. Review the two new documents and exact hashes.
2. Reconfirm Gate 1.1 has zero outcome-generating runs.
3. Commit the approved documents on `gate-1.2-preregistration`.
4. Push that branch and create an immutable annotated preregistration tag under separate Craig authorization.
5. Require public CI against the exact commit and tag.
6. Only then separately authorize Gate 1.1 execution.

This candidate authorizes no commit, push, tag, implementation, scientific run, analysis, merge, release, Gate 2 work, or LLM adapter.
