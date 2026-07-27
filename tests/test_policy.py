import unittest
from pathlib import Path

from lineageguard.catalog import Catalog
from lineageguard.models import Change
from lineageguard.policy import analyze


ROOT = Path(__file__).resolve().parents[1]


class PolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = Catalog.from_file(ROOT / "fixtures" / "catalog.json")
        self.source = "urn:li:dataset:(urn:li:dataPlatform:snowflake,commerce.orders,PROD)"

    def test_breaking_pii_change_with_model_dependency_is_blocked(self) -> None:
        report = analyze(self.catalog, Change(self.source, "customer_email", "drop_field"))
        self.assertEqual(report.decision, "BLOCK")
        self.assertGreaterEqual(report.risk_score, 70)
        self.assertTrue(any(asset.kind == "ml_model" for asset in report.impacted))
        self.assertTrue(any(f.code == "MISSING_OWNER" for f in report.findings))

    def test_migration_plan_downgrades_hard_block_to_review(self) -> None:
        report = analyze(self.catalog, Change(
            self.source,
            "customer_email",
            "drop_field",
            migration_plan="Dual-write customer_key for one release and test rollback.",
        ))
        self.assertEqual(report.decision, "REVIEW")

    def test_receipt_is_deterministic(self) -> None:
        change = Change(self.source, "gross_amount", "rename_field")
        first = analyze(self.catalog, change)
        second = analyze(self.catalog, change)
        self.assertEqual(first.receipt_sha256, second.receipt_sha256)


if __name__ == "__main__":
    unittest.main()

