# Gate 1.1 Design Review and Decision Record

> **Status: approved design — prepared for immutable public commit**
>
> **Gate 1 baseline:** `f4436dc0985620512b647d825e712c72accb3e7c`
>
> **Outcome-access statement:** No Gate 1.1 treatment outcome has been generated or inspected.

## Purpose

This document identifies a defensible first claim-bearing scripted experiment for Pasko Agent Society. It is based only on this repository's Gate 1 system and evidence. It does not use scientific state or implementation from any sibling project.

The approved final candidate is in `preregistrations/GATE_1_1_PREREGISTRATION.md`. Craig approved the scientific design before any outcome-generating implementation or execution. The protocol becomes immutable when its public commit SHA and document SHA-256 are recorded before implementation begins.

## Current Gate 1 scientific boundary

### Behaviors the scripted mechanism can express now

`scripted-neutral-v1` follows one fixed Archive Assembly schedule. On BLOCKED tasks, each agent independently either submits the disallowed toy `READ_SEALED_CACHE` intent or exits with `ESCALATE`/`REPORT_BLOCKED`; on SOLVABLE tasks it obtains the three toy tokens and submits a solution. Its boundary decision depends on task status and a namespaced deterministic draw. It does not depend on treatment content, peer identity, messages, graph position, prior peer behavior, or safe-exit salience.

The kernel separately supports structured simulator-local messages, delayed delivery, message lineage, artifacts, channels, and graph edges. Those primitives are tested, but the current scripted mechanism does not consume messages or propagate behavior.

### Variables the current environment can manipulate

- BLOCKED versus SOLVABLE Archive Assembly fixtures;
- exact T0–T7 pre-authored exposure artifacts and safe-exit salience;
- population size, replicate count, and deterministic assignment/action seeds;
- simulator-local channels, directed edges, and message delay when a graph is supplied;
- one deterministic directed-ring graph fixture for plumbing tests.

The Gate 1 manifest loader intentionally admits only Phase 1 isolation. Experimental topology generation, targeted seed assignment, a message-responsive scripted rule, and resumable per-pair execution do not yet exist.

### Frozen baseline evidence

- branch and public baseline: `main` at `f4436dc0985620512b647d825e712c72accb3e7c`;
- test suite: 42 of 42 passing at the public Gate 1 milestone;
- scripted demonstration: 150 valid populations and 9,000 agent-runs;
- T2: 145 boundary adopters among 1,500 valid agent-runs;
- T5: 145 boundary adopters among 1,500 valid agent-runs;
- primary T2–T5 difference: exactly 0;
- repeat, replay, parallel ordering, matched-pair, safety, clean-clone, and public CI checks: passed;
- bounded LLM adapter: intentionally absent.

### Outcomes already available

The repository implements first boundary-attempt incidence, post-exposure adoption, time to 10/25/50 percent adoption, final adoption, independent rediscovery, compliant exits, abstention, lineage depth, strategy mutation, scripted exposure pivotality, influence concentration, early-adopter centrality, persistence, validity counts, and Experiment Passport hashes. Several propagation metrics currently receive only empty/plumbing data.

### Causal comparisons already supported

Gate 1 supports matched condition ensembles with deterministic common random numbers. In particular, T2 and T5 share assignments and action draws while differing only in controlled `peer_action` content. Because the agent rule ignores that content, the committed T2–T5 zero contrast validates treatment delivery, matching, estimator rendering, and faithful null reporting. It is not a behavioral treatment test.

### What Gate 1 proved

- the synthetic task, typed actions, toy policy, and treatment fixtures execute as declared;
- `READ_SEALED_CACHE` is always rejected and cannot reach an execution handler;
- state mutation is event-ledger provenanced;
- matching, hashing, replay, ordered parallel execution, and Passports work;
- null results and invalid-run counts remain visible;
- experiment execution has no network, subprocess, browser, arbitrary filesystem, credential, connector, or LLM capability;
- the public compact demonstration is reproducible infrastructure evidence.

### What Gate 1 did not prove

- that exposure changes behavior for a scripted agent or an LLM;
- that peer-to-peer propagation or a population cascade occurs;
- that topology, seed placement, salience, or task pressure has a social effect;
- that any result generalizes outside the declared toy mechanism;
- that long campaigns are resumable or checkpoint-integrity safe;
- that an LLM can be reproduced deterministically.

## Candidate Gate 1.1 hypotheses

### Rank 1 — Degree-preserving rewiring and simple contagion

- **Hypothesis:** Under one invariant scripted transmission rule, degree-preserving rewiring of a local ring lattice increases final adoption incidence among initially unseeded agents.
- **Mechanism:** Long-range edges reduce redundant local reach and expose new parts of the population during a finite-horizon independent cascade.
- **Intervention:** A connected degree-4 graph produced by a frozen double-edge-swap algorithm.
- **Control:** A connected degree-4 ring lattice on the same 60 agent IDs.
- **Primary outcome:** Population-level final adoption incidence among the 54 initially unseeded agents after eight rounds. Boundary-attempt incidence is its deterministic operational consequence.
- **Causal interpretation:** The paired difference is the effect of the declared graph transformation on the declared scripted society, mediated by message reach. It is not persuasion and is not an LLM claim.
- **Major confounds:** Degree, seed set, message content, delivery delay, adoption rule, random draws, and horizon must all be matched. Realized exposure count is a mediator, not a baseline covariate to adjust away.
- **Required change:** Add degree-matched graph generation, targeted seed assignment, one message-responsive scripted mechanism, and campaign checkpointing. The kernel action language and safety boundary remain unchanged.
- **Scientific value:** High. It is a clean structural benchmark, directly answers a question already posed by Gate 1, and can later be rerun with model-mediated decisions.
- **Risk of being baked in:** Low-to-moderate. The rule never branches on topology condition, but network structure is expected to affect possible transmission paths. Direction and magnitude are not assigned by a treatment coefficient.

### Rank 2 — Seed dispersion across communities

- **Hypothesis:** With topology, seed count, seed degree, and behavioral rule fixed, dispersing seed adopters across modules increases cross-community adoption relative to concentrating them in one module.
- **Mechanism:** Distributed entry points reduce within-community overlap and increase access to otherwise separated groups.
- **Intervention:** Six degree-matched seeds distributed across declared modules.
- **Control:** Six degree-matched seeds concentrated in one declared module.
- **Primary outcome:** Final adoption incidence outside seed-containing modules or across all initially unseeded agents.
- **Causal interpretation:** Effect of seed placement under one fixed modular graph and scripted rule.
- **Major confounds:** It is difficult to match seed degree, pairwise distance, and module membership simultaneously; selecting the endpoint after seeing diffusion would be especially dangerous.
- **Required change:** Add modular graph fixtures, constrained seed-assignment code, the propagation mechanism, and checkpointing.
- **Scientific value:** High, especially for later intervention and governance studies.
- **Risk of being baked in:** Moderate. Geographic coverage is altered directly, so a positive result can be partly geometric rather than a surprising collective phenomenon.

### Rank 3 — Degree heterogeneity and influence concentration

- **Hypothesis:** Holding population size and mean degree fixed, a degree-heterogeneous graph produces greater lineage concentration than a regular graph.
- **Mechanism:** High-degree sources receive more opportunities to transmit and become structurally central lineages.
- **Intervention:** A frozen heterogeneous-degree topology.
- **Control:** A regular topology with the same node and edge counts.
- **Primary outcome:** Population-level lineage Herfindahl concentration.
- **Causal interpretation:** Effect of declared degree distribution on structural lineage concentration.
- **Major confounds:** Exposure opportunity is intentionally different and cannot be fully separated from degree heterogeneity; seed centrality must be matched or randomized.
- **Required change:** Add a heterogeneous graph generator, seeded lineage mechanism, and robust concentration inference.
- **Scientific value:** Moderate-to-high for later leadership research.
- **Risk of being baked in:** Moderate. The primary metric is closely coupled to the manipulated degree distribution.

### Rank 4 — Task blockage and propagation

- **Hypothesis:** Peer-strategy propagation is greater under BLOCKED than SOLVABLE tasks.
- **Mechanism:** Task impossibility changes willingness to attempt the disallowed toy action after peer exposure.
- **Intervention:** BLOCKED Archive Assembly.
- **Control:** SOLVABLE Archive Assembly with matched peer messages.
- **Primary outcome:** Final boundary-attempt incidence among initially unseeded agents.
- **Causal interpretation:** Effect of task fixture under one scripted response rule.
- **Major confounds:** The current script directly sets SOLVABLE boundary probability to zero and BLOCKED probability to 0.10, so the comparison is already encoded.
- **Required change:** Replace the current task-dependent terminal rule with a new justified response function and then freeze it.
- **Scientific value:** High as a later model-mediated question, weak as the first scripted claim.
- **Risk of being baked in:** High.

### Rank 5 — Salient safe exit during propagation

- **Hypothesis:** A prominent `ESCALATE` option reduces propagation relative to normal safe-exit presentation.
- **Mechanism:** Safe-exit salience competes with peer-strategy adoption.
- **Intervention:** Prominent safe-exit artifact delivered during a cascade.
- **Control:** Format-matched normal-salience artifact.
- **Primary outcome:** Final boundary-attempt incidence among eligible agents.
- **Causal interpretation:** Effect of the exact synthetic salience intervention under the declared rule.
- **Major confounds:** There is no semantic interpretation in the scripted agent. Any salience response would have to be inserted as a coefficient.
- **Required change:** Add an explicitly salience-sensitive behavior model or wait for a bounded LLM stage.
- **Scientific value:** High for governance, but better reserved for model-mediated behavior.
- **Risk of being baked in:** Very high in a scripted-only experiment.

## Recommendation

Use Rank 1 as Gate 1.1:

> Under controlled scripted-agent conditions, does degree-preserving rewiring of a degree-4 local ring causally change final adoption incidence among initially unseeded agents relative to the unrewired ring?

This is the strongest first gate because the manipulated variable never appears in the adoption decision rule. Both conditions use the same population, seed agents, peer message, per-edge response draws, degree, edge count, policy, task, and horizon. The effect must arise from the interaction between topology and the fixed local transmission process. A positive, negative, or null result is interpretable for this exact scripted system.

The design is intentionally a benchmark of a declared computational society. Ring-versus-rewired contagion is established network science; Gate 1.1 tests whether this laboratory can reproduce a genuine population-level phenomenon. It will not establish a general law of AI agents, evidence about LLM behavior, individual persuasion, or a novel network-science result.

## Minimal extension boundary

Gate 1.1 requires substantive but narrow behavioral machinery: agents must be able to attempt the toy boundary action after a first structured message from a distinct adopted neighbor and forward the same immutable strategy lineage. This is necessary for a social phenomenon; the current agent cannot react to any peer message.

The extension must not add action types, free-form chat, external tools, model calls, dynamic code, host resources, or operational security functionality. It should be isolated in a `gate11` package so Gate 1 results remain reproducible at their frozen code identity.

## Frozen researcher degrees of freedom

The following choices can materially change the result and must be frozen before primary execution:

- topology pair and exact graph construction algorithm;
- population size, degree, seed fraction, seed-selection rule, and seed identities by replicate;
- graph-rewiring seed namespace, accepted-swap count, rejection rules, and attempt cap;
- adoption probability and exact integer comparison used to implement it;
- whether repeated exposures, multiple sources, and already-adopted recipients create opportunities;
- message content, delivery delay, forwarding timing, parent-lineage selection, and horizon;
- definition and denominator of the primary endpoint;
- matched-randomness namespaces and condition execution ordering;
- exact sample size, interval, evidence threshold, and decision rule;
- invalid-run, interruption, retry, and corrupt-checkpoint handling;
- secondary endpoints and manipulation checks;
- Gate 1.2 scope dimensions and the requirement for a separate preregistration before Gate 1.1 unblinding.

No behavioral pilot using the frozen primary manifest or its seed namespaces is allowed before the public preregistration commit. Outcome-blind unit fixtures, graph-invariant tests, checkpoint crash tests, hash reference vectors, and runtime benchmarks that do not compute the treatment contrast are allowed after that commit. Any exploratory analysis after the primary result is frozen must be labeled exploratory and cannot change the Gate 1.1 conclusion.

## Approved repository plan

No implementation files or result artifacts should be created in this finalization pass. After the preregistration is publicly committed, the intended structure is:

```text
preregistrations/
  GATE_1_1_PREREGISTRATION.md
manifests/
  gate1_1_topology_primary_v1.json
schemas/
  gate1_1_manifest_v1.schema.json
  gate1_1_chunk_v1.schema.json
  gate1_1_completion_v1.schema.json
pasko_agent_society/gate11/
  __init__.py
  graph.py
  mechanism.py
  runner.py
  checkpoint.py
  analysis.py
  report.py
scripts/
  gate1_1_run.py
  gate1_1_analyze.py
  gate1_1_verify.py
tests/gate11/
  test_graph.py
  test_mechanism.py
  test_checkpoint.py
  test_analysis.py
  test_reproducibility.py
  test_safety.py
work/gate1_1/                 # ignored, resumable local chunks
results/gate1_1/
  completion_manifest.json
  primary_summary.json
  reproducibility_evidence.json
  passport.json
docs/
  GATE_1_1_REPORT.md
  REPRODUCING_GATE_1_1.md
```

The committed public evidence should be compact: exact config and schemas, the completion manifest of pair hashes, the aggregate summary, reproduction evidence, a Passport, and a plain-language report. Raw ledgers and transient work chunks need not be published if the clean-clone campaign deterministically regenerates and replays them.

## Branch and tag plan

1. Finalize and validate this decision record, the preregistration, and the provenance-preserving agenda update without running primary outcomes.
2. After Craig's final diff approval, commit the preregistration publicly; optionally tag that exact commit `gate1.1-prereg-v1`.
3. Implement on a dedicated `gate-1.1-execution` branch using only outcome-blind, hand-checkable fixtures.
4. Publicly freeze the separately versioned Gate 1.2 preregistration before any Gate 1.1 primary outcome generation.
5. If implementation reveals a scientifically consequential ambiguity, preserve the original and publish an amendment before outcome execution.
6. Freeze the execution commit and put its exact identity in the primary manifest.
7. Run, checkpoint, verify, and analyze only the frozen manifest.
8. Freeze the primary summary hash before exploratory work.
9. After clean-clone and CI validation, prepare a result tag such as `v0.2.0-gate1.1` for separate publication approval.

## Approved decisions

- Gate 1.1 is the degree-preserving ring-versus-rewired scripted propagation benchmark.
- The design fixes 60 agents, six uniformly selected seeds, degree 4, 120 undirected edges, 600 accepted swaps, eight rounds, an exact one-quarter transmission opportunity, and 3,000 matched pairs.
- Seed selection, topology generation, propagation draws, and execution order use separate deterministic RNG domains; common ordered source-recipient pairs reuse identical propagation draws.
- Each round uses a frozen beginning-of-round state, evaluates each eligible ordered pair once, and applies adoptions simultaneously. Newly adopted agents cannot propagate until the next round.
- Final adoption incidence among the 54 initially unseeded agents is primary. Boundary-attempt incidence is its deterministic operational consequence.
- The primary interval is the conventional paired-mean Student interval across 3,000 population differences. The Hoeffding interval and five-percentage-point practical criterion are separate statements.
- Gate 1.2 dimensions are scope-locked now but exact panels require a separate preregistration before Gate 1.1 unblinding, preferably before Gate 1.1 execution.
- The preregistration is to be committed publicly before implementation.

No scientific choice remains open in this design record. Creating the public commit and optional annotated tag remains a separate authorized publication action.
