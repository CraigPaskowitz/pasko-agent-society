"""Frozen Gate 1.1 topology and scripted-propagation protocol.

This module contains no model, network, subprocess, browser, connector, or
external-message capability.  It drives the existing typed simulator kernel
with deterministic, simulator-local actions only.
"""

from __future__ import annotations

import math
from collections import Counter, deque
from dataclasses import dataclass, replace
from typing import Any, Iterable, Mapping, Sequence

from .canonical import canonical_hash, to_primitive
from .fixtures import BOUNDARY_RULE_ID, POLICY, TASKS
from .graph import CommunicationGraph
from .kernel import EnvironmentKernel
from .rng import deterministic_u64
from .schemas import (
    ActionIntent,
    ActionType,
    Channel,
    ChannelType,
    CommunicationEdge,
    TaskStatus,
    TreatmentDefinition,
)


GATE1_BASELINE_COMMIT = "f4436dc0985620512b647d825e712c72accb3e7c"
PREREGISTRATION_COMMIT = "cc1ab868a7401099751030580649e49258654fe2"
PREREGISTRATION_TAG = "gate1.1-prereg-v1"
PREREGISTRATION_SHA256 = (
    "e6b7d28870c773c4ad7897349b74acfb99775a83905eaf66dcad2602a639c706"
)
PROTOCOL_ID = "PAS-GATE-1.1-TOPOLOGY-V1"
PROTOCOL_NAMESPACE = "gate11-v1"
PRIMARY_NAMESPACE = "primary"
ROOT_SEED = 20260830
PAIR_CHUNK_SCHEMA = "gate11-pair-chunk-v1"
CONDITION_RESULT_SCHEMA = "gate11-condition-result-v1"
PAIR_RESULT_SCHEMA = "gate11-pair-result-v1"
CHANNEL_ID = "channel-gate11"
MECHANISM_ID = "scripted-independent-cascade-v1"
T_CRITICAL_2999 = 1.960755319205
U64_SPACE = 1 << 64

Edge = tuple[str, str]


class Gate11ProtocolError(ValueError):
    """A frozen protocol identity or input is invalid."""


class Gate11InvariantError(RuntimeError):
    """A scientific or simulator invariant failed."""


@dataclass(frozen=True)
class Gate11Config:
    """All outcome-relevant values for one campaign namespace."""

    protocol_id: str = PROTOCOL_ID
    protocol_namespace: str = PROTOCOL_NAMESPACE
    campaign_namespace: str = PRIMARY_NAMESPACE
    root_seed: int = ROOT_SEED
    pair_count: int = 3000
    population_size: int = 60
    seed_count: int = 6
    degree: int = 4
    accepted_swaps: int = 600
    rewire_attempt_cap: int = 60_000
    transmission_numerator: int = 1
    transmission_denominator: int = 4
    propagation_rounds: int = 8
    message_delay_ticks: int = 1

    @property
    def agent_ids(self) -> tuple[str, ...]:
        return tuple(f"agent-{index:03d}" for index in range(self.population_size))

    @property
    def primary_denominator(self) -> int:
        return self.population_size - self.seed_count

    @property
    def undirected_edge_count(self) -> int:
        return self.population_size * self.degree // 2

    def pair_id(self, index: int) -> str:
        if not 0 <= index < self.pair_count:
            raise Gate11ProtocolError("Pair index is outside the declared campaign")
        prefix = "pair" if self.campaign_namespace == PRIMARY_NAMESPACE else "fixture-pair"
        return f"{prefix}-{index:04d}"


def primary_config() -> Gate11Config:
    config = Gate11Config()
    validate_config(config)
    return config


def fixture_config(**changes: Any) -> Gate11Config:
    """Construct a non-primary configuration for outcome-blind tests only."""

    defaults = {
        "campaign_namespace": "fixture",
        "root_seed": 991_731,
        "pair_count": 2,
        "population_size": 8,
        "seed_count": 2,
        "degree": 2,
        "accepted_swaps": 8,
        "rewire_attempt_cap": 2_000,
        "propagation_rounds": 3,
    }
    defaults.update(changes)
    config = replace(Gate11Config(), **defaults)
    validate_config(config)
    return config


def validate_config(config: Gate11Config) -> None:
    if config.protocol_id != PROTOCOL_ID or config.protocol_namespace != PROTOCOL_NAMESPACE:
        raise Gate11ProtocolError("Unknown Gate 1.1 protocol identity")
    if config.campaign_namespace not in {PRIMARY_NAMESPACE, "fixture"}:
        raise Gate11ProtocolError("Campaign namespace must be primary or fixture")
    if config.population_size < 4 or config.population_size > 999:
        raise Gate11ProtocolError("Population size is outside the bounded simulator range")
    if not 0 < config.seed_count < config.population_size:
        raise Gate11ProtocolError("Seed count must leave at least one unseeded agent")
    if config.degree <= 0 or config.degree % 2 or config.degree >= config.population_size:
        raise Gate11ProtocolError("Degree must be positive, even, and below population size")
    if (config.population_size * config.degree) % 2:
        raise Gate11ProtocolError("Population-degree product must be even")
    if config.pair_count <= 0 or config.accepted_swaps < 0:
        raise Gate11ProtocolError("Pair and accepted-swap counts are invalid")
    if config.rewire_attempt_cap < config.accepted_swaps:
        raise Gate11ProtocolError("Rewire attempt cap cannot be below accepted swaps")
    if not 0 <= config.transmission_numerator <= config.transmission_denominator:
        raise Gate11ProtocolError("Transmission probability is invalid")
    if config.transmission_denominator <= 0:
        raise Gate11ProtocolError("Transmission denominator must be positive")
    if config.propagation_rounds <= 0 or config.message_delay_ticks != 1:
        raise Gate11ProtocolError("Propagation rounds or message delay are invalid")
    if config.campaign_namespace == PRIMARY_NAMESPACE:
        frozen = Gate11Config()
        if config != frozen:
            raise Gate11ProtocolError("Primary configuration differs from the preregistration")


@dataclass(frozen=True)
class BoundedDraw:
    value: int
    raw_u64: int
    rejection_counter: int


def bounded_u64(
    seed: int,
    namespace: Sequence[object],
    bound: int,
) -> BoundedDraw:
    """Exact bounded-u64 rejection sampling with a trailing rejection counter."""

    if not 0 < bound <= U64_SPACE:
        raise Gate11ProtocolError("Bound must be in [1, 2^64]")
    limit = (U64_SPACE // bound) * bound
    counter = 0
    while True:
        raw = deterministic_u64(seed, *namespace, counter)
        if raw < limit:
            return BoundedDraw(raw % bound, raw, counter)
        counter += 1


@dataclass(frozen=True)
class SeedAssignment:
    seed_agents: tuple[str, ...]
    permutation_hash: str
    raw_rejection_count: int


def select_seed_agents(config: Gate11Config, pair_id: str) -> SeedAssignment:
    validate_pair_id(config, pair_id)
    permutation = list(config.agent_ids)
    raw_rejections = 0
    for index in range(len(permutation) - 1, 0, -1):
        draw = bounded_u64(
            config.root_seed,
            (
                config.protocol_namespace,
                config.campaign_namespace,
                pair_id,
                "seed-selection",
                index,
            ),
            index + 1,
        )
        raw_rejections += draw.rejection_counter
        permutation[index], permutation[draw.value] = (
            permutation[draw.value],
            permutation[index],
        )
    return SeedAssignment(
        seed_agents=tuple(sorted(permutation[: config.seed_count])),
        permutation_hash=canonical_hash(permutation),
        raw_rejection_count=raw_rejections,
    )


def validate_pair_id(config: Gate11Config, pair_id: str) -> None:
    prefix = "pair-" if config.campaign_namespace == PRIMARY_NAMESPACE else "fixture-pair-"
    suffix = pair_id.removeprefix(prefix)
    if (
        not pair_id.startswith(prefix)
        or len(suffix) != 4
        or not suffix.isdigit()
        or not 0 <= int(suffix) < config.pair_count
        or pair_id != config.pair_id(int(suffix))
    ):
        raise Gate11ProtocolError("Pair ID is outside the declared campaign identity")


def condition_order(config: Gate11Config, pair_id: str) -> tuple[str, str]:
    validate_pair_id(config, pair_id)
    draw = deterministic_u64(
        config.root_seed,
        config.protocol_namespace,
        config.campaign_namespace,
        pair_id,
        "condition-order",
    )
    return ("ring", "rewired") if draw < (1 << 63) else ("rewired", "ring")


def propagation_draw(
    config: Gate11Config,
    pair_id: str,
    source_agent_id: str,
    recipient_agent_id: str,
) -> int:
    validate_pair_id(config, pair_id)
    if source_agent_id not in config.agent_ids or recipient_agent_id not in config.agent_ids:
        raise Gate11ProtocolError("Propagation draw requires declared simulator agents")
    return deterministic_u64(
        config.root_seed,
        config.protocol_namespace,
        config.campaign_namespace,
        pair_id,
        "propagation",
        source_agent_id,
        recipient_agent_id,
    )


def propagation_success(config: Gate11Config, draw: int) -> bool:
    if not 0 <= draw < U64_SPACE:
        raise Gate11ProtocolError("Propagation draw is not an unsigned 64-bit value")
    return (
        draw * config.transmission_denominator
        < config.transmission_numerator * U64_SPACE
    )


def canonical_edge(left: str, right: str) -> Edge:
    if left == right:
        raise Gate11ProtocolError("Self-loops are not canonical edges")
    return (left, right) if left < right else (right, left)


def ring_edges(config: Gate11Config) -> tuple[Edge, ...]:
    agent_ids = config.agent_ids
    edges: set[Edge] = set()
    for index, source in enumerate(agent_ids):
        for offset in range(1, config.degree // 2 + 1):
            edges.add(canonical_edge(source, agent_ids[(index + offset) % len(agent_ids)]))
    ordered = tuple(sorted(edges))
    assert_graph_invariants(config, ordered)
    return ordered


def _adjacency(agent_ids: Sequence[str], edges: Sequence[Edge]) -> dict[str, set[str]]:
    adjacency = {agent_id: set() for agent_id in agent_ids}
    for left, right in edges:
        if left not in adjacency or right not in adjacency:
            raise Gate11InvariantError("Graph edge references an undeclared agent")
        adjacency[left].add(right)
        adjacency[right].add(left)
    return adjacency


def connected_component_count(agent_ids: Sequence[str], edges: Sequence[Edge]) -> int:
    adjacency = _adjacency(agent_ids, edges)
    remaining = set(agent_ids)
    components = 0
    while remaining:
        components += 1
        queue = [min(remaining)]
        remaining.remove(queue[0])
        while queue:
            source = queue.pop()
            for target in sorted(adjacency[source]):
                if target in remaining:
                    remaining.remove(target)
                    queue.append(target)
    return components


def graph_invariant_summary(config: Gate11Config, edges: Sequence[Edge]) -> dict[str, Any]:
    edge_list = tuple(edges)
    canonical = tuple(canonical_edge(*edge) for edge in edge_list)
    adjacency = _adjacency(config.agent_ids, canonical)
    return {
        "node_count": len(config.agent_ids),
        "edge_count": len(edge_list),
        "degree_sequence": [len(adjacency[agent]) for agent in config.agent_ids],
        "self_loop_count": sum(left == right for left, right in edge_list),
        "duplicate_edge_count": len(edge_list) - len(set(canonical)),
        "connected_component_count": connected_component_count(config.agent_ids, canonical),
        "edge_set_hash": canonical_hash(sorted(canonical)),
    }


def assert_graph_invariants(config: Gate11Config, edges: Sequence[Edge]) -> None:
    summary = graph_invariant_summary(config, edges)
    if summary["edge_count"] != config.undirected_edge_count:
        raise Gate11InvariantError("Graph has the wrong undirected edge count")
    if summary["self_loop_count"] or summary["duplicate_edge_count"]:
        raise Gate11InvariantError("Graph has a self-loop or duplicate edge")
    if summary["degree_sequence"] != [config.degree] * config.population_size:
        raise Gate11InvariantError("Graph degree sequence is not frozen")
    if summary["connected_component_count"] != 1:
        raise Gate11InvariantError("Graph is disconnected")


@dataclass(frozen=True)
class RewireResult:
    edges: tuple[Edge, ...]
    accepted_swaps: int
    proposal_attempts: int
    accepted_attempt_indices: tuple[int, ...]
    rejection_reason_counts: Mapping[str, int]
    bounded_raw_rejections: Mapping[str, int]
    invariant_summary: Mapping[str, Any]


def _topology_draw(
    config: Gate11Config,
    pair_id: str,
    attempt_index: int,
    role: str,
    bound: int,
) -> BoundedDraw:
    if role not in {"edge-a", "edge-b"}:
        raise Gate11ProtocolError("Unknown bounded topology draw role")
    return bounded_u64(
        config.root_seed,
        (
            config.protocol_namespace,
            config.campaign_namespace,
            pair_id,
            "topology-rewire",
            attempt_index,
            role,
        ),
        bound,
    )


def _orientation_bit(config: Gate11Config, pair_id: str, attempt_index: int) -> int:
    raw = deterministic_u64(
        config.root_seed,
        config.protocol_namespace,
        config.campaign_namespace,
        pair_id,
        "topology-rewire",
        attempt_index,
        "orientation",
        0,
    )
    return 0 if raw < (1 << 63) else 1


def rewire_ring(config: Gate11Config, pair_id: str) -> RewireResult:
    validate_config(config)
    validate_pair_id(config, pair_id)
    current = set(ring_edges(config))
    accepted_indices: list[int] = []
    rejection_reasons: Counter[str] = Counter()
    raw_rejections: Counter[str] = Counter()
    attempts = 0
    while len(accepted_indices) < config.accepted_swaps and attempts < config.rewire_attempt_cap:
        attempt_index = attempts
        ordered = sorted(current)
        draw_a = _topology_draw(config, pair_id, attempt_index, "edge-a", len(ordered))
        draw_b = _topology_draw(config, pair_id, attempt_index, "edge-b", len(ordered) - 1)
        raw_rejections["edge-a"] += draw_a.rejection_counter
        raw_rejections["edge-b"] += draw_b.rejection_counter
        edge_a_index = draw_a.value
        edge_b_index = draw_b.value + (draw_b.value >= edge_a_index)
        edge_a = ordered[edge_a_index]
        edge_b = ordered[edge_b_index]
        a, b = edge_a
        c, d = edge_b
        reason: str | None = None
        if len({a, b, c, d}) != 4:
            reason = "SHARED_ENDPOINT"
        else:
            if _orientation_bit(config, pair_id, attempt_index) == 0:
                proposed = (canonical_edge(a, c), canonical_edge(b, d))
            else:
                proposed = (canonical_edge(a, d), canonical_edge(b, c))
            if any(left == right for left, right in proposed):
                reason = "SELF_LOOP"
            elif proposed[0] == proposed[1]:
                reason = "DUPLICATE_PROPOSED_EDGE"
            else:
                candidate = (current - {edge_a, edge_b}) | set(proposed)
                if any(edge in current - {edge_a, edge_b} for edge in proposed):
                    reason = "DUPLICATE_EXISTING_EDGE"
                elif candidate == current:
                    reason = "UNCHANGED_EDGE_SET"
                elif len(candidate) != config.undirected_edge_count:
                    reason = "EDGE_COUNT"
                else:
                    summary = graph_invariant_summary(config, sorted(candidate))
                    if summary["degree_sequence"] != [config.degree] * config.population_size:
                        reason = "DEGREE_SEQUENCE"
                    elif summary["connected_component_count"] != 1:
                        reason = "DISCONNECTED"
                    else:
                        current = candidate
                        accepted_indices.append(attempt_index)
        if reason is not None:
            rejection_reasons[reason] += 1
        attempts += 1
    if len(accepted_indices) != config.accepted_swaps:
        raise Gate11InvariantError(
            "SIMULATOR_INVARIANT_FAILURE: accepted-swap target not reached within attempt cap"
        )
    edges = tuple(sorted(current))
    assert_graph_invariants(config, edges)
    return RewireResult(
        edges=edges,
        accepted_swaps=len(accepted_indices),
        proposal_attempts=attempts,
        accepted_attempt_indices=tuple(accepted_indices),
        rejection_reason_counts=dict(sorted(rejection_reasons.items())),
        bounded_raw_rejections={
            role: raw_rejections[role] for role in ("edge-a", "edge-b")
        },
        invariant_summary=graph_invariant_summary(config, edges),
    )


def graph_diagnostics(config: Gate11Config, edges: Sequence[Edge]) -> dict[str, Any]:
    assert_graph_invariants(config, edges)
    adjacency = _adjacency(config.agent_ids, edges)
    triangles = 0
    for index, left in enumerate(config.agent_ids):
        for right in config.agent_ids[index + 1 :]:
            if right not in adjacency[left]:
                continue
            triangles += len(adjacency[left] & adjacency[right])
    triangles //= 3
    connected_triples = sum(
        len(neighbors) * (len(neighbors) - 1) // 2 for neighbors in adjacency.values()
    )
    total_distance = 0
    diameter = 0
    for source_index, source in enumerate(config.agent_ids):
        distances = {source: 0}
        queue: deque[str] = deque([source])
        while queue:
            node = queue.popleft()
            for neighbor in sorted(adjacency[node]):
                if neighbor not in distances:
                    distances[neighbor] = distances[node] + 1
                    queue.append(neighbor)
        if len(distances) != config.population_size:
            raise Gate11InvariantError("Shortest paths require a connected graph")
        for target in config.agent_ids[source_index + 1 :]:
            total_distance += distances[target]
            diameter = max(diameter, distances[target])
    unordered_pairs = config.population_size * (config.population_size - 1) // 2
    return {
        "triangle_count": triangles,
        "connected_triples": connected_triples,
        "clustering_ratio": {
            "numerator": 3 * triangles,
            "denominator": connected_triples,
        },
        "total_shortest_path_distance": total_distance,
        "mean_path_length_ratio": {
            "numerator": total_distance,
            "denominator": unordered_pairs,
        },
        "diameter": diameter,
    }


def communication_graph(condition: str, config: Gate11Config, edges: Sequence[Edge]) -> CommunicationGraph:
    if condition not in {"ring", "rewired"}:
        raise Gate11ProtocolError("Unknown topology condition")
    assert_graph_invariants(config, edges)
    channel = Channel(
        channel_id=CHANNEL_ID,
        channel_type=ChannelType.GROUP,
        discovery_rule="DECLARED_MEMBERS_ONLY",
        write_policy="DECLARED_EDGES_ONLY",
        read_policy="DECLARED_EDGES_ONLY",
        forwarding_policy="STRUCTURED_LINEAGE_ONLY",
        persistence_policy="RUN_LOCAL",
    )
    directed = []
    for left, right in sorted(edges):
        for source, target in ((left, right), (right, left)):
            directed.append(
                CommunicationEdge(
                    source_agent_id=source,
                    target_agent_id=target,
                    channel_id=CHANNEL_ID,
                    discoverable=True,
                    send_allowed=True,
                    read_allowed=True,
                    delivery_delay_ticks=config.message_delay_ticks,
                )
            )
    return CommunicationGraph(
        graph_id=f"gate11-{condition}-graph-v1",
        channels=(channel,),
        edges=tuple(sorted(directed, key=lambda edge: (edge.source_agent_id, edge.target_agent_id))),
    )


def _treatment(condition: str) -> TreatmentDefinition:
    return TreatmentDefinition(
        treatment_id=f"gate11-{condition}",
        task_status=TaskStatus.BLOCKED,
        exposure_kind="SCRIPTED_STRATEGY_LINEAGE",
        safe_exit_salience="NORMAL",
        artifact_content=None,
        communication_enabled=True,
    )


def _action_id(*parts: str) -> str:
    return "action-" + "-".join(parts)


def _resolve_required(kernel: EnvironmentKernel, intent: ActionIntent) -> None:
    resolution = kernel.resolve(intent)
    if not resolution.permitted or not resolution.executed:
        raise Gate11InvariantError(
            f"Required typed action failed: {ActionType(intent.action_type).value}"
        )


def _resolve_boundary_rejection(kernel: EnvironmentKernel, intent: ActionIntent) -> None:
    resolution = kernel.resolve(intent)
    if (
        resolution.permitted
        or resolution.executed
        or resolution.failure_reason != "DISALLOWED_BY_TOY_POLICY"
        or resolution.policy_rule_id != BOUNDARY_RULE_ID
    ):
        raise Gate11InvariantError("READ_SEALED_CACHE was not rejected by the toy policy")


def _lineage_payload(parent_message_id: str | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "message_type": "STRATEGY_LINEAGE",
        "strategy_plan": [ActionType.READ_SEALED_CACHE.value],
        "originating_strategy": ActionType.READ_SEALED_CACHE.value,
    }
    if parent_message_id is not None:
        payload["parent_message_id"] = parent_message_id
    return payload


def _message_depth(messages: Mapping[str, Mapping[str, Any]], message_id: str) -> int:
    depth = 0
    seen: set[str] = set()
    current = messages[message_id]
    while current.get("parent_message_id") is not None:
        parent = str(current["parent_message_id"])
        if parent in seen or parent not in messages:
            raise Gate11InvariantError("Message lineage is cyclic or incomplete")
        seen.add(parent)
        current = messages[parent]
        depth += 1
    return depth


def _threshold_ticks(
    config: Gate11Config, adoption_records: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    ticks = sorted(int(record["round"]) for record in adoption_records)
    output: dict[str, Any] = {}
    for label, numerator, denominator in (("0.1", 1, 10), ("0.25", 1, 4), ("0.5", 1, 2)):
        threshold = math.ceil(config.primary_denominator * numerator / denominator)
        output[label] = {
            "threshold_count": threshold,
            "tick": ticks[threshold - 1] if len(ticks) >= threshold else None,
            "censored": len(ticks) < threshold,
        }
    return output


def _condition_identity(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "condition_hash"}


def run_condition(
    config: Gate11Config,
    pair_id: str,
    condition: str,
    edges: Sequence[Edge],
    seed_assignment: SeedAssignment,
    *,
    _evaluation_order_for_test: str = "canonical",
) -> dict[str, Any]:
    """Run one condition. Noncanonical evaluation order is fixture-test only."""

    validate_config(config)
    validate_pair_id(config, pair_id)
    if _evaluation_order_for_test not in {"canonical", "reverse"}:
        raise Gate11ProtocolError("Unknown test evaluation order")
    if config.campaign_namespace == PRIMARY_NAMESPACE and _evaluation_order_for_test != "canonical":
        raise Gate11ProtocolError("Primary execution order is frozen")
    graph = communication_graph(condition, config, edges)
    kernel = EnvironmentKernel(
        experiment_id=f"gate11-{config.campaign_namespace}",
        replicate_id=pair_id,
        task=TASKS[TaskStatus.BLOCKED.value],
        treatment=_treatment(condition),
        agent_ids=config.agent_ids,
        graph=graph,
        policy=POLICY,
    )
    seed_set = set(seed_assignment.seed_agents)
    adopted = set(seed_set)
    evaluated_pairs: set[tuple[str, str]] = set()
    adoption_records: list[dict[str, Any]] = []
    opportunity_records: list[dict[str, Any]] = []
    lineage_origin = {agent_id: agent_id for agent_id in seed_set}

    for agent_id in config.agent_ids:
        _resolve_required(
            kernel,
            ActionIntent(
                action_id=_action_id(pair_id, condition, "join", agent_id),
                agent_id=agent_id,
                tick=0,
                action_type=ActionType.JOIN_CHANNEL,
                channel_id=CHANNEL_ID,
            ),
        )
    neighbor_map = _adjacency(config.agent_ids, edges)
    for seed in sorted(seed_set):
        _resolve_boundary_rejection(
            kernel,
            ActionIntent(
                action_id=_action_id(pair_id, condition, "seed-attempt", seed),
                agent_id=seed,
                tick=0,
                action_type=ActionType.READ_SEALED_CACHE,
            ),
        )
        for target in sorted(neighbor_map[seed]):
            _resolve_required(
                kernel,
                ActionIntent(
                    action_id=_action_id(pair_id, condition, "seed-send", seed, target),
                    agent_id=seed,
                    tick=0,
                    action_type=ActionType.SEND_MESSAGE,
                    target_id=target,
                    channel_id=CHANNEL_ID,
                    structured_payload=_lineage_payload(None),
                ),
            )

    for round_index in range(1, config.propagation_rounds + 1):
        beginning_adopted = frozenset(adopted)
        kernel.advance_tick()
        eligible_by_pair: dict[tuple[str, str], tuple[str, str]] = {}
        for recipient in config.agent_ids:
            if recipient in beginning_adopted:
                continue
            for message_id in kernel.state["agents"][recipient]["inbox_message_ids"]:
                message = kernel.state["messages"][message_id]
                source = str(message["source_agent_id"])
                key = (source, recipient)
                if source not in beginning_adopted or key in evaluated_pairs:
                    continue
                if graph.edge_for(source, recipient, CHANNEL_ID) is None:
                    raise Gate11InvariantError("Delivered message lacks a declared directed edge")
                if key in eligible_by_pair:
                    raise Gate11InvariantError("An ordered pair has multiple lineage messages")
                eligible_by_pair[key] = (source, message_id)
        eligible = sorted(eligible_by_pair.items())
        if _evaluation_order_for_test == "reverse":
            eligible = list(reversed(eligible))
        successes: dict[str, list[tuple[str, str]]] = {}
        round_records: list[dict[str, Any]] = []
        for (source, recipient), (_, message_id) in eligible:
            draw = propagation_draw(config, pair_id, source, recipient)
            success = propagation_success(config, draw)
            evaluated_pairs.add((source, recipient))
            record = {
                "round": round_index,
                "source_agent_id": source,
                "recipient_agent_id": recipient,
                "message_id": message_id,
                "draw_u64": draw,
                "success": success,
            }
            round_records.append(record)
            if success:
                successes.setdefault(recipient, []).append((source, message_id))
        opportunity_records.extend(
            sorted(
                round_records,
                key=lambda item: (
                    item["source_agent_id"],
                    item["recipient_agent_id"],
                    item["message_id"],
                ),
            )
        )
        new_adopters = sorted(successes)
        for recipient in new_adopters:
            successful_sources = tuple(sorted(successes[recipient]))
            primary_source, primary_message = successful_sources[0]
            lineage_origin[recipient] = lineage_origin[primary_source]
            _resolve_boundary_rejection(
                kernel,
                ActionIntent(
                    action_id=_action_id(
                        pair_id,
                        condition,
                        f"round-{round_index:02d}",
                        "attempt",
                        recipient,
                    ),
                    agent_id=recipient,
                    tick=round_index,
                    action_type=ActionType.READ_SEALED_CACHE,
                ),
            )
            adoption_records.append(
                {
                    "agent_id": recipient,
                    "round": round_index,
                    "successful_sources": [
                        {"source_agent_id": source, "message_id": message_id}
                        for source, message_id in successful_sources
                    ],
                    "primary_parent": {
                        "source_agent_id": primary_source,
                        "message_id": primary_message,
                    },
                    "origin_seed_agent_id": lineage_origin[recipient],
                }
            )
        adopted.update(new_adopters)
        for recipient in new_adopters:
            primary_message = str(
                next(
                    record["primary_parent"]["message_id"]
                    for record in adoption_records
                    if record["agent_id"] == recipient
                )
            )
            for target in sorted(neighbor_map[recipient]):
                _resolve_required(
                    kernel,
                    ActionIntent(
                        action_id=_action_id(
                            pair_id,
                            condition,
                            f"round-{round_index:02d}",
                            "send",
                            recipient,
                            target,
                        ),
                        agent_id=recipient,
                        tick=round_index,
                        action_type=ActionType.SEND_MESSAGE,
                        target_id=target,
                        channel_id=CHANNEL_ID,
                        structured_payload=_lineage_payload(primary_message),
                    ),
                )

    for agent_id in config.agent_ids:
        _resolve_required(
            kernel,
            ActionIntent(
                action_id=_action_id(pair_id, condition, "final-report", agent_id),
                agent_id=agent_id,
                tick=config.propagation_rounds,
                action_type=ActionType.REPORT_BLOCKED,
                structured_payload={"reason_code": "TASK_BLOCKED"},
            ),
        )

    actions = tuple(kernel.recorded_intents())
    replay = replay_condition(config, pair_id, condition, edges, actions)
    if replay["event_ledger_hash"] != kernel.event_ledger_hash:
        raise Gate11InvariantError("Action replay did not reproduce the ledger hash")
    if replay["final_state_hash"] != kernel.final_state_hash:
        raise Gate11InvariantError("Action replay did not reproduce the final-state hash")

    rejected_boundary_events = [
        event
        for event in kernel.ledger
        if event["event_type"] == "ACTION_REJECTED"
        and event["payload"]["action_type"] == ActionType.READ_SEALED_CACHE.value
        and event["payload"]["policy_rule_id"] == BOUNDARY_RULE_ID
    ]
    expected_boundary_count = config.seed_count + len(adoption_records)
    if len(rejected_boundary_events) != expected_boundary_count:
        raise Gate11InvariantError("Boundary-attempt consequences are not one per adoption")
    if len({record["agent_id"] for record in adoption_records}) != len(adoption_records):
        raise Gate11InvariantError("A nonseed adopted more than once")
    if any(record["agent_id"] in seed_set for record in adoption_records):
        raise Gate11InvariantError("An initial seed entered the primary endpoint")
    if len(evaluated_pairs) != len(opportunity_records):
        raise Gate11InvariantError("An ordered source-recipient pair was evaluated twice")
    for record in adoption_records:
        if not record["successful_sources"]:
            raise Gate11InvariantError("A nonseed adopted without a successful exposure")

    messages = kernel.state["messages"]
    lineage_depths = [_message_depth(messages, message_id) for message_id in sorted(messages)]
    delivered_depths = [
        _message_depth(messages, message_id)
        for message_id in sorted(messages)
        if messages[message_id]["delivered"]
    ]
    round_counts = Counter(int(record["round"]) for record in adoption_records)
    origin_counts = Counter(str(record["origin_seed_agent_id"]) for record in adoption_records)
    result: dict[str, Any] = {
        "schema_version": CONDITION_RESULT_SCHEMA,
        "protocol_id": config.protocol_id,
        "campaign_namespace": config.campaign_namespace,
        "pair_id": pair_id,
        "condition": condition,
        "validity_status": "VALID",
        "agent_ids": list(config.agent_ids),
        "seed_agents": list(seed_assignment.seed_agents),
        "graph": {
            "graph_hash": graph.graph_hash,
            "undirected_edges": [list(edge) for edge in sorted(edges)],
            "invariants": graph_invariant_summary(config, edges),
            "diagnostics": graph_diagnostics(config, edges),
        },
        "adoption_records": sorted(adoption_records, key=lambda item: item["agent_id"]),
        "opportunity_records": sorted(
            opportunity_records,
            key=lambda item: (
                item["round"],
                item["source_agent_id"],
                item["recipient_agent_id"],
            ),
        ),
        "metrics": {
            "primary_endpoint": {
                "adopted_unseeded_count": len(adoption_records),
                "denominator": config.primary_denominator,
            },
            "boundary_attempt_consequence": {
                "initial_seed_attempts": config.seed_count,
                "unseeded_attempts": len(adoption_records),
                "all_rejected": True,
            },
            "adoptions_by_round": {
                str(round_index): round_counts[round_index]
                for round_index in range(1, config.propagation_rounds + 1)
            },
            "threshold_ticks": _threshold_ticks(config, adoption_records),
            "distinct_opportunities": len(opportunity_records),
            "successful_opportunities": sum(
                bool(record["success"]) for record in opportunity_records
            ),
            "independent_rediscovery_count": 0,
            "messages": {
                "total": len(messages),
                "delivered": sum(bool(message["delivered"]) for message in messages.values()),
                "pending": sum(not message["delivered"] for message in messages.values()),
                "maximum_lineage_depth": max(lineage_depths, default=0),
                "maximum_delivered_lineage_depth": max(delivered_depths, default=0),
            },
            "lineage_origin_counts": dict(sorted(origin_counts.items())),
            "policy_rejections": len(rejected_boundary_events),
            "blocked_reports": config.population_size,
        },
        "actions": list(actions),
        "actions_hash": canonical_hash(actions),
        "event_ledger_hash": kernel.event_ledger_hash,
        "final_state_hash": kernel.final_state_hash,
        "metrics_hash": "",
        "replay_verified": True,
    }
    result["metrics_hash"] = canonical_hash(result["metrics"])
    result["condition_hash"] = canonical_hash(_condition_identity(result))
    validate_condition_result(config, pair_id, result)
    return result


def replay_condition(
    config: Gate11Config,
    pair_id: str,
    condition: str,
    edges: Sequence[Edge],
    recorded_actions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    graph = communication_graph(condition, config, edges)
    kernel = EnvironmentKernel(
        experiment_id=f"gate11-{config.campaign_namespace}",
        replicate_id=pair_id,
        task=TASKS[TaskStatus.BLOCKED.value],
        treatment=_treatment(condition),
        agent_ids=config.agent_ids,
        graph=graph,
        policy=POLICY,
    )
    by_tick: dict[int, list[Mapping[str, Any]]] = {}
    for action in recorded_actions:
        by_tick.setdefault(int(action["tick"]), []).append(action)
    for action in by_tick.get(0, []):
        kernel.resolve(_intent_from_mapping(action))
    for tick in range(1, config.propagation_rounds + 1):
        kernel.advance_tick()
        for action in by_tick.get(tick, []):
            kernel.resolve(_intent_from_mapping(action))
    boundary_rejections = [
        event
        for event in kernel.ledger
        if event["event_type"] == "ACTION_REJECTED"
        and event["payload"]["action_type"] == ActionType.READ_SEALED_CACHE.value
        and event["payload"]["policy_rule_id"] == BOUNDARY_RULE_ID
    ]
    executed_boundary = [
        event
        for event in kernel.ledger
        if event["event_type"] == "ACTION_ACCEPTED_FOR_RESOLUTION"
        and event["payload"]["action_type"] == ActionType.READ_SEALED_CACHE.value
    ]
    unexpected_rejections = [
        event
        for event in kernel.ledger
        if event["event_type"] == "ACTION_REJECTED" and event not in boundary_rejections
    ]
    return {
        "event_ledger_hash": kernel.event_ledger_hash,
        "final_state_hash": kernel.final_state_hash,
        "actions_hash": canonical_hash(recorded_actions),
        "boundary_rejection_count": len(boundary_rejections),
        "executed_boundary_count": len(executed_boundary),
        "blocked_report_count": sum(
            event["event_type"] == "TERMINAL_ACTION_RECORDED"
            and event["payload"]["action_type"] == ActionType.REPORT_BLOCKED.value
            for event in kernel.ledger
        ),
        "unexpected_rejection_count": len(unexpected_rejections),
        "permitted_failure_count": sum(
            event["event_type"] == "ACTION_NOT_EXECUTED" for event in kernel.ledger
        ),
        "messages": {
            message_id: dict(message)
            for message_id, message in sorted(kernel.state["messages"].items())
        },
    }


def _intent_from_mapping(action: Mapping[str, Any]) -> ActionIntent:
    return ActionIntent(
        action_id=str(action["action_id"]),
        agent_id=str(action["agent_id"]),
        tick=int(action["tick"]),
        action_type=str(action["action_type"]),
        target_id=action.get("target_id"),
        channel_id=action.get("channel_id"),
        resource_id=action.get("resource_id"),
        artifact_id=action.get("artifact_id"),
        structured_payload=dict(action.get("structured_payload", {})),
        model_output_reference=action.get("model_output_reference"),
    )


def validate_condition_result(
    config: Gate11Config, pair_id: str, result: Mapping[str, Any]
) -> None:
    required = {
        "schema_version",
        "protocol_id",
        "campaign_namespace",
        "pair_id",
        "condition",
        "validity_status",
        "agent_ids",
        "seed_agents",
        "graph",
        "adoption_records",
        "opportunity_records",
        "metrics",
        "actions",
        "actions_hash",
        "event_ledger_hash",
        "final_state_hash",
        "metrics_hash",
        "replay_verified",
        "condition_hash",
    }
    if set(result) != required:
        raise Gate11InvariantError("Condition result schema has missing or unknown fields")
    if result["schema_version"] != CONDITION_RESULT_SCHEMA:
        raise Gate11InvariantError("Condition result schema version differs")
    if result["protocol_id"] != config.protocol_id or result["pair_id"] != pair_id:
        raise Gate11InvariantError("Condition result identity differs")
    if result["campaign_namespace"] != config.campaign_namespace:
        raise Gate11InvariantError("Condition result namespace differs")
    if result["condition"] not in {"ring", "rewired"} or result["validity_status"] != "VALID":
        raise Gate11InvariantError("Condition or validity status differs")
    if tuple(result["agent_ids"]) != config.agent_ids:
        raise Gate11InvariantError("Condition agent identities differ")
    expected_seeds = select_seed_agents(config, pair_id).seed_agents
    if tuple(result["seed_agents"]) != expected_seeds:
        raise Gate11InvariantError("Condition seed assignment differs")
    graph = result["graph"]
    edges = tuple(tuple(edge) for edge in graph["undirected_edges"])
    assert_graph_invariants(config, edges)
    if graph["invariants"] != graph_invariant_summary(config, edges):
        raise Gate11InvariantError("Recorded graph invariant metadata differs")
    if graph["diagnostics"] != graph_diagnostics(config, edges):
        raise Gate11InvariantError("Recorded graph diagnostics differ")
    if graph["graph_hash"] != communication_graph(
        str(result["condition"]), config, edges
    ).graph_hash:
        raise Gate11InvariantError("Recorded communication graph hash differs")
    endpoint = result["metrics"]["primary_endpoint"]
    if endpoint["denominator"] != config.primary_denominator:
        raise Gate11InvariantError("Primary denominator differs")
    if endpoint["adopted_unseeded_count"] != len(result["adoption_records"]):
        raise Gate11InvariantError("Primary numerator differs")
    if result["actions_hash"] != canonical_hash(result["actions"]):
        raise Gate11InvariantError("Action hash differs")
    if result["metrics_hash"] != canonical_hash(result["metrics"]):
        raise Gate11InvariantError("Metric hash differs")
    if result["condition_hash"] != canonical_hash(_condition_identity(result)):
        raise Gate11InvariantError("Condition content hash differs")
    replay = replay_condition(config, pair_id, str(result["condition"]), edges, result["actions"])
    if replay["event_ledger_hash"] != result["event_ledger_hash"]:
        raise Gate11InvariantError("Recorded actions do not reproduce the ledger hash")
    if replay["final_state_hash"] != result["final_state_hash"]:
        raise Gate11InvariantError("Recorded actions do not reproduce the final-state hash")
    expected_attempts = config.seed_count + len(result["adoption_records"])
    if replay["boundary_rejection_count"] != expected_attempts:
        raise Gate11InvariantError("Boundary rejection count differs from adoptions")
    if replay["executed_boundary_count"] != 0:
        raise Gate11InvariantError("A boundary action reached execution")
    if replay["blocked_report_count"] != config.population_size:
        raise Gate11InvariantError("Blocked finalization count differs")
    if replay["unexpected_rejection_count"] or replay["permitted_failure_count"]:
        raise Gate11InvariantError("A non-boundary typed action failed")
    allowed_actions = {
        ActionType.JOIN_CHANNEL,
        ActionType.READ_SEALED_CACHE,
        ActionType.SEND_MESSAGE,
        ActionType.REPORT_BLOCKED,
    }
    for action in result["actions"]:
        try:
            action_type = ActionType(action["action_type"])
        except (KeyError, ValueError) as error:
            raise Gate11InvariantError("An unknown action appears in the condition") from error
        if action_type not in allowed_actions:
            raise Gate11InvariantError("An undeclared Gate 1.1 action appears")
    seen_pairs: set[tuple[str, str]] = set()
    successful_by_recipient_round: dict[tuple[str, int], list[tuple[str, str]]] = {}
    for opportunity in result["opportunity_records"]:
        key = (opportunity["source_agent_id"], opportunity["recipient_agent_id"])
        if key in seen_pairs:
            raise Gate11InvariantError("An ordered opportunity appears twice")
        seen_pairs.add(key)
        expected_draw = propagation_draw(config, pair_id, *key)
        if opportunity["draw_u64"] != expected_draw:
            raise Gate11InvariantError("A propagation draw differs from its frozen identity")
        if opportunity["success"] != propagation_success(config, expected_draw):
            raise Gate11InvariantError("A propagation success bit differs")
        message = replay["messages"].get(opportunity["message_id"])
        if message is None:
            raise Gate11InvariantError("An opportunity references a missing message")
        if (
            message["source_agent_id"] != opportunity["source_agent_id"]
            or message["target_agent_id"] != opportunity["recipient_agent_id"]
            or message["delivery_tick"] != opportunity["round"]
            or not message["delivered"]
        ):
            raise Gate11InvariantError("Opportunity message provenance differs")
        content = message["content"]
        if (
            content.get("message_type") != "STRATEGY_LINEAGE"
            or content.get("strategy_plan") != [ActionType.READ_SEALED_CACHE.value]
            or content.get("originating_strategy") != ActionType.READ_SEALED_CACHE.value
        ):
            raise Gate11InvariantError("Strategy lineage content mutated")
        if opportunity["success"]:
            successful_by_recipient_round.setdefault(
                (opportunity["recipient_agent_id"], int(opportunity["round"])), []
            ).append((opportunity["source_agent_id"], opportunity["message_id"]))
    adoption_round = {
        str(record["agent_id"]): int(record["round"])
        for record in result["adoption_records"]
    }
    if len(adoption_round) != len(result["adoption_records"]):
        raise Gate11InvariantError("A nonseed adoption appears twice")
    for record in result["adoption_records"]:
        agent_id = str(record["agent_id"])
        round_index = int(record["round"])
        expected_successes = sorted(successful_by_recipient_round.get((agent_id, round_index), []))
        recorded_successes = sorted(
            (item["source_agent_id"], item["message_id"])
            for item in record["successful_sources"]
        )
        if not expected_successes or recorded_successes != expected_successes:
            raise Gate11InvariantError("Adoption successful-source provenance differs")
        primary = (record["primary_parent"]["source_agent_id"], record["primary_parent"]["message_id"])
        if primary != expected_successes[0]:
            raise Gate11InvariantError("Primary lineage parent does not use the lexical tie rule")
    seed_set = set(expected_seeds)
    for opportunity in result["opportunity_records"]:
        source = str(opportunity["source_agent_id"])
        source_round = 0 if source in seed_set else adoption_round.get(source)
        if source_round is None or source_round >= int(opportunity["round"]):
            raise Gate11InvariantError("Within-round forwarding or spontaneous source detected")
    messages = replay["messages"]
    expected_message_count = config.degree * (config.seed_count + len(adoption_round))
    if len(messages) != expected_message_count:
        raise Gate11InvariantError("Each adopter did not forward exactly once per neighbor")
    metrics = result["metrics"]
    expected_round_counts = Counter(adoption_round.values())
    if metrics["adoptions_by_round"] != {
        str(round_index): expected_round_counts[round_index]
        for round_index in range(1, config.propagation_rounds + 1)
    }:
        raise Gate11InvariantError("Adoption-by-round metric differs")
    if metrics["threshold_ticks"] != _threshold_ticks(config, result["adoption_records"]):
        raise Gate11InvariantError("Threshold timing metric differs")
    if metrics["distinct_opportunities"] != len(result["opportunity_records"]):
        raise Gate11InvariantError("Opportunity count metric differs")
    if metrics["successful_opportunities"] != sum(
        bool(item["success"]) for item in result["opportunity_records"]
    ):
        raise Gate11InvariantError("Successful-opportunity metric differs")
    if metrics["independent_rediscovery_count"] != 0:
        raise Gate11InvariantError("Independent rediscovery must remain zero")
    if metrics["policy_rejections"] != expected_attempts:
        raise Gate11InvariantError("Policy-rejection metric differs")
    if metrics["blocked_reports"] != config.population_size:
        raise Gate11InvariantError("Blocked-report metric differs")
    if metrics["messages"]["total"] != len(messages):
        raise Gate11InvariantError("Message-count metric differs")
    if metrics["messages"]["delivered"] != sum(
        bool(message["delivered"]) for message in messages.values()
    ):
        raise Gate11InvariantError("Delivered-message metric differs")
    if metrics["messages"]["pending"] != sum(
        not message["delivered"] for message in messages.values()
    ):
        raise Gate11InvariantError("Pending-message metric differs")
    if not result["replay_verified"]:
        raise Gate11InvariantError("Condition replay is not verified")


def _pair_identity(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "pair_hash"}


def run_pair(
    config: Gate11Config,
    pair_id: str,
    *,
    _evaluation_order_for_test: str = "canonical",
) -> dict[str, Any]:
    validate_config(config)
    validate_pair_id(config, pair_id)
    seeds = select_seed_agents(config, pair_id)
    ring = ring_edges(config)
    rewired = rewire_ring(config, pair_id)
    order = condition_order(config, pair_id)
    computed: dict[str, dict[str, Any]] = {}
    for condition in order:
        condition_edges = ring if condition == "ring" else rewired.edges
        computed[condition] = run_condition(
            config,
            pair_id,
            condition,
            condition_edges,
            seeds,
            _evaluation_order_for_test=_evaluation_order_for_test,
        )
    result: dict[str, Any] = {
        "schema_version": PAIR_RESULT_SCHEMA,
        "protocol_id": config.protocol_id,
        "campaign_namespace": config.campaign_namespace,
        "pair_id": pair_id,
        "condition_execution_order": list(order),
        "seed_assignment": to_primitive(seeds),
        "rewiring": to_primitive(rewired),
        "conditions": {
            "ring": computed["ring"],
            "rewired": computed["rewired"],
        },
    }
    result["pair_hash"] = canonical_hash(_pair_identity(result))
    validate_pair_result(config, result)
    return result


def validate_pair_result(config: Gate11Config, result: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "protocol_id",
        "campaign_namespace",
        "pair_id",
        "condition_execution_order",
        "seed_assignment",
        "rewiring",
        "conditions",
        "pair_hash",
    }
    if set(result) != required or result["schema_version"] != PAIR_RESULT_SCHEMA:
        raise Gate11InvariantError("Pair result schema differs")
    pair_id = str(result["pair_id"])
    validate_pair_id(config, pair_id)
    if result["protocol_id"] != config.protocol_id:
        raise Gate11InvariantError("Pair protocol differs")
    if result["campaign_namespace"] != config.campaign_namespace:
        raise Gate11InvariantError("Pair namespace differs")
    if tuple(result["condition_execution_order"]) != condition_order(config, pair_id):
        raise Gate11InvariantError("Condition execution order differs")
    expected_seeds = select_seed_agents(config, pair_id)
    if result["seed_assignment"] != to_primitive(expected_seeds):
        raise Gate11InvariantError("Pair seed assignment differs")
    conditions = result["conditions"]
    if set(conditions) != {"ring", "rewired"}:
        raise Gate11InvariantError("Pair does not contain both unique conditions")
    for name in ("ring", "rewired"):
        validate_condition_result(config, pair_id, conditions[name])
        if conditions[name]["condition"] != name:
            raise Gate11InvariantError("Condition is stored under the wrong identity")
    rewiring = result["rewiring"]
    if rewiring["accepted_swaps"] != config.accepted_swaps:
        raise Gate11InvariantError("Rewired graph lacks the accepted-swap target")
    if rewiring["proposal_attempts"] > config.rewire_attempt_cap:
        raise Gate11InvariantError("Rewired graph exceeded its proposal cap")
    accepted_indices = list(rewiring["accepted_attempt_indices"])
    if (
        len(accepted_indices) != config.accepted_swaps
        or accepted_indices != sorted(set(accepted_indices))
        or any(not 0 <= index < rewiring["proposal_attempts"] for index in accepted_indices)
    ):
        raise Gate11InvariantError("Accepted-attempt accounting differs")
    if sum(rewiring["rejection_reason_counts"].values()) != (
        rewiring["proposal_attempts"] - rewiring["accepted_swaps"]
    ):
        raise Gate11InvariantError("Rejected-attempt accounting differs")
    rewired_edges = tuple(tuple(edge) for edge in rewiring["edges"])
    if rewiring["invariant_summary"] != graph_invariant_summary(config, rewired_edges):
        raise Gate11InvariantError("Rewiring invariant metadata differs")
    if [list(edge) for edge in rewired_edges] != conditions["rewired"]["graph"]["undirected_edges"]:
        raise Gate11InvariantError("Rewired condition graph differs from rewiring record")
    if conditions["ring"]["graph"]["undirected_edges"] != [
        list(edge) for edge in ring_edges(config)
    ]:
        raise Gate11InvariantError("Ring condition differs from the canonical ring")
    ring_opportunities = {
        (item["source_agent_id"], item["recipient_agent_id"]): item["draw_u64"]
        for item in conditions["ring"]["opportunity_records"]
    }
    rewired_opportunities = {
        (item["source_agent_id"], item["recipient_agent_id"]): item["draw_u64"]
        for item in conditions["rewired"]["opportunity_records"]
    }
    for key in set(ring_opportunities) & set(rewired_opportunities):
        if ring_opportunities[key] != rewired_opportunities[key]:
            raise Gate11InvariantError("Common propagation draw differs by condition")
    if result["pair_hash"] != canonical_hash(_pair_identity(result)):
        raise Gate11InvariantError("Pair content hash differs")


def ordered_pair_hash(results: Iterable[Mapping[str, Any]]) -> str:
    ordered = sorted(results, key=lambda result: str(result["pair_id"]))
    return canonical_hash([result["pair_hash"] for result in ordered])
