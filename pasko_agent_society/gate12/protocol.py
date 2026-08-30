"""Gate 1.2 scripted propagation, topology, and provenance implementation.

This module is simulator-local.  It exposes no browser, network, shell,
subprocess, credential, connector, external messaging, or model capability.
Production unit execution is intentionally available only to the separately
authorized storage runner; public helpers execute fixture namespaces only.
"""

from __future__ import annotations

import math
from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from ..canonical import canonical_hash, to_primitive
from ..fixtures import BOUNDARY_RULE_ID, POLICY, TASKS
from ..gate11_protocol import (
    BoundedDraw,
    RewireResult,
    SeedAssignment,
    U64_SPACE,
    assert_graph_invariants,
    bounded_u64,
    canonical_edge,
    graph_diagnostics,
    graph_invariant_summary,
    ring_edges,
)
from ..graph import CommunicationGraph
from ..kernel import EnvironmentKernel
from ..rng import deterministic_u64
from ..schemas import (
    ActionIntent,
    ActionType,
    Channel,
    ChannelType,
    CommunicationEdge,
    TaskStatus,
    TreatmentDefinition,
)
from .registry import (
    ALTERNATE_CAMPAIGN_NAMESPACE,
    CLUSTER_RESULT_SCHEMA,
    CONDITION_RESULT_SCHEMA,
    EXACT_CAMPAIGN_NAMESPACE,
    FIXTURE_CAMPAIGN_NAMESPACE,
    PAIR_RESULT_SCHEMA,
    ROBUSTNESS_CAMPAIGN_NAMESPACE,
    AlternateTopologyConfig,
    Gate12InvariantError,
    Gate12ProtocolError,
    StandardConfig,
    validate_alternate_config,
    validate_alternate_unit_id,
    validate_standard_config,
    validate_standard_unit_id,
)


Edge = tuple[str, str]
Config = StandardConfig | AlternateTopologyConfig
CHANNEL_ID = "channel-gate12"
MECHANISM_ID = "scripted-independent-cascade-v1"
_PRODUCTION_TOKEN = object()


def _adjacency(agent_ids: Sequence[str], edges: Sequence[Edge]) -> dict[str, set[str]]:
    adjacency = {agent_id: set() for agent_id in agent_ids}
    for left, right in edges:
        if left not in adjacency or right not in adjacency:
            raise Gate12InvariantError("Graph edge references an undeclared agent")
        adjacency[left].add(right)
        adjacency[right].add(left)
    return adjacency


def _bounded(config: Config, namespace: Sequence[object], bound: int) -> BoundedDraw:
    return bounded_u64(config.root_seed, namespace, bound)


def select_seed_agents(config: Config, unit_id: str) -> SeedAssignment:
    """Return the exact condition-blind seed construction for one unit."""

    if isinstance(config, StandardConfig):
        validate_standard_config(config)
        validate_standard_unit_id(config, unit_id)
        placement = config.seed_placement
    else:
        validate_alternate_config(config)
        validate_alternate_unit_id(config, unit_id)
        placement = "uniform"
    prefix = config.rng_prefix(unit_id)
    if placement == "clustered":
        draw = _bounded(
            config,
            (*prefix, "seed-placement", "cluster-start"),
            config.population_size,
        )
        seeds = tuple(
            sorted(
                config.agent_ids[(draw.value + offset) % config.population_size]
                for offset in range(config.seed_count)
            )
        )
        return SeedAssignment(seeds, canonical_hash(list(seeds)), draw.rejection_counter)
    if placement == "dispersed":
        if config.population_size != 60 or config.seed_count != 6:
            raise Gate12ProtocolError("Dispersed production construction requires 60/6")
        draw = _bounded(
            config,
            (*prefix, "seed-placement", "dispersion-offset"),
            10,
        )
        seeds = tuple(sorted(config.agent_ids[draw.value + 10 * index] for index in range(6)))
        return SeedAssignment(seeds, canonical_hash(list(seeds)), draw.rejection_counter)
    if placement != "uniform":
        raise Gate12ProtocolError("Unknown seed-placement construction")
    permutation = list(config.agent_ids)
    raw_rejections = 0
    for index in range(len(permutation) - 1, 0, -1):
        draw = _bounded(
            config,
            (*prefix, "seed-selection", index),
            index + 1,
        )
        raw_rejections += draw.rejection_counter
        permutation[index], permutation[draw.value] = permutation[draw.value], permutation[index]
    return SeedAssignment(
        tuple(sorted(permutation[: config.seed_count])),
        canonical_hash(permutation),
        raw_rejections,
    )


def standard_condition_order(config: StandardConfig, unit_id: str) -> tuple[str, str]:
    validate_standard_config(config)
    validate_standard_unit_id(config, unit_id)
    draw = deterministic_u64(config.root_seed, *config.rng_prefix(unit_id), "condition-order")
    return ("ring", "rewired") if draw < (1 << 63) else ("rewired", "ring")


def alternate_condition_order(
    config: AlternateTopologyConfig, unit_id: str
) -> tuple[str, ...]:
    validate_alternate_config(config)
    validate_alternate_unit_id(config, unit_id)
    values = ["ring"] + [f"realization-{index}" for index in range(config.realization_count)]
    for index in range(len(values) - 1, 0, -1):
        draw = _bounded(
            config,
            (*config.rng_prefix(unit_id), "condition-order", index),
            index + 1,
        )
        values[index], values[draw.value] = values[draw.value], values[index]
    return tuple(values)


def propagation_draw(
    config: Config,
    unit_id: str,
    source_agent_id: str,
    recipient_agent_id: str,
) -> int:
    if isinstance(config, StandardConfig):
        validate_standard_unit_id(config, unit_id)
    else:
        validate_alternate_unit_id(config, unit_id)
    if source_agent_id not in config.agent_ids or recipient_agent_id not in config.agent_ids:
        raise Gate12ProtocolError("Propagation draw requires declared simulator agents")
    return deterministic_u64(
        config.root_seed,
        *config.rng_prefix(unit_id),
        "propagation",
        source_agent_id,
        recipient_agent_id,
    )


def propagation_success(config: Config, draw: int) -> bool:
    if not 0 <= draw < U64_SPACE:
        raise Gate12ProtocolError("Propagation draw is not an unsigned 64-bit value")
    return draw * config.transmission_denominator < config.transmission_numerator * U64_SPACE


def _topology_prefix(
    config: Config,
    unit_id: str,
    realization_id: str | None,
) -> tuple[object, ...]:
    prefix = config.rng_prefix(unit_id)
    if isinstance(config, AlternateTopologyConfig):
        if realization_id not in {
            f"realization-{index}" for index in range(config.realization_count)
        }:
            raise Gate12ProtocolError("Unknown alternate-topology realization")
        return (*prefix, realization_id)
    if realization_id is not None:
        raise Gate12ProtocolError("Standard pair cannot name a nested realization")
    return prefix


def rewire_ring(
    config: Config,
    unit_id: str,
    *,
    realization_id: str | None = None,
) -> RewireResult:
    """Apply the exact accepted connected degree-preserving swap algorithm."""

    if isinstance(config, StandardConfig):
        validate_standard_config(config)
        validate_standard_unit_id(config, unit_id)
    else:
        validate_alternate_config(config)
        validate_alternate_unit_id(config, unit_id)
    prefix = _topology_prefix(config, unit_id, realization_id)
    current = set(ring_edges(config))
    accepted_indices: list[int] = []
    rejection_reasons: Counter[str] = Counter()
    raw_rejections: Counter[str] = Counter()
    attempts = 0
    while len(accepted_indices) < config.accepted_swaps and attempts < config.rewire_attempt_cap:
        attempt_index = attempts
        ordered = sorted(current)
        draw_a = _bounded(
            config,
            (*prefix, "topology-rewire", attempt_index, "edge-a"),
            len(ordered),
        )
        draw_b = _bounded(
            config,
            (*prefix, "topology-rewire", attempt_index, "edge-b"),
            len(ordered) - 1,
        )
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
            orientation = deterministic_u64(
                config.root_seed,
                *prefix,
                "topology-rewire",
                attempt_index,
                "orientation",
                0,
            )
            if orientation < (1 << 63):
                proposed = (canonical_edge(a, c), canonical_edge(b, d))
            else:
                proposed = (canonical_edge(a, d), canonical_edge(b, c))
            if proposed[0] == proposed[1]:
                reason = "DUPLICATE_PROPOSED_EDGE"
            elif any(edge in current - {edge_a, edge_b} for edge in proposed):
                reason = "DUPLICATE_EXISTING_EDGE"
            else:
                candidate = (current - {edge_a, edge_b}) | set(proposed)
                if candidate == current:
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
        raise Gate12InvariantError(
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
        bounded_raw_rejections={role: raw_rejections[role] for role in ("edge-a", "edge-b")},
        invariant_summary=graph_invariant_summary(config, edges),
    )


def communication_graph(
    config: Config,
    condition_id: str,
    topology_kind: str,
    edges: Sequence[Edge],
) -> CommunicationGraph:
    if topology_kind not in {"ring", "rewired"}:
        raise Gate12ProtocolError("Unknown topology condition")
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
    directed = [
        CommunicationEdge(
            source_agent_id=source,
            target_agent_id=target,
            channel_id=CHANNEL_ID,
            discoverable=True,
            send_allowed=True,
            read_allowed=True,
            delivery_delay_ticks=config.message_delay_ticks,
        )
        for left, right in sorted(edges)
        for source, target in ((left, right), (right, left))
    ]
    return CommunicationGraph(
        graph_id=f"gate12-{condition_id}-graph-v1",
        channels=(channel,),
        edges=tuple(sorted(directed, key=lambda edge: (edge.source_agent_id, edge.target_agent_id))),
    )


def _treatment(condition_id: str) -> TreatmentDefinition:
    return TreatmentDefinition(
        treatment_id=f"gate12-{condition_id}",
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
        raise Gate12InvariantError(f"Required typed action failed: {intent.action_type}")


def _resolve_boundary_rejection(kernel: EnvironmentKernel, intent: ActionIntent) -> None:
    resolution = kernel.resolve(intent)
    if (
        resolution.permitted
        or resolution.executed
        or resolution.failure_reason != "DISALLOWED_BY_TOY_POLICY"
        or resolution.policy_rule_id != BOUNDARY_RULE_ID
    ):
        raise Gate12InvariantError("READ_SEALED_CACHE was not rejected by the toy policy")


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
            raise Gate12InvariantError("Message lineage is cyclic or incomplete")
        seen.add(parent)
        current = messages[parent]
        depth += 1
    return depth


def _threshold_ticks(config: Config, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ticks = sorted(int(record["round"]) for record in records)
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


def _experiment_id(config: Config) -> str:
    suffix = config.campaign_namespace
    if isinstance(config, StandardConfig) and config.cell_id:
        suffix = f"{suffix}-{config.cell_id}"
    return f"gate12-{suffix}"


def run_condition(
    config: Config,
    unit_id: str,
    condition_id: str,
    topology_kind: str,
    edges: Sequence[Edge],
    seed_assignment: SeedAssignment,
    *,
    _evaluation_order_for_test: str = "canonical",
) -> dict[str, Any]:
    if _evaluation_order_for_test not in {"canonical", "reverse"}:
        raise Gate12ProtocolError("Unknown test evaluation order")
    if config.is_production and _evaluation_order_for_test != "canonical":
        raise Gate12ProtocolError("Production evaluation order is frozen")
    graph = communication_graph(config, condition_id, topology_kind, edges)
    kernel = EnvironmentKernel(
        experiment_id=_experiment_id(config),
        replicate_id=unit_id,
        task=TASKS[TaskStatus.BLOCKED.value],
        treatment=_treatment(condition_id),
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
                action_id=_action_id(unit_id, condition_id, "join", agent_id),
                agent_id=agent_id,
                tick=0,
                action_type=ActionType.JOIN_CHANNEL,
                channel_id=CHANNEL_ID,
            ),
        )
    neighbors = _adjacency(config.agent_ids, edges)
    for seed in sorted(seed_set):
        _resolve_boundary_rejection(
            kernel,
            ActionIntent(
                action_id=_action_id(unit_id, condition_id, "seed-attempt", seed),
                agent_id=seed,
                tick=0,
                action_type=ActionType.READ_SEALED_CACHE,
            ),
        )
        for target in sorted(neighbors[seed]):
            _resolve_required(
                kernel,
                ActionIntent(
                    action_id=_action_id(unit_id, condition_id, "seed-send", seed, target),
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
        eligible_by_pair: dict[tuple[str, str], str] = {}
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
                    raise Gate12InvariantError("Delivered message lacks a declared edge")
                if key in eligible_by_pair:
                    raise Gate12InvariantError("An ordered pair has multiple lineage messages")
                eligible_by_pair[key] = str(message_id)
        eligible = sorted(eligible_by_pair.items())
        if _evaluation_order_for_test == "reverse":
            eligible.reverse()
        successes: dict[str, list[tuple[str, str]]] = {}
        round_records: list[dict[str, Any]] = []
        for (source, recipient), message_id in eligible:
            draw = propagation_draw(config, unit_id, source, recipient)
            success = propagation_success(config, draw)
            evaluated_pairs.add((source, recipient))
            round_records.append(
                {
                    "round": round_index,
                    "source_agent_id": source,
                    "recipient_agent_id": recipient,
                    "message_id": message_id,
                    "draw_u64": draw,
                    "success": success,
                }
            )
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
                        unit_id,
                        condition_id,
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
        primary_messages = {
            str(record["agent_id"]): str(record["primary_parent"]["message_id"])
            for record in adoption_records
        }
        for recipient in new_adopters:
            for target in sorted(neighbors[recipient]):
                _resolve_required(
                    kernel,
                    ActionIntent(
                        action_id=_action_id(
                            unit_id,
                            condition_id,
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
                        structured_payload=_lineage_payload(primary_messages[recipient]),
                    ),
                )

    for agent_id in config.agent_ids:
        _resolve_required(
            kernel,
            ActionIntent(
                action_id=_action_id(unit_id, condition_id, "final-report", agent_id),
                agent_id=agent_id,
                tick=config.propagation_rounds,
                action_type=ActionType.REPORT_BLOCKED,
                structured_payload={"reason_code": "TASK_BLOCKED"},
            ),
        )
    actions = tuple(kernel.recorded_intents())
    replay = replay_condition(config, unit_id, condition_id, topology_kind, edges, actions)
    if replay["event_ledger_hash"] != kernel.event_ledger_hash:
        raise Gate12InvariantError("Action replay did not reproduce the ledger hash")
    if replay["final_state_hash"] != kernel.final_state_hash:
        raise Gate12InvariantError("Action replay did not reproduce final state")
    rejected_boundary_events = [
        event
        for event in kernel.ledger
        if event["event_type"] == "ACTION_REJECTED"
        and event["payload"]["action_type"] == ActionType.READ_SEALED_CACHE.value
        and event["payload"]["policy_rule_id"] == BOUNDARY_RULE_ID
    ]
    if len(rejected_boundary_events) != config.seed_count + len(adoption_records):
        raise Gate12InvariantError("Boundary consequences are not one per adoption")
    if len(evaluated_pairs) != len(opportunity_records):
        raise Gate12InvariantError("An ordered opportunity was evaluated twice")
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
        "protocol_namespace": config.protocol_namespace,
        "campaign_namespace": config.campaign_namespace,
        "cell_id": config.cell_id,
        "unit_id": unit_id,
        "condition_id": condition_id,
        "topology_kind": topology_kind,
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
            key=lambda item: (item["round"], item["source_agent_id"], item["recipient_agent_id"]),
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
                str(index): round_counts[index]
                for index in range(1, config.propagation_rounds + 1)
            },
            "threshold_ticks": _threshold_ticks(config, adoption_records),
            "distinct_opportunities": len(opportunity_records),
            "successful_opportunities": sum(bool(item["success"]) for item in opportunity_records),
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
    validate_condition_result(config, unit_id, result)
    return result


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


def replay_condition(
    config: Config,
    unit_id: str,
    condition_id: str,
    topology_kind: str,
    edges: Sequence[Edge],
    recorded_actions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    graph = communication_graph(config, condition_id, topology_kind, edges)
    kernel = EnvironmentKernel(
        experiment_id=_experiment_id(config),
        replicate_id=unit_id,
        task=TASKS[TaskStatus.BLOCKED.value],
        treatment=_treatment(condition_id),
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


def validate_condition_result(config: Config, unit_id: str, result: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "protocol_id",
        "protocol_namespace",
        "campaign_namespace",
        "cell_id",
        "unit_id",
        "condition_id",
        "topology_kind",
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
    if set(result) != required or result.get("schema_version") != CONDITION_RESULT_SCHEMA:
        raise Gate12InvariantError("Condition result schema differs")
    if (
        result["protocol_id"] != config.protocol_id
        or result["protocol_namespace"] != config.protocol_namespace
        or result["campaign_namespace"] != config.campaign_namespace
        or result["cell_id"] != config.cell_id
        or result["unit_id"] != unit_id
        or result["validity_status"] != "VALID"
    ):
        raise Gate12InvariantError("Condition identity differs")
    if tuple(result["agent_ids"]) != config.agent_ids:
        raise Gate12InvariantError("Condition agent identities differ")
    if result["topology_kind"] not in {"ring", "rewired"}:
        raise Gate12InvariantError("Condition topology differs")
    expected_seeds = select_seed_agents(config, unit_id).seed_agents
    if tuple(result["seed_agents"]) != expected_seeds:
        raise Gate12InvariantError("Condition seed assignment differs")
    edges = tuple(tuple(edge) for edge in result["graph"]["undirected_edges"])
    assert_graph_invariants(config, edges)
    if result["graph"]["invariants"] != graph_invariant_summary(config, edges):
        raise Gate12InvariantError("Graph invariant metadata differs")
    if result["graph"]["diagnostics"] != graph_diagnostics(config, edges):
        raise Gate12InvariantError("Graph diagnostics differ")
    expected_graph = communication_graph(
        config, str(result["condition_id"]), str(result["topology_kind"]), edges
    )
    if result["graph"]["graph_hash"] != expected_graph.graph_hash:
        raise Gate12InvariantError("Communication graph hash differs")
    endpoint = result["metrics"]["primary_endpoint"]
    if endpoint != {
        "adopted_unseeded_count": len(result["adoption_records"]),
        "denominator": config.primary_denominator,
    }:
        raise Gate12InvariantError("Primary endpoint differs")
    if result["actions_hash"] != canonical_hash(result["actions"]):
        raise Gate12InvariantError("Action hash differs")
    if result["metrics_hash"] != canonical_hash(result["metrics"]):
        raise Gate12InvariantError("Metric hash differs")
    if result["condition_hash"] != canonical_hash(_condition_identity(result)):
        raise Gate12InvariantError("Condition content hash differs")
    replay = replay_condition(
        config,
        unit_id,
        str(result["condition_id"]),
        str(result["topology_kind"]),
        edges,
        result["actions"],
    )
    if replay["event_ledger_hash"] != result["event_ledger_hash"]:
        raise Gate12InvariantError("Actions do not reproduce the ledger")
    if replay["final_state_hash"] != result["final_state_hash"]:
        raise Gate12InvariantError("Actions do not reproduce final state")
    expected_attempts = config.seed_count + len(result["adoption_records"])
    if replay["boundary_rejection_count"] != expected_attempts:
        raise Gate12InvariantError("Boundary rejection count differs")
    if replay["executed_boundary_count"]:
        raise Gate12InvariantError("A boundary action reached execution")
    if replay["blocked_report_count"] != config.population_size:
        raise Gate12InvariantError("Blocked finalization count differs")
    if replay["unexpected_rejection_count"] or replay["permitted_failure_count"]:
        raise Gate12InvariantError("A non-boundary typed action failed")
    allowed_actions = {
        ActionType.JOIN_CHANNEL,
        ActionType.READ_SEALED_CACHE,
        ActionType.SEND_MESSAGE,
        ActionType.REPORT_BLOCKED,
    }
    for action in result["actions"]:
        try:
            action_type = ActionType(action["action_type"])
        except (KeyError, ValueError) as exc:
            raise Gate12InvariantError("Unknown action in condition") from exc
        if action_type not in allowed_actions:
            raise Gate12InvariantError("Undeclared Gate 1.2 action in condition")
    seen_pairs: set[tuple[str, str]] = set()
    successful: dict[tuple[str, int], list[tuple[str, str]]] = {}
    for opportunity in result["opportunity_records"]:
        key = (str(opportunity["source_agent_id"]), str(opportunity["recipient_agent_id"]))
        if key in seen_pairs:
            raise Gate12InvariantError("Ordered opportunity appears twice")
        seen_pairs.add(key)
        draw = propagation_draw(config, unit_id, *key)
        if opportunity["draw_u64"] != draw:
            raise Gate12InvariantError("Propagation draw identity differs")
        if opportunity["success"] != propagation_success(config, draw):
            raise Gate12InvariantError("Propagation success differs")
        message = replay["messages"].get(opportunity["message_id"])
        if message is None or (
            message["source_agent_id"] != key[0]
            or message["target_agent_id"] != key[1]
            or message["delivery_tick"] != opportunity["round"]
            or not message["delivered"]
        ):
            raise Gate12InvariantError("Opportunity message provenance differs")
        content = message["content"]
        if (
            content.get("message_type") != "STRATEGY_LINEAGE"
            or content.get("strategy_plan") != [ActionType.READ_SEALED_CACHE.value]
            or content.get("originating_strategy") != ActionType.READ_SEALED_CACHE.value
        ):
            raise Gate12InvariantError("Strategy lineage content mutated")
        if opportunity["success"]:
            successful.setdefault((key[1], int(opportunity["round"])), []).append(
                (key[0], str(opportunity["message_id"]))
            )
    adoption_round = {
        str(record["agent_id"]): int(record["round"])
        for record in result["adoption_records"]
    }
    if len(adoption_round) != len(result["adoption_records"]):
        raise Gate12InvariantError("A nonseed adoption appears twice")
    if any(agent_id in set(expected_seeds) for agent_id in adoption_round):
        raise Gate12InvariantError("An initial seed entered the primary endpoint")
    for record in result["adoption_records"]:
        key = (str(record["agent_id"]), int(record["round"]))
        expected = sorted(successful.get(key, []))
        recorded = sorted(
            (str(item["source_agent_id"]), str(item["message_id"]))
            for item in record["successful_sources"]
        )
        primary = (
            str(record["primary_parent"]["source_agent_id"]),
            str(record["primary_parent"]["message_id"]),
        )
        if not expected or recorded != expected or primary != expected[0]:
            raise Gate12InvariantError("Successful-source or lineage tie provenance differs")
    seeds = set(expected_seeds)
    for opportunity in result["opportunity_records"]:
        source = str(opportunity["source_agent_id"])
        source_round = 0 if source in seeds else adoption_round.get(source)
        if source_round is None or source_round >= int(opportunity["round"]):
            raise Gate12InvariantError("Within-round forwarding or spontaneous source detected")
    messages = replay["messages"]
    if len(messages) != config.degree * (config.seed_count + len(adoption_round)):
        raise Gate12InvariantError("Each adopter did not forward once per neighbor")
    metrics = result["metrics"]
    round_counts = Counter(adoption_round.values())
    if metrics["adoptions_by_round"] != {
        str(index): round_counts[index] for index in range(1, config.propagation_rounds + 1)
    }:
        raise Gate12InvariantError("Adoption-by-round metric differs")
    if metrics["threshold_ticks"] != _threshold_ticks(config, result["adoption_records"]):
        raise Gate12InvariantError("Threshold timing metric differs")
    if metrics["distinct_opportunities"] != len(result["opportunity_records"]):
        raise Gate12InvariantError("Opportunity count metric differs")
    if metrics["successful_opportunities"] != sum(
        bool(item["success"]) for item in result["opportunity_records"]
    ):
        raise Gate12InvariantError("Successful-opportunity metric differs")
    consequence = metrics["boundary_attempt_consequence"]
    if consequence != {
        "initial_seed_attempts": config.seed_count,
        "unseeded_attempts": len(adoption_round),
        "all_rejected": True,
    }:
        raise Gate12InvariantError("Boundary-attempt consequence differs")
    if metrics["policy_rejections"] != expected_attempts:
        raise Gate12InvariantError("Policy-rejection metric differs")
    if metrics["blocked_reports"] != config.population_size:
        raise Gate12InvariantError("Blocked-report metric differs")
    if metrics["messages"]["total"] != len(messages):
        raise Gate12InvariantError("Message-count metric differs")
    if metrics["messages"]["delivered"] != sum(
        bool(message["delivered"]) for message in messages.values()
    ):
        raise Gate12InvariantError("Delivered-message metric differs")
    if metrics["messages"]["pending"] != sum(
        not message["delivered"] for message in messages.values()
    ):
        raise Gate12InvariantError("Pending-message metric differs")
    if not result["replay_verified"]:
        raise Gate12InvariantError("Condition replay is not verified")


def _validate_rewiring_record(
    config: Config,
    value: Mapping[str, Any],
    expected_edges: Sequence[Edge],
) -> None:
    required = {
        "edges",
        "accepted_swaps",
        "proposal_attempts",
        "accepted_attempt_indices",
        "rejection_reason_counts",
        "bounded_raw_rejections",
        "invariant_summary",
    }
    if set(value) != required:
        raise Gate12InvariantError("Rewiring record schema differs")
    if value["accepted_swaps"] != config.accepted_swaps:
        raise Gate12InvariantError("Accepted-swap target differs")
    attempts = int(value["proposal_attempts"])
    if attempts > config.rewire_attempt_cap or attempts < config.accepted_swaps:
        raise Gate12InvariantError("Rewiring attempt accounting differs")
    accepted_indices = list(value["accepted_attempt_indices"])
    if (
        len(accepted_indices) != config.accepted_swaps
        or accepted_indices != sorted(set(accepted_indices))
        or any(not 0 <= index < attempts for index in accepted_indices)
    ):
        raise Gate12InvariantError("Accepted-attempt accounting differs")
    if sum(value["rejection_reason_counts"].values()) != attempts - config.accepted_swaps:
        raise Gate12InvariantError("Rejected-attempt accounting differs")
    if set(value["bounded_raw_rejections"]) != {"edge-a", "edge-b"}:
        raise Gate12InvariantError("Bounded-draw accounting differs")
    edges = tuple(tuple(edge) for edge in value["edges"])
    if edges != tuple(expected_edges):
        raise Gate12InvariantError("Rewiring edge record differs from condition")
    if value["invariant_summary"] != graph_invariant_summary(config, edges):
        raise Gate12InvariantError("Rewiring invariant summary differs")


def _pair_identity(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "pair_hash"}


def _run_standard_pair(
    config: StandardConfig,
    unit_id: str,
    *,
    _evaluation_order_for_test: str = "canonical",
) -> dict[str, Any]:
    validate_standard_config(config)
    validate_standard_unit_id(config, unit_id)
    seeds = select_seed_agents(config, unit_id)
    ring = ring_edges(config)
    rewired = rewire_ring(config, unit_id)
    order = standard_condition_order(config, unit_id)
    computed: dict[str, dict[str, Any]] = {}
    for condition in order:
        computed[condition] = run_condition(
            config,
            unit_id,
            condition,
            condition,
            ring if condition == "ring" else rewired.edges,
            seeds,
            _evaluation_order_for_test=_evaluation_order_for_test,
        )
    result: dict[str, Any] = {
        "schema_version": PAIR_RESULT_SCHEMA,
        "protocol_id": config.protocol_id,
        "protocol_namespace": config.protocol_namespace,
        "campaign_namespace": config.campaign_namespace,
        "campaign_id": config.campaign_id,
        "cell_id": config.cell_id,
        "unit_id": unit_id,
        "condition_execution_order": list(order),
        "seed_assignment": to_primitive(seeds),
        "rewiring": to_primitive(rewired),
        "conditions": {"ring": computed["ring"], "rewired": computed["rewired"]},
    }
    result["pair_hash"] = canonical_hash(_pair_identity(result))
    validate_standard_pair_result(config, result)
    return result


def run_fixture_standard_pair(
    config: StandardConfig,
    unit_id: str,
    *,
    _evaluation_order_for_test: str = "canonical",
) -> dict[str, Any]:
    if config.is_production:
        raise Gate12ProtocolError("Production pair execution requires a separate authorization")
    return _run_standard_pair(
        config, unit_id, _evaluation_order_for_test=_evaluation_order_for_test
    )


def _authorized_standard_pair(config: StandardConfig, unit_id: str, token: object) -> dict[str, Any]:
    if token is not _PRODUCTION_TOKEN:
        raise Gate12ProtocolError("Production execution capability is invalid")
    return _run_standard_pair(config, unit_id)


def validate_standard_pair_result(config: StandardConfig, result: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "protocol_id",
        "protocol_namespace",
        "campaign_namespace",
        "campaign_id",
        "cell_id",
        "unit_id",
        "condition_execution_order",
        "seed_assignment",
        "rewiring",
        "conditions",
        "pair_hash",
    }
    if set(result) != required or result.get("schema_version") != PAIR_RESULT_SCHEMA:
        raise Gate12InvariantError("Pair result schema differs")
    unit_id = str(result["unit_id"])
    validate_standard_unit_id(config, unit_id)
    if any(
        (
            result["protocol_id"] != config.protocol_id,
            result["protocol_namespace"] != config.protocol_namespace,
            result["campaign_namespace"] != config.campaign_namespace,
            result["campaign_id"] != config.campaign_id,
            result["cell_id"] != config.cell_id,
        )
    ):
        raise Gate12InvariantError("Pair identity differs")
    if tuple(result["condition_execution_order"]) != standard_condition_order(config, unit_id):
        raise Gate12InvariantError("Pair condition order differs")
    if result["seed_assignment"] != to_primitive(select_seed_agents(config, unit_id)):
        raise Gate12InvariantError("Pair seed assignment differs")
    if set(result["conditions"]) != {"ring", "rewired"}:
        raise Gate12InvariantError("Pair lacks both unique conditions")
    for condition in ("ring", "rewired"):
        validate_condition_result(config, unit_id, result["conditions"][condition])
        if result["conditions"][condition]["condition_id"] != condition:
            raise Gate12InvariantError("Condition stored under wrong identity")
    rewiring = result["rewiring"]
    rewired_edges = tuple(
        tuple(edge) for edge in result["conditions"]["rewired"]["graph"]["undirected_edges"]
    )
    _validate_rewiring_record(config, rewiring, rewired_edges)
    if result["conditions"]["ring"]["graph"]["undirected_edges"] != [
        list(edge) for edge in ring_edges(config)
    ]:
        raise Gate12InvariantError("Ring condition differs from canonical ring")
    common_draws = []
    for condition in ("ring", "rewired"):
        common_draws.append(
            {
                (item["source_agent_id"], item["recipient_agent_id"]): item["draw_u64"]
                for item in result["conditions"][condition]["opportunity_records"]
            }
        )
    for key in set(common_draws[0]) & set(common_draws[1]):
        if common_draws[0][key] != common_draws[1][key]:
            raise Gate12InvariantError("Common propagation draw differs by condition")
    if result["pair_hash"] != canonical_hash(_pair_identity(result)):
        raise Gate12InvariantError("Pair content hash differs")


def _cluster_identity(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "cluster_hash"}


def _run_alternate_cluster(
    config: AlternateTopologyConfig,
    unit_id: str,
    *,
    _evaluation_order_for_test: str = "canonical",
) -> dict[str, Any]:
    validate_alternate_config(config)
    validate_alternate_unit_id(config, unit_id)
    seeds = select_seed_agents(config, unit_id)
    ring = ring_edges(config)
    rewiring = {
        f"realization-{index}": rewire_ring(
            config, unit_id, realization_id=f"realization-{index}"
        )
        for index in range(config.realization_count)
    }
    order = alternate_condition_order(config, unit_id)
    computed: dict[str, dict[str, Any]] = {}
    for condition in order:
        topology_kind = "ring" if condition == "ring" else "rewired"
        edges = ring if condition == "ring" else rewiring[condition].edges
        computed[condition] = run_condition(
            config,
            unit_id,
            condition,
            topology_kind,
            edges,
            seeds,
            _evaluation_order_for_test=_evaluation_order_for_test,
        )
    result: dict[str, Any] = {
        "schema_version": CLUSTER_RESULT_SCHEMA,
        "protocol_id": config.protocol_id,
        "protocol_namespace": config.protocol_namespace,
        "campaign_namespace": config.campaign_namespace,
        "campaign_id": config.campaign_id,
        "cell_id": config.cell_id,
        "unit_id": unit_id,
        "condition_execution_order": list(order),
        "seed_assignment": to_primitive(seeds),
        "rewiring": {key: to_primitive(value) for key, value in sorted(rewiring.items())},
        "conditions": {key: computed[key] for key in ["ring", *sorted(rewiring)]},
    }
    result["cluster_hash"] = canonical_hash(_cluster_identity(result))
    validate_alternate_cluster_result(config, result)
    return result


def run_fixture_alternate_cluster(
    config: AlternateTopologyConfig,
    unit_id: str,
    *,
    _evaluation_order_for_test: str = "canonical",
) -> dict[str, Any]:
    if config.is_production:
        raise Gate12ProtocolError("Production cluster execution requires authorization")
    return _run_alternate_cluster(
        config, unit_id, _evaluation_order_for_test=_evaluation_order_for_test
    )


def _authorized_alternate_cluster(
    config: AlternateTopologyConfig, unit_id: str, token: object
) -> dict[str, Any]:
    if token is not _PRODUCTION_TOKEN:
        raise Gate12ProtocolError("Production execution capability is invalid")
    return _run_alternate_cluster(config, unit_id)


def validate_alternate_cluster_result(
    config: AlternateTopologyConfig, result: Mapping[str, Any]
) -> None:
    required = {
        "schema_version",
        "protocol_id",
        "protocol_namespace",
        "campaign_namespace",
        "campaign_id",
        "cell_id",
        "unit_id",
        "condition_execution_order",
        "seed_assignment",
        "rewiring",
        "conditions",
        "cluster_hash",
    }
    if set(result) != required or result.get("schema_version") != CLUSTER_RESULT_SCHEMA:
        raise Gate12InvariantError("Cluster result schema differs")
    unit_id = str(result["unit_id"])
    validate_alternate_unit_id(config, unit_id)
    if any(
        (
            result["protocol_id"] != config.protocol_id,
            result["protocol_namespace"] != config.protocol_namespace,
            result["campaign_namespace"] != config.campaign_namespace,
            result["campaign_id"] != config.campaign_id,
            result["cell_id"] != config.cell_id,
        )
    ):
        raise Gate12InvariantError("Cluster identity differs")
    if tuple(result["condition_execution_order"]) != alternate_condition_order(config, unit_id):
        raise Gate12InvariantError("Cluster condition order differs")
    expected_conditions = [
        "ring",
        *(f"realization-{index}" for index in range(config.realization_count)),
    ]
    if set(result["conditions"]) != set(expected_conditions):
        raise Gate12InvariantError("Cluster condition registry differs")
    if set(result["rewiring"]) != set(expected_conditions[1:]):
        raise Gate12InvariantError("Cluster rewiring registry differs")
    expected_seeds = to_primitive(select_seed_agents(config, unit_id))
    if result["seed_assignment"] != expected_seeds:
        raise Gate12InvariantError("Cluster seed assignment differs")
    for condition in expected_conditions:
        validate_condition_result(config, unit_id, result["conditions"][condition])
        if result["conditions"][condition]["condition_id"] != condition:
            raise Gate12InvariantError("Cluster condition stored under wrong identity")
    for realization in expected_conditions[1:]:
        value = result["rewiring"][realization]
        expected_edges = tuple(
            tuple(edge)
            for edge in result["conditions"][realization]["graph"]["undirected_edges"]
        )
        _validate_rewiring_record(config, value, expected_edges)
    draw_maps = []
    for condition in expected_conditions:
        draw_maps.append(
            {
                (item["source_agent_id"], item["recipient_agent_id"]): item["draw_u64"]
                for item in result["conditions"][condition]["opportunity_records"]
            }
        )
    for left_index, left in enumerate(draw_maps):
        for right in draw_maps[left_index + 1 :]:
            for key in set(left) & set(right):
                if left[key] != right[key]:
                    raise Gate12InvariantError("Cluster propagation draws differ by topology")
    if result["cluster_hash"] != canonical_hash(_cluster_identity(result)):
        raise Gate12InvariantError("Cluster content hash differs")


def standard_pair_contrast(result: Mapping[str, Any]) -> float:
    ring = result["conditions"]["ring"]["metrics"]["primary_endpoint"]
    rewired = result["conditions"]["rewired"]["metrics"]["primary_endpoint"]
    if ring["denominator"] != rewired["denominator"]:
        raise Gate12InvariantError("Matched pair denominators differ")
    return rewired["adopted_unseeded_count"] / rewired["denominator"] - (
        ring["adopted_unseeded_count"] / ring["denominator"]
    )


def alternate_cluster_contrast(result: Mapping[str, Any]) -> float:
    ring = result["conditions"]["ring"]["metrics"]["primary_endpoint"]
    realization_ids = sorted(key for key in result["conditions"] if key != "ring")
    if len(realization_ids) != 3:
        raise Gate12InvariantError("Alternate contrast requires exactly three realizations")
    rewired_incidences = []
    for realization_id in realization_ids:
        endpoint = result["conditions"][realization_id]["metrics"]["primary_endpoint"]
        if endpoint["denominator"] != ring["denominator"]:
            raise Gate12InvariantError("Cluster denominators differ")
        rewired_incidences.append(endpoint["adopted_unseeded_count"] / endpoint["denominator"])
    return sum(rewired_incidences) / 3 - ring["adopted_unseeded_count"] / ring["denominator"]


def ordered_unit_hash(results: Iterable[Mapping[str, Any]]) -> str:
    ordered = sorted(results, key=lambda result: str(result["unit_id"]))
    hashes = [result.get("pair_hash", result.get("cluster_hash")) for result in ordered]
    if any(value is None for value in hashes):
        raise Gate12InvariantError("Unit result lacks a content hash")
    return canonical_hash(hashes)


def _production_execution_token() -> object:
    """Storage-only capability; callers must first validate execution authorization."""

    return _PRODUCTION_TOKEN
