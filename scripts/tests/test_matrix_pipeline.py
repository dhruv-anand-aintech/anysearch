import importlib.util
import json
import re
import unittest
import tempfile
import subprocess
from unittest.mock import patch
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


check = module("check", "scripts/check_search_research.py")
change = module("change", "scripts/generate_matrix_changelog.py")
data = module("data", "docs/tools/search_matrix/data_utils.py")


class PipelineTests(unittest.TestCase):
    def test_review_expiry_and_future_dates(self):
        audit = json.loads(
            (ROOT / "docs/tools/search_matrix/research.json").read_text()
        )
        self.assertEqual(check.validate_research(audit, today=date(2026, 10, 22)), [])
        self.assertTrue(check.validate_research(audit, today=date(2027, 1, 1)))
        self.assertTrue(check.validate_research(audit, today=date(2026, 1, 1)))

    def test_all_new_categorical_cells_have_individual_evidence(self):
        folder = ROOT / "docs/tools/search_matrix"
        review = json.loads((folder / "categorical-research.json").read_text())
        self.assertEqual(len(review["providers"]), 8)
        self.assertEqual(sum(len(p["cells"]) for p in review["providers"].values()), 96)
        for slug, native in review["providers"].items():
            row = json.loads((folder / "data" / (slug + ".json")).read_text())
            if slug == "bing_legacy":
                self.assertTrue(row["comparison_only"])
                self.assertEqual(row["mode"]["values"], native["mode"]["values"])
                for key, source in native["cells"].items():
                    self.assertEqual(row[key]["support"], source["support"])
                    self.assertEqual(row[key]["source_url"], source["source_url"])
                    self.assertEqual(row[key]["checked_at"], source["checked_at"])
                    self.assertGreater(len(source["comment"]), 40)
                    self.assertNotIn(
                        "No anysearch adapter; see native", row[key]["comment"]
                    )
            else:
                self.assertNotIn("comparison_only", row)
                self.assertEqual(
                    row["sdk_support"]["value"], "Python + TypeScript adapters"
                )
        self.assertEqual(
            review["providers"]["bing_legacy"]["cells"]["snippet"]["support"],
            "not_applicable",
        )
        self.assertEqual(
            review["providers"]["deepseek"]["cells"]["snippet"]["support"], "full"
        )
        self.assertEqual(
            review["providers"]["tinyfish"]["cells"]["news"]["support"], "full"
        )
        self.assertEqual(
            review["providers"]["tinyfish"]["cells"]["safe_search"]["support"], "none"
        )
        self.assertEqual(
            review["providers"]["tinyfish"]["cells"]["content"]["support"], "partial"
        )

    def test_explicit_primary_price_metadata(self):
        rows = json.loads((ROOT / "docs/tools/search_matrix/bundle.json").read_text())
        by_slug = {r["links"]["slug"]: r for r in rows}
        self.assertEqual(
            by_slug["deepseek"]["pricing_per_1k"]["primary_price"]["amount_usd_per_1k"],
            0.75,
        )
        self.assertEqual(
            by_slug["keiro"]["pricing_per_1k"]["primary_price"]["amount_usd_per_1k"],
            0.10,
        )
        for slug in ["jina", "firecrawl", "bing_legacy", "google_pse"]:
            self.assertIsNone(
                by_slug[slug]["pricing_per_1k"]["primary_price"]["amount_usd_per_1k"]
            )
        for row in rows:
            self.assertTrue(row["pricing_per_1k"]["primary_price"]["billing_unit"])
            self.assertTrue(
                row["pricing_per_1k"]["primary_price"]["source_url"].startswith(
                    "https://"
                )
            )

    def test_lowest_documented_price_drives_sorting(self):
        rows = json.loads((ROOT / "docs/tools/search_matrix/bundle.json").read_text())
        by_slug = {r["links"]["slug"]: r for r in rows}
        for row in rows:
            lowest = row["pricing_per_1k"]["lowest_price"]
            primary = row["pricing_per_1k"]["primary_price"]
            for field in ("billing_unit", "basis", "checked_at"):
                self.assertTrue(lowest.get(field), row["links"]["slug"] + ": " + field)
            self.assertTrue(lowest["source_url"].startswith("https://"))
            low, high = lowest["amount_usd_per_1k"], primary["amount_usd_per_1k"]
            if isinstance(low, (int, float)) and isinstance(high, (int, float)):
                self.assertLessEqual(low, high, row["links"]["slug"])
        # $0 self-hosted software and an open library are not hosted per-1K rates.
        for slug in ("searxng", "duckduckgo"):
            self.assertIsNone(
                by_slug[slug]["pricing_per_1k"]["lowest_price"]["amount_usd_per_1k"]
            )
            self.assertEqual(
                by_slug[slug]["pricing_per_1k"]["primary_price"]["amount_usd_per_1k"], 0
            )
        # Volume and annual tiers rank by the cheapest documented rate.
        self.assertEqual(
            by_slug["keiro"]["pricing_per_1k"]["lowest_price"]["amount_usd_per_1k"],
            0.03,
        )
        self.assertEqual(
            by_slug["serpapi_google"]["pricing_per_1k"]["lowest_price"][
                "amount_usd_per_1k"
            ],
            9.17,
        )
        self.assertEqual(
            by_slug["serper"]["pricing_per_1k"]["lowest_price"]["amount_usd_per_1k"],
            0.30,
        )
        self.assertEqual(
            by_slug["searchapi"]["pricing_per_1k"]["lowest_price"]["amount_usd_per_1k"],
            2.0,
        )
        ranked = [
            row["pricing_per_1k"]["lowest_price"]["amount_usd_per_1k"] for row in rows
        ]
        self.assertNotIn(0, [amount for amount in ranked if amount is not None])

    def test_changelog_entries_are_versioned(self):
        history = json.loads(
            (ROOT / "docs/tools/search_matrix/changelog.json").read_text()
        )
        pattern = re.compile(r"^1\.\d+\.\d+$")
        self.assertRegex(history["version"], pattern)
        self.assertEqual(history["version"], history["entries"][0]["version"])
        for entry in history["entries"]:
            self.assertRegex(entry["version"], pattern)
        self.assertEqual(history["entries"][-1]["version"], "1.0.0")
        versions = [tuple(map(int, e["version"].split("."))) for e in history["entries"]]
        self.assertEqual(versions, sorted(versions, reverse=True))
        self.assertEqual(history["version"], ".".join(map(str, versions[0])))

    def test_new_provider_has_cell_target(self):
        row = {
            "name": "DeepSeek",
            "links": {"slug": "deepseek"},
            "requires_key": {"support": "unknown"},
        }
        items = change.changes_for_pair(None, row, row, {})
        self.assertEqual(
            items,
            [
                {
                    "summary": "DeepSeek added to the comparison",
                    "target": "cell-deepseek-requires-key",
                }
            ],
        )

    def test_evidence_not_fabricated_as_product_history(self):
        row = {
            "name": "X",
            "links": {"slug": "x"},
            "evidence": {"checked_at": "2026-10-21"},
        }
        self.assertEqual(
            change.changes_for_pair({**row, "evidence": {}}, row, row, {}), []
        )

    def test_untracked_provider_is_in_changelog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            matrix = root / "matrix"
            (matrix / "data").mkdir(parents=True)

            def git(*args):
                subprocess.run(
                    ["git", *args], cwd=root, check=True, capture_output=True
                )

            git("init")
            git("config", "user.email", "test@example.invalid")
            git("config", "user.name", "Test")
            (matrix / "schema.json").write_text('{"properties":{}}')
            git("add", ".")
            git("commit", "-m", "fixture")
            (matrix / "data/new.json").write_text(
                json.dumps(
                    {
                        "name": "New",
                        "links": {"slug": "new"},
                        "requires_key": {"support": "unknown"},
                    }
                )
            )
            with (
                patch.object(change, "ROOT", root),
                patch("sys.argv", ["changelog", "--matrix-dir", "matrix"]),
            ):
                change.main()
            history = json.loads((matrix / "changelog.json").read_text())
            self.assertEqual(history["entry_count"], 1)
            self.assertEqual(
                history["entries"][0]["items"][0]["target"], "cell-new-requires-key"
            )

    def test_generated_coverage_and_comparison_only(self):
        rows = json.loads((ROOT / "docs/tools/search_matrix/bundle.json").read_text())
        by_slug = {r["links"]["slug"]: r for r in rows}
        self.assertNotIn("comparison_only", by_slug["deepseek"])
        self.assertTrue(by_slug["bing_legacy"]["comparison_only"])
        self.assertTrue(
            all(
                "comparison_only" in row
                for row in rows
                if row["links"]["slug"] == "bing_legacy"
            )
        )
        required_links = json.loads(
            (ROOT / "docs/tools/search_matrix/schema.json").read_text()
        )["$defs"]["links"]["required"]
        for row in rows:
            self.assertTrue(set(required_links).issubset(row["links"]))
            self.assertRegex(row["checked_at"]["value"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(row["evidence"]["source_urls"])
        self.assertEqual(
            json.loads((ROOT / "docs/tools/search_matrix/updated.json").read_text())[
                "updated_at"
            ],
            "2026-10-21T00:00:00Z",
        )


if __name__ == "__main__":
    unittest.main()
