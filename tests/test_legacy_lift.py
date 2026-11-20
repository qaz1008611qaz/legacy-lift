import os
import unittest

from legacy_lift.planner import plan, strongly_connected
from legacy_lift.scanner import scan_file, scan_repo
from legacy_lift.tasks import devin_prompt

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "py2_shop")


def rules(report):
    return {f.rule for f in report.findings}


class ScannerTest(unittest.TestCase):
    def setUp(self):
        self.reports = scan_repo(FIXTURE)

    def test_finds_every_module(self):
        self.assertEqual(set(self.reports), {
            "cli", "shop", "shop.utils", "shop.models", "shop.orders", "shop.payments", "shop.api"})

    def test_detects_python2_constructs(self):
        self.assertEqual(rules(self.reports["shop.orders"]), {"xrange", "except-comma", "print-statement"})
        self.assertEqual(rules(self.reports["shop.models"]), {"dict-iter", "has-key"})
        self.assertIn("unicode-type", rules(self.reports["shop.payments"]))
        self.assertIn("legacy-stdlib", rules(self.reports["shop.utils"]))

    def test_ignores_strings_and_comments(self):
        path = os.path.join(FIXTURE, "..", "tmp_clean.py")
        with open(path, "w") as fh:
            fh.write('msg = "print me, xrange(3)"  # d.has_key(x)\nprint(msg)\n')
        try:
            self.assertEqual(scan_file(os.path.dirname(path), path).findings, [])
        finally:
            os.remove(path)

    def test_resolves_local_imports_only(self):
        self.assertEqual(self.reports["shop.utils"].imports, set())          # ConfigParser is stdlib
        self.assertEqual(self.reports["shop.orders"].imports, {"shop.payments", "shop.models"})
        self.assertEqual(self.reports["cli"].imports, {"shop.api"})


class PlannerTest(unittest.TestCase):
    def setUp(self):
        self.reports = scan_repo(FIXTURE)
        self.batches = plan(self.reports, max_risk=20)
        self.batch_of = {m: b.index for b in self.batches for m in b.modules}

    def test_cycle_moves_together(self):
        self.assertEqual(self.batch_of["shop.orders"], self.batch_of["shop.payments"])

    def test_dependencies_migrate_first(self):
        for name, rep in self.reports.items():
            for dep in rep.imports:
                if self.batch_of[dep] == self.batch_of[name]:
                    continue  # same batch, e.g. an import cycle
                self.assertLess(self.batch_of[dep], self.batch_of[name], f"{dep} must precede {name}")

    def test_order_on_fixture(self):
        order = [b.modules for b in self.batches]
        self.assertEqual(order[0], ["shop", "shop.utils"])
        self.assertEqual(self.batch_of["cli"], len(self.batches))

    def test_risk_budget_splits_batches(self):
        tight = plan(self.reports, max_risk=3)
        self.assertGreater(len(tight), len(self.batches))

    def test_every_module_planned_once(self):
        planned = [m for b in self.batches for m in b.modules]
        self.assertEqual(sorted(planned), sorted(self.reports))

    def test_tarjan_handles_deep_chain(self):
        chain = {f"m{i}": {f"m{i+1}"} for i in range(5000)}
        chain["m5000"] = set()
        self.assertEqual(len(strongly_connected(chain)), 5001)


class PromptTest(unittest.TestCase):
    def test_prompt_has_acceptance_criteria(self):
        reports = scan_repo(FIXTURE)
        batch = next(b for b in plan(reports) if "shop.orders" in b.modules)
        prompt = devin_prompt(batch, reports)
        self.assertIn("characterization tests", prompt)
        self.assertIn("except E, e -> except E as e", prompt)
        self.assertIn("str/bytes", prompt)


if __name__ == "__main__":
    unittest.main()
