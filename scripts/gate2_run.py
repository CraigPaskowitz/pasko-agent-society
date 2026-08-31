#!/usr/bin/env python3
"""Operator-owned OpenAI transport for the frozen Gate 2 campaign.

This is the sole live network boundary. It is not imported by the simulator,
tests, replay, verification, or analysis paths.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pasko_agent_society.canonical import canonical_hash  # noqa: E402
from pasko_agent_society.gate2.evidence import add_content_hash, sanitize_provider_value  # noqa: E402
from pasko_agent_society.gate2.manifest import load_campaign_spec  # noqa: E402
from pasko_agent_society.gate2.protocol import (  # noqa: E402
    CONDITIONS,
    MAX_INPUT_TOKENS,
    MODEL_ID,
    request_body,
    request_byte_identity,
)
from pasko_agent_society.gate2.runner import TransportOutcome, run_campaign  # noqa: E402
from pasko_agent_society.gate2.storage import CampaignPaths, atomic_write_json, read_json  # noqa: E402


RESPONSES_URL = "https://api.openai.com/v1/responses"
INPUT_TOKENS_URL = "https://api.openai.com/v1/responses/input_tokens"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def api_key() -> str:
    value = os.environ.get("OPENAI_API_KEY", "")
    if not value:
        raise RuntimeError("OPENAI_API_KEY is required only for the operator-owned live transport")
    return value


def _post_json(url: str, body: Mapping[str, Any], timeout: int) -> tuple[int, Mapping[str, Any], Mapping[str, str]]:
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=encoded,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "pasko-agent-society-gate2-v1",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = json.loads(response.read().decode("utf-8"))
        if not isinstance(raw, Mapping):
            raise RuntimeError("Provider response is not a JSON object")
        headers = {key.casefold(): value for key, value in response.headers.items()}
        return int(response.status), raw, headers


class OpenAIResponsesTransport:
    def __call__(self, body: Mapping[str, Any], timeout: int) -> TransportOutcome:
        try:
            status, raw, headers = _post_json(RESPONSES_URL, body, timeout)
            retry_after = headers.get("retry-after")
            return TransportOutcome(
                http_status=status,
                raw_response=raw,
                retry_after_seconds=float(retry_after) if retry_after else None,
            )
        except urllib.error.HTTPError as error:
            try:
                decoded = json.loads(error.read().decode("utf-8"))
                raw = decoded if isinstance(decoded, Mapping) else {"error": str(decoded)}
            except (UnicodeDecodeError, json.JSONDecodeError):
                raw = {"error": {"type": "unparseable_http_error", "message": str(error.reason)}}
            retry_after = error.headers.get("Retry-After") if error.headers else None
            status = int(error.code)
            return TransportOutcome(
                http_status=status,
                raw_response=raw,
                error_code=f"HTTP_{status}",
                error_message=str(error.reason),
                retryable=status in {408, 409, 429} or 500 <= status <= 599,
                retry_after_seconds=float(retry_after) if retry_after else None,
            )
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError) as error:
            return TransportOutcome(
                http_status=None,
                raw_response=None,
                error_code=type(error).__name__,
                error_message=str(error),
                retryable=True,
            )


def load_runtime(args: argparse.Namespace):
    root = Path(args.repository_root).resolve()
    spec = load_campaign_spec(root / args.manifest, require_certified=True)
    context = spec.context()
    paths = CampaignPaths(root / Path(*spec.artifact_root.parts))
    return root, spec, context, paths


def smoke_command(args: argparse.Namespace) -> int:
    body = {
        "model": MODEL_ID,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": "Return the fixed connectivity status object."}]}],
        "reasoning": {"effort": "none"},
        "temperature": 1.0,
        "max_output_tokens": 64,
        "service_tier": "default",
        "store": False,
        "tools": [],
        "text": {"format": {"type": "json_schema", "name": "gate2-provider-smoke-v1", "strict": True, "schema": {"type": "object", "additionalProperties": False, "properties": {"status": {"type": "string", "enum": ["OK"]}}, "required": ["status"]}}},
    }
    started = utc_now()
    outcome = OpenAIResponsesTransport()(body, 120)
    if outcome.http_status is None or not 200 <= outcome.http_status < 300 or outcome.raw_response is None:
        raise RuntimeError(f"Provider smoke test failed: {outcome.error_code}")
    record = add_content_hash(
        {
            "schema_version": "gate2-nonproduction-provider-smoke-v1",
            "identity": "NONPRODUCTION_PROVIDER_SMOKE_TEST",
            "scientifically_unrelated_to_T2_T5": True,
            "started_at": started,
            "completed_at": utc_now(),
            "request_hash": canonical_hash(body),
            "model_requested": MODEL_ID,
            "http_status": outcome.http_status,
            "sanitized_response": sanitize_provider_value(outcome.raw_response),
        }
    )
    output = Path(args.output)
    atomic_write_json(output, record)
    print(json.dumps({"status": "PASS", "record_hash": record["content_hash"], "output": str(output)}, indent=2))
    return 0


def count_tokens_command(args: argparse.Namespace) -> int:
    root, spec, _, _ = load_runtime(args)
    counts = {}
    evidence = {}
    for condition in CONDITIONS:
        body = request_body(root, condition)
        status, raw, _ = _post_json(INPUT_TOKENS_URL, body, 120)
        count = raw.get("input_tokens")
        if status != 200 or not isinstance(count, int) or not 0 < count <= MAX_INPUT_TOKENS:
            raise RuntimeError(f"Frozen {condition} request token count is invalid: {count}")
        counts[condition] = count
        evidence[condition] = sanitize_provider_value(raw)
    record = add_content_hash(
        {
            "schema_version": "gate2-input-token-count-v1",
            "identity": "NON_GENERATIVE_PROVIDER_INPUT_TOKEN_COUNT",
            "campaign_spec_hash": spec.spec_hash,
            "request_byte_identity": request_byte_identity(root),
            "counts": counts,
            "provider_evidence": evidence,
            "counted_at": utc_now(),
            "production_outcome_generating_calls": 0,
        }
    )
    output = Path(args.output)
    atomic_write_json(output, record)
    print(json.dumps({"status": "PASS", "counts": counts, "record_hash": record["content_hash"]}, indent=2))
    return 0


def run_command(args: argparse.Namespace) -> int:
    root, _, context, paths = load_runtime(args)
    authorization = read_json(Path(args.authorization))
    token_record = read_json(Path(args.input_token_count))
    if token_record.get("schema_version") != "gate2-input-token-count-v1":
        raise RuntimeError("Input-token count evidence is invalid")
    def report_progress(status: Mapping[str, Any]) -> None:
        # Deliberately outcome-blind: no condition-specific values are emitted.
        print(json.dumps({
            "operational_progress": {
                "valid_completed": status["valid_completed"],
                "pending_required": status["pending_required"],
                "technical_invalid": status["technical_invalid"],
                "checkpoint_hash": status["checkpoint_hash"],
                "integrity_status": status["integrity_status"],
            }
        }, sort_keys=True), flush=True)

    result = run_campaign(
        root,
        context,
        paths,
        transport=OpenAIResponsesTransport(),
        input_token_counts=token_record["counts"],
        authorization=authorization,
        progress=report_progress,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Pasko Agent Society Gate 2 live operator boundary")
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--manifest", default="manifests/gate2_peer_exposure_v1.json")
    commands = parser.add_subparsers(dest="command", required=True)
    smoke = commands.add_parser("smoke")
    smoke.add_argument("--output", required=True)
    smoke.set_defaults(handler=smoke_command)
    count = commands.add_parser("count-input-tokens")
    count.add_argument("--output", required=True)
    count.set_defaults(handler=count_tokens_command)
    run = commands.add_parser("run")
    run.add_argument("--authorization", required=True)
    run.add_argument("--input-token-count", required=True)
    run.set_defaults(handler=run_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
