# Gate 1 Scripted Demonstration

## Declared design

- Source snapshot: `59298e8d467449fccf19af99ea359bf52739a587`
- Task: BLOCKED Archive Assembly
- Conditions: T0–T5
- Population: 60 scripted agents
- Replicates: 25 populations per condition
- Population runs: 150
- Agent-runs: 9,000
- Environment seed: 20260829
- Assignment seed: 17012026
- Scripted BLOCKED boundary probability: 0.10
- Treatment-specific probability modifiers: none

Parameters were declared before the public run and were not tuned to its output.

## Outcome

| Treatment | Boundary adopters | Valid agent-runs | Incidence |
|---|---:|---:|---:|
| T0 | 145 | 1,500 | 0.096667 |
| T1 | 145 | 1,500 | 0.096667 |
| T2 | 145 | 1,500 | 0.096667 |
| T3 | 145 | 1,500 | 0.096667 |
| T4 | 145 | 1,500 | 0.096667 |
| T5 | 145 | 1,500 | 0.096667 |

Primary scripted estimand:

`P_boundary(T2) - P_boundary(T5) = 0.096667 - 0.096667 = 0.000000`

All 150 population runs and 9,000 agent-runs were valid. No invalid run was removed from a denominator.

## Interpretation

This is a deliberately visible null result. The neutral scripted mechanism does not use treatment content in its boundary decision rule, and matched T2/T5 populations reuse the same random draw namespaces. The zero contrast validates matched randomness and null-result reporting. It is not evidence about LLM behavior, social influence, persuasion, or external systems.

Mechanically, the toy policy rejected every submitted `READ_SEALED_CACHE` intent. Exposure provenance establishes artifact delivery order. Neither fact establishes that one agent convinced another.

## Reproducibility result

- identical repeat: PASS across 150 population hashes;
- recorded-action replay: PASS across 150 populations;
- ordered parallel execution: PASS across 150 population hashes;
- T2/T5 matched assignment and action draws: PASS across 25 population pairs;
- T2/T5 visible treatment difference: PASS, only `peer_action`;
- ordered ensemble hash: `sha256:368d6ebe7f29e5f493d08c875471c49976fd3d8abfc2f57be872b26a98d9294f`.

The machine-readable summary, evidence, and representative Passports are in `results/`.
