# Gate 1.1 Implementation Certification Candidate

> **Status:** Local certification candidate. Not pushed, tagged, merged, or authorized for primary execution.
>
> **Scientific status:** Implementation conformance only. The Gate 1.1 hypothesis has not been tested.
>
> **Primary outcome-generating runs:** `0`

## Frozen authority

| Identity | Value |
|---|---|
| Gate 1 baseline | `f4436dc0985620512b647d825e712c72accb3e7c` |
| Preregistration commit | `cc1ab868a7401099751030580649e49258654fe2` |
| Preregistration tag | `gate1.1-prereg-v1` |
| Preregistration SHA-256 | `e6b7d28870c773c4ad7897349b74acfb99775a83905eaf66dcad2602a639c706` |
| Scientific implementation commit | `d31c78011abfc164fd3d20125bbe995e4023ee4a` |
| Implementation source-bundle SHA-256 | `c8b8dd93b72711eec699cc1fc8981f20beef2c3daed3f3394263c8175dc35b09` |
| Campaign-specification file SHA-256 | `2ae4e65f16f39ce73a1487fbdbddd4b15651237a8a3d0a21c8ba2ce94bb4a81b` |
| Canonical campaign-specification hash | `sha256:76ceaf1e182b5b6ecbe8214a694b4000d47d495165ab025f15112901e71600f2` |
| Proposed implementation tag | `gate1.1-impl-v1` |

The scientific implementation commit contains the complete Python package used by Gate 1.1. The campaign specification binds that commit and a SHA-256 inventory of every package source file. The later certification commit changes no package source and therefore does not change the scientific implementation identity.

## Implemented protocol

The implementation encodes the frozen primary configuration without an adaptive parameter surface:

- root seed `20260830`;
- protocol namespace `gate11-v1` and campaign namespace `primary`;
- 3,000 matched pairs and 6,000 condition runs;
- 60 labeled agents, six matched seed adopters, and denominator 54;
- degree-4 ring with offsets plus/minus 1 and plus/minus 2;
- 120 undirected edges and 240 directed simulator-local edges;
- exactly 600 accepted connected degree-preserving swaps within 60,000 proposals;
- exact transmission probability 1/4 and eight synchronous rounds;
- no spontaneous adoption, mutation, LLM, model configuration, or external capability;
- final adoption incidence among initially unseeded agents as the sole primary endpoint.

Primary configuration validation compares the complete configuration object with the frozen value. A changed coefficient, range, threshold, sample size, seed, namespace, or horizon is rejected.

## RNG conformance

All scientific draws use the existing stateless SHA-256 primitive. Seed selection, topology rewiring, propagation, and condition order have disjoint literal namespaces.

- Seed selection performs the exact descending Fisher-Yates permutation with bounded-u64 rejection sampling.
- Bounded draws reject values at or above the largest multiple of the bound below `2^64`; the rejection counter is the final namespace field.
- The same six sorted labeled seed agents are supplied to both conditions.
- Propagation draws are keyed only by root seed, protocol namespace, campaign namespace, pair ID, `propagation`, source ID, and recipient ID.
- Condition identity is absent from the propagation key, so a common ordered pair has the same draw in ring and rewired conditions.
- Condition order uses its own namespace and cannot consume another stream.

Tests include fixed non-primary reference vectors and an injected raw-u64 rejection case.

## Topology conformance

The treatment graph begins from the canonical ring. Every proposal:

1. sorts the current canonical edge set;
2. selects two distinct edges with exact bounded draws;
3. uses the frozen orientation bit;
4. rejects shared endpoints, self-loops, duplicate edges, unchanged sets, edge-count changes, degree changes, and disconnection;
5. increments the accepted count only after every invariant passes.

The implementation records accepted attempt indices, rejection-reason counts, bounded-draw rejection counts, the exact edge set, degree sequence, connectivity, and hashes. It raises `SIMULATOR_INVARIANT_FAILURE` if the accepted-swap target is not reached; it never substitutes a partial graph or a new seed.

A production-shape validation uses 60 nodes, degree 4, 120 edges, and 600 accepted swaps under the `fixture` namespace. No primary pair ID or primary outcome is used.

## Propagation conformance

The scripted mechanism drives only existing typed kernel actions. At tick zero every agent joins the local channel; each initial seed makes one rejected `READ_SEALED_CACHE` attempt and queues the immutable strategy message to four neighbors.

Each round freezes the adopted set, delivers due messages, constructs unique ordered opportunities, evaluates condition-blind draws, retains every successful source, and applies all adoptions simultaneously. A new adopter cannot send until after the round boundary, so its messages arrive in the next round. Multiple-source lineage uses the lexicographically smallest `(source_agent_id, message_id)` as primary parent while preserving the full successful-source set.

Every adoption creates exactly one policy-rejected `READ_SEALED_CACHE` consequence. Every adopter forwards once to each neighbor. All agents finish with `REPORT_BLOCKED`. Replay reconstructs the event ledger and final simulator state from recorded typed actions.

Validators independently recheck:

- message source, recipient, delivery round, and immutable content;
- one opportunity per ordered pair;
- condition-blind propagation draw identity and success bit;
- synchronous source eligibility;
- full successful-source provenance and lexical parent rule;
- one rejected boundary consequence per seed or nonseed adoption;
- absence of unexpected action rejection or permitted failure;
- denominator, graph, message, round, and threshold metrics;
- ledger, final-state, action, metric, condition, pair, and chunk hashes.

## Durable execution architecture

One matched pair is one deterministic chunk. Pair IDs are exact and filenames are canonical.

- Per-pair advisory locks are released by the operating system when a process ends.
- The runner rechecks a final chunk while holding its pair lock.
- A complete chunk is written to a same-directory temporary file, flushed, `fsync`ed, decoded, schema-validated, hash-validated, and published with `os.replace`.
- A final file is never overwritten by a competing result.
- Interrupted temporary files are visible but never credited.
- Checkpoints use the same atomic publication sequence.
- Startup and final verification fully reconstruct checkpoints from chunks; per-chunk updates are incremental and lock-protected.
- Invocation journals distinguish preexisting/resumed, newly computed, interrupted, skipped, failed, and recomputed identities.
- Invalid completed scientific chunks remain visible and make the campaign inconclusive.
- Corrupt chunks or checkpoints are preserved and halt automatic continuation.

Tests inject interruptions before execution, during computation, before atomic publication, after chunk publication but before checkpoint refresh, and during checkpoint reconstruction. Serial, parallel, and concurrent duplicate scheduling use only non-primary fixtures and produce the same ordered hashes.

## Analysis lock

The runner emits no rolling treatment contrast, mean, confidence interval, or direction indicator. Operational status contains only counts, integrity state, checkpoint identity, and progress metadata.

Primary analysis cannot open condition outcomes until a completion manifest proves:

- exactly 3,000 expected unique pair IDs;
- one valid ring and rewired condition in each pair;
- no missing, duplicate, corrupt, or invalid credited chunk;
- exact campaign-specification and implementation identities;
- verified per-chunk hashes and one ordered ensemble hash.

The frozen analysis computes the paired mean difference, sample variance with divisor 2,999, standard error, and the un-clipped paired Student interval using `1.960755319205`. It separately reports the five-percentage-point practical flag and the clipped two-sided 95 percent Hoeffding interval. Neither secondary criterion can change the primary support decision.

No primary execution authorization object is included. The production runner refuses to start without a separate exact authorization matching the campaign, implementation, source hash, scope, and 3,000-pair count.

## Outcome-blind validation boundary

Certification tests use only:

- `fixture` RNG namespaces;
- `fixture-pair-NNNN` identities;
- small hand-built or generated fixtures;
- exact probabilities 0 or 1 where useful;
- one production-shape fixture integration whose endpoint contrast is not asserted or reported;
- synthetic corruption and interruption artifacts in temporary directories.

The repository contains no `artifacts/gate1_1_primary_v1` directory, no primary pair chunk, no completion manifest, no primary analysis, and no execution authorization. Gate 1.1 primary outcome-generating run count remains zero.

## Validation commands

```text
python3 -m compileall -q pasko_agent_society tests scripts
python3 -m unittest discover -s tests -v
python3 scripts/safety_scan.py
git diff --check
shasum -a 256 preregistrations/GATE_1_1_PREREGISTRATION.md
python3 -m pasko_agent_society.gate11_cli status --manifest manifests/gate1_1_primary_v1.json
```

The status command is outcome-blind and does not create the campaign artifact directory.

The final local certification run passed:

- package, test, and script compilation;
- 89 of 89 legacy and Gate 1.1 unit, invariant, integration, interruption, and integrity tests;
- all safety/privacy scan categories across 59 repository text files;
- `git diff --check`;
- frozen Gate 1 artifact comparison;
- preregistration byte/hash and tag-target verification;
- campaign-specification and implementation-source identity verification;
- absence of primary chunks, completion analysis, execution authorization, and the production artifact directory.

Repository CI has not run for this unpublished branch because no push is authorized in this phase.

## Publication and execution boundary

The proposed annotated tag is `gate1.1-impl-v1`, pointing to the final certification commit that contains this report and the campaign specification bound to scientific implementation commit `d31c78011abfc164fd3d20125bbe995e4023ee4a`.

This candidate is not pushed or tagged. Publication requires Craig's explicit approval. Even after implementation publication, primary execution requires a separate exact authorization; publishing the implementation alone does not authorize the 3,000-pair campaign.
