#!/usr/bin/env python3
"""Comparative summary of WebKit reports; historical reports are never modified."""
from __future__ import annotations

import json
from pathlib import Path


def _reports(root: Path):
    for path in root.rglob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and isinstance(value.get("schema"), str):
            yield path, value


def _signature(report: dict) -> dict:
    schema = report.get("schema", "")
    events = report.get("events", [])
    names = [item.get("name") for item in events if isinstance(item, dict)] if isinstance(events, list) else []
    tests = report.get("tests", {}) if isinstance(report.get("tests"), dict) else {}
    if schema == "ns2-fontface-survey-safe-v2":
        getter = next((e for e in events if isinstance(e, dict) and e.get("name", "").startswith("getter")), {}) if isinstance(events, list) else {}
        return {"getterObserved": bool(getter), "getterInsideLoad": getter.get("info", {}).get("insideLoad"),
                "loadResolved": "resolved" in names, "matchingFaces": next((e.get("info", {}).get("matchingFaces") for e in events if isinstance(e, dict) and e.get("name") == "resolved"), None) if isinstance(events, list) else None}
    if "fontface" in schema:
        return {"verdict": report.get("verdict"), "eventNames": names}
    if "webkit-api-probe" in schema:
        return {"apis": report.get("apis", {}), "functional": report.get("functional", {})}
    return {"eventNames": names, "tests": tests}


def analyze_report(report: dict, root: Path) -> dict:
    schema = report.get("schema")
    previous = [(path, item) for path, item in _reports(root) if item.get("schema") == schema and item.get("reportId") != report.get("reportId")]
    previous.sort(key=lambda pair: str(pair[1].get("receivedAt", pair[1].get("timestamp", ""))))
    current = _signature(report)
    if not previous:
        return {"baseline": "none", "previousCount": 0, "current": current, "changes": []}
    baseline_path, baseline = previous[-1]
    old = _signature(baseline)
    keys = sorted(set(current) | set(old))
    changes = [{"field": key, "previous": old.get(key), "current": current.get(key)} for key in keys if old.get(key) != current.get(key)]
    return {"baseline": baseline_path.name, "previousCount": len(previous), "current": current, "previous": old, "changes": changes}


def build_summary(root: Path) -> dict:
    groups: dict[str, list[tuple[Path, dict]]] = {}
    for path, report in _reports(root):
        groups.setdefault(report["schema"], []).append((path, report))
    schemas = {}
    for schema, records in sorted(groups.items()):
        records.sort(key=lambda pair: str(pair[1].get("receivedAt", pair[1].get("timestamp", ""))))
        path, latest = records[-1]
        schemas[schema] = {"count": len(records), "latestFile": path.name,
                           "latestTimestamp": latest.get("receivedAt", latest.get("timestamp")),
                           "latest": _signature(latest)}
    return {"schema": "ns2-lab-summary-v1", "reportCount": sum(len(items) for items in groups.values()), "bySchema": schemas}
