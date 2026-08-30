# Project Thesis & Repository Positioning

## Project thesis

**Pasko Agent Society is an open experimental laboratory for reproducible research on collective AI-agent behavior.**

It studies how individual AI-agent behavior becomes population behavior under controlled changes in task pressure, peer exposure, communication structure, permissions, safe exits, incentives, and monitoring.

Its scientific advantage is experimental control. Agent populations can be cloned, reset, given precisely controlled observations, placed into declared graphs, forked from identical histories, and repeated across many inference calls.

The project does not ask whether agents behave like humans. It asks which collective phenomena are properties of a particular model, prompt, task, topology, or control structure—and which survive changes in those components.

## Recommended repository name

### `pasko-agent-society` — recommended

Best fit because it preserves the sibling relationship to Pasko Republic while making population behavior the central object of study. It is broader than a communication experiment but does not imply government or politics.

### `pasko-agent-republic`

Not recommended. Too easily confused with Pasko Republic and implies institutional/government structure.

### `pasko-agents`

Too generic; sounds like an agent SDK or production framework.

### `pasko-agent-lab`

Good second choice, but weaker on the population/society thesis.

## Public positioning

Use:

> An open experimental laboratory for reproducible research on emergent behavior, coordination, influence, information propagation, norm formation, and control in populations of AI agents.

Avoid positioning it as an agent-control product, cyber tooling, a swarm platform, or a simulator of the 2026 OpenAI/Hugging Face incident.

## Relationship to Pasko Republic

Keep concepts parallel but code independent.

| Pasko Republic | Pasko Agent Society |
|---|---|
| Republic Kernel | Environment Kernel |
| Society Model | Agent Model |
| Human social networks | Agent communication graph |
| Behavior functions | Executable model/agent mechanism |
| Event ledger | Event ledger |
| Counterfactual forks | Controlled experiment forks |
| Experiment Passport | Experiment Passport |
| Ensembles | Ensembles |

Do not create a generic shared Pasko simulation framework yet.

Potential future shared primitives are canonical hashing, Experiment Passport envelopes, ledger-event envelopes, manifest identity, and run-validity schemas—but only after both projects independently stabilize the same semantics.
