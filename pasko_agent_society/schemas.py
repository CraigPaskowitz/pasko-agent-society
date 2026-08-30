"""Versioned, typed schemas for the Gate 1 simulator."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


SCHEMA_VERSION = "1.0.0"
ENVIRONMENT_VERSION = "gate1-kernel-1.0.0"


class ActionType(str, Enum):
    REQUEST_RESOURCE = "REQUEST_RESOURCE"
    USE_TOOL = "USE_TOOL"
    SEND_MESSAGE = "SEND_MESSAGE"
    CREATE_ARTIFACT = "CREATE_ARTIFACT"
    READ_ARTIFACT = "READ_ARTIFACT"
    JOIN_CHANNEL = "JOIN_CHANNEL"
    PROPOSE_COLLABORATION = "PROPOSE_COLLABORATION"
    ACCEPT_COLLABORATION = "ACCEPT_COLLABORATION"
    ABSTAIN = "ABSTAIN"
    ESCALATE = "ESCALATE"
    REPORT_BLOCKED = "REPORT_BLOCKED"
    SUBMIT_SOLUTION = "SUBMIT_SOLUTION"
    READ_SEALED_CACHE = "READ_SEALED_CACHE"


class TaskStatus(str, Enum):
    SOLVABLE = "SOLVABLE"
    BLOCKED = "BLOCKED"


class ValidityStatus(str, Enum):
    VALID = "VALID"
    MODEL_ERROR = "MODEL_ERROR"
    PARSE_ERROR = "PARSE_ERROR"
    TIMEOUT = "TIMEOUT"
    SIMULATOR_INVARIANT_FAILURE = "SIMULATOR_INVARIANT_FAILURE"


class ChannelType(str, Enum):
    DIRECT = "DIRECT"
    GROUP = "GROUP"
    BOARD = "BOARD"


@dataclass(frozen=True)
class ActionIntent:
    action_id: str
    agent_id: str
    tick: int
    action_type: ActionType | str
    target_id: str | None = None
    channel_id: str | None = None
    resource_id: str | None = None
    artifact_id: str | None = None
    structured_payload: Mapping[str, Any] = field(default_factory=dict)
    model_output_reference: str | None = None


@dataclass(frozen=True)
class ActionResolution:
    action_id: str
    permitted: bool
    policy_rule_id: str | None
    executed: bool
    failure_reason: str | None
    resulting_event_ids: tuple[str, ...]
    observation_recipients: tuple[str, ...]


@dataclass(frozen=True)
class ToyResource:
    resource_id: str
    token: str


@dataclass(frozen=True)
class TaskFixture:
    task_id: str
    status: TaskStatus
    required_tokens: tuple[str, ...]
    resources: tuple[ToyResource, ...]
    allowed_tool_ids: tuple[str, ...]
    max_rounds: int = 8


@dataclass(frozen=True)
class PolicyRule:
    rule_id: str
    action_type: ActionType
    disposition: str


@dataclass(frozen=True)
class PolicyFixture:
    policy_id: str
    rules: tuple[PolicyRule, ...]


@dataclass(frozen=True)
class ArtifactContent:
    artifact_schema: str
    task_fact: str
    peer_action: str
    policy_label: str
    safe_exit: str


@dataclass(frozen=True)
class TreatmentDefinition:
    treatment_id: str
    task_status: TaskStatus
    exposure_kind: str
    safe_exit_salience: str
    artifact_content: ArtifactContent | None
    communication_enabled: bool = False


@dataclass(frozen=True)
class CommunicationEdge:
    source_agent_id: str
    target_agent_id: str
    channel_id: str
    discoverable: bool
    send_allowed: bool
    read_allowed: bool
    delivery_delay_ticks: int


@dataclass(frozen=True)
class Channel:
    channel_id: str
    channel_type: ChannelType
    discovery_rule: str
    write_policy: str
    read_policy: str
    forwarding_policy: str
    persistence_policy: str


@dataclass(frozen=True)
class AgentOutcome:
    agent_id: str
    valid: bool = True
    validity_status: ValidityStatus = ValidityStatus.VALID
    boundary_attempt_ticks: tuple[int, ...] = ()
    boundary_exposure_tick: int | None = None
    first_terminal_action: str | None = None
    terminal_tick: int | None = None
    abstain_ticks: tuple[int, ...] = ()
    solution_valid: bool = False
    strategy_source_id: str | None = None
    decision_with_exposure: str | None = None
    decision_without_exposure: str | None = None
    degree_centrality: float = 0.0
    post_reset_reused: bool = False


@dataclass(frozen=True)
class ExperimentManifest:
    experiment_id: str
    schema_version: str
    environment_version: str
    agent_mechanism: Mapping[str, Any]
    model_config: Mapping[str, Any] | None
    population_size: int
    task_fixture: str
    policy_fixture: str
    communication_topology: Mapping[str, Any]
    treatment: str
    seed_adopter_fraction: float
    replicate_count: int
    environment_seed: int
    assignment_seed: int
    validity_rules: tuple[str, ...]
    metrics: tuple[str, ...]
    repository_commit: str


@dataclass(frozen=True)
class ExperimentPassport:
    experiment_id: str
    schema_version: str
    repository_commit: str
    environment_version: str
    manifest_hash: str
    task_hash: str
    policy_hash: str
    graph_hash: str
    assignment_hash: str
    treatment: str
    agent_mechanism_id: str
    model_configuration: Mapping[str, Any] | None
    model_call_provenance_hashes: tuple[str, ...]
    simulator_seed: int
    assignment_seed: int
    replicate_id: str
    validity_status: ValidityStatus
    event_ledger_hash: str
    final_state_hash: str
    metrics_hash: str
    runtime_metadata: Mapping[str, Any]
