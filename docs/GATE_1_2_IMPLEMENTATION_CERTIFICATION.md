# Gate 1.2 Implementation Certification Candidate

> **Status:** Local certification candidate. Not pushed, tagged, merged to `main`, or authorized for production execution.
>
> **Scientific status:** Outcome-blind implementation conformance only. Gate 1.2 replication and robustness have not been tested.
>
> **Gate 1.2 production outcome-generating runs:** `0`

## Frozen authority and implementation identity

| Identity | Value |
|---|---|
| Gate 1.1 published result commit | `43081df22f7b84ba16c2cf7e8edca28b45105ac4` |
| Gate 1.1 published result tag | `gate1.1-result-v1` |
| Gate 1.2 preregistration commit | `c6e9506525d8e6088a6ecb6f417e375e040fd9aa` |
| Gate 1.2 preregistration tag | `gate1.2-prereg-v1` |
| Gate 1.2 preregistration SHA-256 | `28e2240b159cad032dbf3d80f28a6d309f80fa11e5ebd9c3edd7d3bc230c8a17` |
| Provenance merge commit | `8b172529300e416aad2d8e7c8512d9b62f6c66f3` |
| Scientific implementation commit | `798985dc77dac6a327848ff4c29445417a616094` |
| Gate 1.2 source-bundle SHA-256 | `bbbcffc40390a357337b154e9d6ed578e41f451fc8c6105a0ea3c83418311bf2` |
| Suite-manifest file SHA-256 | `89ff2c154a2fb093484c1e6a358de725455ff727ad65f5f88153081b6c60901d` |
| Canonical suite-manifest hash | `sha256:f529f43d05228602ec4d13684b928d7f390fdbb7962f3805ff408af8fa32ee54` |
| Proposed implementation tag | `gate1.2-impl-v1` |

The provenance merge has exactly two parents, in order: the published Gate 1.1 result commit and the frozen Gate 1.2 preregistration commit. The preregistration is therefore an unchanged ancestor of this implementation lineage rather than a copied or recreated document.

The scientific implementation commit contains the package source used by Gate 1.2. The suite manifest binds that commit to a canonical SHA-256 inventory of the shared package and Gate 1.2 package source. The later certification commit contains only identity binding, validation, CI, tests, and this report; it does not change the bound scientific package source.

## Frozen campaign registry

Gate 1.2 uses protocol `PAS-GATE-1.2-ROBUSTNESS-V1` and RNG namespace `gate12-v1`. Its three campaign families are operationally and cryptographically separate from Gate 1.1.

| Family | Root | Independent units | Condition runs | Child canonical hash |
|---|---:|---:|---:|---|
| Exact replication, `gate12-replication-3000-v1` | `20260831` | 3,000 pairs | 6,000 | `sha256:fa05076a90c42bae40b04413a74c48a282f5ad07b06862db75b7898cd3a8102b` |
| Standard robustness, `gate12-standard-robustness-1000-v1` | `20260901` | 10,000 pairs | 20,000 | `sha256:92f890817009d4dbb73cac348f3a9de653237e6484ca53e35e7c5379533feea5` |
| Alternate topology, `gate12-alt-topology-1000-v1` | `20260902` | 1,000 clusters | 4,000 | `sha256:ca32d2cd1db4563da14911bfe0c3bfc0574a04bd616bfc59ef0d8d23c5cb7020` |
| **Total** | — | **14,000** | **30,000** | — |

The standard robustness registry contains exactly ten cells, each with 1,000 matched pairs:

| Frozen cell | Sole parameter change | Denominator |
|---|---|---:|
| `p-1-of-8` | transmission probability `1/8` | 54 |
| `p-3-of-8` | transmission probability `3/8` | 54 |
| `seeds-3` | three initial seeds | 57 |
| `seeds-12` | twelve initial seeds | 48 |
| `rounds-4` | four propagation rounds | 54 |
| `rounds-12` | twelve propagation rounds | 54 |
| `swaps-360` | 360 accepted swaps | 54 |
| `swaps-840` | 840 accepted swaps | 54 |
| `seed-placement-clustered` | frozen clustered placement | 54 |
| `seed-placement-dispersed` | frozen dispersed placement | 54 |

The manifest rejects an unknown cell, a reordered cell registry, a changed coefficient, or any difference from the frozen complete configuration. The robustness family contains exactly these ten contrasts plus `alternate-topology-3`.

## RNG and matching conformance

Gate 1.2 reuses the certified Gate 1.1 stateless SHA-256 RNG, canonical ring, bounded-u64 rejection sampler, graph invariants, toy kernel, policy, and typed action mechanism where their semantics are identical.

- Exact replication, standard robustness, and alternate topology have separate frozen roots and campaign domains.
- Gate 1.1 and Gate 1.2 protocol namespaces cannot collide.
- Each standard cell includes its exact cell ID in the deterministic RNG prefix.
- Uniform seed selection uses the frozen descending Fisher-Yates construction with exact bounded-u64 rejection.
- Both members of a matched pair receive the same sorted seed labels.
- Clustered placement draws one start label and selects six consecutive ring labels with modular rotation.
- Dispersed placement draws one offset from zero through nine and selects the six labels at spacing ten.
- Neither seed-placement construction reads or depends on the treatment topology.
- Propagation draws omit condition and topology identity, so the same ordered source-recipient pair gets the same draw wherever it exists.
- Alternate-topology clusters share seeds and propagation draws while their three rewired graphs use distinct realization-specific rewiring domains.

Tests cover fixed domain identities, bounded sampling, matched seed equality, cross-condition propagation equality, cross-cell separation, Gate 1.1/Gate 1.2 separation, and seed-placement tie and rotation semantics.

## Mechanism and topology conformance

The exact-replication configuration preserves Gate 1.1's 60 labeled agents, six seeds, degree-4 ring, 120 undirected edges, 600 accepted connected degree-preserving swaps, 60,000-proposal cap, transmission probability 1/4, eight synchronous rounds, and denominator 54.

The parameterized runner retains the same scientific mechanism for every registered cell:

1. freeze the adopted set at round start;
2. construct each distinct eligible ordered opportunity once;
3. use its predetermined condition-blind draw;
4. retain every successful source for a recipient;
5. choose the lexicographically smallest source/message as primary lineage;
6. apply new adoptions simultaneously;
7. create exactly one rejected `READ_SEALED_CACHE` consequence per adoption;
8. allow new adopters to forward only in the next round.

The rewiring implementation begins from the canonical ring and accepts a proposal only after verifying degree 4, 120 edges, connectedness, no self-loop, no duplicate edge, and the frozen accepted-swap count. It never substitutes a partial graph or a different scientific seed. Nonproduction, production-shaped fixtures verify exact counts of 360, 600, and 840 accepted swaps.

## Alternate-topology conformance

Each alternate-topology chunk is one independent cluster with exactly one ring result and three independently rewired treatment results. The cluster shares seed labels and propagation draws while only treatment rewiring realization varies.

The confirmatory contrast first averages the three rewired incidences, then subtracts the single ring incidence. It emits exactly one contrast for each cluster. Validators and analysis tests reject any attempt to treat the 3,000 nested rewired realizations as independent units.

## Durable execution and recovery

One matched pair or one four-run alternate cluster is one deterministic durable chunk. Production execution is inaccessible through fixture entry points and requires a separately supplied authorization matching the entire frozen suite.

- Per-unit locks prevent concurrent duplicate credit.
- Complete chunks are written to same-directory temporary files, flushed, `fsync`ed, decoded, schema-validated, hash-validated, and atomically published with `os.replace`.
- Existing valid chunks are resumed and never recomputed automatically.
- Corrupt or identity-mismatched chunks remain visible and halt continuation.
- Checkpoints reconstruct from chunks and use atomic publication.
- Invocation journals distinguish newly executed, preexisting/resumed, interrupted, failed, skipped, and recomputed units.
- Twelve subcampaign completion manifests bind ordered chunk hashes; one suite completion manifest binds all 14,000 units and 30,000 condition runs.
- Worker count and scheduling order cannot affect scientific identities or ordered completion hashes.

Failure-injection tests cover interruption before execution, during computation, before atomic publication, after chunk publication but before checkpoint refresh, and during reconstruction for both pair and cluster chunks. Corruption, duplicate identity, missing unit, malformed hash, impossible metadata, and incomplete suite cases are rejected.

## Analysis lock and frozen inference

Operational status exposes only unit counts, integrity state, checkpoint hashes, and restart metadata. It does not expose condition means, contrast signs, interim intervals, favorable-cell counts, or classification trends.

Confirmatory analysis has no partial-campaign mode. It opens only after all twelve subcampaign completion manifests and the suite completion manifest verify exactly 14,000 valid unique units, 30,000 condition runs, no missing or duplicate identities, no invalid credited chunks, exact schemas, and bound implementation and manifest identities. An existing valid analysis is returned without recomputation.

The implementation freezes:

- exact-replication paired inference over 3,000 differences with `t = 1.960755319205`;
- a separate five-percentage-point practical flag and Hoeffding statistic;
- the preregistered cross-gate plus/minus 0.05 magnitude-equivalence rule using `t = 1.645361877311`;
- eleven paired or cluster contrasts over 1,000 independent units each;
- unadjusted cell intervals with `t = 1.962341461134`;
- Bonferroni simultaneous family intervals with `t = 2.844038318881`;
- strong robustness only when all eleven simultaneous lower bounds are strictly positive;
- all-positive point-estimate stability and strong-reversal flags as separate outputs.

The exact first-match joint classifier implements all eight frozen labels, including every equality boundary. Exhaustive synthetic tests trigger every label and prove that one favorable cell cannot rescue family-wide failure. No test uses a canonical Gate 1.2 production unit.

## No-outcome certification boundary

All scientific fixtures use fixture protocol namespaces, fixture campaign identities, and nonproduction roots. Production configurations are rejected by public fixture execution helpers. Tests use small synthetic populations, probabilities zero or one, hand-built graphs, synthetic contrast arrays, and temporary artifact roots.

No replication pair, standard-robustness pair, alternate-topology cluster, production topology, production checkpoint, completion manifest, authorization, or Gate 1.2 analysis exists. The production artifact and result directories have not been created.

```text
Gate 1.2 production outcome-generating runs = 0
```

## Validation evidence

The certification validator binds the frozen preregistration, two-parent provenance merge, Gate 1.1 public evidence, Gate 1.2 scientific-code commit, source inventory, suite manifest, campaign registry, and absence of Gate 1.2 outputs.

The final outcome-blind validation passed:

- compilation of package, tests, and scripts;
- 153 of 153 tests: 89 Gate 1/Gate 1.1 tests plus 64 Gate 1.2 tests;
- Gate 1.1 compact-result validation and all reviewed public file hashes;
- Gate 1.1 scientific source-bundle regression check;
- Gate 1.2 preregistration byte and annotated-tag checks;
- Gate 1.2 implementation certification validator;
- safety/privacy, credential, private-path, external-I/O, unrelated-code, and offensive-capability scans;
- `git diff --check`;
- artifact-free clean-clone validation;
- absence of an LLM or external model/API dependency;
- absence of every Gate 1.2 production outcome artifact.

The working execution checkout retains ignored raw Gate 1.1 campaign artifacts from the already published Gate 1.1 result. Two legacy tests intentionally assert that a fresh checkout has no such directory. Therefore, as disclosed for the Gate 1.1 publication, the authoritative full-suite run is the artifact-free clean clone; no canonical Gate 1.1 artifact was deleted or altered to make the local execution checkout appear clean.

## Publication and execution boundary

The proposed annotated tag is `gate1.2-impl-v1`, pointing to the final certification commit that contains this report and the suite specification bound to scientific implementation commit `798985dc77dac6a327848ff4c29445417a616094`.

This candidate is not pushed or tagged. Publication of the implementation branch and annotated tag requires Craig's explicit authorization. Publication alone will not authorize any Gate 1.2 production execution. A later, separate authorization must bind the published implementation tag and exact suite manifest before any of the 30,000 condition runs may begin.
