"""Apply reviewed official-source research without pretending native features are SDK support."""

from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/tools/search_matrix"
RESEARCH = MATRIX / "research.json"


def cell(value, url, comment=""):
    return {"value": value, "source_url": url, "comment": comment}


def apply_research():
    audit = json.loads(RESEARCH.read_text())
    categorical = json.loads((MATRIX / "categorical-research.json").read_text())[
        "providers"
    ]
    existing = {
        p.stem: json.loads(p.read_text()) for p in (MATRIX / "data").glob("*.json")
    }
    for slug, review in audit["providers"].items():
        if slug not in existing and "name" not in review:
            continue  # shared research, e.g. SerpApi engine family
        if slug not in existing:
            url = review["source_url"]
            out = {
                "name": review["name"],
                "links": {"slug": slug, "docs": url, "website": review["website"]},
                "env_keys": cell(
                    "Not integrated",
                    url,
                    "Comparison only; anysearch does not read a key for this provider.",
                ),
                "python_extra": cell("Not integrated", url),
                "mode": {
                    "values": [],
                    "source_url": url,
                    "comment": "No unified SDK mode mapping.",
                },
                "p50_latency": cell("No current comparable measurement verified", url),
                "notes": "Comparison only; no anysearch SDK adapter is claimed.",
                "comparison_only": True,
            }
            if slug not in categorical:
                raise ValueError(f"Missing categorical research for {slug}")
            for key, native_cell in categorical[slug]["cells"].items():
                out[key] = {k: v for k, v in native_cell.items() if k != "prior_value"}
            out["mode"] = {
                k: v for k, v in categorical[slug]["mode"].items() if k != "prior_value"
            }
            existing[slug] = out
    for slug, out in existing.items():
        base = "serpapi" if slug.startswith("serpapi_") else slug
        review = audit["providers"].get(base)
        if not review:
            raise ValueError(f"Missing reviewed research for {slug}")
        url = review["source_url"]
        caveat = review.get("caveat", "")
        out["api_category"] = cell(review["category"], url)
        out["api_status"] = cell(review["status"], url, caveat)
        out["native_api"] = cell(review["overview"], url, caveat)
        out["rate_limits"] = cell(review["limits"], url, caveat)
        out["checked_at"] = cell(
            review["checked_at"],
            url,
            "Official public documentation reviewed; no paid API or benchmark run. "
            + caveat,
        )
        out["capability_basis"] = cell(
            "Native API — reviewed"
            if out.get("comparison_only")
            else "Existing SDK mappings",
            url,
            "SDK availability is separate from native provider capability. Each native feature cell carries its own checked date and evidence.",
        )
        out["sdk_support"] = cell(
            "Comparison only — no adapter"
            if out.get("comparison_only")
            else "Python + TypeScript adapters",
            out["links"].get(
                "github", "https://github.com/dhruv-anand-aintech/anysearch"
            ),
            "SDK adapter availability only. See Capability basis for the feature rows; native features do not imply an SDK adapter.",
        )
        out["pricing_per_1k"] = cell(
            review["pricing"],
            url,
            "Units and commitments differ; do not rank these as equivalent flat per-query prices. "
            + caveat,
        )
        out["pricing_per_1k"]["primary_price"] = review["primary_price"]
        out["pricing_per_1k"]["lowest_price"] = review["lowest_price"]
        out["free_tier_limits"] = cell(
            review["free"],
            url,
            "Trial, monthly credits and model-tool promotions are distinct. " + caveat,
        )
        for field in [
            "api_status",
            "native_api",
            "rate_limits",
            "checked_at",
            "pricing_per_1k",
            "free_tier_limits",
        ]:
            out[field]["links"] = {
                f"Official source {i + 1}": u
                for i, u in enumerate(review.get("sources", []))
            }
        out["evidence"] = {
            "checked_at": review["checked_at"],
            "source_urls": list(dict.fromkeys([url] + review.get("sources", []))),
            "effective_date": review.get("effective_date"),
            "method": "official documentation; no new benchmarks",
        }
        if slug in categorical:
            sources = [c["source_url"] for c in categorical[slug]["cells"].values()]
            sources += [
                u
                for c in categorical[slug]["cells"].values()
                for u in c.get("links", {}).values()
            ]
            sources.append(categorical[slug]["mode"]["source_url"])
            out["evidence"]["source_urls"] = list(
                dict.fromkeys(out["evidence"]["source_urls"] + sources)
            )
        if base == "google_pse" or base == "bing_legacy":
            out["deprecated"] = True
        # Keep historical benchmarks explicitly dated; a source review does not rerun them.
        if not out.get("comparison_only"):
            old = out["p50_latency"]
            old["value"] = "Historical July 2026: " + old["value"]
            old["comment"] = (
                "Historical evidence retained from July 2026; not remeasured or claimed current. "
                + old.get("comment", "")
            )
        (MATRIX / "data" / f"{slug}.json").write_text(json.dumps(out, indent=2) + "\n")
    lines = [
        "# New-column categorical coverage audit",
        "",
        "Checked 2026-10-21. Prior production values: 84 unknown feature cells and seven empty Mode lists. These were generated placeholders caused by equating no SDK adapter with unknown vendor capability. Native documentation is now a separate basis; existing SDK mappings are unchanged.",
        "",
        "Legend: full = supported; partial = indirect/conditional/limited; none = not exposed by the scoped documented contract; not_applicable = retired/different output abstraction; unknown = specifically undocumented after review, not assumed unsupported.",
        "",
        "| Provider | Row | Prior | Researched value | Checked | Evidence and scope |",
        "|---|---|---|---|---|---|",
    ]
    for slug, reviewed in categorical.items():
        for key, c in list(reviewed["cells"].items()) + [("mode", reviewed["mode"])]:
            value = c.get("support", ", ".join(c.get("values", [])))
            reason = c["comment"].replace("|", " / ")
            extra_links = " ".join(
                f"[{label}]({url})" for label, url in c.get("links", {}).items()
            )
            lines.append(
                f"| {slug} | {key} | {c['prior_value']} | {value} | {c['checked_at']} | [{reason}]({c['source_url']}) {extra_links} |"
            )
    (MATRIX / "categorical-coverage-audit.md").write_text("\n".join(lines) + "\n")
    return audit


if __name__ == "__main__":
    apply_research()
