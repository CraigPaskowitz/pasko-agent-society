# Reproducibility

## Two layers

AI-agent research must separate deterministic environment replay from stochastic model replication.

## Environment reproducibility

Given identical environment state and recorded model actions, the simulator must reproduce identical action resolutions, deliveries, ledger events, state hashes, and final result hashes.

## Model-call provenance

For each model call record when available:

- provider;
- model and snapshot/version;
- timestamp;
- system-instruction hash;
- observation/input hash;
- action-schema hash;
- temperature/top-p or equivalent;
- reasoning configuration;
- provider seed if supported;
- output limit;
- response hash;
- parsed-action hash;
- retries;
- terminal API status.

Unavailable controls are explicitly marked unavailable.

## Replay

Replay reuses recorded outputs/actions and verifies deterministic environment execution.

## Repeat

Repeat makes new calls under the nominal same model configuration. Results may differ.

## Statistical replication

Replication runs a fresh ensemble and compares outcome/treatment-effect distributions.

This is the primary reproducibility concept for model behavior.

## Experiment Passport

```text
ExperimentPassport
- experiment_id
- schema_version
- repository_commit
- environment_version
- manifest_hash
- task_hash
- policy_hash
- graph_hash
- assignment_hash
- agent_mechanism_id
- model_configuration
- model_call_provenance_hashes[]
- simulator_seed
- replicate_id
- validity_status
- event_ledger_hash
- final_state_hash
- metrics_hash
- runtime_metadata
```

## Public artifacts

Commit manifests, fixtures, compact summaries, representative passports, figures, reproduction commands, and hashes.

Do not commit huge model-call corpora by default.
