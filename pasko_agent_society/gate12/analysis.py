"""Frozen Gate 1.2 inference and joint-classification rules.

The pure functions accept already-complete vectors.  Artifact-backed analysis
is locked by ``storage.verify_suite_completion`` before these functions can be
called on production data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .manifest import GATE11_ESTIMATE, GATE11_STANDARD_ERROR, GATE11_SUPPORTED
from .registry import (
    ANALYSIS_SCHEMA,
    ALL_ROBUSTNESS_CONTRAST_IDS,
    EQUIVALENCE_MARGIN,
    PRACTICAL_MAGNITUDE_THRESHOLD,
    T_CRITICAL_2999,
    T_CRITICAL_999,
    T_CRITICAL_EQUIV_2999,
    T_CRITICAL_FAMILY_999,
    Gate12ProtocolError,
)


class AnalysisLockedError(RuntimeError):
    """Confirmatory analysis was requested before complete suite verification."""


@dataclass(frozen=True)
class MeanStatistics:
    independent_units: int
    estimate: float
    sample_variance: float
    standard_error: float
    degrees_of_freedom: int
    t_critical: float
    lower: float
    upper: float

    def as_mapping(self) -> dict[str, Any]:
        return {
            "independent_units": self.independent_units,
            "estimate": self.estimate,
            "sample_variance": self.sample_variance,
            "standard_error": self.standard_error,
            "degrees_of_freedom": self.degrees_of_freedom,
            "t_critical": self.t_critical,
            "lower": self.lower,
            "upper": self.upper,
        }


def paired_mean_statistics(
    differences: Sequence[float], *, expected_units: int, t_critical: float
) -> MeanStatistics:
    if len(differences) != expected_units or expected_units < 2:
        raise Gate12ProtocolError("Paired vector does not contain the frozen unit count")
    values = [float(value) for value in differences]
    if any(not math.isfinite(value) or not -1 <= value <= 1 for value in values):
        raise Gate12ProtocolError("Paired difference lies outside [-1, 1]")
    estimate = math.fsum(values) / expected_units
    variance = math.fsum((value - estimate) ** 2 for value in values) / (expected_units - 1)
    standard_error = math.sqrt(variance / expected_units)
    margin = t_critical * standard_error
    return MeanStatistics(
        independent_units=expected_units,
        estimate=estimate,
        sample_variance=variance,
        standard_error=standard_error,
        degrees_of_freedom=expected_units - 1,
        t_critical=t_critical,
        lower=estimate - margin,
        upper=estimate + margin,
    )


def hoeffding_interval(estimate: float, units: int, *, alpha: float = 0.05) -> dict[str, Any]:
    if units <= 0 or not 0 < alpha < 1:
        raise Gate12ProtocolError("Hoeffding inputs are invalid")
    half_width = math.sqrt(2 * math.log(2 / alpha) / units)
    return {
        "method": "two-sided-hoeffding-bounded-minus1-plus1",
        "alpha": alpha,
        "half_width": half_width,
        "lower": estimate - half_width,
        "upper": estimate + half_width,
        "certified_positive": estimate - half_width > 0,
    }


def exact_replication_statistics(differences: Sequence[float]) -> dict[str, Any]:
    stats = paired_mean_statistics(
        differences,
        expected_units=3000,
        t_critical=T_CRITICAL_2999,
    )
    return {
        "paired_difference": stats.as_mapping(),
        "directional_support": stats.lower > 0,
        "practical_magnitude": {
            "threshold": PRACTICAL_MAGNITUDE_THRESHOLD,
            "threshold_met": stats.estimate >= PRACTICAL_MAGNITUDE_THRESHOLD,
        },
        "hoeffding": hoeffding_interval(stats.estimate, 3000),
    }


def cross_gate_magnitude_consistency(
    replication_estimate: float,
    replication_standard_error: float,
    *,
    gate11_estimate: float = GATE11_ESTIMATE,
    gate11_standard_error: float = GATE11_STANDARD_ERROR,
) -> dict[str, Any]:
    if any(
        not math.isfinite(value) or value < 0
        for value in (replication_standard_error, gate11_standard_error)
    ):
        raise Gate12ProtocolError("Cross-gate standard error is invalid")
    contrast = replication_estimate - gate11_estimate
    standard_error = math.sqrt(replication_standard_error**2 + gate11_standard_error**2)
    ci90 = (
        contrast - T_CRITICAL_EQUIV_2999 * standard_error,
        contrast + T_CRITICAL_EQUIV_2999 * standard_error,
    )
    ci95 = (
        contrast - T_CRITICAL_2999 * standard_error,
        contrast + T_CRITICAL_2999 * standard_error,
    )
    if ci90[0] > -EQUIVALENCE_MARGIN and ci90[1] < EQUIVALENCE_MARGIN:
        classification = "consistent within five percentage points"
    elif ci95[0] > EQUIVALENCE_MARGIN or ci95[1] < -EQUIVALENCE_MARGIN:
        classification = "inconsistent by at least five percentage points"
    else:
        classification = "magnitude inconclusive"
    return {
        "gate1_1_estimate": gate11_estimate,
        "replication_estimate": replication_estimate,
        "contrast_replication_minus_gate1_1": contrast,
        "standard_error": standard_error,
        "equivalence_margin": EQUIVALENCE_MARGIN,
        "ci90": {"lower": ci90[0], "upper": ci90[1]},
        "ci95": {"lower": ci95[0], "upper": ci95[1]},
        "classification": classification,
    }


def alternate_cluster_contrast_from_counts(
    ring_adopted: int,
    rewired_adopted: Sequence[int],
    *,
    denominator: int = 54,
) -> float:
    if len(rewired_adopted) != 3:
        raise Gate12ProtocolError("Alternate cluster must contain exactly three rewired outcomes")
    counts = [ring_adopted, *rewired_adopted]
    if denominator <= 0 or any(not 0 <= count <= denominator for count in counts):
        raise Gate12ProtocolError("Alternate cluster count or denominator is invalid")
    mean_rewired = math.fsum(count / denominator for count in rewired_adopted) / 3
    return mean_rewired - ring_adopted / denominator


def robustness_family_statistics(
    contrast_vectors: Mapping[str, Sequence[float]],
) -> dict[str, Any]:
    if tuple(contrast_vectors) != ALL_ROBUSTNESS_CONTRAST_IDS:
        raise Gate12ProtocolError("Robustness family IDs or frozen order differ")
    cells: list[dict[str, Any]] = []
    for cell_id in ALL_ROBUSTNESS_CONTRAST_IDS:
        values = contrast_vectors[cell_id]
        unadjusted = paired_mean_statistics(
            values,
            expected_units=1000,
            t_critical=T_CRITICAL_999,
        )
        family_margin = T_CRITICAL_FAMILY_999 * unadjusted.standard_error
        cells.append(
            {
                "cell_id": cell_id,
                "estimate": unadjusted.estimate,
                "sample_variance": unadjusted.sample_variance,
                "standard_error": unadjusted.standard_error,
                "unadjusted_95": {
                    "lower": unadjusted.lower,
                    "upper": unadjusted.upper,
                    "t_critical": T_CRITICAL_999,
                },
                "bonferroni_simultaneous_95": {
                    "lower": unadjusted.estimate - family_margin,
                    "upper": unadjusted.estimate + family_margin,
                    "t_critical": T_CRITICAL_FAMILY_999,
                    "family_size": 11,
                },
            }
        )
    return {
        "family_size": 11,
        "independent_units_per_contrast": 1000,
        "cells": cells,
        "all_point_estimates_positive": all(cell["estimate"] > 0 for cell in cells),
        "strong_robustness_certified": all(
            cell["bonferroni_simultaneous_95"]["lower"] > 0 for cell in cells
        ),
        "strong_directional_reversal": any(
            cell["bonferroni_simultaneous_95"]["upper"] < 0 for cell in cells
        ),
    }


def joint_classification(
    *,
    campaigns_complete_and_valid: bool,
    gate11_supported: bool,
    replication_supported: bool,
    gate11_estimate: float,
    replication_estimate: float,
    robust_certified: bool,
    robust_all_positive: bool,
    robust_reversal: bool,
) -> dict[str, Any]:
    if gate11_supported and gate11_estimate <= 0:
        raise Gate12ProtocolError("Gate 1.1 support is inconsistent with its point estimate")
    if replication_supported and replication_estimate <= 0:
        raise Gate12ProtocolError("Replication support is inconsistent with its point estimate")
    if robust_certified and not robust_all_positive:
        raise Gate12ProtocolError("Strong robustness implies positive point estimates")
    if not campaigns_complete_and_valid:
        label = "invalid/inconclusive"
    elif gate11_supported and replication_supported and robust_certified:
        label = "replicated and robust"
    elif gate11_supported and replication_supported and not robust_all_positive:
        label = "replicated but specification-sensitive"
    elif gate11_supported and replication_supported and robust_all_positive and not robust_certified:
        label = "replicated; robustness directionally consistent but imprecise"
    elif gate11_estimate > 0 and replication_estimate > 0 and not (
        gate11_supported and replication_supported
    ):
        label = "directionally consistent but imprecise"
    elif gate11_supported and replication_estimate <= 0:
        label = "failed replication"
    elif (
        (not gate11_supported and replication_supported)
        or ((gate11_estimate > 0) != (replication_estimate > 0))
    ):
        label = "heterogeneous/inconclusive"
    elif (
        not gate11_supported
        and not replication_supported
        and gate11_estimate <= 0
        and replication_estimate <= 0
    ):
        label = "concordant non-support"
    else:
        raise Gate12ProtocolError("Classification inputs violate the frozen exhaustive domain")
    return {
        "classification": label,
        "strong_directional_reversal_present": robust_reversal,
        "components": {
            "S11": gate11_supported,
            "Srep": replication_supported,
            "P11": gate11_estimate > 0,
            "Prep": replication_estimate > 0,
            "Rcert": robust_certified,
            "Rsign": robust_all_positive,
            "Rreverse": robust_reversal,
        },
    }


def classify_with_published_gate11(
    *,
    campaigns_complete_and_valid: bool,
    replication_supported: bool,
    replication_estimate: float,
    robust_certified: bool,
    robust_all_positive: bool,
    robust_reversal: bool,
) -> dict[str, Any]:
    return joint_classification(
        campaigns_complete_and_valid=campaigns_complete_and_valid,
        gate11_supported=GATE11_SUPPORTED,
        replication_supported=replication_supported,
        gate11_estimate=GATE11_ESTIMATE,
        replication_estimate=replication_estimate,
        robust_certified=robust_certified,
        robust_all_positive=robust_all_positive,
        robust_reversal=robust_reversal,
    )


def _analysis_identity(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "content_hash"}


def validate_confirmatory_analysis(
    value: Mapping[str, Any],
    *,
    suite_id: str,
    suite_spec_hash: str,
    implementation_commit: str,
    implementation_source_hash: str,
    suite_completion_hash: str,
) -> None:
    from ..canonical import canonical_hash

    required = {
        "schema_version",
        "suite_id",
        "suite_spec_hash",
        "implementation_commit",
        "implementation_source_hash",
        "suite_completion_hash",
        "validity_status",
        "exact_replication",
        "cross_gate_magnitude",
        "robustness_family",
        "joint_classification",
        "content_hash",
    }
    if set(value) != required or value.get("schema_version") != ANALYSIS_SCHEMA:
        raise Gate12ProtocolError("Gate 1.2 analysis schema differs")
    expected = {
        "suite_id": suite_id,
        "suite_spec_hash": suite_spec_hash,
        "implementation_commit": implementation_commit,
        "implementation_source_hash": implementation_source_hash,
        "suite_completion_hash": suite_completion_hash,
        "validity_status": "VALID_COMPLETE",
    }
    if any(value[key] != item for key, item in expected.items()):
        raise Gate12ProtocolError("Gate 1.2 analysis identity differs")
    if value["content_hash"] != canonical_hash(_analysis_identity(value)):
        raise Gate12ProtocolError("Gate 1.2 analysis content hash differs")
    exact = value["exact_replication"]
    robust = value["robustness_family"]
    if exact["paired_difference"]["independent_units"] != 3000:
        raise Gate12ProtocolError("Exact-replication analysis unit count differs")
    if robust["family_size"] != 11 or len(robust["cells"]) != 11:
        raise Gate12ProtocolError("Robustness analysis family differs")
    if tuple(cell["cell_id"] for cell in robust["cells"]) != ALL_ROBUSTNESS_CONTRAST_IDS:
        raise Gate12ProtocolError("Robustness analysis cell order differs")


def analyze_completed_suite(
    *,
    contexts: Sequence[Any],
    paths_by_id: Mapping[str, Any],
    suite_completion_path: Path,
    analysis_path: Path,
) -> Mapping[str, Any]:
    """Open the confirmatory lock only after all 14,000 units verify.

    Existing valid analysis bytes are returned without recomputing.  The
    function deliberately has no partial-campaign mode.
    """

    from ..canonical import canonical_hash
    from .protocol import alternate_cluster_contrast, standard_pair_contrast
    from .registry import AlternateTopologyConfig, StandardConfig
    from .storage import (
        ChunkIntegrityError,
        atomic_write_json,
        load_completed_unit_results,
        read_json,
        verify_suite_completion,
    )

    completion = verify_suite_completion(contexts, paths_by_id, suite_completion_path)
    first = contexts[0]
    identities = {
        "suite_id": first.suite_id,
        "suite_spec_hash": first.suite_spec_hash,
        "implementation_commit": first.implementation_commit,
        "implementation_source_hash": first.implementation_source_hash,
        "suite_completion_hash": completion["content_hash"],
    }
    if analysis_path.exists():
        existing = read_json(analysis_path)
        validate_confirmatory_analysis(existing, **identities)
        return existing

    exact_differences: list[float] | None = None
    robustness_vectors: dict[str, list[float]] = {}
    for context in contexts:
        try:
            paths = paths_by_id[context.subcampaign_id]
        except KeyError as error:
            raise AnalysisLockedError("A required subcampaign path is absent") from error
        results = load_completed_unit_results(context, paths)
        config = context.config
        if isinstance(config, AlternateTopologyConfig):
            robustness_vectors[str(config.cell_id)] = [
                alternate_cluster_contrast(result) for result in results
            ]
        elif isinstance(config, StandardConfig) and config.cell_id is None:
            exact_differences = [standard_pair_contrast(result) for result in results]
        else:
            robustness_vectors[str(config.cell_id)] = [
                standard_pair_contrast(result) for result in results
            ]
    if exact_differences is None or tuple(robustness_vectors) != ALL_ROBUSTNESS_CONTRAST_IDS:
        raise AnalysisLockedError("The complete frozen campaign registry is not available")
    exact = exact_replication_statistics(exact_differences)
    magnitude = cross_gate_magnitude_consistency(
        exact["paired_difference"]["estimate"],
        exact["paired_difference"]["standard_error"],
    )
    robustness = robustness_family_statistics(robustness_vectors)
    classification = classify_with_published_gate11(
        campaigns_complete_and_valid=True,
        replication_supported=bool(exact["directional_support"]),
        replication_estimate=float(exact["paired_difference"]["estimate"]),
        robust_certified=bool(robustness["strong_robustness_certified"]),
        robust_all_positive=bool(robustness["all_point_estimates_positive"]),
        robust_reversal=bool(robustness["strong_directional_reversal"]),
    )
    value: dict[str, Any] = {
        "schema_version": ANALYSIS_SCHEMA,
        **identities,
        "validity_status": "VALID_COMPLETE",
        "exact_replication": exact,
        "cross_gate_magnitude": magnitude,
        "robustness_family": robustness,
        "joint_classification": classification,
    }
    value["content_hash"] = canonical_hash(value)
    try:
        atomic_write_json(
            analysis_path,
            value,
            validator=lambda item: validate_confirmatory_analysis(item, **identities),
        )
    except ChunkIntegrityError:
        raise
    return value
