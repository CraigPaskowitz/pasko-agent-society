# Gate 1 Safety Validation Report

Validation date: 2026-08-29

## Scope and provenance

The release candidate was built only in the new `pasko-agent-society` working directory from the nine supplied foundation documents listed in `docs/FOUNDATION_PROVENANCE.md`. Implementation code was written independently. No unrelated repository was read, modified, or used as a code source.

The public experiment source snapshot is `59298e8d467449fccf19af99ea359bf52739a587`. The manifest records that snapshot, and the compact result artifacts were generated from it.

## Automated invariant tests

Command:

```bash
python3 -m unittest discover -s tests -v
```

Status: PASS, 42 tests.

The suite covers the exact action enum; SOLVABLE/BLOCKED resources; T0–T7; fixed-width treatment delivery; the sole T2/T5 visible-content difference; unknown actions; unsafe identifiers and payloads; sealed-action rejection in every treatment; state-mutation provenance; observation scoping; local communication and lineage; all specified metrics; invalid-run visibility; matched assignments; deterministic repeats; action replay; ordered parallel execution; null reporting; Passport fields; absence of a live model adapter; and runtime tripwires for network and process calls.

## Static safety, privacy, and secret scan

Command:

```bash
python3 scripts/safety_scan.py
```

Status: PASS.

Final scan file count: 45.

| Category | Status |
|---|---|
| credentials or tokens | PASS |
| private host paths or file URIs | PASS |
| external-I/O or dynamic-import dependencies in experiment code | PASS |
| unrelated-repository markers in implementation code | PASS |
| offensive-security dependencies | PASS |

The scanner examines repository text for credential signatures and private host paths, parses every experiment-package module for network, browser, process, remote-protocol, or dynamic-import dependencies, and checks implementation code for unrelated-repository provenance markers and offensive-security dependencies.

## Manual tracked-file review

Status: PASS.

- Foundation documents contain only their intended public research framing.
- The bootstrap prompt itself is not a tracked public artifact.
- No real credential, host path, private operational datum, or proprietary implementation content is present.
- No code was copied from OpenClaw, Pasko Republic, Study Sunday, another Pasko Labs repository, or a private work repository.
- No live provider configuration, LLM SDK, connector, browser, shell, subprocess, network client, package installer, or external messaging implementation is present.
- No exploit, vulnerability-scanning, privilege-escalation, persistence, evasion, credential-acquisition, or other offensive-security implementation is present.
- GitHub is used only for ordinary source publication and CI, never as an agent experiment.

## Synthetic boundary review

Status: PASS.

`READ_SEALED_CACHE` appears only as a typed simulator enum, fixture content, structured local lineage content, metrics/tests, and explanatory documentation. The kernel rejects it before action resolution. Its unreachable handler raises a simulator invariant error. It has no mapping to a real resource, filesystem location, URL, command, permission, credential, API, or host.

Agent-controlled payloads accept only small typed schemas and safe atoms. Unknown fields, free-form messages, URLs, host paths, file URIs, command words, and non-simulator identifiers are rejected. Communication resolves only across declared simulator agents, channels, and graph edges.

## Demonstration and reproducibility

Status: PASS.

- 150 attempted population runs; 150 valid; 0 invalid.
- 9,000 attempted agent-runs; 9,000 valid; 0 invalid.
- Identical full repeat: 150 of 150 population hashes matched.
- Recorded-action replay: 150 of 150 ledger and final-state hashes matched.
- Parallel ordering: 150 of 150 ordered result hashes matched.
- Matched T2/T5 randomness: 25 of 25 paired population assignments and action hashes matched.
- Primary scripted T2−T5 result: 0.000000.

This demonstration validates infrastructure only and is not evidence about LLM behavior.

## Release hygiene

- Python compile check: PASS.
- Unit and invariant tests: PASS.
- Secret/privacy/static safety scan: PASS.
- `git diff --check`: PASS.
- Clean-clone validation: PASS at evidence commit `c5fbce489146ed897f964c21f7a60bbac6cbb848` (compile, 42 tests, safety scan, and `git diff --check`).
- CI workflow: configured for Python 3.11 and 3.12; live status is reported by the public repository check state.

No safety claim extends beyond this declared synthetic Gate 1 implementation.
