# Contributing

Thank you for helping improve Pasko Agent Society.

## Gate 1 scope

Contributions must preserve the synthetic-only safety boundary in `SAFETY.md`. Gate 1 changes may improve the deterministic kernel, typed simulator actions, toy fixtures, controlled treatment artifacts, local graph plumbing, scripted validation, metrics, replay, manifests, Passports, documentation, or tests.

Do not add live model calls, network clients, browsers, shell or subprocess execution, arbitrary filesystem access, external connectors, credentials, real messaging, package installation during experiments, dynamic code execution, security scanning of real systems, offensive-security functionality, or operational incident techniques.

`READ_SEALED_CACHE` must remain an always-rejected in-memory enum with no mapping to a path, URL, command, permission, API, credential, or host resource.

## Scientific contributions

- Predeclare the estimand and distinguish primary from secondary outcomes.
- Keep T2 versus the information-matched T5 control as the primary comparison.
- Retain invalid runs and report their reasons.
- Distinguish mechanical causality, exposure provenance, and treatment effects.
- Label scripted outcomes as infrastructure validation, never LLM evidence.
- Treat null and negative results as valid outcomes.

## Development checks

Use Python 3.11 or newer. Runtime dependencies are intentionally empty.

```bash
python3 -m compileall -q pasko_agent_society tests scripts
python3 -m unittest discover -s tests -v
python3 scripts/safety_scan.py
git diff --check
```

Pull requests should describe the declared scientific or infrastructure change, tests added, expected safety impact, and whether any manifest or result hash changes.

By participating, you agree to `CODE_OF_CONDUCT.md`. Contributions are licensed under Apache-2.0.
