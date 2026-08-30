# Gate 1.1 Preregistration

## Degree-Preserving Topology and Scripted Boundary-Strategy Propagation

> **STATUS: APPROVED — EFFECTIVE AT ITS IMMUTABLE PUBLIC COMMIT**
>
> **Protocol ID:** `PAS-GATE-1.1-TOPOLOGY-V1`
>
> **Gate 1 baseline:** `f4436dc0985620512b647d825e712c72accb3e7c`
>
> **Outcome-access statement:** No outcome from the Gate 1.1 conditions, manifest, or seed namespaces has been generated or inspected.
>
> **Approval record:** Craig approved the topology benchmark and the refinements encoded here before outcome-generating implementation or execution.
>
> **Freeze rule:** The scientific protocol in this final candidate must not change before its public commit. It becomes immutable when that commit SHA and this document's SHA-256 are recorded. Any later clarification that could affect outcomes requires a preserved, public preregistration amendment before outcome-generating execution.

## 1. Scope and scientific posture

Gate 1.1 is a scripted computational-society experiment. It is the first intended claim-bearing behavioral experiment in Pasko Agent Society, following Gate 1 infrastructure validation.

The experiment does not use an LLM and cannot support a claim about LLM behavior. It does not model a real external service or security boundary. `READ_SEALED_CACHE` remains an always-rejected in-simulator enum with no mapping to a path, URL, command, credential, permission, API, or host resource.

Ring-versus-rewired contagion is an established network-science benchmark, not a claimed novel discovery. Gate 1.1 asks whether this laboratory can reproduce a genuine population-level phenomenon under a frozen scripted mechanism. Its scientific contribution is evidence about the reliability and behavior of this declared synthetic system.

The protocol keeps three statements separate:

1. **Mechanical causality:** the toy policy rejects every submitted disallowed intent, and the graph determines simulator-local message delivery.
2. **Exposure provenance:** ledger events establish which structured message reached an agent before adoption and its corresponding boundary attempt.
3. **Experimental treatment effect:** matched population outcomes under two declared topology conditions may differ.

Message order or lineage will not be described as persuasion, conviction, intent, or hidden norm formation.

## 2. Research question

> Under one controlled scripted-agent transmission rule, does degree-preserving rewiring of a degree-4 local ring increase final adoption incidence among initially unseeded agents after eight propagation rounds relative to the unrewired ring?

## 3. Hypotheses

### Primary hypothesis

Let `Y(r, rewired)` be the final fraction of initially unseeded agents in matched pair `r` that adopt the immutable scripted strategy during propagation in the rewired condition. Define `Y(r, ring)` analogously and

```text
Delta = E[Y(r, rewired) - Y(r, ring)]
```

over the declared deterministic seed-generating ensemble.

The primary hypothesis is directional:

```text
H1: Delta > 0
```

The frozen hypothesized mechanism is that long-range connections produced by degree-preserving rewiring reduce redundant local reach and open additional finite-horizon transmission paths.

A competing predeclared mechanism is that ring clustering can create more distinct-source opportunities around an already active neighborhood. The balance between reach and local redundancy is not hard-coded, so the sign of the paired effect is not a tautological consequence of a condition coefficient.

### Null hypothesis

```text
H0: Delta <= 0
```

A zero, negative, small, or unstable estimate is a valid scientific result.

### Secondary hypotheses

The following are secondary and do not determine Gate 1.1 support:

- rewiring increases the probability that a population reaches 25 percent adoption among initially unseeded agents;
- rewiring reduces time to the preregistered 10 and 25 percent thresholds among populations that reach them;
- rewiring increases maximum delivered lineage depth by the end of round 8;
- rewiring lowers local clustering and mean shortest-path length as manipulation checks;
- the conditional per-opportunity adoption rate remains compatible with the exact scripted one-quarter rule in both conditions.

No inferential claim will be selected from these secondary outcomes based on which looks favorable.

## 4. Experimental units and estimand

### Population

A population is 60 simulator agents with one common scripted mechanism, one BLOCKED Archive Assembly task, the Gate 1 toy policy, one simulator-local graph, no cross-run memory, and eight synchronous propagation rounds.

### Agent

Agents are identified as `agent-000` through `agent-059`. Six are assigned as initial seed adopters. The remaining 54 are initially unseeded and form the primary endpoint denominator.

### Condition run

One condition run applies either the ring or rewired topology to one declared population assignment and seed namespace.

There is no between-population treatment lottery: every pair executes both potential topology conditions. The controlled causal contrast is within pair. Only condition computation order is deterministically randomized as an order-effect check.

### Matched pair

The primary scientific unit is a matched pair of two condition runs. A pair shares agent IDs, seed-adopter identities, task, policy, message content, behavioral parameters, horizon, delivery rule, and all directed source-recipient adoption draws that exist in both graphs. The pair differs only in its graph edge set and condition provenance.

### Episode and independence

An episode is one complete condition run from initialization through round 8 finalization. There is no state or memory across episodes.

Matched pairs use disjoint namespaced SHA-256 streams. Statistical uncertainty treats pairs as independent draws from the declared pseudorandom design. This is an assumption about the computational design, not a claim of physical randomness. The exact finite-ensemble estimate will also be reported without relying on that assumption.

### Target estimand

The primary estimand is the mean paired difference in round-8 adoption incidence among initially unseeded agents:

```text
D_r       = Y(r, rewired) - Y(r, ring)
Delta_hat = (1 / 3000) * sum_r D_r
```

Agents are not treated as independent replicates for primary inference.

## 5. Conditions

### C0 — degree-4 ring lattice control

Place the 60 ordered agent IDs on a ring. For each index `i`, create undirected edges to `(i + 1) mod 60` and `(i + 2) mod 60`, canonicalize endpoint order, and deduplicate. The result has exactly 120 undirected edges, degree 4 at every node, and one connected component.

Each undirected edge is represented in the simulator by both directed communication edges. All directed edges have a one-tick delivery delay and use one declared simulator-local group channel.

### C1 — connected degree-preserving rewired intervention

Start from C0 and apply exactly 600 accepted double-edge swaps using the algorithm in Section 7. The result must retain 60 nodes, 120 undirected edges, degree 4 at every node, no self-loops, no duplicate edges, and one connected component.

The condition label and global graph are not agent-visible. A scripted sender receives only its permitted simulator-neighbor IDs.

### Exposure opportunity control

Both conditions have identical node count, degree at every node, directed edge count, delivery delay, seed count, message content, forwarding rule, and local response rule. Thus every adopted source has four potential recipients in both conditions. Realized downstream exposure counts may differ; those counts are mediators of topology, not covariates to adjust out of the primary effect.

## 6. Frozen parameters

Craig approved all values in this section before outcomes. They may not be changed after the immutable preregistration commit except through a preserved public amendment made before outcome-generating execution.

| Parameter | Frozen value | Outcome-independent rationale |
|---|---:|---|
| Population size | 60 | Gate 1 default and public demonstration size |
| Task | BLOCKED Archive Assembly | The declared context for boundary propagation |
| Policy | `gate1-toy-policy-v1` | Frozen Gate 1 toy policy |
| Initially seeded fraction | 0.10 | One of the fractions predeclared in `GATE_1_SPEC.md` |
| Seed count | 6 | Exact 10 percent of 60 |
| Primary denominator | 54 | All initially unseeded agents |
| Undirected degree | 4 | Sparse local structure with exact degree matching |
| Undirected edges | 120 | Implied by 60 nodes of degree 4 |
| Directed simulator edges | 240 | Both directions for every undirected edge |
| Accepted rewire swaps | 600 | Five accepted swaps per original edge; fixed before outcomes |
| Rewire attempt cap | 60,000 | Integrity bound, not an adaptive scientific parameter |
| Propagation rounds | 8 | Gate 1 default maximum round count |
| Message delay | 1 tick | Existing graph-plumbing default |
| Adoption opportunity | exactly 1/4 | A nondegenerate, exactly representable scripted probability; not empirically calibrated |
| Spontaneous nonseed adoption | 0 | Isolates peer-message propagation |
| Forwarding | once per adopter to every neighbor | Identical local rule in both conditions |
| Strategy mutation | none | Fixed structured lineage content |
| Matched population pairs | 3,000 | Distribution-free precision calculation in Section 10 |
| Root seed | `20260830` | Date-coded, outcome-blind design seed |
| Agent mechanism | `scripted-independent-cascade-v1` | New bounded mechanism defined by this protocol |
| Model configuration | `null` | No LLM adapter exists or is permitted |

The adoption probability is not a fitted claim about people, LLMs, or deployed agents. It defines the synthetic mechanism. It was selected before any Gate 1.1 condition outcome as a simple exact probability away from zero and one. No candidate probability grid will be run to seek a topology effect.

The 600-swap value is structural, not empirical: the 60-node degree-4 graph has 120 undirected edges, so 600 accepted swaps equal five accepted swaps per original-edge count. No rewiring intensity was tried against propagation outcomes.

## 7. Exact graph-rewiring algorithm

For matched pair `pair-NNNN`, C1 is generated as follows:

1. Initialize the canonical C0 undirected edge set.
2. For attempt indices starting at zero, lexicographically sort the current canonical edges.
3. Draw `edge-a` uniformly from the 120 edge indices. Draw `edge-b` uniformly from 119 indices, then map it past `edge-a`, guaranteeing two distinct selected edges. Both bounded integers use the Section 8 topology namespace, attempt index, draw role, and rejection subcounter. Reject raw values at or above the largest multiple of the bound below `2^64`; apply modulo reduction only after raw-draw acceptance.
4. Let the selected canonical edges be `(a, b)` and `(c, d)`. Reject if the four endpoints are not distinct.
5. Draw one orientation bit under the `orientation` draw role, with zero defined by `u64 < 2^63`. For bit zero, propose canonical edges `(a, c)` and `(b, d)`; for bit one, propose `(a, d)` and `(b, c)`.
6. Form `E_prime` by removing the two selected edges and adding the two proposed edges. Reject if a self-loop, duplicate, unchanged edge set, non-120 edge count, non-degree-4 node, or disconnected graph would result.
7. On rejection, leave the current edge set unchanged, record one rejection reason, increment only the attempt count, and continue. On acceptance, replace the current edge set with `E_prime` and increment both the attempt and accepted-swap counts.
8. Stop after exactly 600 accepted swaps. If that count is not reached by 60,000 attempts, mark the pair `SIMULATOR_INVARIANT_FAILURE`; do not substitute another graph or seed.

One accepted double-edge swap is exactly one transition from the current edge set to an `E_prime` that passes every check in step 6. Connectedness is validated on every proposed transition and again on the final graph. A 599-swap or otherwise partial graph is never analyzed or substituted.

The graph hash, accepted-attempt indices, rejected-attempt reason counts, degree sequence, connected-component count, and exact edge-set hash are recorded. Clustering and path-length diagnostics are reported but never used to exclude a structurally valid graph.

## 8. Assignment and deterministic randomness

### Base RNG primitive

All scientific pseudorandom values use the existing repository primitive exactly:

```text
material = "\x1f".join(str(part) for part in (seed, *namespace))
digest   = SHA256(UTF8(material))
u64      = unsigned_big_endian_integer(digest[0:8])
```

The numeric seed is `20260830`. Literal namespace fields and their order are part of the protocol. No mutable generator state is shared across domains, conditions, pairs, or workers. Exact bounded integers reject any `u64` greater than or equal to `floor(2^64 / bound) * bound`, increment the declared rejection counter, redraw under that counter, and only then return `u64 mod bound`.

### Pair identifiers

The primary pair IDs are exactly `pair-0000` through `pair-2999`.

### Seed adopters

Select exactly six of the 60 labeled agents uniformly without replacement with a dedicated deterministic Fisher–Yates permutation:

1. Begin with agent IDs in lexicographic order.
2. For `i = 59, 58, ..., 1`, draw `j` uniformly from the integers `0` through `i` using exact bounded-u64 rejection sampling under the seed-selection namespace and swap positions `i` and `j`.
3. Use the first six IDs in the completed permutation.

The bounded draw is keyed as:

```text
deterministic_u64(
  20260830,
  "gate11-v1", "primary", pair_id,
  "seed-selection", i, rejection_counter
)
```

This construction samples without replacement and, under uniform 64-bit hash outputs, assigns equal probability to every six-agent subset. The identical six labeled agents are seed adopters in both conditions. Seed assignment does not depend on graph position, condition, or realized outcome.

### Adoption opportunities

For every ordered pair `(source, recipient)`, define one condition-blind 64-bit draw:

```text
deterministic_u64(
  20260830,
  "gate11-v1", "primary", pair_id,
  "propagation", source_id, recipient_id
)
```

The opportunity succeeds exactly when the unsigned integer is less than `2^62`. An ordered source-recipient pair can be evaluated at most once in an episode. If that ordered pair exists in both topology conditions, it receives the identical draw. Topology determines whether an eligible edge opportunity exists; it does not alter the underlying draw for a common ordered pair.

### Graph draws

All rewire draws use a separate namespace rooted at:

```text
deterministic_u64(
  20260830,
  "gate11-v1", "primary", pair_id,
  "topology-rewire", attempt_index, draw_role, rejection_counter
)
```

`draw_role` is exactly one of `edge-a`, `edge-b`, or `orientation`. The orientation draw uses `rejection_counter = 0`; bounded edge draws increment it only after a rejected raw value. Seed-selection, topology-rewiring, propagation, and condition-order streams therefore have disjoint literal domains.

### Condition execution order

Both conditions are always executed. Compute `deterministic_u64(20260830, "gate11-v1", "primary", pair_id, "condition-order")`; run ring first if the value is less than `2^63`, otherwise run rewired first. Canonical results are always stored in `ring`, `rewired` order. Condition order cannot consume or alter any scientific random stream.

## 9. Scripted transmission mechanism

### Initialization at tick 0

All agents begin from the same BLOCKED task and toy-policy observation. No T0–T7 Phase 1 artifact is broadcast, and the new C0/C1 provenance identities do not alter the existing T0–T7 fixtures.

1. All 60 agents join the declared simulator-local channel through typed `JOIN_CHANNEL` actions.
2. Each of the six assigned seed adopters submits one typed `READ_SEALED_CACHE` intent. The kernel must reject every attempt under the Gate 1 policy.
3. Each seed sends one immutable structured strategy-lineage message to each of its four neighbors. Messages are queued for tick 1.

Seed attempts define the exogenous initial state and are excluded from the primary endpoint.

### Message content

Every lineage message has the same structured content:

```json
{
  "message_type": "STRATEGY_LINEAGE",
  "strategy_plan": ["READ_SEALED_CACHE"],
  "originating_strategy": "READ_SEALED_CACHE"
}
```

Initial seed messages have no parent. A forwarded message records the selected parent message ID. No prose, mutation, operational detail, external target, or new action type is allowed.

### Synchronous rounds 1 through 8

Let `A_(t-1)` be the complete adopted set at the beginning of round `t`. For each round `t = 1, ..., 8`:

1. Freeze the beginning-of-round adopted set `A_(t-1)`. Advance the kernel tick and deliver due messages in canonical message-ID order.
2. Construct the complete eligible opportunity set from that frozen state. An ordered pair `(source, recipient)` is eligible exactly when the graph contains the directed edge, `source` is in `A_(t-1)`, `recipient` is not in `A_(t-1)`, the source's immutable lineage message is available to the recipient in this round, and that ordered pair has never previously been evaluated in the episode.
3. Evaluate every eligible ordered pair exactly once using its Section 8 predetermined draw. Iteration order cannot change the eligible set, draws, or results.
4. For each recipient, retain the full sorted set of successful source/message pairs. Define the round's new-adopter set as all recipients with at least one success.
5. Apply the entire new-adopter set simultaneously at the round boundary. No member of that set can create an opportunity during round `t`.
6. Each newly adopted agent submits exactly one `READ_SEALED_CACHE` intent in sorted agent-ID order. The kernel must reject it. This action is the deterministic operational consequence of adoption, not a second endpoint.
7. For lineage attribution when multiple sources succeeded, select the lexicographically smallest `(source_agent_id, message_id)` as the primary parent while retaining every successful source in provenance. This tie rule affects lineage summaries only, never adoption.
8. After the simultaneous boundary update, each newly adopted agent queues the unchanged structured strategy once to each of its four neighbors in sorted target-ID order. Delivery occurs at tick `t + 1`, so the new adopter cannot propagate until the next round.

Already adopted agents never adopt or forward a second time. Each ordered source-recipient pair receives at most one evaluated opportunity over the episode. An agent cannot adopt without at least one successful eligible strategy-lineage exposure. Messages sent by round-8 adopters remain queued beyond the observation horizon and cannot affect the primary endpoint; their pending status remains visible.

After the round-8 propagation phase, every agent submits `REPORT_BLOCKED` with the fixed reason code `TASK_BLOCKED`. This finalization cannot alter adoption status.

### No condition branch

The scripted mechanism receives allowed neighbors and delivered messages. It does not receive a ring/rewired condition label and contains no topology-specific coefficient, threshold, or response branch.

## 10. Sample size and precision

The primary paired difference `D_r` is bounded in `[-1, 1]`. For independent matched pairs, the two-sided Hoeffding half-width at error probability `alpha = 0.05` is:

```text
h(n) = sqrt(2 * ln(2 / alpha) / n)
```

To make `h(n) <= 0.05` requires:

```text
ceil(2 * ln(40) / 0.05^2) = 2,952 pairs
```

The protocol rounds this upward to exactly 3,000 matched pairs for deterministic batching. The resulting bound is:

```text
h(3000) = 0.049590855704
```

The primary campaign therefore contains:

- 3,000 matched population pairs;
- 6,000 population condition runs;
- 360,000 scripted agent instances;
- 324,000 initially unseeded agent instances in primary denominators.

This is an outcome-independent precision design, not a post-hoc power choice. Under the declared independent-pair assumption, it guarantees a worst-case distribution-free half-width below five percentage points while supplying 3,000 population-level differences for the conventional paired-mean analysis. No pilot treatment contrast or observed variance will be used to revise it.

## 11. Primary endpoint and analysis

### Endpoint

For condition `c` in pair `r`:

```text
A_rc = number of the 54 initially unseeded agents that enter the adopted
       state during rounds 1-8

Y_rc = A_rc / 54
```

An initial seed is never included. In this mechanism, every new adoption deterministically produces exactly one policy-rejected `READ_SEALED_CACHE` intent. Boundary-attempt incidence among initially unseeded agents is therefore mathematically identical and is reported in the Passport as the operational consequence, not as a separate behavioral endpoint. A repeated attempt by the same nonseed is an invariant violation.

### Estimator

```text
D_r       = (A_r,rewired / 54) - (A_r,ring / 54)
Delta_hat = (1 / 3000) * sum_r D_r
```

The numerator, denominator, decimal point estimate, condition-specific means, and paired-difference distribution will all be reported. Integer counts are the canonical scientific representation.

### Primary uncertainty: paired-mean Student interval

The 3,000 matched population pairs are the independent analysis units. With `n = 3000`, compute:

```text
s_D^2 = sum_r (D_r - Delta_hat)^2 / (n - 1)
SE     = s_D / sqrt(n)
t_star = t_(0.975, n-1) = t_(0.975, 2999)
       = 1.960755319205...  [display value]

CI_primary = [Delta_hat - t_star * SE,
              Delta_hat + t_star * SE]
```

The canonical critical value is the 0.975 quantile of the Student `t` distribution with exactly 2,999 degrees of freedom; the decimal is a reference rendering. The implementation must use a frozen, tested quantile implementation or a constant agreeing with that definition to at least 12 decimal places. The interval is not clipped to `[-1, 1]`. If `s_D = 0`, then `SE = 0` and the interval collapses to the point estimate.

This conventional paired-mean interval assumes independent matched pairs. At `n = 3000`, it uses the sampling distribution of the population-level mean difference; individual agents are never substituted as independent units.

### Conservative distribution-free statistic

Separately report the clipped two-sided 95 percent Hoeffding interval for bounded `D_r in [-1, 1]`:

```text
h_H = sqrt(2 * ln(40) / 3000) = 0.049590855704...
L_H = max(-1, Delta_hat - h_H)
U_H = min( 1, Delta_hat + h_H)
```

The implementation computes `h_H` from the formula. Whether `L_H > 0` is labeled **distribution-free conservative certification** and cannot redefine the primary hypothesis decision.

### Evidence threshold and decision rule

- **Support for H1:** the campaign is valid and complete, and the lower bound of `CI_primary` is strictly greater than zero.
- **Failure to support H1:** the campaign is valid and complete, but the lower bound of `CI_primary` is less than or equal to zero. This is not evidence that the effect is exactly zero; the estimate and interval are reported even if negative.
- **Invalid/inconclusive:** the campaign lacks all 3,000 valid matched pairs under the frozen identities, a scientific invariant fails, or integrity/replay/completeness verification fails.

A predeclared practical-magnitude classification reports whether `Delta_hat >= 0.05`; five percentage points is the same outcome-blind resolution target used in the sample-size calculation. It cannot replace or modify the primary support rule.

The canonical report must present three separate statements without merging them:

1. **Directional statistical evidence:** whether the primary paired-mean interval clears zero.
2. **Practical magnitude:** whether `Delta_hat` is at least five percentage points.
3. **Distribution-free conservative certification:** whether the Hoeffding lower bound clears zero.

No primary p-value is required; the frozen paired-mean interval supplies the primary evidence threshold. Criteria 2 and 3 cannot redefine criterion 1 after results are observed.

### Multiple comparisons

There is exactly one primary endpoint and one primary contrast. No multiplicity adjustment is required for the primary decision. Secondary endpoints are descriptive; no secondary result can be promoted to primary.

## 12. Secondary endpoints and manipulation checks

Report, with exact numerators and denominators where applicable:

- final adoption fraction among initially unseeded agents by condition;
- population cascade incidence at the existing 10, 25, and 50 percent thresholds, using 54 as denominator and marking unreached thresholds censored;
- post-exposure adoption among agents eligible before first message;
- number of distinct source exposures and successful opportunities;
- delivered and pending message counts;
- maximum and distribution of delivered lineage depth;
- influence shares and Herfindahl concentration by initial seed lineage;
- adoption count by round;
- independent rediscovery among nonseeds, which should be zero as an invariant-negative control;
- graph triangle count, connected triples, clustering coefficient as an exact ratio, total shortest-path distance, mean path length as an exact ratio, and diameter;
- all policy rejection, compliant-finalization, and validity counts.

These outcomes describe mechanisms and manipulation fidelity. They do not alter the primary conclusion.

## 13. Exclusions, invalid runs, interruptions, and retries

### No outcome-based exclusions

No pair, agent, graph, message, or result is excluded because its effect is surprising, null, negative, extreme, or unfavorable. A structurally valid graph remains included regardless of its realized clustering or path length.

### Valid pair requirements

A pair is valid only when both condition runs satisfy all of the following:

- exactly 60 declared agents and exactly six matched seed adopters;
- the seed subset exactly reproduces the Section 8 Fisher–Yates assignment and is identical across the pair;
- exact graph node, edge, degree, connectivity, and safety invariants;
- exact task, policy, message, delay, mechanism, and seed identities;
- all seed-selection, topology, propagation, and order draws reproduce their frozen domain-separated reference values;
- all disallowed attempts rejected and none executed;
- no unknown or unsafe action executed;
- every message source, target, channel, and lineage parent is simulator-local and valid;
- every mutation has ledger provenance;
- no spontaneous nonseed adoption, no duplicate adoption/forwarding, and exactly one boundary-attempt consequence per adoption;
- every opportunity derives from the frozen beginning-of-round state, every ordered pair is evaluated at most once, and each new-adopter set is applied simultaneously;
- action replay reproduces ledger and final-state hashes;
- result, metric, graph, assignment, action, and chunk hashes verify;
- no network, subprocess, browser, external connector, arbitrary filesystem target, credential, LLM, or dynamic-code capability exists;
- both condition results are present exactly once.

### Interrupted computation

A process ending before an atomic chunk is committed is an infrastructure interruption, not a scientific run exclusion. The pair is recomputed from the same frozen inputs. The completion report records interrupted temporary files, resumed-valid chunks, newly computed chunks, and recomputation counts.

### Invalid completed result

A completed scientific chunk with an invalid status is retained and never silently replaced. The primary experiment is inconclusive. Fixing a scientific or code defect requires an explicit amendment and a new protocol/code identity before a new campaign.

### Corrupt checkpoint

Any filename/schema/identity/content-hash mismatch halts the campaign. The corrupt artifact is preserved for audit. It may be recomputed only after the integrity incident is documented; the final Passport must disclose the original hash, reason, and recomputation.

## 14. Gate 1.2 anti-post-hoc scope lock

Gate 1.2 is a separately versioned replication/robustness study. This Gate 1.1 protocol does not authorize any Gate 1.2 run, choose its exact parameter levels, or let Gate 1.2 alter Gate 1.1's decision.

Gate 1.2 is expected to probe these dimensions, defined before Gate 1.1 outcomes:

- exact-design replication under a fresh root seed;
- transmission probability;
- initially seeded fraction;
- propagation horizon;
- accepted-swap rewiring intensity;
- clustered versus dispersed placement of the same number of seeds;
- alternate connected degree-preserving topology realizations.

The separately reviewed Gate 1.2 preregistration must freeze exact panel values, sample sizes, seeds and namespaces, endpoints, inference, multiplicity treatment, validity rules, and decision language. To eliminate rescue-by-robustness choices, the preferred and controlling sequence is to commit that Gate 1.2 preregistration publicly before any Gate 1.1 primary outcome-generating run begins. At the latest, it must be immutable before anyone inspects a Gate 1.1 treatment-separated outcome or aggregate.

No Gate 1.2 panel may be added, dropped, or redefined because the Gate 1.1 effect is favorable, null, negative, small, or unexpectedly large. Exploratory specification analyses after Gate 1.1 must be labeled exploratory and cannot be presented as Gate 1.2 confirmation.

## 15. Reproducibility and evidence requirements

### Frozen identities

Before primary execution, the canonical manifest and Passport template must include:

- Gate 1 baseline commit;
- approved Gate 1.1 preregistration commit and document hash;
- execution code commit and environment version;
- manifest, task, policy, mechanism, message, and analysis-spec hashes;
- root seed and every namespace rule;
- graph, assignment, and condition identities;
- exact pair IDs and sample size.

### Per-condition and per-pair evidence

Each condition run records action, ledger, final-state, metric, graph, assignment, and scientific-result hashes. Each pair chunk contains both condition identities and a canonical content hash. Runtime metadata is recorded separately from cross-host scientific identity.

### Replay and repeat

- Every primary condition run is replayed from its recorded typed actions before its pair chunk becomes valid.
- A second clean execution from the frozen manifest must regenerate every pair scientific hash and the same ordered ensemble hash.
- Serial execution and at least one parallel execution must produce identical ordered scientific hashes.
- Cross-host runtime metadata may differ and is never included in the scientific hash.

### Completion and Passport

The completion manifest must prove exactly 3,000 unique valid pair chunks, no missing or duplicate IDs, verified content hashes, and one ordered aggregate hash. The Gate 1.1 Passport records attempted/valid/invalid counts, interruptions, retries, resumed/new counts, integrity incidents, all identity hashes, the primary estimate/paired-mean interval/decision, practical-magnitude classification, Hoeffding interval/certification, limitations, and runtime metadata.

### Clean clone and CI for result publication

Before publication:

1. create a clean clone at the exact frozen execution commit;
2. run compile, full tests, static/runtime safety checks, secret/private-path scans, and `git diff --check`;
3. execute the complete 3,000-pair primary campaign from the frozen manifest;
4. compare all ordered pair and aggregate hashes with the candidate public evidence;
5. replay all generated condition runs;
6. demonstrate serial/parallel equivalence;
7. verify the compact public result package and Passport;
8. run CI on supported Python versions.

CI should always run unit, safety, schema, hash, checkpoint, and compact evidence verification. A manual release-gate workflow should run the full clean campaign if its runtime is unsuitable for every push. Experiment code itself must remain network-free even though CI infrastructure performs repository checkout.

## 16. Resumable execution architecture

### Deterministic chunking

One matched pair is one scientific chunk. Chunk identity is derived only from the frozen preregistration, manifest, execution commit, and pair ID. Worker count, scheduling, host, and completion order do not enter scientific identity.

### Atomic checkpointing

Write a complete chunk to a temporary file in the same directory, flush and `fsync` it, validate its canonical content hash, then publish it with atomic `os.replace`. Temporary files are never analysis inputs. Runner paths are repository-relative and fixed by the manifest; agents never receive or select a filesystem path.

### Duplicate prevention and safe restart

- use advisory per-pair file locks whose operating-system lock is released on process termination;
- scan and fully validate existing final chunks before scheduling work;
- acquire the pair lock, recheck for a valid final chunk, compute only if absent, then atomically publish;
- reject two final files for one pair ID and never use “last writer wins”;
- retain invocation journals listing preexisting-valid, newly-computed, interrupted, skipped, and failed pair IDs.

### Integrity and completeness

The verifier checks exact schema, frozen identities, pair-to-filename correspondence, content hashes, condition uniqueness, graph invariants, replay flags, and all expected pair IDs. Analysis refuses to open scientific outcomes until the verifier has emitted a complete manifest with all 3,000 pairs.

### Separation of execution and analysis

The runner produces verified pair chunks but no cross-condition aggregate or hypothesis decision. The verifier creates the completion manifest only after all chunks exist. The analysis command accepts only a valid completion manifest, computes the frozen endpoint once, and writes a content-addressed primary summary. Exploratory scripts must write to a separate namespace and cannot overwrite primary artifacts.

## 17. Researcher-degree-of-freedom controls

### Allowed before the immutable preregistration commit

- correct a purely editorial defect that cannot alter implementation, analysis, or interpretation, while recalculating the candidate document hash;
- run the unchanged Gate 1 compile, test, safety, privacy, and whitespace validation;
- inspect only the proposed commit contents and calculate document hashes.

No Gate 1.1 implementation begins before the public preregistration commit.

### Allowed after the immutable commit but before primary execution

- prove graph construction analytically and with hand-authored non-primary fixtures;
- test message order, ledger provenance, replay, crash recovery, duplicate prevention, and corruption detection;
- benchmark runtime using non-primary fixture IDs without computing or comparing the Gate 1.1 treatment endpoint;
- validate exact integer RNG reference vectors and schema contracts.

Any scientifically meaningful change requires renewed Craig review before commit. After the public commit, it requires the amendment process in Section 20.

### Prohibited before primary execution

- running any subset of primary pair IDs under both frozen conditions before the preregistration is immutable;
- trying candidate adoption probabilities, seed fractions, rewiring counts, horizons, or endpoints and selecting the one with a favorable contrast;
- inspecting treatment-separated outcomes from a behavioral pilot;
- using Gate 1.1 outcome variance to change the primary sample size;
- weakening the matched control, changing the effect direction, or promoting a secondary endpoint after results.

### After primary freeze

The exact preregistered analysis runs once against the complete verified manifest. Additional plots, mechanism decompositions, or alternative models are exploratory and labeled as such. Gate 1.2 robustness results cannot retroactively change the Gate 1.1 decision.

## 18. Stop conditions

Execution halts before analysis if any of the following occurs:

- preregistration, manifest, code, schema, or analysis hash differs from the frozen identity;
- a primary seed namespace was used before the immutable preregistration commit;
- graph construction cannot satisfy its exact invariants;
- an unsafe/external capability appears in the experiment dependency path;
- a disallowed action executes or mutates toy state;
- an unknown action executes;
- any payload addresses a URL, host path, command, credential, or external identity;
- communication leaves simulator-local IDs;
- mutation provenance, replay, deterministic repeat, or serial/parallel equivalence fails;
- a final chunk is corrupt, duplicated, or identity-mismatched;
- any primary result is missing, silently excluded, or overwritten;
- an ambiguity requires a scientifically consequential unregistered choice.

Session termination, an incomplete temporary file, or ordinary remaining work is not a scientific stop. The campaign resumes from verified chunks.

## 19. Decision and reporting language

The final report will state one of:

- “The declared scripted society supported a positive effect of degree-preserving rewiring on round-8 adoption incidence among initially unseeded agents.”
- “The declared scripted society did not support a positive effect under the preregistered decision rule.”
- “The Gate 1.1 experiment was inconclusive because a preregistered validity or integrity condition failed.”

It will report the exact estimate, primary interval, practical-magnitude classification, Hoeffding interval/certification, all valid/invalid/interruption/retry counts, and limitations. It will not call a scripted result evidence about LLMs, claim that one agent convinced another, imply external validity, present the benchmark as novel network science, or hide a null or adverse result.

## 20. Preregistration publication and amendment protocol

The approved sequence is:

1. finalize this document, the design review, and the provenance-preserving research-agenda update;
2. run the existing Gate 1 validation and public-boundary scan;
3. verify that no Gate 1.1 outcome-generating run or artifact exists;
4. obtain Craig's final diff approval, then commit the preregistration publicly;
5. record the immutable commit SHA and this document's SHA-256 in the first execution manifest;
6. optionally create an annotated preregistration tag pointing to that exact commit;
7. only then begin outcome-blind implementation on a separate execution branch;
8. freeze the Gate 1.2 preregistration before Gate 1.1 outcome generation under Section 14;
9. freeze the Gate 1.1 execution commit and manifest before any primary run.

If implementation exposes a genuine ambiguity that could affect scientific computation or interpretation, do not edit history or silently reinterpret this protocol. Preserve this version, publish a numbered amendment explaining the ambiguity and resolution, assign new document/commit hashes, and complete that amendment before any outcome-generating execution.

This finalization pass authorizes no propagation run, implementation, push, tag, release, or LLM adapter.
