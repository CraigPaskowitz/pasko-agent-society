"""Strict loader for versioned, local-only Gate 1 experiment manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .canonical import to_primitive
from .fixtures import TREATMENTS
from .schemas import ENVIRONMENT_VERSION, SCHEMA_VERSION, ExperimentManifest


_SUITE_KEYS = {"schema_version", "suite_id", "repository_commit", "defaults", "experiments"}
_MANIFEST_KEYS = {
    "experiment_id",
    "environment_version",
    "agent_mechanism",
    "model_config",
    "population_size",
    "task_fixture",
    "policy_fixture",
    "communication_topology",
    "treatment",
    "seed_adopter_fraction",
    "replicate_count",
    "environment_seed",
    "assignment_seed",
    "validity_rules",
    "metrics",
}
_AGENT_KEYS = {
    "id",
    "type",
    "blocked_boundary_probability",
    "solvable_boundary_probability",
    "escalate_probability",
    "treatment_effects_encoded",
}
_TOPOLOGY_KEYS = {"topology_id", "communication_enabled"}


def load_manifest_suite(path: str | Path) -> tuple[str, tuple[ExperimentManifest, ...]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != _SUITE_KEYS:
        raise ValueError("Manifest suite has missing or unknown top-level fields")
    if data["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Unsupported manifest schema version")
    if _contains_external_configuration(data):
        raise ValueError("Manifest may not configure paths, URLs, commands, or credentials")
    defaults = data["defaults"]
    experiments = data["experiments"]
    if not isinstance(defaults, dict) or not isinstance(experiments, list):
        raise ValueError("Manifest defaults and experiments have invalid types")
    unknown_defaults = set(defaults) - _MANIFEST_KEYS
    if unknown_defaults:
        raise ValueError(f"Unknown manifest default fields: {sorted(unknown_defaults)}")
    resolved: list[ExperimentManifest] = []
    for override in experiments:
        if not isinstance(override, dict) or set(override) - _MANIFEST_KEYS:
            raise ValueError("Experiment has unknown fields")
        values = {**defaults, **override}
        if set(values) != _MANIFEST_KEYS:
            raise ValueError("Resolved experiment is missing fields")
        manifest = ExperimentManifest(
            experiment_id=str(values["experiment_id"]),
            schema_version=str(data["schema_version"]),
            environment_version=str(values["environment_version"]),
            agent_mechanism=dict(values["agent_mechanism"]),
            model_config=values["model_config"],
            population_size=int(values["population_size"]),
            task_fixture=str(values["task_fixture"]),
            policy_fixture=str(values["policy_fixture"]),
            communication_topology=dict(values["communication_topology"]),
            treatment=str(values["treatment"]),
            seed_adopter_fraction=float(values["seed_adopter_fraction"]),
            replicate_count=int(values["replicate_count"]),
            environment_seed=int(values["environment_seed"]),
            assignment_seed=int(values["assignment_seed"]),
            validity_rules=tuple(str(item) for item in values["validity_rules"]),
            metrics=tuple(str(item) for item in values["metrics"]),
            repository_commit=str(data["repository_commit"]),
        )
        validate_manifest(manifest)
        resolved.append(manifest)
    if len({manifest.treatment for manifest in resolved}) != len(resolved):
        raise ValueError("Each suite treatment must appear exactly once")
    return str(data["suite_id"]), tuple(resolved)


def validate_manifest(manifest: ExperimentManifest) -> None:
    if _contains_external_configuration(to_primitive(manifest)):
        raise ValueError("Manifest may not configure paths, URLs, commands, or credentials")
    if manifest.environment_version != ENVIRONMENT_VERSION:
        raise ValueError("Unsupported environment version")
    if manifest.treatment not in TREATMENTS:
        raise ValueError("Unknown treatment")
    treatment = TREATMENTS[manifest.treatment]
    if manifest.task_fixture != treatment.task_status.value:
        raise ValueError("Treatment and task fixture do not match")
    if manifest.policy_fixture != "gate1-toy-policy-v1":
        raise ValueError("Unknown policy fixture")
    if set(manifest.agent_mechanism) != _AGENT_KEYS:
        raise ValueError("Agent mechanism fields are not the bounded scripted schema")
    if manifest.agent_mechanism["type"] != "SCRIPTED_STOCHASTIC":
        raise ValueError("Gate 1 bootstrap supports the scripted mechanism only")
    if manifest.model_config is not None:
        raise ValueError("No live or configured model adapter exists in this bootstrap")
    if set(manifest.communication_topology) != _TOPOLOGY_KEYS:
        raise ValueError("Communication topology fields are invalid")
    if manifest.communication_topology != {
        "topology_id": "phase1-isolation-v1",
        "communication_enabled": False,
    }:
        raise ValueError("Phase 1 manifests must remain isolated")
    if manifest.population_size <= 0 or manifest.replicate_count <= 0:
        raise ValueError("Population and replicate counts must be positive")
    if manifest.seed_adopter_fraction != 0.0:
        raise ValueError("Phase 1 controlled exposure has no seed adopters")
    if not manifest.validity_rules or not manifest.metrics:
        raise ValueError("Validity rules and metrics must be declared")


def _contains_external_configuration(value: Any, parent_key: str = "") -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            lowered = str(key).casefold()
            if any(fragment in lowered for fragment in ("credential", "secret", "token", "url", "host_path", "command")):
                if lowered not in {"metrics"}:
                    return True
            if _contains_external_configuration(item, lowered):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_external_configuration(item, parent_key) for item in value)
    if isinstance(value, str):
        lowered = value.casefold()
        if "://" in lowered or value.startswith(("/", "~")) or "\\" in value:
            return True
        if lowered in {"bash", "curl", "powershell", "python", "sh", "ssh", "wget", "zsh"}:
            return True
    return False
