#!/usr/bin/env python3
"""Validate a compact local Gate 2 result package without provider access."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pasko_agent_society.gate2.evidence import verify_content_hash  # noqa: E402


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package")
    args = parser.parse_args(argv)
    root = Path(args.package).resolve()
    index = json.loads((root / "evidence-index.json").read_text())
    verify_content_hash(index)
    if index["publication_status"] != "LOCAL_CANDIDATE_NOT_PUBLISHED":
        raise RuntimeError("Unexpected publication status")
    for member in index["members"]:
        path = root / member["path"]
        if file_sha256(path) != member["sha256"]:
            raise RuntimeError(f"Package member hash differs: {member['path']}")
    passport = json.loads((root / "gate2_passport.json").read_text())
    validation = json.loads((root / "validation-report.json").read_text())
    analysis = json.loads((root / "primary-analysis.json").read_text())
    for value in (passport, validation, analysis):
        verify_content_hash(value)
    if analysis["analysis_run_count"] != 1 or validation["status"] != "PASS":
        raise RuntimeError("Analysis or validation status differs")
    if passport["gate2_1_started"] or validation["gate2_1_started"]:
        raise RuntimeError("Gate 2.1 must remain absent")
    print(json.dumps({"status": "PASS", "member_count": index["member_count"], "primary_decision": analysis["primary_decision"], "evidence_index_hash": index["content_hash"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
