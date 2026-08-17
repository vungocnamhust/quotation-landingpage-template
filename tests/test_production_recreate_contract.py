from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProductionRecreateRegressionContractTests(unittest.TestCase):
    def test_disposable_production_recreate_regression_is_isolated_and_targets_nginx(self):
        script = (ROOT / "scripts/test_production_recreate_regression.sh").read_text()
        self.assertIn("docker network create", script)
        self.assertIn(".env.production.regression", script)
        self.assertIn("INSERT INTO quotations", script)
        self.assertIn("up -d --wait --no-deps --force-recreate nginx", script)
        self.assertIn("http://quotation-ingress/", script)
        self.assertIn("nslookup quotation-ingress", script)


if __name__ == "__main__":
    unittest.main()
