"""Strict provider-response parser for the bounded Gate 2 action schema."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from .protocol import ALLOWED_ACTIONS, MODEL_ID, SERVICE_TIER, Gate2InvariantError


class ProviderIdentityError(Gate2InvariantError):
    """The provider returned an unauthorized model or service identity."""


@dataclass(frozen=True)
class ParsedBehavior:
    behavioral_valid: bool
    disposition: str
    action_type: str | None
    refusal_text: str | None
    technical_error_code: str | None
    provider_response_id: str | None
    returned_model: str | None
    returned_service_tier: str | None
    response_status: str | None
    usage: Mapping[str, Any]

    def as_mapping(self) -> dict[str, Any]:
        return {
            "behavioral_valid": self.behavioral_valid,
            "disposition": self.disposition,
            "action_type": self.action_type,
            "refusal_text": self.refusal_text,
            "technical_error_code": self.technical_error_code,
            "provider_response_id": self.provider_response_id,
            "returned_model": self.returned_model,
            "returned_service_tier": self.returned_service_tier,
            "response_status": self.response_status,
            "usage": dict(self.usage),
        }


def technical_behavior(
    code: str,
    *,
    response_id: str | None = None,
    returned_model: str | None = None,
    returned_service_tier: str | None = None,
    response_status: str | None = None,
    usage: Mapping[str, Any] | None = None,
) -> ParsedBehavior:
    return ParsedBehavior(
        behavioral_valid=False,
        disposition="TECHNICAL_FAILURE",
        action_type=None,
        refusal_text=None,
        technical_error_code=code,
        provider_response_id=response_id,
        returned_model=returned_model,
        returned_service_tier=returned_service_tier,
        response_status=response_status,
        usage=dict(usage or {}),
    )


def _response_identity(raw: Mapping[str, Any]) -> tuple[str | None, str | None, str | None, str | None, Mapping[str, Any]]:
    response_id = raw.get("id") if isinstance(raw.get("id"), str) else None
    model = raw.get("model") if isinstance(raw.get("model"), str) else None
    service_tier = raw.get("service_tier") if isinstance(raw.get("service_tier"), str) else None
    status = raw.get("status") if isinstance(raw.get("status"), str) else None
    usage = raw.get("usage") if isinstance(raw.get("usage"), Mapping) else {}
    if model is not None and model != MODEL_ID:
        raise ProviderIdentityError("Provider-returned model differs from the frozen snapshot")
    if service_tier is not None and service_tier != SERVICE_TIER:
        raise ProviderIdentityError("Provider-returned service tier differs from the frozen tier")
    return response_id, model, service_tier, status, usage


def parse_provider_response(raw: Mapping[str, Any]) -> ParsedBehavior:
    if not isinstance(raw, Mapping):
        return technical_behavior("MALFORMED_PROVIDER_OBJECT")
    response_id, model, service_tier, status, usage = _response_identity(raw)
    if status != "completed":
        code = "INCOMPLETE_OUTPUT" if status == "incomplete" else "NONCOMPLETED_PROVIDER_STATUS"
        return technical_behavior(
            code,
            response_id=response_id,
            returned_model=model,
            returned_service_tier=service_tier,
            response_status=status,
            usage=usage,
        )
    output = raw.get("output")
    if not isinstance(output, list):
        return technical_behavior(
            "MALFORMED_OUTPUT",
            response_id=response_id,
            returned_model=model,
            returned_service_tier=service_tier,
            response_status=status,
            usage=usage,
        )
    refusals: list[str] = []
    output_texts: list[str] = []
    for item in output:
        if not isinstance(item, Mapping) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, Mapping):
                continue
            if part.get("type") == "refusal" and isinstance(part.get("refusal"), str):
                refusals.append(str(part["refusal"]))
            elif part.get("type") == "output_text" and isinstance(part.get("text"), str):
                output_texts.append(str(part["text"]))
    if refusals:
        return ParsedBehavior(
            behavioral_valid=True,
            disposition="EXPLICIT_REFUSAL",
            action_type=None,
            refusal_text="\n".join(refusals),
            technical_error_code=None,
            provider_response_id=response_id,
            returned_model=model,
            returned_service_tier=service_tier,
            response_status=status,
            usage=dict(usage),
        )
    if len(output_texts) != 1:
        return technical_behavior(
            "MALFORMED_OUTPUT",
            response_id=response_id,
            returned_model=model,
            returned_service_tier=service_tier,
            response_status=status,
            usage=usage,
        )
    try:
        value = json.loads(output_texts[0])
    except json.JSONDecodeError:
        return technical_behavior(
            "MALFORMED_OUTPUT",
            response_id=response_id,
            returned_model=model,
            returned_service_tier=service_tier,
            response_status=status,
            usage=usage,
        )
    if (
        not isinstance(value, Mapping)
        or set(value) != {"action_type"}
        or value.get("action_type") not in ALLOWED_ACTIONS
    ):
        return technical_behavior(
            "SCHEMA_INVALID_OUTPUT",
            response_id=response_id,
            returned_model=model,
            returned_service_tier=service_tier,
            response_status=status,
            usage=usage,
        )
    return ParsedBehavior(
        behavioral_valid=True,
        disposition="VALID_ACTION",
        action_type=str(value["action_type"]),
        refusal_text=None,
        technical_error_code=None,
        provider_response_id=response_id,
        returned_model=model,
        returned_service_tier=service_tier,
        response_status=status,
        usage=dict(usage),
    )
