#!/usr/bin/env python3
"""Outcome-blind Gate 2 implementation certification validator."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pasko_agent_society.gate2.manifest import (  # noqa: E402
    implementation_source_hash,
    load_campaign_spec,
    verify_evidence_schema_files,
)
from pasko_agent_society.gate2.protocol import (  # noqa: E402
    GATE2_PREREGISTRATION_SHA256,
    request_byte_identity,
    verify_prompt_assets,
)


MANIFEST = ROOT / "manifests/gate2_peer_exposure_v1.json"
PACKAGE = ROOT / "pasko_agent_society/gate2"


def validate() -> dict[str, object]:
    spec = load_campaign_spec(MANIFEST)
    if hashlib.sha256((ROOT / "preregistrations/GATE_2_PREREGISTRATION.md").read_bytes()).hexdigest() != GATE2_PREREGISTRATION_SHA256:
        raise RuntimeError("Gate 2 preregistration bytes differ")
    assets = verify_prompt_assets(ROOT)
    request_identity = request_byte_identity(ROOT)
    if request_identity["canonical_byte_lengths"]["T2"] != request_identity["canonical_byte_lengths"]["T5"]:
        raise RuntimeError("T2/T5 request byte lengths differ")
    source_hash = implementation_source_hash(ROOT)
    evidence_schema_hashes = verify_evidence_schema_files(ROOT)
    if spec.implementation_status == "CERTIFIED_CANDIDATE" and source_hash != spec.implementation_source_hash:
        raise RuntimeError("Certified source bundle differs")
    forbidden = {"http", "requests", "socket", "subprocess", "urllib", "webbrowser"}
    findings = []
    for path in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [item.name for item in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if name.split(".")[0] in forbidden:
                    findings.append(f"{path.name}:{name}")
    if findings:
        raise RuntimeError(f"Deterministic package has external-I/O imports: {findings}")
    production_root = ROOT / "artifacts/gate2_peer_exposure_v1"
    if production_root.exists():
        raise RuntimeError("Gate 2 production artifact root exists during implementation certification")
    return {
        "schema_version": "gate2-implementation-validation-v1",
        "status": "PASS",
        "implementation_status": spec.implementation_status,
        "campaign_spec_hash": spec.spec_hash,
        "campaign_spec_file_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "source_bundle_sha256": source_hash,
        "preregistration_sha256": GATE2_PREREGISTRATION_SHA256,
        "prompt_asset_hashes": assets,
        "evidence_schema_hashes": evidence_schema_hashes,
        "request_byte_identity": request_identity,
        "deterministic_package_external_io_findings": findings,
        "production_outcome_generating_calls": 0,
        "production_artifact_root_exists": False,
    }


def main() -> int:
    print(json.dumps(validate(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
