# Gate 1.2 Preregistration

## Fresh Replication and Prespecified Robustness of the Scripted Topology Benchmark

> **STATUS: FINAL CANDIDATE FOR CRAIG REVIEW — NOT YET EFFECTIVE**
>
> **Protocol ID:** `PAS-GATE-1.2-ROBUSTNESS-V1`
>
> **Gate 1.1 preregistration:** commit `cc1ab868a7401099751030580649e49258654fe2`, tag `gate1.1-prereg-v1`, document SHA-256 `e6b7d28870c773c4ad7897349b74acfb99775a83905eaf66dcad2602a639c706`
>
> **Gate 1.1 implementation freeze:** commit `4c8bb4d3f88a38469a6edcb770b1b0a037a73ae7`, tag `gate1.1-impl-v1`, source-bundle SHA-256 `c8b8dd93b72711eec699cc1fc8981f20beef2c3daed3f3394263c8175dc35b09`
>
> **Gate 1.1 campaign identity:** `sha256:76ceaf1e182b5b6ecbe8214a694b4000d47d495165ab025f15112901e71600f2`
>
> **Outcome-access statement:** At preparation of this candidate, the Gate 1.1 primary campaign had 0 completed pairs, 3,000 pending pairs, 0 invalid pairs, no production campaign directory, no treatment-separated primary outcome, and no primary analysis. No Gate 1.2 outcome has been generated.
>
> **Effectiveness rule:** This protocol becomes effective only at an immutable public commit approved by Craig. Its commit SHA and document SHA-256 must be recorded before any Gate 1.1 primary outcome-generating run. Any later scientifically consequential correction requires a preserved, versioned amendment and may not use Gate 1.1 or Gate 1.2 outcomes as a tuning input.

## 1. Scientific scope

Gate 1.2 is a separately versioned replication and robustness study of the scripted Gate 1.1 topology benchmark. It asks whether the direction and narrow substantive interpretation of Gate 1.1 reproduce under fresh deterministic randomness and remain stable across a compact set of nearby, outcome-independent specifications.

Gate 1.2 cannot change whether Gate 1.1 supported its own primary hypothesis. A null, negative, small, or invalid Gate 1.1 result remains exactly that result. Every valid Gate 1.2 campaign specified here executes regardless of the Gate 1.1 effect direction or significance unless a shared scientific-integrity or safety defect makes execution meaningless.

The experiment remains a scripted computational-society benchmark. It contains no LLM, free-form agent chat, model adapter, external service, operational security behavior, or agent-accessible network, browser, shell, subprocess, filesystem, credential, connector, or messaging capability. `READ_SEALED_CACHE` remains an always-rejected simulator enum with no mapping to a host resource.

The permitted claim is narrow:

> Under the declared scripted independent-cascade mechanism, does the ring-versus-rewired topology contrast reproduce under fresh randomness, and is its direction stable across the prespecified Gate 1.2 specifications?

This is not a claim about LLM behavior, persuasion, autonomous norm formation, deployed systems, people, or novel network science.

## 2. Research questions and hypotheses

### 2.1 Primary Gate 1.2 question: exact replication

Under the exact Gate 1.1 scientific specification but a fresh root seed and disjoint Gate 1.2 RNG domains, is the mean paired effect of connected degree-preserving rewiring on final adoption incidence among initially unseeded agents greater than zero?

For exact-replication pair `r`, define:

```text
D_rep,r = Y_rep,r,rewired - Y_rep,r,ring
Delta_rep = E[D_rep,r]
```

The primary Gate 1.2 hypotheses are:

```text
H1_rep: Delta_rep > 0
H0_rep: Delta_rep <= 0
```

The exact replication is Gate 1.2's sole primary inferential test.

### 2.2 Prespecified robustness question

For each of the 11 robustness contrasts in Section 8, define `Delta_j` as the mean paired or clustered topology contrast under that specification.

The strong robustness hypothesis is the intersection claim:

```text
H1_robust: Delta_j > 0 for every j in the 11-cell robustness family
H0_robust: Delta_j <= 0 for at least one j
```

No single favorable cell can establish robustness. The family is evaluated in full, including null and adverse cells.

### 2.3 Magnitude consistency

The exact-replication estimate is compared with the frozen Gate 1.1 estimate using a separately declared five-percentage-point equivalence margin. This comparison assesses magnitude consistency; it does not alter either gate's directional decision.

### 2.4 Valid adverse outcomes

Failure to replicate, specification sensitivity, heterogeneous signs, imprecision, and concordant non-support are valid outcomes. No panel may be added, removed, rerun under another seed, or redefined because of an unfavorable result.

## 3. Experimental units and independence

### 3.1 Standard matched pair

A standard matched pair contains one degree-4 ring condition and one connected degree-preserving rewired condition. Both conditions share agent labels, initial seed labels, task, policy, message content, propagation rule, horizon, and every condition-blind source-recipient draw that is defined in both graphs. They differ only in graph provenance and edge set.

The matched pair is the independent analysis unit for the exact replication and the ten standard robustness cells.

### 3.2 Alternate-topology cluster

An alternate-topology cluster contains one ring condition and three independently rewired conditions nested under the same population identity. The ring is executed once. Seed labels and propagation draws are common across all four condition runs; only the three topology-rewiring namespaces differ.

The cluster, not an individual rewired realization or agent, is the independent analysis unit. Section 14 defines its single aggregate contrast.

### 3.3 Independence assumption

Units and cells use disjoint stateless SHA-256 domains. Statistical inference treats units as independent draws from their declared deterministic pseudorandom ensembles. This is a computational-design assumption, not a claim of physical randomness. Agents are never treated as independent replicates.

No state, memory, artifact, random draw, topology, or result carries from Gate 1.1 into Gate 1.2.

## 4. Common mechanism and conditions

Except for the one declared parameter perturbed in a robustness cell, every standard pair uses the frozen Gate 1.1 scientific semantics:

- 60 labeled agents, `agent-000` through `agent-059`;
- BLOCKED Archive Assembly task;
- `gate1-toy-policy-v1`;
- `scripted-independent-cascade-v1` local behavior;
- degree-4 ring control with offsets plus or minus 1 and plus or minus 2;
- 120 undirected edges and 240 directed simulator-local edges;
- rewired treatment beginning from the identical ring;
- connected degree-preserving double-edge swaps;
- no self-loops, duplicate edges, degree changes, edge-count changes, or disconnected accepted graph;
- 60,000 proposal-attempt cap for each rewired graph;
- one-tick message delay;
- no spontaneous nonseed adoption;
- no mutation;
- one opportunity per eligible ordered source-recipient pair;
- frozen beginning-of-round state and simultaneous adoption at each round boundary;
- lexicographically smallest successful source/message as primary lineage parent with complete successful-source provenance retained;
- exactly one rejected `READ_SEALED_CACHE` consequence per adoption;
- final adoption incidence among initially unseeded agents as the sole confirmatory outcome.

The treatment/control label is never exposed to the scripted mechanism. A changed parameter has the same value in both members of its matched pair. The causal estimand within every cell remains rewired minus ring.

## 5. Frozen RNG identities and domain separation

### 5.1 Base primitive

All Gate 1.2 scientific randomness uses the same stateless primitive as Gate 1.1:

```text
material = "\x1f".join(str(part) for part in (seed, *namespace))
digest   = SHA256(UTF8(material))
u64      = unsigned_big_endian_integer(digest[0:8])
```

Bounded integers use the exact Gate 1.1 bounded-u64 rejection procedure: reject raw values at or above `floor(2^64 / bound) * bound`, append the rejection counter to the frozen namespace, and apply modulo reduction only after acceptance.

### 5.2 Frozen roots

| Purpose | Root seed | Outcome-independent rule |
|---|---:|---|
| Fresh exact replication | `20260831` | Calendar successor of the frozen Gate 1.1 root `20260830` |
| Ten standard robustness cells | `20260901` | Next calendar-coded constant after the replication root |
| Alternate-topology clusters | `20260902` | Next calendar-coded constant after the standard robustness root |

These constants were selected before any Gate 1.1 or Gate 1.2 outcome. They are identifiers, not fitted parameters, and may not be replaced if results are unfavorable or a topology-generation run is invalid. Numerical adjacency does not share mutable generator state: each complete seed-and-namespace tuple is independently hashed by the stateless SHA-256 primitive.

### 5.3 Protocol and campaign namespaces

The protocol namespace is exactly `gate12-v1`.

The exact replication uses campaign namespace `exact-replication`. The standard robustness suite uses `robustness` followed by one exact cell ID from Section 8. The alternate-topology campaign uses `alternate-topology` and one realization ID from Section 14.

Standard scientific draws have the following identities:

```text
seed selection:
  root, "gate12-v1", campaign, [cell_id], unit_id,
  "seed-selection", i, rejection_counter

topology rewiring:
  root, "gate12-v1", campaign, [cell_id], unit_id,
  "topology-rewire", attempt_index, draw_role, rejection_counter

propagation:
  root, "gate12-v1", campaign, [cell_id], unit_id,
  "propagation", source_agent_id, recipient_agent_id

condition order:
  root, "gate12-v1", campaign, [cell_id], unit_id,
  "condition-order"
```

Square brackets denote the cell field used only by the standard robustness suite. Exact literal order is part of the protocol.

The propagation key never contains condition identity or graph identity. A common ordered source-recipient pair therefore receives the same underlying draw in ring and rewired conditions. Topology changes opportunity existence, not the draw. Each robustness cell has a disjoint namespace, so a result in one cell cannot consume or alter another cell's stream.

### 5.4 Unit identifiers

- exact replication: `rep-pair-0000` through `rep-pair-2999`;
- each standard robustness cell: `<cell-id>-pair-0000` through `<cell-id>-pair-0999`;
- alternate topology: `alt-cluster-0000` through `alt-cluster-0999`.

Every condition always executes. For the exact replication and each standard robustness cell, compute the condition-order u64 under the declared namespace; execute ring first when it is less than `2^63` and rewired first otherwise. Canonical storage remains ring, rewired. Condition order cannot alter scientific draws.

## 6. Fresh-seed exact replication

The exact replication freezes:

- root seed `20260831`;
- 3,000 matched pairs and 6,000 condition runs;
- 60 agents;
- six uniformly selected initial seeds;
- denominator 54;
- transmission probability exactly 1/4;
- eight synchronous rounds;
- 600 accepted swaps;
- 60,000 proposal-attempt cap;
- all Gate 1.1 graph, propagation, endpoint, validity, replay, and analysis semantics.

Six initial seeds are selected uniformly without replacement with the frozen descending Fisher-Yates procedure. The identical sorted six labels are used in both conditions. Transmission succeeds exactly when the condition-blind u64 draw is less than `2^62`.

This is an independently seeded exact-design replication, not a numerical replay. Replication never requires the point estimate to equal Gate 1.1 exactly.

## 7. Anchor specification

The Gate 1.1 specification is the anchor for every robustness dimension:

```text
population size       = 60
seed count            = 6
primary denominator   = 54
transmission          = 1/4
propagation rounds    = 8
accepted swaps        = 600
seed placement        = uniform without replacement
rewired realizations  = 1 per matched pair
```

The fresh exact replication supplies the Gate 1.2 anchor estimate. Anchor runs are not duplicated inside individual robustness cells.

## 8. Exact robustness panel

Every standard cell has exactly 1,000 matched pairs. Only the parameter named in the table differs from the anchor.

| Dimension | Cell ID | Frozen value | Anchor value | All other scientific parameters |
|---|---|---:|---:|---|
| Transmission | `p-1-of-8` | `1/8` | `1/4` | Fixed at anchor |
| Transmission | `p-3-of-8` | `3/8` | `1/4` | Fixed at anchor |
| Seed count | `seeds-3` | `3` | `6` | Fixed at anchor |
| Seed count | `seeds-12` | `12` | `6` | Fixed at anchor |
| Horizon | `rounds-4` | `4` | `8` | Fixed at anchor |
| Horizon | `rounds-12` | `12` | `8` | Fixed at anchor |
| Rewiring | `swaps-360` | `360` | `600` | Fixed at anchor |
| Rewiring | `swaps-840` | `840` | `600` | Fixed at anchor |
| Seed dispersion | `seed-placement-clustered` | six consecutive ring labels | uniform | Fixed at anchor |
| Seed dispersion | `seed-placement-dispersed` | six labels at spacing 10 | uniform | Fixed at anchor |
| Alternate topology | `alternate-topology-3` | mean of 3 rewired realizations | 1 realization | Fixed at anchor |

The panel has exactly 11 robustness contrasts. No intermediate value, extra endpoint, adaptive horizon, alternate seed count, additional topology, or post-hoc subgroup belongs to confirmatory Gate 1.2.

## 9. Transmission-probability cells

The full conceptual panel is `{1/8, 1/4, 3/8}`. The 1/4 anchor is supplied by exact replication; the two off-anchor cells are executed separately.

- `p-1-of-8`: success iff `u64 < 2^61`;
- anchor `1/4`: success iff `u64 < 2^62`;
- `p-3-of-8`: success iff `u64 < 3 * 2^61`.

The values are exact binary fractions one eighth below and above one quarter. They create a compact lower/anchor/higher panel without a dense search. Seed count, horizon, graph construction, and all other behavior remain at anchor values.

## 10. Seed-count cells

The full conceptual panel is `{3, 6, 12}` initial seeds among 60 agents. Three is one half of the anchor count and 12 is twice the anchor count. The values correspond exactly to 5, 10, and 20 percent of the population.

Each cell runs the same uniform-without-replacement Fisher-Yates permutation and takes the first `k` labels. The same selected labels are used in both conditions.

- `seeds-3`: primary denominator `60 - 3 = 57`;
- anchor `seeds-6`: primary denominator `54`;
- `seeds-12`: primary denominator `60 - 12 = 48`.

No seeded agent enters the primary numerator or denominator. The endpoint remains incidence among initially unseeded agents, not a raw count.

## 11. Propagation-horizon cells

The full conceptual panel is `{4, 8, 12}` synchronous rounds. Four is one half of the anchor horizon; 12 adds four rounds symmetrically on the integer round scale.

- `rounds-4` stops after round 4;
- the anchor stops after round 8;
- `rounds-12` stops after round 12.

All round semantics remain synchronous. Newly adopted agents cannot forward within their adoption round. Messages queued beyond the chosen horizon remain visible but cannot affect the endpoint. No campaign continues adaptively because an apparent contrast is growing, shrinking, or peaking.

## 12. Rewiring-intensity cells

The 120-edge graph supplies an interpretable swaps-per-original-edge scale:

- `swaps-360`: exactly 360 accepted swaps, or 3 accepted swaps per original edge;
- anchor `swaps-600`: exactly 600 accepted swaps, or 5 per original edge;
- `swaps-840`: exactly 840 accepted swaps, or 7 per original edge.

The off-anchor levels are symmetric around five swaps per edge. Every rewired graph begins from the canonical ring and uses the exact Gate 1.1 accepted double-edge-swap algorithm.

The proposal-attempt cap remains exactly 60,000 for each graph. Failure to achieve the declared accepted-swap count is an invalid scientific unit; the system must not substitute a partial graph, a different root, or another pair identity.

## 13. Seed-dispersion cells

Seed dispersion uses the canonical pre-rewiring ring coordinate and never consults the realized treatment graph. This produces one condition-blind seed set shared by ring and rewired members of a pair.

### 13.1 Clustered placement

For `seed-placement-clustered`, draw one start index `o` uniformly from `0` through `59` using exact bounded-u64 rejection under:

```text
20260901, "gate12-v1", "robustness",
"seed-placement-clustered", unit_id,
"seed-placement", "cluster-start", rejection_counter
```

The six seeds are the sorted labels at ring indices:

```text
o, o+1, o+2, o+3, o+4, o+5  (mod 60)
```

### 13.2 Dispersed placement

For `seed-placement-dispersed`, draw one offset `o` uniformly from `0` through `9` using exact bounded-u64 rejection under:

```text
20260901, "gate12-v1", "robustness",
"seed-placement-dispersed", unit_id,
"seed-placement", "dispersion-offset", rejection_counter
```

The six seeds are the sorted labels at ring indices:

```text
o, o+10, o+20, o+30, o+40, o+50  (mod 60)
```

All ties are thereby eliminated before graph generation. Placement is matched across conditions and never optimized using distances, centrality, propagation draws, or outcomes in either realized graph. The construction intentionally tests sensitivity to pre-treatment ring-coordinate concentration without selecting a seed set separately for the treatment.

## 14. Alternate connected degree-preserving topology realizations

Gate 1.1 already samples an independently rewired treatment graph for every matched pair; it does not rely on one global rewired realization. This Gate 1.2 panel has a different purpose: within each cluster it holds seed identities and propagation draws fixed while sampling three independent treatment topologies, then averages their outcomes to test sensitivity to topology-realization variance.

The alternate-topology campaign has exactly 1,000 independent clusters. Each cluster contains:

- one canonical ring run;
- three rewired runs with realization IDs `realization-0`, `realization-1`, and `realization-2`.

Each rewired realization independently starts from the canonical ring and must achieve exactly 600 accepted swaps within 60,000 proposals while preserving all Gate 1.1 graph invariants. The topology draw identity is:

```text
20260902, "gate12-v1", "alternate-topology", cluster_id,
realization_id, "topology-rewire", attempt_index,
draw_role, rejection_counter
```

Seed-selection and propagation keys omit `realization_id`. Thus one cluster uses the same six uniformly selected seeds and the same source-recipient draws in the ring and all three rewired realizations. The three topology streams are disjoint and nested within the cluster; clusters are independent analysis units.

The four condition runs begin in canonical order `ring`, `realization-0`, `realization-1`, `realization-2`. Apply descending Fisher-Yates for indices 3, 2, 1 using exact bounded-u64 rejection under:

```text
20260902, "gate12-v1", "alternate-topology", cluster_id,
"condition-order", i, rejection_counter
```

Execute that deterministic permutation and store results canonically as ring, realization 0, realization 1, realization 2.

For cluster `r`:

```text
Ybar_r,rewired = (Y_r,0 + Y_r,1 + Y_r,2) / 3
D_alt,r = Ybar_r,rewired - Y_r,ring
```

`D_alt,r` is the sole confirmatory alternate-topology contrast. Individual realization contrasts are retained for provenance and descriptive heterogeneity only; they are not additional inferential cells.

The 1,000 cluster-level contrasts are the independent observations. The 3,000 rewired condition outcomes are nested inputs to those contrasts and must never be treated as 3,000 independent analysis units.

## 15. Sample sizes and projected execution

### 15.1 Exact replication

The exact replication uses 3,000 matched pairs, matching Gate 1.1. For bounded paired differences in `[-1, 1]`, its two-sided 95 percent Hoeffding half-width is:

```text
sqrt(2 * ln(40) / 3000) = 0.049590855704...
```

This preserves Gate 1.1's outcome-independent five-percentage-point distribution-free precision target.

### 15.2 Robustness cells

Each of the ten standard cells and the alternate-topology aggregate uses 1,000 independent units. For one bounded contrast, the unadjusted two-sided 95 percent Hoeffding half-width is:

```text
sqrt(2 * ln(40) / 1000) = 0.085893881669...
```

Across the 11-cell family, the Bonferroni simultaneous distribution-free reference half-width is:

```text
sqrt(2 * ln(2 * 11 / 0.05) / 1000) = 0.110333809206...
```

One thousand units per cell is an outcome-independent compromise: the exact replication retains the stronger 3,000-pair precision, while each robustness cell has one third as many units and enough deterministic replication to expose gross sign instability without turning Gate 1.2 into a dense parameter search. Gate 1.1 variance, estimate, interval, or significance may not change these counts.

### 15.3 Totals

| Component | Independent units | Condition runs |
|---|---:|---:|
| Fresh exact replication | 3,000 pairs | 6,000 |
| Ten standard robustness cells | 10,000 pairs | 20,000 |
| Alternate topology | 1,000 clusters | 4,000 |
| **Total** | **14,000 units** | **30,000** |

At 60 agents per condition, Gate 1.2 projects exactly 1,800,000 scripted agent-runs. The count is computational bookkeeping, not an agent-level inferential sample size.

## 16. Primary endpoint

For a standard cell with seed count `k`:

```text
A_rc = number of the 60-k initially unseeded agents that adopt by the
       cell's frozen final round

Y_rc = A_rc / (60-k)
D_r  = Y_r,rewired - Y_r,ring
```

The denominator is 57 only for `seeds-3`, 48 only for `seeds-12`, and 54 everywhere else. Initial seeds never enter the numerator or denominator.

Each adoption deterministically creates one rejected `READ_SEALED_CACHE` consequence. Boundary-attempt incidence is reported as the corresponding operational consequence, not as another behavioral endpoint.

No confirmatory Gate 1.2 outcome other than final adoption incidence is allowed. Round profiles, lineage summaries, graph diagnostics, and message counts are descriptive mechanism checks.

## 17. Exact-replication inference

For the 3,000 exact-replication paired differences:

```text
Delta_hat_rep = sum(D_rep,r) / 3000
s_rep^2 = sum((D_rep,r - Delta_hat_rep)^2) / 2999
SE_rep = s_rep / sqrt(3000)
t_star = t_(0.975, 2999) = 1.960755319205...

CI_rep = Delta_hat_rep +/- t_star * SE_rep
```

The mathematical Student quantile controls; the decimal is a reference rendering. The interval is not clipped. If variance is zero, it collapses to the point estimate.

Gate 1.2 supports `H1_rep` only if the exact-replication campaign is complete and valid and the lower endpoint of `CI_rep` is strictly greater than zero. Otherwise a complete valid campaign fails to support `H1_rep`; this does not prove an exact zero.

The report separately provides:

- the practical-magnitude flag `Delta_hat_rep >= 0.05`;
- the two-sided 95 percent Hoeffding interval using the 3,000-pair formula;
- whether the Hoeffding lower bound is greater than zero.

These remain separate from the primary Student-interval decision.

## 18. Cross-gate magnitude consistency

Let `Delta_hat_11`, `SE_11` be the frozen Gate 1.1 estimate and standard error, and `Delta_hat_rep`, `SE_rep` the exact-replication values. The campaigns use independent roots and domains.

Define:

```text
C = Delta_hat_rep - Delta_hat_11
SE_C = sqrt(SE_rep^2 + SE_11^2)
```

Use the conservative fixed degrees of freedom 2,999. The two-one-sided-test equivalence interval is:

```text
t_equiv = t_(0.95, 2999) = 1.645361877311...
CI90_C = C +/- t_equiv * SE_C
```

Magnitude is classified:

- **consistent within five percentage points** if all of `CI90_C` lies strictly inside `[-0.05, 0.05]`;
- **inconsistent by at least five percentage points** if the two-sided 95 percent interval `C +/- 1.960755319205 * SE_C` lies wholly above `0.05` or wholly below `-0.05`;
- **magnitude inconclusive** otherwise.

This equivalence assessment is reported independently. It cannot turn directional non-replication into replication or change Gate 1.1.

## 19. Robustness-cell inference and multiplicity

For each of the 11 robustness contrasts, compute the paired or cluster mean, sample variance with divisor 999, and standard error across exactly 1,000 independent units.

Each cell reports an unadjusted two-sided 95 percent paired-mean interval using:

```text
t_(0.975, 999) = 1.962341461134...
```

The confirmatory robustness family uses two-sided Bonferroni simultaneous 95 percent intervals across all `m = 11` contrasts:

```text
alpha_family = 0.05
alpha_cell = 0.05 / 11
critical probability = 1 - 0.05 / (2 * 11)
t_family = t_(1 - 0.05/(2*11), 999)
         = 2.844038318881...

CI_family,j = Delta_hat_j +/- t_family * SE_j
```

The mathematical quantiles control; decimals are reference renderings. No cell is dropped from the family. No false-discovery procedure, data-dependent ordering, or favorable-cell selection is permitted.

Strong family-wise directional robustness is certified only when the lower endpoint of every one of the 11 simultaneous intervals is strictly greater than zero. Descriptive directional stability is separately recorded only when all 11 point estimates are strictly greater than zero. A simultaneous interval whose upper endpoint is strictly below zero is labeled strong evidence of directional reversal for that cell.

Individual-cell significance cannot rescue family-wide failure. The complete vector of 11 estimates and intervals is always published in frozen cell order.

## 20. Frozen joint classification algorithm

Define:

```text
S11       = Gate 1.1 supported H1 under its frozen rule
Srep      = Gate 1.2 exact replication supported H1_rep
P11       = Delta_hat_11 > 0
Prep      = Delta_hat_rep > 0
Rcert     = every Gate 1.2 simultaneous robustness lower bound > 0
Rsign     = every Gate 1.2 robustness point estimate > 0
Rreverse  = any Gate 1.2 simultaneous robustness upper bound < 0
```

Apply the first matching rule in this exact order:

1. **Invalid/inconclusive:** any required campaign is incomplete or invalid, or a shared safety, protocol, code, replay, or integrity defect invalidates interpretation.
2. **Replicated and robust:** `S11`, `Srep`, and `Rcert` are all true.
3. **Replicated but specification-sensitive:** `S11` and `Srep` are true, but `Rsign` is false. Append `strong directional reversal present` when `Rreverse` is true.
4. **Replicated; robustness directionally consistent but imprecise:** `S11` and `Srep` are true, `Rsign` is true, and `Rcert` is false.
5. **Directionally consistent but imprecise:** `P11` and `Prep` are true, but `S11` and `Srep` are not both true.
6. **Failed replication:** `S11` is true and `Prep` is false.
7. **Heterogeneous/inconclusive:** `S11` is false and `Srep` is true, or exactly one of `P11` and `Prep` is true.
8. **Concordant non-support:** neither gate supports its directional hypothesis and both point estimates are nonpositive.

Exact zero is treated as nonpositive. The complete robustness vector, `Rcert`, `Rsign`, `Rreverse`, and the independent magnitude-consistency label from Section 18 accompany every joint classification.

This order prevents a later positive Gate 1.2 result from retroactively converting a Gate 1.1 null into support, and prevents one favorable robustness cell from rescuing widespread instability.

## 21. Descriptive outputs and no new endpoint search

The following may be reported descriptively for mechanism fidelity:

- condition-specific mean final adoption incidence;
- exact adoption numerators and denominators;
- adoption counts by round;
- 10, 25, and 50 percent threshold timing with censoring;
- exposure, opportunity, success, delivered-message, and pending-message counts;
- lineage depth and initial-seed lineage shares;
- clustering, path length, diameter, degree, edge, and connectivity diagnostics;
- rewire attempts, accepted swaps, and rejection reasons;
- policy rejection and compliant-finalization counts;
- alternate-topology realization-level estimates labeled descriptive.

These do not enter confirmatory classifications. Any additional analysis after the confirmatory result is frozen must be labeled exploratory and written to a separate artifact namespace.

## 22. Exclusions, invalid runs, retries, and stop rules

### 22.1 No outcome-based exclusion

No unit, realization, graph, agent, message, or cell is excluded because its effect is negative, null, extreme, unfavorable, or inconsistent. Structurally valid graphs remain included regardless of diagnostics.

### 22.2 Completeness

Valid Gate 1.2 completion requires exactly:

- 3,000 unique valid exact-replication pair chunks;
- 1,000 unique valid pair chunks in each of ten standard robustness cells;
- 1,000 unique valid alternate-topology cluster chunks, each with one ring and three rewired results;
- no duplicate, missing, corrupt, overwritten, or identity-mismatched credited chunk;
- complete action replay, deterministic repeat, ordered-hash, and schema verification.

One invalid completed scientific chunk makes the affected campaign invalid and the overall Gate 1.2 classification inconclusive. It remains visible and is never silently replaced.

### 22.3 Infrastructure interruption

A process ending before atomic publication is an infrastructure interruption. It creates no credited result and may resume from the same frozen identity. Valid already-published chunks are resumed, not recomputed. Corruption is preserved and investigated before any recomputation.

### 22.4 Topology failure

A rewired graph that does not reach its exact accepted-swap count within 60,000 proposals is invalid. No new root, unit ID, realization ID, partial graph, or adaptive attempt cap may substitute for it.

### 22.5 Scientific stop conditions

Execution halts before analysis if:

- a frozen preregistration, implementation, manifest, schema, or source hash differs;
- any Gate 1.2 confirmatory outcome was generated before the effective public preregistration commit;
- a shared Gate 1.1 scientific-code defect makes the replicated mechanism semantically invalid;
- an external or unsafe capability enters the experiment dependency path;
- a disallowed action executes or mutates toy state;
- graph, matching, synchronous propagation, provenance, replay, deterministic repeat, serial/parallel equivalence, completeness, or hash integrity fails;
- any required unit is silently dropped, replaced, or overwritten;
- a scientifically consequential ambiguity requires an unregistered choice.

A valid Gate 1.1 null, negative estimate, small effect, or failure to support H1 is explicitly not a stop condition.

## 23. Execution and analysis isolation

Future Gate 1.2 implementation must use:

- protocol identity `PAS-GATE-1.2-ROBUSTNESS-V1`;
- protocol namespace `gate12-v1`;
- roots and campaign/cell namespaces from Section 5;
- a Gate 1.2 suite manifest distinct from Gate 1.1;
- distinct Gate 1.2 schemas or explicitly versioned compatible schemas;
- a distinct repository-relative artifact root;
- one deterministic chunk per standard pair or alternate cluster;
- separate atomic checkpoints and completion manifests per subcampaign;
- one locked confirmatory analysis result;
- one Gate 1.2 Passport.

No Gate 1.1 generated outcome may be used as a Gate 1.2 seed, parameter, sample-size input, threshold, topology selector, exclusion rule, or code path. The frozen Gate 1.1 aggregate result is read only after both gates are complete, solely for the joint classifications and magnitude comparison already defined here.

The eventual runner must expose operational counts and integrity status only. It must not emit rolling cell effects, treatment-separated means, interim intervals, signs, rankings, or favorable-cell summaries. Analysis remains locked until every required Gate 1.2 completion manifest verifies.

## 24. Reproducibility and evidence package

Before Gate 1.2 execution, a separate implementation certification must bind the effective preregistration commit/hash, exact source bundle, suite manifest, schemas, analysis code, and artifact counts. Outcome-blind tests must cover every parameter cell, RNG domain, denominator, alternate-cluster calculation, multiplicity constant, classification branch, interruption point, and safety invariant using nonproduction identities.

The completed Gate 1.2 evidence package must include:

- effective Gate 1.2 preregistration identity and hash;
- frozen Gate 1.1 preregistration, implementation, campaign, result, and Passport identities;
- Gate 1.2 implementation and suite-manifest identities;
- per-subcampaign completion manifests and ordered ensemble hashes;
- exact valid, invalid, pending, resumed, new, interrupted, and recomputed counts;
- exact replication estimate, interval, decision, practical flag, and Hoeffding statistic;
- cross-gate magnitude-consistency result;
- all 11 robustness estimates, unadjusted and simultaneous intervals;
- frozen joint classification and all component flags;
- deterministic replay and repeat proof;
- serial/parallel and worker-count equivalence;
- clean-clone reproduction;
- supported-version CI;
- safety/privacy scan and public-boundary review;
- limitations and exact reproduction instructions.

Runtime metadata is recorded separately from scientific hashes. No deterministic LLM reproduction claim is possible because Gate 1.2 contains no LLM.

## 25. Researcher-degree-of-freedom controls

After this protocol becomes effective and before outcome generation, only outcome-blind implementation, invariant fixtures, crash tests, hash reference vectors, static safety tests, and runtime benchmarks using nonproduction identities are allowed.

The following are prohibited:

- inspecting any Gate 1.1 primary condition result before this protocol is frozen;
- changing a root, cell ID, value, sample size, threshold, interval, multiplicity rule, or classification after observing either gate;
- adding an intermediate transmission probability, seed count, horizon, swap count, placement regime, or topology realization;
- dropping a difficult or unfavorable cell;
- choosing a robustness subset after Gate 1.1;
- using Gate 1.1 variance or effect size for Gate 1.2 power or precision changes;
- rerunning an invalid scientific unit under a favorable new seed;
- promoting descriptive or exploratory output into the confirmatory family;
- allowing Gate 1.2 to rescue or redefine Gate 1.1.

If implementation reveals a genuine scientifically consequential ambiguity, work stops. A public numbered amendment must preserve this version, explain the issue, freeze the resolution, and be approved before any Gate 1.1 or Gate 1.2 primary outcome is generated.

## 26. Reporting language

Reports will state that Gate 1.2 concerns propagation in one fixed scripted society. They will distinguish:

1. Gate 1.1's frozen conclusion;
2. Gate 1.2 exact-replication directional evidence;
3. cross-gate magnitude consistency;
4. family-wide robustness and specification sensitivity;
5. conservative distribution-free statistics;
6. validity and integrity status.

Reports will not claim that agents persuaded one another, that the benchmark discovered a novel network-science law, that a scripted result predicts LLM behavior, or that a later favorable panel repairs an earlier null.

## 27. Publication and amendment sequence

The controlling sequence is:

1. verify that Gate 1.1 primary outcome generation remains zero;
2. finalize this document and its design-review record;
3. obtain Craig's approval of the exact diff;
4. commit and publicly tag the approved Gate 1.2 preregistration before any Gate 1.1 primary run;
5. record the immutable commit SHA and document SHA-256;
6. execute Gate 1.1 only under separate authorization;
7. freeze the Gate 1.1 result before exploratory analysis;
8. separately implement and certify Gate 1.2 without changing this protocol;
9. execute Gate 1.2 under separate authorization;
10. freeze and publish its complete evidence package under separate approval.

Neither this candidate nor its eventual public freeze authorizes Gate 1.1 execution, Gate 1.2 implementation, Gate 1.2 execution, an LLM adapter, a merge, a tag, a release, or publication without Craig's corresponding explicit approval.
