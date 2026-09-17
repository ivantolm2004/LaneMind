import tempfile
import unittest
from pathlib import Path

from coach_core.analysis import analyze_match, build_training_plan
from coach_core.demo import DEMO_MATCH
from coach_core.store import Store


class AnalysisTests(unittest.TestCase):
    def test_demo_identifies_main_problems(self):
        report = analyze_match(DEMO_MATCH, 123456789)
        keys = [item["key"] for item in report["findings"]]
        self.assertIn("survivability", keys)
        self.assertIn("farm", keys)
        self.assertIn("fight_selection", keys)
        self.assertFalse(report["won"])
        self.assertEqual(report["data_quality"], "summary")

    def test_training_plan_prioritizes_recurring_problem(self):
        first = analyze_match(DEMO_MATCH, 123456789)
        second = analyze_match({**DEMO_MATCH, "match_id": 8400000002}, 123456789)
        plan = build_training_plan([first, second])
        self.assertEqual(plan["matches_analyzed"], 2)
        self.assertEqual(plan["focus"][0]["key"], "survivability")

    def test_stable_match_gets_consistency_finding(self):
        match = {
            "match_id": 1, "duration": 2400, "radiant_win": True,
            "players": [{"account_id": 1, "player_slot": 0, "hero_id": 2, "kills": 10,
                         "deaths": 3, "assists": 16, "last_hits": 270, "gold_per_min": 580,
                         "xp_per_min": 650, "tower_damage": 3300, "lane_role": 1}],
        }
        report = analyze_match(match, 1)
        self.assertEqual(report["findings"][0]["key"], "consistency")
        self.assertTrue(report["won"])


class StoreTests(unittest.TestCase):
    def test_upsert_prevents_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(str(Path(directory) / "test.sqlite3"))
            report = analyze_match(DEMO_MATCH, 123456789)
            store.save_match(DEMO_MATCH, report, 123456789, "demo")
            store.save_match(DEMO_MATCH, report, 123456789, "demo")
            self.assertEqual(len(store.reports()), 1)
            store.close()

    def test_model_setting_and_ai_summary_are_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(str(Path(directory) / "test.sqlite3"))
            report = analyze_match(DEMO_MATCH, 123456789)
            store.save_match(DEMO_MATCH, report, 123456789, "demo")
            store.set_setting("selected_model", "qwen3:4b")
            store.save_ai_summary(report["match_id"], "qwen3:4b", "ru", "Проверенный отчёт")
            self.assertEqual(store.get_setting("selected_model"), "qwen3:4b")
            saved = store.reports()[0]["ai_summary"]
            self.assertEqual(saved["content"], "Проверенный отчёт")
            self.assertEqual(saved["model"], "qwen3:4b")
            store.close()


if __name__ == "__main__":
    unittest.main()
