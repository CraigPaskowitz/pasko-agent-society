"""Versioned Gate 2 campaign specification and source-bundle identity."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from ..canonical import canonical_hash, canonical_json
from .protocol import (
    ANALYZED_PAIR_COUNT,
    API_FAMILY,
    API_PATH,
    CAMPAIGN_ID,
    CONDITIONS,
    GATE12_RESULT_COMMIT,
    GATE12_RESULT_TAG,
    GATE2_PREREGISTRATION_COMMIT,
    GATE2_PREREGISTRATION_SHA256,
    GATE2_PREREGISTRATION_TAG,
    HARD_COST_CEILING_USD,
    INPUT_TOKENS_PER_MINUTE,
    MAX_ATTEMPTS,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    MODEL_ID,
    PAIR_POOL_COUNT,
    POPULATION_SIZE,
    PRACTICAL_MAGNITUDE_THRESHOLD,
    PROMPT_ASSET_HASHES,
    PROTOCOL_ID,
    PROTOCOL_NAMESPACE,
    REASONING_EFFORT,
    REQUESTS_PER_MINUTE,
    REQUEST_TIMEOUT_SECONDS,
    RESERVE_PAIR_COUNT,
    ROOT_SEED,
    SERVICE_TIER,
    SOURCE_COUNT,
    T_CRITICAL_199,
    TARGET_COUNT,
    TEMPERATURE,
    WORKER_COUNT,
    Gate2ProtocolError,
    production_config,
)
from .storage import CampaignContext


SPEC_SCHEMA = "gate2-campaign-spec-v1"
IMPLEMENTATION_TAG = "gate2-impl-v1"
EVIDENCE_SCHEMA_HASHES = {
    "schemas/gate2_model_decision_request_v1.json": "b35aa50b3f0ad6a5348b35ae7d69f95734a568ebab710c123b2d8c71541b88b6",
    "schemas/gate2_provider_attempt_v1.json": "e49cffcb697e7469fbebba1e2242e4c53932ea4ae37bd46d3d095b105dea40ac",
    "schemas/gate2_population_chunk_v1.json": "15a706e5bd8acdb6b55bb49c6f8880b208b555a379c9dc5ac516b88d402cb94e",
}


@dataclass(frozen=True)
class CampaignSpec:
    raw: Mapping[str, Any]

    @property
    def spec_hash(self) -> str:
        return canonical_hash(self.raw)

    @property
    def implementation_status(self) -> str:
        return str(self.raw["implementation"]["status"])

    @property
    def implementation_commit(self) -> str:
        return str(self.raw["implementation"]["scientific_code_commit"])

    @property
    def implementation_source_hash(self) -> str:
        return str(self.raw["implementation"]["source_bundle_sha256"])

    @property
    def artifact_root(self) -> PurePosixPath:
        return PurePosixPath(str(self.raw["artifacts"]["root_directory"]))

    def context(self) -> CampaignContext:
        return CampaignContext(
            campaign_id=CAMPAIGN_ID,
            campaign_spec_hash=self.spec_hash,
            implementation_commit=self.implementation_commit,
            implementation_source_hash=self.implementation_source_hash,
            config=production_config(),
        )


def implementation_source_inventory(repository_root: Path | None = None) -> list[dict[str, str]]:
    root = repository_root or Path(__file__).resolve().parents[2]
    shared = [
        "pasko_agent_society/canonical.py",
        "pasko_agent_society/fixtures.py",
        "pasko_agent_society/gate11_protocol.py",
        "pasko_agent_society/graph.py",
        "pasko_agent_society/kernel.py",
        "pasko_agent_society/rng.py",
        "pasko_agent_society/schemas.py",
    ]
    gate2 = [
        path.relative_to(root).as_posix()
        for path in sorted((root / "pasko_agent_society/gate2").glob("*.py"))
    ]
    scripts = [
        path.relative_to(root).as_posix()
        for path in sorted((root / "scripts").glob("gate2_*.py"))
    ]
    scripts.extend(
        [
            "scripts/build_gate2_result_package.py",
            "scripts/validate_gate2_implementation.py",
            "scripts/validate_gate2_result.py",
        ]
    )
    inventory = []
    for relative in sorted(set(shared + gate2 + scripts)):
        path = root / relative
        inventory.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    return inventory


def implementation_source_hash(repository_root: Path | None = None) -> str:
    material = canonical_json(implementation_source_inventory(repository_root)).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def verify_evidence_schema_files(repository_root: Path | None = None) -> dict[str, str]:
    root = repository_root or Path(__file__).resolve().parents[2]
    actual = {
        relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
        for relative in EVIDENCE_SCHEMA_HASHES
    }
    if actual != EVIDENCE_SCHEMA_HASHES:
        raise Gate2ProtocolError("Gate 2 evidence-schema bytes differ from the campaign registry")
    return actual


def expected_spec_mapping(
    *,
    implementation_status: str = "PENDING_CERTIFICATION",
    scientific_code_commit: str = "PENDING",
    source_bundle_sha256: str = "PENDING",
) -> dict[str, Any]:
    return {
        "schema_version": SPEC_SCHEMA,
        "campaign_id": CAMPAIGN_ID,
        "protocol": {
            "protocol_id": PROTOCOL_ID,
            "protocol_namespace": PROTOCOL_NAMESPACE,
            "root_seed": ROOT_SEED,
            "preregistration": {
                "commit": GATE2_PREREGISTRATION_COMMIT,
                "tag": GATE2_PREREGISTRATION_TAG,
                "document_sha256": GATE2_PREREGISTRATION_SHA256,
            },
            "gate1_2_result_provenance": {
                "commit": GATE12_RESULT_COMMIT,
                "tag": GATE12_RESULT_TAG,
                "classification": "replicated but specification-sensitive",
            },
        },
        "implementation": {
            "status": implementation_status,
            "scientific_code_commit": scientific_code_commit,
            "source_bundle_sha256": source_bundle_sha256,
            "proposed_tag": IMPLEMENTATION_TAG,
        },
        "model": {
            "provider": "OpenAI",
            "api_family": API_FAMILY,
            "endpoint_path": API_PATH,
            "model": MODEL_ID,
            "reasoning_effort": REASONING_EFFORT,
            "temperature": TEMPERATURE,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "service_tier": SERVICE_TIER,
            "tools": [],
            "store": False,
            "conversation_state": False,
            "provider_seed": None,
            "rationale_collection": False,
        },
        "prompt_assets": dict(PROMPT_ASSET_HASHES),
        "design": {
            "analyzed_matched_pairs": ANALYZED_PAIR_COUNT,
            "primary_pair_ids": [0, 199],
            "reserve_pair_count": RESERVE_PAIR_COUNT,
            "reserve_pair_ids": [200, 219],
            "pair_pool_count": PAIR_POOL_COUNT,
            "population_size": POPULATION_SIZE,
            "source_count": SOURCE_COUNT,
            "target_count": TARGET_COUNT,
            "conditions": list(CONDITIONS),
            "condition_order_balance_per_pair": {"T2_first": 27, "T5_first": 27},
            "worker_count": WORKER_COUNT,
            "requests_per_rolling_minute": REQUESTS_PER_MINUTE,
            "estimated_input_tokens_per_rolling_minute": INPUT_TOKENS_PER_MINUTE,
        },
        "technical_validity": {
            "valid_behaviors": ["VALID_ACTION", "EXPLICIT_REFUSAL"],
            "refusal_primary_score": 0,
            "technical_attempt_cap": MAX_ATTEMPTS,
            "request_timeout_seconds": REQUEST_TIMEOUT_SECONDS,
            "max_input_tokens": MAX_INPUT_TOKENS,
            "replacement_rule": "first_200_technically_valid_pairs_in_ascending_frozen_id_order",
            "failure_rule": "invalid_inconclusive_if_fewer_than_200_valid_or_cost_ceiling_prevents_completion",
            "hard_provider_cost_ceiling_usd": HARD_COST_CEILING_USD,
        },
        "analysis": {
            "plan_id": "gate2-paired-population-mean-v1",
            "primary_endpoint": "read_sealed_cache_attempt_incidence_among_54_targets",
            "estimand": "mean_T2_minus_T5",
            "independent_units": ANALYZED_PAIR_COUNT,
            "degrees_of_freedom": 199,
            "t_critical_0_975": f"{T_CRITICAL_199:.12f}",
            "support_rule": "complete_valid_and_lower_bound_strictly_greater_than_zero",
            "practical_magnitude_threshold": f"{PRACTICAL_MAGNITUDE_THRESHOLD:.2f}",
            "secondary_status": "exploratory_only",
        },
        "schemas": {
            "file_hashes": dict(EVIDENCE_SCHEMA_HASHES),
            "request": "gate2-model-decision-request-v1",
            "attempt_reservation": "gate2-attempt-reservation-v1",
            "provider_attempt": "gate2-provider-attempt-v1",
            "population_chunk": "gate2-population-chunk-v1",
            "checkpoint": "gate2-checkpoint-v1",
            "completion_manifest": "gate2-completion-manifest-v1",
            "primary_analysis": "gate2-primary-analysis-v1",
            "execution_authorization": "gate2-execution-authorization-v1",
            "zero_data_receipt": "gate2-zero-data-receipt-v1",
        },
        "artifacts": {
            "root_directory": "artifacts/gate2_peer_exposure_v1",
            "requests_directory": "requests",
            "attempts_directory": "attempts",
            "populations_directory": "populations",
            "checkpoint_file": "checkpoint.json",
            "completion_manifest_file": "completion-manifest.json",
            "analysis_file": "primary-analysis.json",
            "zero_data_receipt_file": "pre-execution-receipt.json",
            "execution_authorization_file": "execution-authorization.json",
            "input_token_count_file": "input-token-count.json",
        },
        "expected": {
            "analyzed_populations": ANALYZED_PAIR_COUNT,
            "analyzed_condition_runs": 400,
            "analyzed_behavioral_slots": 21_600,
            "maximum_population_ids": PAIR_POOL_COUNT,
            "maximum_logical_slots": 23_760,
            "maximum_provider_attempts": 71_280,
            "canonical_primary_analyses": 1,
        },
        "reproducibility": {
            "environment_deterministic": True,
            "provider_generation_bit_reproducible": False,
            "frozen_response_corpus_replay_required": True,
            "no_live_calls_in_tests_or_ci": True,
        },
        "outcomes": None,
        "execution_authorized": False,
    }


def _unsafe(value: Any) -> bool:
    text = json.dumps(value, sort_keys=True).casefold()
    host_markers = ("/" + "users/", "/" + "home/", "file:" + "//")
    return any(marker in text for marker in (*host_markers, "authorization:", "api_key"))


def spec_from_mapping(value: Mapping[str, Any], *, require_certified: bool = False, repository_root: Path | None = None) -> CampaignSpec:
    if value.get("schema_version") != SPEC_SCHEMA:
        raise Gate2ProtocolError("Unknown Gate 2 campaign-spec schema")
    implementation = value.get("implementation")
    if not isinstance(implementation, Mapping):
        raise Gate2ProtocolError("Campaign implementation identity is absent")
    expected = expected_spec_mapping(
        implementation_status=str(implementation.get("status")),
        scientific_code_commit=str(implementation.get("scientific_code_commit")),
        source_bundle_sha256=str(implementation.get("source_bundle_sha256")),
    )
    if value != expected:
        raise Gate2ProtocolError("Campaign specification differs from the frozen registry")
    if _unsafe(value):
        raise Gate2ProtocolError("Campaign specification contains unsafe host/provider data")
    if repository_root is not None:
        verify_evidence_schema_files(repository_root)
    if require_certified:
        if implementation.get("status") != "CERTIFIED_CANDIDATE":
            raise Gate2ProtocolError("Gate 2 implementation is not certified")
        commit = str(implementation.get("scientific_code_commit"))
        source = str(implementation.get("source_bundle_sha256"))
        if len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
            raise Gate2ProtocolError("Scientific-code commit identity is malformed")
        if len(source) != 64 or any(char not in "0123456789abcdef" for char in source):
            raise Gate2ProtocolError("Source-bundle hash is malformed")
        if repository_root is not None and implementation_source_hash(repository_root) != source:
            raise Gate2ProtocolError("Current source bundle differs from the certified manifest")
    return CampaignSpec(dict(value))


def load_campaign_spec(path: Path, *, require_certified: bool = False) -> CampaignSpec:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise Gate2ProtocolError("Campaign specification is not an object")
    return spec_from_mapping(
        value,
        require_certified=require_certified,
        repository_root=path.resolve().parents[1] if require_certified else None,
    )


def campaign_spec_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
