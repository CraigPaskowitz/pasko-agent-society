#!/usr/bin/env python3
"""Conservative static release scan with no network or process dependency."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "pasko_agent_society"
IGNORED_PARTS = {".git", "__pycache__", "generated", ".venv"}
TEXT_SUFFIXES = {"", ".cff", ".json", ".md", ".py", ".toml", ".txt", ".yml", ".yaml"}
FORBIDDEN_IMPORT_ROOTS = {
    "ftplib",
    "http",
    "importlib",
    "paramiko",
    "playwright",
    "requests",
    "selenium",
    "socket",
    "subprocess",
    "telnetlib",
    "urllib",
    "webbrowser",
}


def repository_text_files() -> list[Path]:
    return [
        path
        for path in sorted(ROOT.rglob("*"))
        if path.is_file()
        and path.suffix.casefold() in TEXT_SUFFIXES
        and not any(part in IGNORED_PARTS for part in path.relative_to(ROOT).parts)
    ]


def scan_secrets(files: list[Path]) -> list[dict[str, str]]:
    prefix_cloud = "A" + "KIA"
    prefix_openai = "s" + "k-"
    prefix_github = "g" + "h[pousr]_"
    pem_marker = "BEGIN " + "PRIVATE KEY"
    patterns = {
        "cloud_access_key": re.compile(prefix_cloud + r"[0-9A-Z]{16}"),
        "provider_token": re.compile(prefix_openai + r"[A-Za-z0-9_-]{20,}"),
        "source_host_token": re.compile(prefix_github + r"[A-Za-z0-9]{30,}"),
        "private_key": re.compile(pem_marker),
    }
    findings = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in patterns.items():
            if pattern.search(text):
                findings.append({"file": str(path.relative_to(ROOT)), "kind": label})
    return findings


def scan_private_host_data(files: list[Path]) -> list[dict[str, str]]:
    unix_user_root = "/" + "Users/"
    linux_user_root = "/" + "home/"
    windows_user_root = "C:" + "\\\\Users\\\\"
    findings = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in (unix_user_root, linux_user_root, windows_user_root, "file:" + "//"):
            if marker in text:
                findings.append(
                    {"file": str(path.relative_to(ROOT)), "kind": "host_path_or_file_uri"}
                )
                break
    return findings


def scan_runtime_imports() -> list[dict[str, str]]:
    findings = []
    for path in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if name.split(".")[0] in FORBIDDEN_IMPORT_ROOTS:
                    findings.append(
                        {
                            "file": str(path.relative_to(ROOT)),
                            "kind": "forbidden_runtime_import",
                            "value": name,
                        }
                    )
    return findings


def scan_proprietary_markers() -> list[dict[str, str]]:
    markers = ("Open" + "Claw", "Pasko " + "Republic", "Study " + "Sunday")
    findings = []
    for path in sorted(PACKAGE.glob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in markers:
            if marker.casefold() in text.casefold():
                findings.append(
                    {
                        "file": str(path.relative_to(ROOT)),
                        "kind": "unrelated_repository_marker_in_implementation",
                        "value": marker,
                    }
                )
    return findings


def scan_offensive_capability() -> list[dict[str, str]]:
    forbidden_roots = {"impacket", "nmap", "scapy"}
    findings = []
    for path in sorted(PACKAGE.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if name.split(".")[0] in forbidden_roots:
                    findings.append(
                        {
                            "file": str(path.relative_to(ROOT)),
                            "kind": "offensive_security_dependency",
                            "value": name,
                        }
                    )
    return findings


def run_scan() -> dict[str, Any]:
    files = repository_text_files()
    categories = {
        "credentials_or_tokens": scan_secrets(files),
        "private_host_paths_or_file_uris": scan_private_host_data(files),
        "external_io_or_dynamic_imports": scan_runtime_imports(),
        "unrelated_repository_markers_in_code": scan_proprietary_markers(),
        "offensive_security_dependencies": scan_offensive_capability(),
    }
    return {
        "schema_version": "1.0.0",
        "files_scanned": len(files),
        "categories": {
            name: {"status": "PASS" if not findings else "FAIL", "findings": findings}
            for name, findings in categories.items()
        },
        "overall_status": "PASS" if not any(categories.values()) else "FAIL",
        "scope_note": (
            "Static scan covers repository text and experiment-package imports. "
            "Foundation documents may name public related projects; implementation code may not."
        ),
    }


def main() -> int:
    report = run_scan()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
