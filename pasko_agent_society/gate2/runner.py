"""Outcome-blind Gate 2 scheduler over an injected operator transport."""

from __future__ import annotations

import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from .evidence import (
    build_attempt_reservation,
    build_attempt_result,
    build_interrupted_attempt_result,
)
from .parser import parse_provider_response, technical_behavior
from .protocol import (
    HARD_COST_CEILING_USD,
    INPUT_PRICE_PER_MILLION,
    INPUT_TOKENS_PER_MINUTE,
    MAX_ATTEMPTS,
    MAX_INPUT_TOKENS,
    MAX_OUTPUT_TOKENS,
    OUTPUT_PRICE_PER_MILLION,
    REQUESTS_PER_MINUTE,
    REQUEST_TIMEOUT_SECONDS,
    Gate2InvariantError,
    build_request_record,
    condition_order,
    run_condition_from_behaviors,
    slot_id,
    target_order,
)
from .storage import (
    CampaignContext,
    CampaignPaths,
    attempt_reservation_path,
    attempt_result_path,
    attempt_results,
    build_population_chunk,
    operational_status,
    population_path,
    publish_attempt_reservation,
    publish_attempt_result,
    publish_population_chunk,
    publish_request,
    read_json,
    rebuild_checkpoint,
    terminal_behavior,
)


class Gate2ProviderBlocker(RuntimeError):
    """A provider/configuration condition cannot be repaired by slot retry."""


class Gate2BudgetBlocker(RuntimeError):
    """The next attempt would cross the frozen provider-spend ceiling."""


@dataclass(frozen=True)
class TransportOutcome:
    http_status: int | None
    raw_response: Mapping[str, Any] | None
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
    retry_after_seconds: float | None = None


Transport = Callable[[Mapping[str, Any], int], TransportOutcome]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def conservative_attempt_cost() -> float:
    return (
        MAX_INPUT_TOKENS * INPUT_PRICE_PER_MILLION
        + MAX_OUTPUT_TOKENS * OUTPUT_PRICE_PER_MILLION
    ) / 1_000_000


class BudgetLedger:
    def __init__(self, paths: CampaignPaths, ceiling: float = HARD_COST_CEILING_USD) -> None:
        self.paths = paths
        self.ceiling = ceiling
        self._lock = threading.Lock()
        self._reserved_count = self.reserved_attempt_count()

    def reserved_attempt_count(self) -> int:
        if not self.paths.attempts.exists():
            return 0
        return sum(1 for _ in self.paths.attempts.rglob("attempt-*-reservation.json"))

    def reserve(self) -> None:
        with self._lock:
            projected = (self._reserved_count + 1) * conservative_attempt_cost()
            if projected > self.ceiling + 1e-12:
                raise Gate2BudgetBlocker("Frozen $85 provider ceiling prevents another attempt")
            self._reserved_count += 1


class RollingRateLimiter:
    def __init__(self, *, requests_per_minute: int, input_tokens_per_minute: int) -> None:
        self.requests_per_minute = requests_per_minute
        self.input_tokens_per_minute = input_tokens_per_minute
        self._events: deque[tuple[float, int]] = deque()
        self._lock = threading.Lock()

    def acquire(self, estimated_input_tokens: int) -> None:
        if estimated_input_tokens > MAX_INPUT_TOKENS:
            raise Gate2ProviderBlocker("Frozen request exceeds the 1,200-token ceiling")
        while True:
            with self._lock:
                now = time.monotonic()
                while self._events and now - self._events[0][0] >= 60:
                    self._events.popleft()
                count_ok = len(self._events) < self.requests_per_minute
                tokens_ok = sum(tokens for _, tokens in self._events) + estimated_input_tokens <= self.input_tokens_per_minute
                if count_ok and tokens_ok:
                    self._events.append((now, estimated_input_tokens))
                    return
                wait_for = 60 - (now - self._events[0][0]) if self._events else 0.01
            time.sleep(max(0.01, min(wait_for, 1.0)))


def _technical_parsed(outcome: TransportOutcome):
    return technical_behavior(outcome.error_code or "TRANSPORT_FAILURE", response_status=None)


def _recover_reserved_attempt(paths: CampaignPaths, logical_slot_id: str, attempt: int) -> None:
    reservation_path = attempt_reservation_path(paths, logical_slot_id, attempt)
    result_path = attempt_result_path(paths, logical_slot_id, attempt)
    if reservation_path.exists() and not result_path.exists():
        reservation = read_json(reservation_path)
        publish_attempt_result(
            paths,
            build_interrupted_attempt_result(reservation, recovered_at=utc_now()),
        )


def _run_slot(
    repository_root: Path,
    context: CampaignContext,
    paths: CampaignPaths,
    pair_id: str,
    target_id: str,
    condition: str,
    *,
    transport: Transport,
    input_token_count: int,
    limiter: RollingRateLimiter,
    budget: BudgetLedger,
    sleep: Callable[[float], None] = time.sleep,
) -> Mapping[str, Any] | None:
    request = build_request_record(repository_root, context.config, pair_id, target_id, condition)
    publish_request(repository_root, context, paths, request)
    logical_slot_id = str(request["logical_slot_id"])
    for attempt in range(1, context.config.max_attempts + 1):
        _recover_reserved_attempt(paths, logical_slot_id, attempt)
        behavior = terminal_behavior(paths, logical_slot_id)
        if behavior is not None:
            return behavior
        result_path = attempt_result_path(paths, logical_slot_id, attempt)
        if result_path.exists():
            continue
        budget.reserve()
        reservation = build_attempt_reservation(
            logical_slot_id=logical_slot_id,
            request_record_hash=str(request["content_hash"]),
            request_content_hash=str(request["request_content_hash"]),
            attempt_number=attempt,
            reserved_at=utc_now(),
            conservative_cost_debit_usd=conservative_attempt_cost(),
        )
        publish_attempt_reservation(paths, reservation)
        limiter.acquire(input_token_count)
        started = utc_now()
        outcome = transport(request["request_body"], REQUEST_TIMEOUT_SECONDS)
        completed = utc_now()
        if (
            outcome.http_status is not None
            and 400 <= outcome.http_status <= 499
            and outcome.http_status not in {408, 409, 429}
        ):
            raise Gate2ProviderBlocker(
                f"Nonretryable provider configuration error {outcome.http_status}: {outcome.error_code}"
            )
        if outcome.raw_response is not None and outcome.http_status is not None and 200 <= outcome.http_status < 300:
            parsed = parse_provider_response(outcome.raw_response)
        else:
            parsed = _technical_parsed(outcome)
        result = build_attempt_result(
            logical_slot_id=logical_slot_id,
            request_record_hash=str(request["content_hash"]),
            request_content_hash=str(request["request_content_hash"]),
            attempt_number=attempt,
            started_at=started,
            completed_at=completed,
            http_status=outcome.http_status,
            parsed=parsed,
            raw_provider_response=outcome.raw_response,
            transport_error=(
                {"code": outcome.error_code, "message": outcome.error_message, "retryable": outcome.retryable}
                if not parsed.behavioral_valid
                else None
            ),
        )
        publish_attempt_result(paths, result)
        if parsed.behavioral_valid:
            return terminal_behavior(paths, logical_slot_id)
        if attempt < context.config.max_attempts:
            delay = max(float(outcome.retry_after_seconds or 0), float(2 ** (attempt - 1)))
            sleep(min(delay, 60.0))
    return None


def _slot_record(paths: CampaignPaths, pair_id: str, target_id: str, condition: str) -> dict[str, Any]:
    logical = slot_id(pair_id, target_id, condition)
    request = read_json(paths.requests / f"{logical.replace(':', '__')}.json")
    results = attempt_results(paths, logical)
    behavior = terminal_behavior(paths, logical)
    return {
        "pair_id": pair_id,
        "target_agent_id": target_id,
        "condition": condition,
        "logical_slot_id": logical,
        "request_record_hash": request["content_hash"],
        "request_content_hash": request["request_content_hash"],
        "attempt_hashes": [item["content_hash"] for item in results],
        "behavior": dict(behavior) if behavior is not None else None,
        "technical_error_codes": [item["technical_error_code"] for item in results if not item["behavioral_valid"]],
    }


def run_population(
    repository_root: Path,
    context: CampaignContext,
    paths: CampaignPaths,
    pair_id: str,
    *,
    transport: Transport,
    input_token_counts: Mapping[str, int],
    limiter: RollingRateLimiter,
    budget: BudgetLedger,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    if population_path(paths, pair_id).exists():
        return "resumed"

    def run_target(target_id: str) -> None:
        for condition in condition_order(context.config, pair_id, target_id):
            _run_slot(
                repository_root,
                context,
                paths,
                pair_id,
                target_id,
                condition,
                transport=transport,
                input_token_count=int(input_token_counts[condition]),
                limiter=limiter,
                budget=budget,
                sleep=sleep,
            )

    with ThreadPoolExecutor(max_workers=context.config.worker_count) as executor:
        futures = [executor.submit(run_target, target_id) for target_id in target_order(context.config, pair_id)]
        for future in futures:
            future.result()

    slots = [
        _slot_record(paths, pair_id, target_id, condition)
        for target_id in context.config.target_ids
        for condition in ("T2", "T5")
    ]
    unresolved = [item for item in slots if item["behavior"] is None]
    if unresolved:
        reasons = [
            f"{item['logical_slot_id']}:{','.join(item['technical_error_codes']) or 'NO_BEHAVIOR'}"
            for item in unresolved
        ]
        chunk = build_population_chunk(
            context,
            pair_id,
            slots,
            condition_results=None,
            invalid_reason_codes=reasons,
        )
    else:
        behaviors = {
            condition: {
                str(item["target_agent_id"]): item["behavior"]
                for item in slots
                if item["condition"] == condition
            }
            for condition in ("T2", "T5")
        }
        condition_results = {
            condition: run_condition_from_behaviors(context.config, pair_id, condition, behaviors[condition])
            for condition in ("T2", "T5")
        }
        chunk = build_population_chunk(
            context,
            pair_id,
            slots,
            condition_results=condition_results,
        )
    status = publish_population_chunk(context, paths, chunk)
    rebuild_checkpoint(context, paths)
    return status


def verify_execution_authorization(context: CampaignContext, authorization: Mapping[str, Any]) -> None:
    required = {
        "schema_version", "authorized", "campaign_id", "campaign_spec_hash",
        "implementation_commit", "implementation_source_hash", "preregistration_tag",
        "production_model_calls_before_authorization", "content_hash",
    }
    if set(authorization) != required or authorization.get("schema_version") != "gate2-execution-authorization-v1":
        raise Gate2ProviderBlocker("Execution authorization schema differs")
    identity = dict(authorization)
    supplied = identity.pop("content_hash")
    from ..canonical import canonical_hash
    if supplied != canonical_hash(identity):
        raise Gate2ProviderBlocker("Execution authorization hash differs")
    expected = {
        "authorized": True,
        "campaign_id": context.campaign_id,
        "campaign_spec_hash": context.campaign_spec_hash,
        "implementation_commit": context.implementation_commit,
        "implementation_source_hash": context.implementation_source_hash,
        "preregistration_tag": "gate2-prereg-v1",
        "production_model_calls_before_authorization": 0,
    }
    if any(authorization.get(key) != value for key, value in expected.items()):
        raise Gate2ProviderBlocker("Execution authorization identity differs")


def run_campaign(
    repository_root: Path,
    context: CampaignContext,
    paths: CampaignPaths,
    *,
    transport: Transport,
    input_token_counts: Mapping[str, int],
    authorization: Mapping[str, Any] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if context.config.campaign_namespace == "production":
        if authorization is None:
            raise Gate2ProviderBlocker("Production execution requires frozen authorization")
        verify_execution_authorization(context, authorization)
        if set(input_token_counts) != {"T2", "T5"} or any(
            not 0 < int(value) <= MAX_INPUT_TOKENS for value in input_token_counts.values()
        ):
            raise Gate2ProviderBlocker("Exact provider token counts are absent or above ceiling")
    limiter = RollingRateLimiter(
        requests_per_minute=REQUESTS_PER_MINUTE,
        input_tokens_per_minute=INPUT_TOKENS_PER_MINUTE,
    )
    budget = BudgetLedger(paths, context.config.hard_cost_ceiling_usd)
    for index in range(context.config.pair_pool_count):
        status = operational_status(context, paths)
        if status["valid_completed"] >= context.config.analyzed_pair_count:
            break
        pair_id = context.config.pair_id(index)
        run_population(
            repository_root,
            context,
            paths,
            pair_id,
            transport=transport,
            input_token_counts=input_token_counts,
            limiter=limiter,
            budget=budget,
            sleep=sleep,
        )
        if progress is not None:
            progress(operational_status(context, paths))
    final = operational_status(context, paths)
    if final["valid_completed"] < context.config.analyzed_pair_count:
        final["campaign_disposition"] = "INVALID_INCONCLUSIVE"
    else:
        final["campaign_disposition"] = "COMPLETE_PENDING_INTEGRITY_VERIFICATION"
    return final
