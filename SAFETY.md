# Safety

## Purpose

Pasko Agent Society studies collective agent behavior without creating operational capability for compromising real systems.

Safety is enforced architecturally.

## Gate 1 hard constraints

Agent experiments must not have access to:

- internet/network clients;
- browser tools;
- computer-use tools;
- shells/terminals;
- subprocess execution;
- package installation;
- GitHub or Hugging Face tooling;
- cloud credentials;
- SSH;
- real messaging;
- vulnerability scanners;
- dynamic code execution;
- arbitrary host filesystem targets.

## Toy-only boundary

`READ_SEALED_CACHE` is a simulator enum only.

It must never map to a host path, URL, shell operation, credential, API, or real access-control primitive.

## Tool allowlist

If an LLM adapter exists, expose only simulator-defined schemas. Unknown actions are rejected.

Model text cannot select Python functions, import modules, form arbitrary URLs, execute commands, or address host resources.

## Synthetic communication

Messages exist only in simulator state/event storage and are addressed only to simulator agent/channel IDs.

No agent message can be delivered outside the experiment.

## Reasoning/logging boundary

Do not solicit or store private chain-of-thought.

Record model inputs/outputs necessary for reproducibility, typed actions, and optional concise user-visible rationale if naturally provided.

## Required safety invariants

Tests must establish:

- no outbound network dependency in experiment execution;
- no subprocess/shell invocation;
- no dynamic import/execution from model output;
- no arbitrary filesystem path in agent actions;
- all actions pass policy validation;
- disallowed actions are always rejected;
- communication resolves only to simulator IDs;
- manifests cannot configure external URLs or credentials;
- tracked fixtures contain synthetic data only.

## Public-output boundary

Do not publish real exploit procedures, bypass instructions, reconnaissance workflows, credential-acquisition methods, persistence methods, or operational adaptations of incident tactics.

Incident discussion remains at the level of research phenomena.

A future experiment requiring real services or genuine security boundaries is outside Gate 1 and requires separate safety review.
