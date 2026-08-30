# Gate 1.1 Result Candidate

> **Status:** Local result candidate; not committed, pushed, tagged, released, or merged.
>
> **Scope:** Scripted topology-propagation benchmark only. Gate 1.2 has not executed.

## Frozen provenance

Gate 1.1 used the public preregistration at `cc1ab868a7401099751030580649e49258654fe2` (`gate1.1-prereg-v1`, document SHA-256 `e6b7d28870c773c4ad7897349b74acfb99775a83905eaf66dcad2602a639c706`) and certified implementation at `4c8bb4d3f88a38469a6edcb770b1b0a037a73ae7` (`gate1.1-impl-v1`). The scientific source identity is `d31c78011abfc164fd3d20125bbe995e4023ee4a`, source-bundle SHA-256 `c8b8dd93b72711eec699cc1fc8981f20beef2c3daed3f3394263c8175dc35b09`.

The campaign specification has file SHA-256 `2ae4e65f16f39ce73a1487fbdbddd4b15651237a8a3d0a21c8ba2ce94bb4a81b` and canonical hash `sha256:76ceaf1e182b5b6ecbe8214a694b4000d47d495165ab025f15112901e71600f2`.

Gate 1.2 was preregistered before outcome generation at `c6e9506525d8e6088a6ecb6f417e375e040fd9aa` (`gate1.2-prereg-v1`, document SHA-256 `28e2240b159cad032dbf3d80f28a6d309f80fa11e5ebd9c3edd7d3bc230c8a17`). Gate 1.2 execution remains zero.

The zero-data receipt was recorded before pair 0 with 0 complete, 3,000 pending, 0 invalid, no checkpoint, no chunks, no completion manifest, and no analysis. Its file SHA-256 is `10fd9ef9ee421bcf248800feecb9d9e1f679b5826f9e6efdb8d5af515b1a9e82`.

## Execution and integrity

- 3,000 matched pairs attempted and valid; 0 missing and 0 invalid.
- 6,000 condition runs valid.
- 3,000 pairs newly executed; 0 resumed, interrupted, retried, failed, excluded, or recomputed.
- Every condition was replayed from recorded typed actions during chunk validation.
- Every primary denominator was 54; every condition graph had 120 undirected edges; every treatment graph recorded exactly 600 accepted swaps.
- No duplicate pair ID, partial credited chunk, or temporary file remained at completion.
- Checkpoint content hash: `sha256:9738b04bac0b3fa89af95e4f8d6e4515b611772d390cc8d6183626ee40cc5b9e`.
- Completion-manifest content hash: `sha256:161e575ca0e56867d4f98ae4159a4214055e93d20062209dcd40639a8502dd86`.
- Ordered ensemble hash: `sha256:f511edb2eb742f8220d94580757320d53546bc9f323cabd0ba0131fb20b64fbd`.
- Primary-analysis content hash: `sha256:a910f13451e642ca57e81a8b2e1bfa04b9705aabbabe5d63cfde0e7e220a4ca8`.

## Preregistered primary result

The endpoint is final adoption incidence among the 54 initially unseeded agents after round eight.

| Quantity | Result |
|---|---:|
| Ring adoption count / denominator | 31,569 / 162,000 |
| Ring mean incidence | 0.1948703704 |
| Rewired adoption count / denominator | 39,420 / 162,000 |
| Rewired mean incidence | 0.2433333333 |
| Paired mean difference, rewired minus ring | 0.0484629630 |
| Paired sample variance | 0.0226395690 |
| Standard error | 0.0027470936 |
| Primary paired-mean 95% interval | [0.0430765847, 0.0538493413] |

The primary lower confidence bound is strictly greater than zero, so the preregistered directional decision is **SUPPORT_H1**.

The estimate is 4.846 percentage points, below the separately preregistered 5-percentage-point practical threshold, so the practical-magnitude flag is **not met**.

The separately reported two-sided 95% Hoeffding interval is `[-0.0011278927, 0.0980538187]`. Its lower bound does not clear zero, so distribution-free conservative positivity is **not certified**.

## Scientific conclusion

Under this frozen scripted independent-cascade mechanism, connected degree-preserving rewiring increased final adoption incidence among initially unseeded agents relative to the degree-4 ring. The result supports the preregistered directional hypothesis, but it does not meet the distinct five-point practical threshold and it does not pass the deliberately conservative Hoeffding certification.

This experiment establishes only a scripted network-propagation benchmark. It does not establish LLM behavior, persuasion, autonomous norm formation, emergent intelligence, general social behavior in real agents, or a novel network-science result. Boundary attempts are a deterministic operational consequence of scripted adoption, not a separate behavioral discovery.

## Reproduction

At exact implementation commit `4c8bb4d3f88a38469a6edcb770b1b0a037a73ae7`, provide the exact authorized execution object and run:

```text
python3 -m compileall -q pasko_agent_society tests scripts
python3 -m unittest discover -s tests -q
python3 scripts/safety_scan.py
python3 -m pasko_agent_society.gate11_cli run --manifest manifests/gate1_1_primary_v1.json --authorization artifacts/gate1_1_primary_v1/execution-authorization.json --workers 8 --invocation-id gate11-primary-run-v1
python3 -m pasko_agent_society.gate11_cli verify --manifest manifests/gate1_1_primary_v1.json
python3 -m pasko_agent_society.gate11_cli analyze --manifest manifests/gate1_1_primary_v1.json
git diff --check
```

An artifact-free clean clone at the exact implementation commit passed compile validation, all 89 tests, the repository safety/privacy scan, and `git diff --check`. A complete one-worker clean reconstruction then generated 3,000 valid pairs and replay-verified all 6,000 condition runs. All 3,000 ordered pair hashes, the checkpoint file, the completion manifest, and the ordered ensemble hash are identical to the canonical eight-worker execution. The canonical analysis was not rerun, preserving the preregistered exactly-once analysis rule.

Two implementation-certification tests intentionally assert that the production artifact directory does not exist. An initial clean-clone test invocation after placing only the authorization file therefore produced those two expected failures before any clean pair ran. The authorization directory was removed, the exact artifact-free commit passed all 89 tests, and only then was the clean reconstruction started. This boundary behavior is disclosed; it is not a campaign integrity failure.

The final repository and candidate-artifact safety/privacy scans passed, frozen authority hashes remained exact, core Gate 1 source remained unchanged, and no Gate 1.2 artifact or execution exists. No result publication is authorized.
