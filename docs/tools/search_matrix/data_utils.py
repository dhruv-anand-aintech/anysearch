#!/usr/bin/env python3
"""Validate, bundle, and export the search provider capability matrix."""

from __future__ import annotations

import argparse
import glob
import json
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

MATRIX_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = MATRIX_DIR / "schema.json"
DATA_GLOB = str(MATRIX_DIR / "data" / "*.json")
BUNDLE_PATH = MATRIX_DIR / "bundle.json"
UPDATED_PATH = MATRIX_DIR / "updated.json"
LLMS_PATH = MATRIX_DIR / "llms.txt"


def _load_json(path: Path) -> OrderedDict:
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=OrderedDict)


def _schema_columns(schema: dict) -> list[tuple[str, str, str]]:
    out = []
    for key, spec in schema.get("properties", {}).items():
        if key in ("links", "notes"):
            continue
        parts = (spec.get("$comment") or key).split("|")
        parts = [p.strip() for p in parts]
        group = parts[0] if len(parts) > 0 else "Other"
        label = parts[1] if len(parts) > 1 else key
        out.append((key, group, label))
    return out


def _validate_feature(filename: str, key: str, value: object) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{filename}: {key} must be an object")
    support = value.get("support")
    if support not in {"", "none", "partial", "full", "unknown"}:
        raise ValueError(f"{filename}: {key}.support invalid: {support!r}")
    for req in ("source_url", "comment"):
        if req not in value or not isinstance(value[req], str):
            raise ValueError(f"{filename}: {key}.{req} must be a string")


def _validate_string_field(filename: str, key: str, value: object) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{filename}: {key} must be an object")
    for req in ("value", "source_url", "comment"):
        if req not in value or not isinstance(value[req], str):
            raise ValueError(f"{filename}: {key}.{req} must be a string")


def validate() -> None:
    schema = _load_json(SCHEMA_PATH)
    properties = schema.get("properties", {})
    required = list(schema.get("required", []))
    feature_keys = [
        k
        for k, spec in properties.items()
        if spec.get("allOf", [{}])[0].get("$ref", "").endswith("featureWithSource")
    ]
    string_keys = [
        k
        for k, spec in properties.items()
        if spec.get("allOf", [{}])[0].get("$ref", "").endswith("stringWithSource")
    ]

    for filename in sorted(glob.glob(DATA_GLOB)):
        data = _load_json(Path(filename))
        missing = [k for k in required if k not in data]
        if missing:
            raise ValueError(f"{filename}: missing keys: {', '.join(missing)}")
        links = data.get("links")
        if not isinstance(links, dict) or not links.get("slug"):
            raise ValueError(f"{filename}: links.slug required")
        for key in feature_keys:
            if key in data:
                _validate_feature(filename, key, data[key])
        for key in string_keys:
            if key in data:
                _validate_string_field(filename, key, data[key])
        print("ok", Path(filename).name)

    print("validate: all files passed")


def bundle() -> None:
    rows = [_load_json(Path(f)) for f in sorted(glob.glob(DATA_GLOB))]
    rows.sort(key=lambda r: r.get("name", ""))
    BUNDLE_PATH.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    UPDATED_PATH.write_text(
        json.dumps({"updated_at": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"bundle: wrote {len(rows)} providers to {BUNDLE_PATH}")


def llms_txt() -> None:
    schema = _load_json(SCHEMA_PATH)
    rows = json.loads(BUNDLE_PATH.read_text(encoding="utf-8"))
    cols = _schema_columns(schema)
    feature_cols = [
        (k, g, l)
        for k, g, l in cols
        if k not in ("name", "env_keys", "python_extra", "requires_key", "mode_notes", "snippet")
    ]

    lines = [
        "# anysearch Search API Provider Matrix",
        "",
        f"Providers: {len(rows)}. Unified parameters and response fields supported via anysearch.",
        "",
    ]
    for row in rows:
        lines.append(f"## {row['name']}")
        lines.append(f"- Docs: {row['links']['docs']}")
        lines.append(f"- Env: {row['env_keys']['value']}")
        for key, _g, label in feature_cols:
            cell = row.get(key, {})
            sup = cell.get("support", "") if isinstance(cell, dict) else ""
            if sup:
                lines.append(f"- {label}: {sup}")
        lines.append("")
    LLMS_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"llms-txt: wrote {LLMS_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["validate", "bundle", "llms-txt"])
    args = parser.parse_args()
    if args.command == "validate":
        validate()
    elif args.command == "bundle":
        bundle()
    else:
        llms_txt()


if __name__ == "__main__":
    main()
