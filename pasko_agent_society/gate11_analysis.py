"""Locked primary analysis for a complete, verified Gate 1.1 campaign."""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .canonical import canonical_hash
from .gate11_manifest import ANALYSIS_SCHEMA
from .gate11_protocol import T_CRITICAL_2999, Gate11ProtocolError
from .gate11_storage import (
    CampaignContext,
    CampaignIncompleteError,
    CampaignPaths,
    ChunkIntegrityError,
    _read_json,
    add_content_hash,
    atomic_write_json,
    load_pair_chunk,
    validate_completion_manifest,
    verify_content_hash,
)


class AnalysisLockedError(RuntimeError):
    """Primary inference is locked because completeness has not been proven."""


def paired_statistics_from_counts(
    ring_counts: Sequence[int],
    rewired_counts: Sequence[int],
    *,
    denominator: int,
    t_critical: float,
) -> dict[str, Any]:
    if len(ring_counts) != len(rewired_counts) or len(ring_counts) < 2:
        raise Gate11ProtocolError("Paired statistics require equal sequences with n >= 2")
    if denominator <= 0:
        raise Gate11ProtocolError("Primary denominator must be positive")
    if any(not 0 <= count <= denominator for count in (*ring_counts, *rewired_counts)):
        raise Gate11ProtocolError("Adoption count is outside the declared denominator")
    n = len(ring_counts)
    numerator_differences = [
        rewired - ring for ring, rewired in zip(ring_counts, rewired_counts, strict=True)
    ]
    differences = [difference / denominator for difference in numerator_differences]
    estimate = sum(differences) / n
    sample_variance = sum((difference - estimate) ** 2 for difference in differences) / (
        n - 1
    )
    standard_error = math.sqrt(sample_variance) / math.sqrt(n)
    primary_lower = estimate - t_critical * standard_error
    primary_upper = estimate + t_critical * standard_error
    hoeffding_half_width = math.sqrt(2 * math.log(40) / n)
    hoeffding_lower = max(-1.0, estimate - hoeffding_half_width)
    hoeffding_upper = min(1.0, estimate + hoeffding_half_width)
    return {
        "independent_matched_pairs": n,
        "primary_denominator_per_condition": denominator,
        "ring": {
            "adoption_count": sum(ring_counts),
            "denominator": n * denominator,
            "mean_incidence": sum(ring_counts) / (n * denominator),
        },
        "rewired": {
            "adoption_count": sum(rewired_counts),
            "denominator": n * denominator,
            "mean_incidence": sum(rewired_counts) / (n * denominator),
        },
        "paired_difference": {
            "estimand": "mean_rewired_minus_ring",
            "estimate": estimate,
            "numerator_difference_distribution": {
                str(value): count
                for value, count in sorted(Counter(numerator_differences).items())
            },
            "sample_variance": sample_variance,
            "standard_error": standard_error,
        },
        "primary_interval": {
            "method": "paired-mean-student",
            "degrees_of_freedom": n - 1,
            "t_critical": t_critical,
            "lower": primary_lower,
            "upper": primary_upper,
        },
        "directional_statistical_evidence": {
            "supported": primary_lower > 0,
            "rule": "complete_valid_and_primary_lower_bound_strictly_greater_than_zero",
        },
        "practical_magnitude": {
            "threshold": 0.05,
            "threshold_met": estimate >= 0.05,
        },
        "distribution_free_conservative_certification": {
            "method": "two-sided-hoeffding-bounded-minus1-plus1",
            "alpha": 0.05,
            "half_width": hoeffding_half_width,
            "lower": hoeffding_lower,
            "upper": hoeffding_upper,
            "certified_positive": hoeffding_lower > 0,
        },
    }


def _analysis_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "content_hash"}


def analyze_primary_campaign(
    context: CampaignContext,
    paths: CampaignPaths,
    *,
    completion_path: Path | None = None,
    output_path: Path | None = None,
) -> Mapping[str, Any]:
    """Open scientific outcomes only after the complete-campaign lock validates."""

    if context.config.campaign_namespace != "primary":
        raise AnalysisLockedError("Primary analysis accepts only the frozen primary namespace")
    completion_file = completion_path or paths.completion_manifest
    if not completion_file.exists():
        raise AnalysisLockedError("Completion manifest does not exist")
    try:
        completion = _read_json(completion_file)
        validate_completion_manifest(context, completion, paths=paths)
    except (ChunkIntegrityError, CampaignIncompleteError, Gate11ProtocolError) as error:
        raise AnalysisLockedError("Completion and integrity verification did not pass") from error
    if context.config.pair_count != 3000 or len(completion["ordered_chunks"]) != 3000:
        raise AnalysisLockedError("Primary analysis requires exactly 3,000 matched pairs")

    ring_counts: list[int] = []
    rewired_counts: list[int] = []
    for index, item in enumerate(completion["ordered_chunks"]):
        expected_pair_id = context.config.pair_id(index)
        if item["pair_id"] != expected_pair_id:
            raise AnalysisLockedError("Completion pair order differs")
        chunk = load_pair_chunk(
            context,
            paths.chunks / f"{expected_pair_id}.json",
            expected_pair_id=expected_pair_id,
        )
        if chunk["content_hash"] != item["chunk_hash"]:
            raise AnalysisLockedError("Completion chunk hash differs")
        pair = chunk["pair_result"]
        ring_counts.append(
            int(pair["conditions"]["ring"]["metrics"]["primary_endpoint"]["adopted_unseeded_count"])
        )
        rewired_counts.append(
            int(pair["conditions"]["rewired"]["metrics"]["primary_endpoint"]["adopted_unseeded_count"])
        )

    statistics = paired_statistics_from_counts(
        ring_counts,
        rewired_counts,
        denominator=54,
        t_critical=T_CRITICAL_2999,
    )
    if statistics["independent_matched_pairs"] != 3000:
        raise AnalysisLockedError("Primary analysis unit count differs")
    if statistics["primary_interval"]["degrees_of_freedom"] != 2999:
        raise AnalysisLockedError("Primary degrees of freedom differ")
    result = add_content_hash(
        {
            "schema_version": ANALYSIS_SCHEMA,
            "campaign_id": context.campaign_id,
            "campaign_spec_hash": context.campaign_spec_hash,
            "implementation_commit": context.implementation_commit,
            "implementation_source_hash": context.implementation_source_hash,
            "completion_manifest_hash": completion["content_hash"],
            "analysis_plan_id": "gate11-paired-mean-v1",
            "statistics": statistics,
            "decision": (
                "SUPPORT_H1"
                if statistics["directional_statistical_evidence"]["supported"]
                else "FAIL_TO_SUPPORT_H1"
            ),
            "claim_scope": "SCRIPTED_TOPOLOGY_PROPAGATION_ONLY",
            "llm_behavior_evidence": False,
        }
    )
    destination = output_path or paths.primary_analysis
    if destination.exists():
        existing = _read_json(destination)
        verify_content_hash(existing)
        if existing != result:
            raise ChunkIntegrityError("Existing primary analysis differs")
        return existing
    atomic_write_json(destination, result, validator=verify_content_hash)
    return result


def validate_primary_analysis(value: Mapping[str, Any]) -> None:
    if value.get("schema_version") != ANALYSIS_SCHEMA:
        raise ChunkIntegrityError("Primary analysis schema differs")
    verify_content_hash(value)
    if canonical_hash(_analysis_identity(value)) != value["content_hash"]:
        raise ChunkIntegrityError("Primary analysis identity differs")
