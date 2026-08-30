# Gate 1.2 Result: Fresh Replication and Prespecified Robustness

> **Status:** Complete, valid, and ready for review. This candidate result package is not published, tagged, merged to `main`, or released.
>
> **Frozen joint classification:** `replicated but specification-sensitive`

## Scientific scope

Gate 1.2 tests whether the positive scripted topology effect published at Gate 1.1 replicates under fresh randomness and remains stable across eleven prespecified robustness contrasts. The Gate 1.2 preregistration was frozen before any Gate 1.1 primary outcome existed, and the Gate 1.2 implementation was frozen before any Gate 1.2 production outcome existed.

This is a scripted independent-cascade benchmark. It is not evidence about LLM behavior, persuasion, autonomous norm formation, emergent intelligence, or general social behavior in real agents. It is not presented as a novel network-science discovery.

## Frozen authorities

| Authority | Identity |
|---|---|
| Gate 1.1 result | `43081df22f7b84ba16c2cf7e8edca28b45105ac4`; `gate1.1-result-v1` |
| Gate 1.2 preregistration | `c6e9506525d8e6088a6ecb6f417e375e040fd9aa`; `gate1.2-prereg-v1` |
| Gate 1.2 preregistration SHA-256 | `28e2240b159cad032dbf3d80f28a6d309f80fa11e5ebd9c3edd7d3bc230c8a17` |
| Gate 1.2 implementation | `b4ca7b598215d14102969045e4717cd5007f1bc3`; `gate1.2-impl-v1` |
| Scientific-code commit | `798985dc77dac6a327848ff4c29445417a616094` |
| Source-bundle SHA-256 | `bbbcffc40390a357337b154e9d6ed578e41f451fc8c6105a0ea3c83418311bf2` |
| Campaign specification | `sha256:f529f43d05228602ec4d13684b928d7f390fdbb7962f3805ff408af8fa32ee54` |

## Execution and integrity

The complete frozen suite contains:

- 3,000 fresh-seed exact-replication matched pairs and 6,000 condition runs;
- 10,000 standard-robustness matched pairs and 20,000 condition runs;
- 1,000 alternate-topology clusters and 4,000 condition runs;
- 14,000 independent units and 30,000 condition runs in total;
- zero invalid, missing, duplicate, excluded, failed, skipped, or recomputed units.

The initial exact-replication process was stopped after 813 valid chunks to replace CPU-bound thread concurrency with process-level concurrency. The same frozen identities resumed all 813 chunks and executed the remaining 2,187. No credited unit was recomputed and no temporary file remained. The eleven other subcampaigns each executed 1,000 new units.

Every chunk, condition result, ledger replay, schema, identity, hash, checkpoint, child completion manifest, and suite manifest passed the certified verification path. The suite completion hash is:

```text
sha256:c111cd3bad274cd83b54298545112d513e5c216d391204b0b6bd56f68ebd332f
```

The ordered suite ensemble hash is:

```text
sha256:7a2554574aa0083bc1007c6dd4c61d07aff86f38062d0ff83e0ee9985c604661
```

## Exact fresh-seed replication

The endpoint is final adoption incidence among the 54 initially unseeded agents after eight rounds.

| Condition | Adoptions | Denominator | Incidence |
|---|---:|---:|---:|
| Ring | 31,996 | 162,000 | 0.19750617283950617 |
| Rewired | 39,789 | 162,000 | 0.2456111111111111 |

The preregistered paired result was:

```text
rewired - ring = 0.04810493827160494
95% paired CI = [0.04272786632773895, 0.05348201021547093]
```

In percentage-point terms, connected degree-preserving rewiring increased final adoption incidence by **4.810 percentage points**, with a paired 95% confidence interval from **4.273 to 5.348 percentage points**.

The lower bound was strictly greater than zero, so the exact replication **supported the preregistered directional hypothesis**.

The point estimate did not meet the separately preregistered five-percentage-point practical threshold. This does not establish that the true effect is below five points; the paired interval crosses five points.

The two-sided 95% Hoeffding interval was:

```text
[-0.0014859174319347065, 0.09769579397514458]
```

Its lower bound did not clear zero, so the deliberately conservative distribution-free positivity certification was not met. This does not reverse the primary paired-interval decision.

## Gate 1.1 magnitude comparison

Gate 1.1 estimated `0.048462962962962965`; Gate 1.2 exact replication estimated `0.04810493827160494`. The preregistered replication-minus-Gate-1.1 contrast was:

```text
-0.00035802469135802484
90% equivalence interval = [-0.006744697989863143, 0.006028648607147093]
95% interval = [-0.00796893619645148, 0.007252886813735429]
```

The frozen magnitude classification is **consistent within five percentage points**. Gate 1.1 remains unchanged by this comparison.

## Eleven-cell robustness family

The table reports percentage-point estimates and preregistered two-sided Bonferroni simultaneous 95% intervals using `t(df=999) = 2.844038318881`.

| Contrast | Estimate (points) | Simultaneous 95% interval (points) |
|---|---:|---:|
| Transmission `1/8` | 0.526 | [-0.051, 1.103] |
| Transmission `3/8` | 15.322 | [13.369, 17.275] |
| Three initial seeds | 3.821 | [2.702, 4.940] |
| Twelve initial seeds | 4.673 | [3.192, 6.154] |
| Four rounds | 2.659 | [1.549, 3.769] |
| Twelve rounds | 4.367 | [3.005, 5.728] |
| 360 accepted swaps | 5.094 | [3.733, 6.456] |
| 840 accepted swaps | 4.607 | [3.264, 5.951] |
| Clustered seeds | 19.424 | [18.224, 20.624] |
| Dispersed seeds | -0.391 | [-1.816, 1.034] |
| Three alternate rewired realizations | 4.044 | [3.054, 5.035] |

Ten point estimates were positive; the dispersed-seed estimate was negative and imprecise. Nine simultaneous lower bounds were positive. The `1/8` and dispersed-seed simultaneous intervals crossed zero. No simultaneous upper bound was below zero, so the frozen strong-directional-reversal modifier was false.

Consequently:

- all eleven point estimates positive: **false**;
- all eleven simultaneous lower bounds positive: **false**;
- strong family-wide robustness certified: **false**;
- strong directional reversal present: **false**.

## Frozen joint classification

Gate 1.1 supported its directional hypothesis. Gate 1.2 exact replication also supported its directional hypothesis. Because not all eleven robustness point estimates were positive, the first matching preregistered classification rule yields:

```text
replicated but specification-sensitive
```

This classification was not selected or reinterpreted after observing the result.

## Conclusion

The Gate 1.1 scripted topology effect replicated under an independently frozen random realization, with a nearly identical effect estimate and a positive paired confidence interval. The magnitude comparison was consistent within the preregistered five-point margin. However, the effect was specification-sensitive across the frozen robustness family: dispersed seed placement produced a small negative, imprecise point estimate, the low-transmission cell was also not simultaneously certified, and strong family-wide robustness was not established.

The correct narrow conclusion is therefore that this scripted topology effect replicated but was not uniformly robust across all prespecified nearby specifications.

## Reproducibility and package boundary

The compact result package contains the frozen campaign specification, pre-execution receipt, authorization, twelve checkpoints, twelve completion manifests, thirteen invocation journals, suite completion manifest, canonical analysis, Passport, execution accounting, validation report, and reproducibility evidence.

The 4.4 GB raw chunk set is not copied into the compact package. Its 14,000 chunk hashes are bound by the child completion manifests and ordered ensemble hashes. The raw local artifacts remain available for deterministic replay/reconstruction during review. Publication of this candidate and any later data-retention decision require separate approval.
