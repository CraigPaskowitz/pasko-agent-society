# Architecture

## 1. Design thesis

Pasko Agent Society separates **environment mechanics** from **agent cognition**.

- The **Environment Kernel** determines what exists, what is permitted, and what happens.
- The **Agent Model** proposes typed actions from its allowed observations and tools.
- The **Communication Graph** determines who can discover, communicate with, and expose whom.
- The **Experiment Engine** creates matched populations, interventions, ensembles, forks, and comparisons.

No agent may narrate simulator state into existence.

## 2. Environment Kernel

The kernel owns deterministic state for:

- experiment ticks;
- tasks;
- toy resources;
- identities;
- permissions;
- artificial policies;
- toy tools;
- synthetic artifacts/files;
- communication channels;
- rewards/scores;
- action validation;
- resets;
- forks;
- event ledger;
- replay;
- state hashing;
- Experiment Passports.

Every state mutation must correspond to ledger events.

## 3. Typed agent-action model

Gate 1 action language:

```text
REQUEST_RESOURCE
USE_TOOL
SEND_MESSAGE
CREATE_ARTIFACT
READ_ARTIFACT
JOIN_CHANNEL
PROPOSE_COLLABORATION
ACCEPT_COLLABORATION
ABSTAIN
ESCALATE
REPORT_BLOCKED
SUBMIT_SOLUTION
READ_SEALED_CACHE
```

`READ_SEALED_CACHE` is a simulator-only disallowed action. It never maps to a real filesystem, URL, credential, command, or security primitive.

```text
ActionIntent
- action_id
- agent_id
- tick
- action_type
- target_id?
- channel_id?
- resource_id?
- artifact_id?
- structured_payload
- model_output_reference?
```

The kernel resolves it:

```text
ActionResolution
- action_id
- permitted
- policy_rule_id?
- executed
- failure_reason?
- resulting_event_ids[]
- observation_recipients[]
```

A **boundary-crossing attempt** is mechanically defined as submission of a typed intent matching a policy rule marked `DISALLOWED`. The kernel rejects it.

## 4. Agent Model

Track only experimentally relevant variables:

```text
AgentInstance
- agent_id
- agent_mechanism_id
- model_provider?
- model_name?
- model_version?
- system_instruction_hash
- task_id
- policy_id
- observation_history_refs[]
- allowed_tool_ids[]
- communication_entitlements[]
- prior_action_refs[]
- resource_state_refs[]
- explicit_confidence?
- model_call_refs[]
```

Do not invent hidden psychology unless a later experiment operationalizes it.

Supported mechanism interface should allow:

- scripted baseline;
- stochastic policy;
- bounded LLM adapter;
- future learned policy.

## 5. Communication / social graph

Communication is first-class state.

```text
CommunicationEdge
- source_agent_id
- target_agent_id
- channel_id
- discoverable
- send_allowed
- read_allowed
- delivery_delay_ticks
```

```text
Channel
- channel_id
- channel_type: DIRECT | GROUP | BOARD
- discovery_rule
- write_policy
- read_policy
- forwarding_policy
- persistence_policy
```

Every delivered message records sender, recipient set, delivery time, content hash, parent lineage, and originating treatment/strategy where applicable.

Influence is measured from outcomes and lineage; it is not assumed from graph position.

## 6. Observation model

Agents never receive global state.

```text
ObservationBundle
- agent_id
- tick
- task_state
- permitted_tool_descriptions
- policy_summary
- own_prior_actions
- own_resource_state
- delivered_messages[]
- readable_artifacts[]
- public_environment_events[]
```

Observation bundles are hashable and retained by reference.

## 7. Experiment Engine

```text
ExperimentManifest
- experiment_id
- schema_version
- environment_version
- agent_mechanism
- model_config?
- population_size
- task_fixture
- policy_fixture
- communication_topology
- treatment
- seed_adopter_fraction
- replicate_count
- environment_seed
- assignment_seed
- validity_rules
- metrics
```

Supports matched populations, controlled interventions, repeated ensembles, deterministic environment replay, model-call recording/hashing, run validity, forks, and comparison.

## 8. Reproducibility layers

### Environment reproducibility

Identical recorded agent actions plus identical environment state must reproduce identical events and state hashes.

### Model stochasticity

Model outputs are not assumed deterministic. Record provider/model/version, generation settings, input/output hashes, parser result, retries, and unavailable controls.

### Statistical replication

Fresh model calls under the same declared configuration create a new ensemble. Reproducibility of model behavior is distributional, not pretend-deterministic.

## 9. No shared software framework with Pasko Republic yet

Keep architecture concepts parallel but implementations independent until both projects have independently stabilized the same primitive.
