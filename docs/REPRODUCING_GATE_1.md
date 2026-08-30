# Reproducing Gate 1

## Requirements

- Python 3.11 or newer
- Git for checkout integrity checks
- no runtime packages
- no API key
- no network access during experiment execution

The repository can be tested directly from a clean checkout. Do not install an LLM SDK or configure a provider.

## Tests and safety checks

```bash
python3 -m compileall -q pasko_agent_society tests scripts
python3 -m unittest discover -s tests -v
python3 scripts/safety_scan.py
git diff --check
```

## Reproduce the compact scripted demonstration

```bash
python3 -m pasko_agent_society.cli run-demo \
  --manifest manifests/gate1_scripted_demo_v1.json \
  --output results/generated
```

The command runs 60 agents in each of 25 replicate populations for T0–T5: 150 population runs and 9,000 agent-runs. It then repeats the full ensemble, reruns it with ordered parallel execution, and replays every primary execution from recorded typed actions.

Compare generated and committed compact artifacts:

```bash
diff -u results/gate1_demo_summary.json results/generated/gate1_demo_summary.json
diff -u results/reproducibility_evidence.json results/generated/reproducibility_evidence.json
```

Representative Passports also include runtime metadata. Their environment, ledger, state, metric, and assignment hashes should match, while the recorded Python version or platform may legitimately differ on another host.

## What is deterministic

For this scripted mechanism and one declared runtime, the manifest, task, policy, graph, assignment, recorded actions, ledger, final state, metrics, and ordered result hashes are deterministic. Namespaced draws make T2/T5 matching independent of execution order.

Environment replay is the claim: recorded actions reproduce environment hashes. The repository makes no claim that an LLM could be reproduced deterministically. No LLM calls occur in Gate 1 bootstrap or CI.

## Invalid runs

Run summaries always retain attempted, valid, invalid, and reason counts. The primary outcome denominator includes valid agent-runs. Invalid runs are visible rather than silently removed.
