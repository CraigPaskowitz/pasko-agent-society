"""Matched population execution, passports, replay, and deterministic ordering."""

from __future__ import annotations

import platform
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .agents import ScriptedParameters, ScriptedStochasticAgent
from .canonical import canonical_hash, to_primitive
from .fixtures import BOUNDARY_RULE_ID, POLICY, TREATMENTS, task_for_treatment
from .graph import CommunicationGraph, empty_graph
from .kernel import EnvironmentKernel
from .manifest import validate_manifest
from .metrics import compute_population_metrics, primary_boundary_effect, validity_counts
from .rng import stable_order
from .schemas import (
    ActionIntent,
    ActionType,
    AgentOutcome,
    ExperimentManifest,
    ExperimentPassport,
    TaskStatus,
    ValidityStatus,
)


@dataclass(frozen=True)
class PopulationResult:
    experiment_id: str
    treatment: str
    replicate_id: str
    validity_status: ValidityStatus
    outcomes: tuple[AgentOutcome, ...]
    actions: tuple[Mapping[str, Any], ...]
    metrics: Mapping[str, Any]
    passport: ExperimentPassport
    actions_hash: str
    result_hash: str


def assignment_for(
    manifest: ExperimentManifest, replicate_id: str
) -> tuple[dict[str, Any], ...]:
    agent_ids = [f"agent-{index:03d}" for index in range(manifest.population_size)]
    randomized = stable_order(
        agent_ids, manifest.assignment_seed, replicate_id, "matched-assignment"
    )
    rank = {agent_id: index for index, agent_id in enumerate(randomized)}
    return tuple(
        {
            "agent_id": agent_id,
            "agent_mechanism_id": manifest.agent_mechanism["id"],
            "matched_assignment_rank": rank[agent_id],
            "replicate_id": replicate_id,
        }
        for agent_id in sorted(agent_ids)
    )


def run_population(
    manifest: ExperimentManifest,
    replicate_index: int,
    *,
    graph: CommunicationGraph | None = None,
) -> PopulationResult:
    validate_manifest(manifest)
    replicate_id = f"replicate-{replicate_index:03d}"
    treatment = TREATMENTS[manifest.treatment]
    task = task_for_treatment(manifest.treatment)
    assignments = assignment_for(manifest, replicate_id)
    agent_ids = tuple(item["agent_id"] for item in assignments)
    communication_graph = graph or empty_graph()
    kernel = EnvironmentKernel(
        experiment_id=manifest.experiment_id,
        replicate_id=replicate_id,
        task=task,
        treatment=treatment,
        agent_ids=agent_ids,
        graph=communication_graph,
    )
    mechanism = ScriptedStochasticAgent(
        parameters=ScriptedParameters.from_mapping(manifest.agent_mechanism),
        environment_seed=manifest.environment_seed,
        replicate_id=replicate_id,
    )
    actions: list[Mapping[str, Any]] = []
    boundary_attempted: set[str] = set()
    boundary_decisions: dict[str, tuple[str, str]] = {}
    for tick in range(1, task.max_rounds + 1):
        kernel.advance_tick()
        for agent_id in agent_ids:
            agent_state = kernel.state["agents"][agent_id]
            intent = mechanism.propose(
                agent_id=agent_id,
                tick=tick,
                task_status=task.status,
                has_artifact=bool(agent_state["delivered_artifacts"]),
                boundary_attempted=agent_id in boundary_attempted,
                terminal_recorded=agent_state["first_terminal_action"] is not None,
            )
            if intent is None:
                continue
            if (
                tick == 5
                and task.status is TaskStatus.BLOCKED
                and bool(agent_state["delivered_artifacts"])
            ):
                with_exposure = ActionType(intent.action_type).value
                without_exposure = mechanism.boundary_decision(
                    agent_id, task.status, exposure_removed=True
                ).value
                boundary_decisions[agent_id] = (with_exposure, without_exposure)
            actions.append(to_primitive(intent))
            resolution = kernel.resolve(intent)
            if (
                ActionType(intent.action_type) is ActionType.READ_SEALED_CACHE
                and not resolution.permitted
                and resolution.policy_rule_id == BOUNDARY_RULE_ID
            ):
                boundary_attempted.add(agent_id)
    outcomes = _outcomes_from_kernel(
        kernel,
        agent_ids,
        communication_graph,
        boundary_decisions,
    )
    messages = tuple(kernel.state["messages"].values())
    metrics = compute_population_metrics(outcomes, task.status, messages)
    passport = ExperimentPassport(
        experiment_id=manifest.experiment_id,
        schema_version=manifest.schema_version,
        repository_commit=manifest.repository_commit,
        environment_version=manifest.environment_version,
        manifest_hash=canonical_hash(manifest),
        task_hash=canonical_hash(task),
        policy_hash=canonical_hash(POLICY),
        graph_hash=communication_graph.graph_hash,
        assignment_hash=canonical_hash(assignments),
        treatment=manifest.treatment,
        agent_mechanism_id=str(manifest.agent_mechanism["id"]),
        model_configuration=manifest.model_config,
        model_call_provenance_hashes=(),
        simulator_seed=manifest.environment_seed,
        assignment_seed=manifest.assignment_seed,
        replicate_id=replicate_id,
        validity_status=ValidityStatus.VALID,
        event_ledger_hash=kernel.event_ledger_hash,
        final_state_hash=kernel.final_state_hash,
        metrics_hash=canonical_hash(metrics),
        runtime_metadata={
            "implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "platform_system": platform.system(),
            "execution_mode": "SCRIPTED_LOCAL_ONLY",
            "external_io_capability": False,
        },
    )
    actions_hash = canonical_hash(actions)
    result_identity = {
        "experiment_id": manifest.experiment_id,
        "treatment": manifest.treatment,
        "replicate_id": replicate_id,
        "event_ledger_hash": passport.event_ledger_hash,
        "final_state_hash": passport.final_state_hash,
        "metrics_hash": passport.metrics_hash,
        "actions_hash": actions_hash,
    }
    return PopulationResult(
        experiment_id=manifest.experiment_id,
        treatment=manifest.treatment,
        replicate_id=replicate_id,
        validity_status=ValidityStatus.VALID,
        outcomes=outcomes,
        actions=tuple(actions),
        metrics=metrics,
        passport=passport,
        actions_hash=actions_hash,
        result_hash=canonical_hash(result_identity),
    )


def _outcomes_from_kernel(
    kernel: EnvironmentKernel,
    agent_ids: tuple[str, ...],
    graph: CommunicationGraph,
    boundary_decisions: Mapping[str, tuple[str, str]],
) -> tuple[AgentOutcome, ...]:
    attempts: dict[str, list[int]] = {agent_id: [] for agent_id in agent_ids}
    for event in kernel.ledger:
        if (
            event["event_type"] == "ACTION_REJECTED"
            and event["payload"]["action_type"] == ActionType.READ_SEALED_CACHE.value
            and event["payload"]["policy_rule_id"] == BOUNDARY_RULE_ID
            and event["actor_id"] in attempts
        ):
            attempts[event["actor_id"]].append(event["tick"])
    outcomes: list[AgentOutcome] = []
    for agent_id in agent_ids:
        state = kernel.state["agents"][agent_id]
        boundary_exposures = [
            exposure
            for exposure in state["exposures"]
            if exposure.get("originating_strategy") == ActionType.READ_SEALED_CACHE.value
        ]
        exposure_tick = (
            min(exposure["tick"] for exposure in boundary_exposures)
            if boundary_exposures
            else None
        )
        decision_pair = boundary_decisions.get(agent_id, (None, None))
        outcomes.append(
            AgentOutcome(
                agent_id=agent_id,
                boundary_attempt_ticks=tuple(attempts[agent_id]),
                boundary_exposure_tick=exposure_tick,
                first_terminal_action=state["first_terminal_action"],
                terminal_tick=state["terminal_tick"],
                abstain_ticks=tuple(state["abstain_ticks"]),
                solution_valid=bool(
                    kernel.state["submissions"].get(agent_id, {}).get("valid", False)
                ),
                strategy_source_id=(
                    "fixture-controlled-peer-note" if boundary_exposures else None
                ),
                decision_with_exposure=decision_pair[0],
                decision_without_exposure=decision_pair[1],
                degree_centrality=graph.degree_centrality(agent_id, len(agent_ids)),
            )
        )
    return tuple(outcomes)


def run_ensemble(
    manifests: Sequence[ExperimentManifest], *, parallelism: int = 1
) -> tuple[PopulationResult, ...]:
    jobs = [
        (manifest, replicate_index)
        for manifest in manifests
        for replicate_index in range(manifest.replicate_count)
    ]
    if parallelism <= 0:
        raise ValueError("parallelism must be positive")
    if parallelism == 1:
        results = [run_population(manifest, index) for manifest, index in jobs]
    else:
        with ThreadPoolExecutor(max_workers=parallelism) as executor:
            futures = [
                executor.submit(run_population, manifest, index)
                for manifest, index in jobs
            ]
            results = [future.result() for future in futures]
    return tuple(
        sorted(results, key=lambda item: (item.treatment, item.replicate_id))
    )


def replay_population(
    manifest: ExperimentManifest,
    replicate_index: int,
    recorded_actions: Sequence[Mapping[str, Any]],
) -> dict[str, str | bool]:
    replicate_id = f"replicate-{replicate_index:03d}"
    treatment = TREATMENTS[manifest.treatment]
    task = task_for_treatment(manifest.treatment)
    assignments = assignment_for(manifest, replicate_id)
    kernel = EnvironmentKernel(
        experiment_id=manifest.experiment_id,
        replicate_id=replicate_id,
        task=task,
        treatment=treatment,
        agent_ids=tuple(item["agent_id"] for item in assignments),
        graph=empty_graph(),
    )
    by_tick: dict[int, list[Mapping[str, Any]]] = {}
    for action in recorded_actions:
        by_tick.setdefault(int(action["tick"]), []).append(action)
    for tick in range(1, task.max_rounds + 1):
        kernel.advance_tick()
        for action in by_tick.get(tick, []):
            kernel.resolve(
                ActionIntent(
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
            )
    return {
        "event_ledger_hash": kernel.event_ledger_hash,
        "final_state_hash": kernel.final_state_hash,
        "actions_hash": canonical_hash(list(recorded_actions)),
    }


def summarize_ensemble(
    suite_id: str, results: Sequence[PopulationResult]
) -> dict[str, Any]:
    by_treatment: dict[str, list[PopulationResult]] = {}
    for result in results:
        by_treatment.setdefault(result.treatment, []).append(result)
    treatment_summaries: dict[str, Any] = {}
    all_outcomes: dict[str, list[AgentOutcome]] = {}
    for treatment, treatment_results in sorted(by_treatment.items()):
        outcomes = [
            outcome
            for result in treatment_results
            for outcome in result.outcomes
            if result.validity_status is ValidityStatus.VALID
        ]
        all_outcomes[treatment] = outcomes
        population_statuses = [result.validity_status for result in treatment_results]
        task_status = TREATMENTS[treatment].task_status
        aggregate_metrics = compute_population_metrics(outcomes, task_status)
        aggregate_metrics["time_to_adoption"] = _summarize_population_adoption_times(
            treatment_results
        )
        treatment_summaries[treatment] = {
            "task_fixture": task_status.value,
            "population_runs": validity_counts(population_statuses),
            "agent_runs": {
                "attempted": sum(len(result.outcomes) for result in treatment_results),
                "valid": len(outcomes),
                "invalid": sum(len(result.outcomes) for result in treatment_results)
                - len(outcomes),
            },
            "metrics": aggregate_metrics,
        }
    primary = (
        primary_boundary_effect(all_outcomes["T2"], all_outcomes["T5"])
        if "T2" in all_outcomes and "T5" in all_outcomes
        else None
    )
    validity = validity_counts([result.validity_status for result in results])
    result_hashes = [result.result_hash for result in results]
    return {
        "schema_version": "1.0.0",
        "suite_id": suite_id,
        "scope": "SCRIPTED_INFRASTRUCTURE_DEMONSTRATION_ONLY",
        "llm_behavior_evidence": False,
        "causal_language": {
            "mechanical": "The toy policy rule mechanically rejected every READ_SEALED_CACHE intent.",
            "exposure_provenance": "Artifact delivery records establish what entered each observation bundle before action.",
            "experimental": "T2 minus T5 is a matched scripted treatment contrast, not an LLM claim.",
        },
        "population_runs": validity,
        "treatments": treatment_summaries,
        "primary_estimand": primary,
        "ordered_result_hashes_hash": canonical_hash(result_hashes),
    }


def ensemble_identity(results: Iterable[PopulationResult]) -> str:
    return canonical_hash([result.result_hash for result in results])


def _summarize_population_adoption_times(
    results: Sequence[PopulationResult],
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for quantile in ("0.1", "0.25", "0.5"):
        declared = [result.metrics["time_to_adoption"][quantile] for result in results]
        ticks = [item["tick"] for item in declared if not item["censored"]]
        tick_counts = Counter(ticks)
        summary[quantile] = {
            "population_runs": len(declared),
            "reached_populations": len(ticks),
            "censored_populations": len(declared) - len(ticks),
            "event_tick_distribution": {
                str(tick): tick_counts[tick] for tick in sorted(tick_counts)
            },
        }
    return summary
