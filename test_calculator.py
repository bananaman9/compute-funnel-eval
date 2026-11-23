"""Deterministic unit and CLI tests for Compute Funnel Eval."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from calculator import batch, placement, reservation, unique_fields

ROOT = Path(__file__).resolve().parent
EXAMPLES = ROOT / "examples"


class CalculatorTests(unittest.TestCase):
    def test_reservation_eligible_and_remainder(self):
        out = reservation(
            quota_seconds=108000,
            duration_seconds=1800,
            multiplier=2,
            age_days=45,
            verified=True,
            good_standing=True,
        )
        self.assertTrue(out["eligible_account"])
        self.assertEqual(out["maximum_full_requests"], 30)
        self.assertEqual(out["remaining_quota_seconds"], 0)
        self.assertEqual(out["calculations"]["quota_seconds_per_request"], 3600)
        self.assertFalse(out["deployment_ready"])

    def test_reservation_young_account_ineligible(self):
        out = reservation(
            quota_seconds=3600,
            duration_seconds=1800,
            multiplier=1,
            age_days=30,
            verified=True,
            good_standing=True,
        )
        self.assertFalse(out["eligible_account"])

    def test_batch_accounts_for_startup_and_multiplier(self):
        out = batch(
            quota_seconds=3600,
            startup_seconds=300,
            case_seconds=45,
            multiplier=2,
            pending_cases=50,
            verified_answers=7,
        )
        # (3600 - 600) // 90 = 33 cases
        self.assertEqual(out["planned_cases"], 33)
        self.assertEqual(out["actual_gpu_seconds"], 300 + 33 * 45)
        self.assertEqual(out["calculations"]["quota_seconds_used"], 3570)
        self.assertEqual(out["remaining_quota_seconds"], 30)
        self.assertEqual(out["verified_answers_before_validation"], 7)

    def test_batch_startup_exceeding_quota_raises(self):
        with self.assertRaises(ValueError):
            batch(
                quota_seconds=500,
                startup_seconds=300,
                case_seconds=45,
                multiplier=2,
                pending_cases=10,
                verified_answers=0,
            )

    def test_placement_filters_by_memory_and_window(self):
        offers = {
            "single_96g_gpu": {
                "devices": 1,
                "memory_per_gpu_gib": 96,
                "window_minutes": 60,
                "programmable": True,
                "runtime_supported": True,
            },
            "split_48g_node": {
                "devices": 1,
                "memory_per_gpu_gib": 48,
                "window_minutes": 120,
                "programmable": True,
                "runtime_supported": True,
            },
            "short_window_spot": {
                "devices": 1,
                "memory_per_gpu_gib": 96,
                "window_minutes": 20,
                "programmable": True,
                "runtime_supported": True,
            },
        }
        out = placement(required_gib=52, load_minutes=10, task_minutes=25, offers=offers)
        self.assertEqual(out["job_minutes"], 35)
        self.assertEqual(out["eligible"], ["single_96g_gpu"])
        self.assertEqual(out["slack_minutes"], {"single_96g_gpu": 25})

    def test_strict_type_checks_reject_bool_as_int(self):
        with self.assertRaises(ValueError):
            reservation(True, 10, 1, 45, True, True)

    def test_unique_fields_rejects_duplicate_json_keys(self):
        with self.assertRaises(ValueError):
            json.loads('{"a": 1, "a": 2}', object_pairs_hook=unique_fields)

    def test_cli_examples(self):
        cases = [
            ("quota", EXAMPLES / "quota_check.json", "maximum_full_requests", 30),
            ("batch", EXAMPLES / "batch_check.json", "planned_cases", 33),
            ("placement", EXAMPLES / "placement_check.json", "eligible", ["single_96g_gpu"]),
        ]
        for op, path, key, expected in cases:
            res = subprocess.run(
                [sys.executable, str(ROOT / "calculator.py"), op, str(path)],
                capture_output=True,
                text=True,
                check=True,
            )
            payload = json.loads(res.stdout)
            self.assertEqual(payload[key], expected)


if __name__ == "__main__":
    unittest.main()
