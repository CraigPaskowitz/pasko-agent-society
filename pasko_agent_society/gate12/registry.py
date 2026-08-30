"""Frozen Gate 1.2 campaign and robustness-cell registry.

The production constructors in this module admit only preregistered Gate 1.2
identities.  Fixture constructors use a separate protocol namespace and roots
that cannot collide with any production draw.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Any, Mapping


PROTOCOL_ID = "PAS-GATE-1.2-ROBUSTNESS-V1"
PROTOCOL_NAMESPACE = "gate12-v1"
FIXTURE_PROTOCOL_NAMESPACE = "gate12-fixture-v1"

GATE11_RESULT_COMMIT = "43081df22f7b84ba16c2cf7e8edca28b45105ac4"
GATE11_RESULT_TAG = "gate1.1-result-v1"
GATE12_PREREGISTRATION_COMMIT = "c6e9506525d8e6088a6ecb6f417e375e040fd9aa"
GATE12_PREREGISTRATION_TAG = "gate1.2-prereg-v1"
GATE12_PREREGISTRATION_SHA256 = (
    "28e2240b159cad032dbf3d80f28a6d309f80fa11e5ebd9c3edd7d3bc230c8a17"
)

EXACT_REPLICATION_ROOT = 20260831
STANDARD_ROBUSTNESS_ROOT = 20260901
ALTERNATE_TOPOLOGY_ROOT = 20260902
PRODUCTION_ROOTS = frozenset(
    {EXACT_REPLICATION_ROOT, STANDARD_ROBUSTNESS_ROOT, ALTERNATE_TOPOLOGY_ROOT}
)

EXACT_CAMPAIGN_NAMESPACE = "exact-replication"
ROBUSTNESS_CAMPAIGN_NAMESPACE = "robustness"
ALTERNATE_CAMPAIGN_NAMESPACE = "alternate-topology"
FIXTURE_CAMPAIGN_NAMESPACE = "fixture"

EXACT_CAMPAIGN_ID = "gate12-replication-3000-v1"
ROBUSTNESS_CAMPAIGN_ID = "gate12-standard-robustness-1000-v1"
ALTERNATE_CAMPAIGN_ID = "gate12-alt-topology-1000-v1"
SUITE_CAMPAIGN_ID = "gate12-suite-v1"

PAIR_CHUNK_SCHEMA = "gate12-pair-chunk-v1"
CLUSTER_CHUNK_SCHEMA = "gate12-cluster-chunk-v1"
CONDITION_RESULT_SCHEMA = "gate12-condition-result-v1"
PAIR_RESULT_SCHEMA = "gate12-pair-result-v1"
CLUSTER_RESULT_SCHEMA = "gate12-cluster-result-v1"
CHECKPOINT_SCHEMA = "gate12-checkpoint-v1"
COMPLETION_SCHEMA = "gate12-completion-manifest-v1"
SUITE_COMPLETION_SCHEMA = "gate12-suite-completion-v1"
ANALYSIS_SCHEMA = "gate12-confirmatory-analysis-v1"
AUTHORIZATION_SCHEMA = "gate12-execution-authorization-v1"

T_CRITICAL_2999 = 1.960755319205
T_CRITICAL_999 = 1.962341461134
T_CRITICAL_FAMILY_999 = 2.844038318881
T_CRITICAL_EQUIV_2999 = 1.645361877311
ROBUSTNESS_FAMILY_SIZE = 11
PRACTICAL_MAGNITUDE_THRESHOLD = 0.05
EQUIVALENCE_MARGIN = 0.05


class Gate12ProtocolError(ValueError):
    """A Gate 1.2 identity or frozen scientific value is invalid."""


class Gate12InvariantError(RuntimeError):
    """A Gate 1.2 simulator or scientific invariant failed."""


@dataclass(frozen=True)
class RobustnessCell:
    cell_id: str
    dimension: str
    transmission_numerator: int = 1
    transmission_denominator: int = 4
    seed_count: int = 6
    propagation_rounds: int = 8
    accepted_swaps: int = 600
    seed_placement: str = "uniform"

    @property
    def primary_denominator(self) -> int:
        return 60 - self.seed_count


_ROBUSTNESS_CELLS = (
    RobustnessCell("p-1-of-8", "transmission", transmission_denominator=8),
    RobustnessCell("p-3-of-8", "transmission", 3, 8),
    RobustnessCell("seeds-3", "seed-count", seed_count=3),
    RobustnessCell("seeds-12", "seed-count", seed_count=12),
    RobustnessCell("rounds-4", "horizon", propagation_rounds=4),
    RobustnessCell("rounds-12", "horizon", propagation_rounds=12),
    RobustnessCell("swaps-360", "rewiring", accepted_swaps=360),
    RobustnessCell("swaps-840", "rewiring", accepted_swaps=840),
    RobustnessCell(
        "seed-placement-clustered",
        "seed-placement",
        seed_placement="clustered",
    ),
    RobustnessCell(
        "seed-placement-dispersed",
        "seed-placement",
        seed_placement="dispersed",
    ),
)
ROBUSTNESS_CELLS: Mapping[str, RobustnessCell] = MappingProxyType(
    {cell.cell_id: cell for cell in _ROBUSTNESS_CELLS}
)
ROBUSTNESS_CELL_IDS = tuple(cell.cell_id for cell in _ROBUSTNESS_CELLS)
ALTERNATE_TOPOLOGY_CELL_ID = "alternate-topology-3"
ALL_ROBUSTNESS_CONTRAST_IDS = ROBUSTNESS_CELL_IDS + (ALTERNATE_TOPOLOGY_CELL_ID,)


@dataclass(frozen=True)
class StandardConfig:
    protocol_id: str = PROTOCOL_ID
    protocol_namespace: str = PROTOCOL_NAMESPACE
    campaign_namespace: str = EXACT_CAMPAIGN_NAMESPACE
    campaign_id: str = EXACT_CAMPAIGN_ID
    cell_id: str | None = None
    root_seed: int = EXACT_REPLICATION_ROOT
    unit_count: int = 3000
    population_size: int = 60
    seed_count: int = 6
    degree: int = 4
    accepted_swaps: int = 600
    rewire_attempt_cap: int = 60_000
    transmission_numerator: int = 1
    transmission_denominator: int = 4
    propagation_rounds: int = 8
    message_delay_ticks: int = 1
    seed_placement: str = "uniform"

    @property
    def agent_ids(self) -> tuple[str, ...]:
        return tuple(f"agent-{index:03d}" for index in range(self.population_size))

    @property
    def primary_denominator(self) -> int:
        return self.population_size - self.seed_count

    @property
    def undirected_edge_count(self) -> int:
        return self.population_size * self.degree // 2

    @property
    def is_production(self) -> bool:
        return self.protocol_namespace == PROTOCOL_NAMESPACE

    def unit_id(self, index: int) -> str:
        if not 0 <= index < self.unit_count:
            raise Gate12ProtocolError("Unit index is outside the declared campaign")
        if self.campaign_namespace == EXACT_CAMPAIGN_NAMESPACE:
            return f"rep-pair-{index:04d}"
        if self.campaign_namespace == ROBUSTNESS_CAMPAIGN_NAMESPACE:
            if self.cell_id is None:
                raise Gate12ProtocolError("Robustness pair lacks a cell identity")
            return f"{self.cell_id}-pair-{index:04d}"
        return f"fixture-pair-{index:04d}"

    def rng_prefix(self, unit_id: str) -> tuple[object, ...]:
        validate_standard_unit_id(self, unit_id)
        if self.campaign_namespace == ROBUSTNESS_CAMPAIGN_NAMESPACE or (
            self.campaign_namespace == FIXTURE_CAMPAIGN_NAMESPACE and self.cell_id is not None
        ):
            return (
                self.protocol_namespace,
                self.campaign_namespace,
                self.cell_id,
                unit_id,
            )
        return (self.protocol_namespace, self.campaign_namespace, unit_id)


@dataclass(frozen=True)
class AlternateTopologyConfig:
    protocol_id: str = PROTOCOL_ID
    protocol_namespace: str = PROTOCOL_NAMESPACE
    campaign_namespace: str = ALTERNATE_CAMPAIGN_NAMESPACE
    campaign_id: str = ALTERNATE_CAMPAIGN_ID
    cell_id: str = ALTERNATE_TOPOLOGY_CELL_ID
    root_seed: int = ALTERNATE_TOPOLOGY_ROOT
    unit_count: int = 1000
    population_size: int = 60
    seed_count: int = 6
    degree: int = 4
    accepted_swaps: int = 600
    rewire_attempt_cap: int = 60_000
    transmission_numerator: int = 1
    transmission_denominator: int = 4
    propagation_rounds: int = 8
    message_delay_ticks: int = 1
    realization_count: int = 3

    @property
    def agent_ids(self) -> tuple[str, ...]:
        return tuple(f"agent-{index:03d}" for index in range(self.population_size))

    @property
    def primary_denominator(self) -> int:
        return self.population_size - self.seed_count

    @property
    def undirected_edge_count(self) -> int:
        return self.population_size * self.degree // 2

    @property
    def is_production(self) -> bool:
        return self.protocol_namespace == PROTOCOL_NAMESPACE

    def unit_id(self, index: int) -> str:
        if not 0 <= index < self.unit_count:
            raise Gate12ProtocolError("Cluster index is outside the declared campaign")
        prefix = "alt-cluster" if self.is_production else "fixture-cluster"
        return f"{prefix}-{index:04d}"

    def rng_prefix(self, unit_id: str) -> tuple[object, ...]:
        validate_alternate_unit_id(self, unit_id)
        return (self.protocol_namespace, self.campaign_namespace, unit_id)


def exact_replication_config() -> StandardConfig:
    config = StandardConfig()
    validate_standard_config(config)
    return config


def robustness_config(cell_id: str) -> StandardConfig:
    try:
        cell = ROBUSTNESS_CELLS[cell_id]
    except KeyError as exc:
        raise Gate12ProtocolError("Cell is outside the frozen robustness registry") from exc
    config = StandardConfig(
        campaign_namespace=ROBUSTNESS_CAMPAIGN_NAMESPACE,
        campaign_id=ROBUSTNESS_CAMPAIGN_ID,
        cell_id=cell.cell_id,
        root_seed=STANDARD_ROBUSTNESS_ROOT,
        unit_count=1000,
        seed_count=cell.seed_count,
        accepted_swaps=cell.accepted_swaps,
        transmission_numerator=cell.transmission_numerator,
        transmission_denominator=cell.transmission_denominator,
        propagation_rounds=cell.propagation_rounds,
        seed_placement=cell.seed_placement,
    )
    validate_standard_config(config)
    return config


def alternate_topology_config() -> AlternateTopologyConfig:
    config = AlternateTopologyConfig()
    validate_alternate_config(config)
    return config


def fixture_standard_config(**changes: Any) -> StandardConfig:
    defaults: dict[str, Any] = {
        "protocol_namespace": FIXTURE_PROTOCOL_NAMESPACE,
        "campaign_namespace": FIXTURE_CAMPAIGN_NAMESPACE,
        "campaign_id": "gate12-fixture-pairs-v1",
        "cell_id": "fixture-cell",
        "root_seed": 912_771,
        "unit_count": 2,
        "population_size": 8,
        "seed_count": 2,
        "degree": 2,
        "accepted_swaps": 4,
        "rewire_attempt_cap": 2_000,
        "propagation_rounds": 3,
    }
    defaults.update(changes)
    config = replace(StandardConfig(), **defaults)
    validate_standard_config(config)
    return config


def fixture_alternate_config(**changes: Any) -> AlternateTopologyConfig:
    defaults: dict[str, Any] = {
        "protocol_namespace": FIXTURE_PROTOCOL_NAMESPACE,
        "campaign_namespace": FIXTURE_CAMPAIGN_NAMESPACE,
        "campaign_id": "gate12-fixture-clusters-v1",
        "cell_id": "fixture-alternate-topology",
        "root_seed": 912_772,
        "unit_count": 2,
        "population_size": 8,
        "seed_count": 2,
        "degree": 2,
        "accepted_swaps": 4,
        "rewire_attempt_cap": 2_000,
        "propagation_rounds": 3,
    }
    defaults.update(changes)
    config = replace(AlternateTopologyConfig(), **defaults)
    validate_alternate_config(config)
    return config


def _validate_common(config: StandardConfig | AlternateTopologyConfig) -> None:
    if config.protocol_id != PROTOCOL_ID:
        raise Gate12ProtocolError("Unknown Gate 1.2 protocol identity")
    if config.population_size < 4 or config.population_size > 999:
        raise Gate12ProtocolError("Population size is outside the bounded simulator range")
    if not 0 < config.seed_count < config.population_size:
        raise Gate12ProtocolError("Seed count must leave an unseeded population")
    if config.degree <= 0 or config.degree % 2 or config.degree >= config.population_size:
        raise Gate12ProtocolError("Degree must be positive, even, and below population size")
    if config.population_size * config.degree % 2:
        raise Gate12ProtocolError("Population-degree product must be even")
    if config.unit_count <= 0 or config.accepted_swaps < 0:
        raise Gate12ProtocolError("Unit or accepted-swap count is invalid")
    if config.rewire_attempt_cap < config.accepted_swaps:
        raise Gate12ProtocolError("Rewire attempt cap cannot be below accepted swaps")
    if config.transmission_denominator <= 0 or not (
        0 <= config.transmission_numerator <= config.transmission_denominator
    ):
        raise Gate12ProtocolError("Transmission probability is invalid")
    if config.propagation_rounds <= 0 or config.message_delay_ticks != 1:
        raise Gate12ProtocolError("Propagation horizon or message delay is invalid")
    if not config.is_production:
        if config.protocol_namespace != FIXTURE_PROTOCOL_NAMESPACE:
            raise Gate12ProtocolError("Nonproduction config lacks the fixture protocol namespace")
        if config.campaign_namespace != FIXTURE_CAMPAIGN_NAMESPACE:
            raise Gate12ProtocolError("Nonproduction config lacks the fixture campaign namespace")
        if config.root_seed in PRODUCTION_ROOTS:
            raise Gate12ProtocolError("Fixture root collides with a production root")


def validate_standard_config(config: StandardConfig) -> None:
    _validate_common(config)
    if config.seed_placement not in {"uniform", "clustered", "dispersed"}:
        raise Gate12ProtocolError("Unknown seed-placement construction")
    if not config.is_production:
        return
    if config.campaign_namespace == EXACT_CAMPAIGN_NAMESPACE:
        if config != StandardConfig():
            raise Gate12ProtocolError("Exact replication differs from the frozen protocol")
        return
    if config.campaign_namespace != ROBUSTNESS_CAMPAIGN_NAMESPACE:
        raise Gate12ProtocolError("Unknown production campaign namespace")
    expected = robustness_config_unchecked(config.cell_id)
    if config != expected:
        raise Gate12ProtocolError("Robustness cell differs from the frozen registry")


def robustness_config_unchecked(cell_id: str | None) -> StandardConfig:
    if cell_id not in ROBUSTNESS_CELLS:
        raise Gate12ProtocolError("Cell is outside the frozen robustness registry")
    cell = ROBUSTNESS_CELLS[str(cell_id)]
    return StandardConfig(
        campaign_namespace=ROBUSTNESS_CAMPAIGN_NAMESPACE,
        campaign_id=ROBUSTNESS_CAMPAIGN_ID,
        cell_id=cell.cell_id,
        root_seed=STANDARD_ROBUSTNESS_ROOT,
        unit_count=1000,
        seed_count=cell.seed_count,
        accepted_swaps=cell.accepted_swaps,
        transmission_numerator=cell.transmission_numerator,
        transmission_denominator=cell.transmission_denominator,
        propagation_rounds=cell.propagation_rounds,
        seed_placement=cell.seed_placement,
    )


def validate_alternate_config(config: AlternateTopologyConfig) -> None:
    _validate_common(config)
    if not config.is_production:
        if config.realization_count <= 0:
            raise Gate12ProtocolError("Fixture must retain at least one realization")
        return
    if config != AlternateTopologyConfig():
        raise Gate12ProtocolError("Alternate-topology config differs from the frozen protocol")


def validate_standard_unit_id(config: StandardConfig, unit_id: str) -> None:
    if not any(unit_id == config.unit_id(index) for index in _candidate_indices(unit_id)):
        raise Gate12ProtocolError("Pair ID is outside the declared campaign")


def validate_alternate_unit_id(config: AlternateTopologyConfig, unit_id: str) -> None:
    if not any(unit_id == config.unit_id(index) for index in _candidate_indices(unit_id)):
        raise Gate12ProtocolError("Cluster ID is outside the declared campaign")


def _candidate_indices(unit_id: str) -> tuple[int, ...]:
    suffix = unit_id.rsplit("-", 1)[-1]
    if len(suffix) != 4 or not suffix.isdigit():
        return ()
    return (int(suffix),)


def standard_config_mapping(config: StandardConfig) -> dict[str, Any]:
    return {
        "campaign_id": config.campaign_id,
        "campaign_namespace": config.campaign_namespace,
        "cell_id": config.cell_id,
        "root_seed": config.root_seed,
        "unit_count": config.unit_count,
        "population_size": config.population_size,
        "seed_count": config.seed_count,
        "primary_denominator": config.primary_denominator,
        "degree": config.degree,
        "undirected_edges": config.undirected_edge_count,
        "accepted_swaps": config.accepted_swaps,
        "rewire_attempt_cap": config.rewire_attempt_cap,
        "transmission": {
            "numerator": config.transmission_numerator,
            "denominator": config.transmission_denominator,
        },
        "propagation_rounds": config.propagation_rounds,
        "message_delay_ticks": config.message_delay_ticks,
        "seed_placement": config.seed_placement,
        "expected_condition_runs": config.unit_count * 2,
    }


def alternate_config_mapping(config: AlternateTopologyConfig) -> dict[str, Any]:
    return {
        "campaign_id": config.campaign_id,
        "campaign_namespace": config.campaign_namespace,
        "cell_id": config.cell_id,
        "root_seed": config.root_seed,
        "unit_count": config.unit_count,
        "population_size": config.population_size,
        "seed_count": config.seed_count,
        "primary_denominator": config.primary_denominator,
        "degree": config.degree,
        "undirected_edges": config.undirected_edge_count,
        "accepted_swaps": config.accepted_swaps,
        "rewire_attempt_cap": config.rewire_attempt_cap,
        "transmission": {
            "numerator": config.transmission_numerator,
            "denominator": config.transmission_denominator,
        },
        "propagation_rounds": config.propagation_rounds,
        "message_delay_ticks": config.message_delay_ticks,
        "seed_placement": "uniform",
        "rewired_realizations_per_cluster": config.realization_count,
        "expected_condition_runs": config.unit_count * (1 + config.realization_count),
    }
