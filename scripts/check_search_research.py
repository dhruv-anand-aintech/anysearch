#!/usr/bin/env python3
"""Validate evidence coverage and age; optionally check public source availability.

A link check never advances checked_at or invents a provider change.
"""

from __future__ import annotations
import argparse
import json
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/tools/search_matrix"


def validate_research(audit, today=None, max_age=45):
    today = today or date.today()
    errors = []
    for slug, row in audit["providers"].items():
        try:
            age = (today - date.fromisoformat(row["checked_at"])).days
        except (KeyError, ValueError):
            errors.append(f"{slug}: invalid checked_at")
            continue
        if age < 0 or age > max_age:
            errors.append(f"{slug}: review is {age} days old (limit {max_age})")
        for key in ["pricing", "free", "limits", "overview", "category", "status"]:
            if not row.get(key):
                errors.append(f"{slug}: missing {key}")
        if not row.get("source_url", "").startswith("https://"):
            errors.append(f"{slug}: missing HTTPS source")
        primary = row.get("primary_price", {})
        amount = primary.get("amount_usd_per_1k")
        if not primary or not primary.get("billing_unit") or not primary.get("basis"):
            errors.append(f"{slug}: primary pricing basis missing")
        if amount is not None and (
            isinstance(amount, bool)
            or not isinstance(amount, (int, float))
            or amount < 0
        ):
            errors.append(f"{slug}: invalid primary price")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-links", action="store_true")
    args = parser.parse_args()
    audit = json.loads((MATRIX / "research.json").read_text())
    errors = validate_research(audit)
    for path in (MATRIX / "data").glob("*.json"):
        row = json.loads(path.read_text())
        slug = row["links"]["slug"]
        base = "serpapi" if slug.startswith("serpapi_") else slug
        if base not in audit["providers"]:
            errors.append(f"{slug}: missing source review")
        if row.get("checked_at", {}).get("value") != audit["providers"].get(
            base, {}
        ).get("checked_at"):
            errors.append(f"{slug}: generated review date mismatch")
    report = []
    if args.check_links:
        urls = sorted(
            {
                u
                for r in audit["providers"].values()
                for u in [r["source_url"]] + r.get("sources", [])
            }
        )
        for url in urls:
            try:
                with urlopen(
                    Request(url, headers={"User-Agent": "Anysearch-source-audit/1.0"}),
                    timeout=15,
                ) as response:
                    report.append({"url": url, "status": response.status})
            except HTTPError as exc:
                report.append({"url": url, "status": exc.code, "review_needed": True})
            except (URLError, TimeoutError):
                report.append(
                    {"url": url, "status": "unreachable", "review_needed": True}
                )
        Path("source-check-report.json").write_text(
            json.dumps(
                {
                    "checked_on": date.today().isoformat(),
                    "links": report,
                    "note": "Availability only; no claim verification or checked_at changes.",
                },
                indent=2,
            )
            + "\n"
        )
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        f"research evidence: {len(audit['providers'])} families covered, dates valid; no paid calls"
    )


if __name__ == "__main__":
    main()
