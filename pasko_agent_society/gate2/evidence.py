"""Canonical, sanitized provider-attempt evidence for Gate 2."""

from __future__ import annotations

from typing import Any, Mapping

from ..canonical import canonical_hash, to_primitive
from .parser import ParsedBehavior
from .protocol import Gate2InvariantError


SENSITIVE_KEYS = {
    "authorization",
    "api_key",
    "openai_api_key",
    "cookie",
    "set-cookie",
    "proxy-authorization",
}


def sanitize_provider_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): sanitize_provider_value(item)
            for key, item in value.items()
            if str(key).casefold() not in SENSITIVE_KEYS
        }
    if isinstance(value, list):
        return [sanitize_provider_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def add_content_hash(value: Mapping[str, Any]) -> dict[str, Any]:
    if "content_hash" in value:
        raise Gate2InvariantError("Caller cannot supply a content hash")
    output = to_primitive(dict(value))
    output["content_hash"] = canonical_hash(output)
    return output


def verify_content_hash(value: Mapping[str, Any]) -> None:
    identity = dict(value)
    supplied = identity.pop("content_hash", None)
    if supplied != canonical_hash(identity):
        raise Gate2InvariantError("Evidence content hash differs")


def build_attempt_reservation(
    *,
    logical_slot_id: str,
    request_record_hash: str,
    request_content_hash: str,
    attempt_number: int,
    reserved_at: str,
    conservative_cost_debit_usd: float,
) -> dict[str, Any]:
    return add_content_hash(
        {
            "schema_version": "gate2-attempt-reservation-v1",
            "logical_slot_id": logical_slot_id,
            "request_record_hash": request_record_hash,
            "request_content_hash": request_content_hash,
            "attempt_number": attempt_number,
            "reserved_at": reserved_at,
            "conservative_cost_debit_usd": conservative_cost_debit_usd,
        }
    )


def build_attempt_result(
    *,
    logical_slot_id: str,
    request_record_hash: str,
    request_content_hash: str,
    attempt_number: int,
    started_at: str,
    completed_at: str,
    http_status: int | None,
    parsed: ParsedBehavior,
    raw_provider_response: Mapping[str, Any] | None,
    transport_error: Mapping[str, Any] | None,
) -> dict[str, Any]:
    sanitized_raw = sanitize_provider_value(raw_provider_response) if raw_provider_response is not None else None
    sanitized_error = sanitize_provider_value(transport_error) if transport_error is not None else None
    return add_content_hash(
        {
            "schema_version": "gate2-provider-attempt-v1",
            "logical_slot_id": logical_slot_id,
            "request_record_hash": request_record_hash,
            "request_content_hash": request_content_hash,
            "attempt_number": attempt_number,
            "started_at": started_at,
            "completed_at": completed_at,
            "http_status": http_status,
            "provider_response_id": parsed.provider_response_id,
            "requested_model": "gpt-5.4-mini-2026-03-17",
            "returned_model": parsed.returned_model,
            "response_status": parsed.response_status,
            "returned_service_tier": parsed.returned_service_tier,
            "usage": dict(parsed.usage),
            "behavioral_valid": parsed.behavioral_valid,
            "disposition": parsed.disposition,
            "action_type": parsed.action_type,
            "refusal_status": parsed.disposition == "EXPLICIT_REFUSAL",
            "refusal_text": parsed.refusal_text,
            "technical_error_code": parsed.technical_error_code,
            "normalized_response": {
                "disposition": parsed.disposition,
                "action_type": parsed.action_type,
                "refusal": parsed.refusal_text,
            },
            "raw_provider_response": sanitized_raw,
            "raw_provider_response_hash": canonical_hash(sanitized_raw) if sanitized_raw is not None else None,
            "technical_error_metadata": sanitized_error,
        }
    )


def build_interrupted_attempt_result(
    reservation: Mapping[str, Any], *, recovered_at: str
) -> dict[str, Any]:
    verify_content_hash(reservation)
    parsed = ParsedBehavior(
        behavioral_valid=False,
        disposition="TECHNICAL_FAILURE",
        action_type=None,
        refusal_text=None,
        technical_error_code="INTERRUPTED_AFTER_DISPATCH_RESERVATION",
        provider_response_id=None,
        returned_model=None,
        returned_service_tier=None,
        response_status=None,
        usage={},
    )
    return build_attempt_result(
        logical_slot_id=str(reservation["logical_slot_id"]),
        request_record_hash=str(reservation["request_record_hash"]),
        request_content_hash=str(reservation["request_content_hash"]),
        attempt_number=int(reservation["attempt_number"]),
        started_at=str(reservation["reserved_at"]),
        completed_at=recovered_at,
        http_status=None,
        parsed=parsed,
        raw_provider_response=None,
        transport_error={"kind": "process_interruption", "message": "No received provider response was durably recorded"},
    )
