import unittest
from unittest.mock import patch

from coach_core.llm import LocalModelProvider
from coach_core.runtime import GpuInfo, HardwareProfile, choose_model, is_dota_running


class RuntimePolicyTests(unittest.TestCase):
    def profile(self, ram=16, vram=8):
        gpus = [GpuInfo("Test GPU", vram)] if vram else []
        return HardwareProfile("Test CPU", 12, ram, gpus)

    def test_dota_always_pauses_inference(self):
        policy = choose_model(self.profile(ram=64, vram=24), dota_active=True)
        self.assertEqual(policy["mode"], "paused")
        self.assertIsNone(policy["model"])
        self.assertTrue(policy["queue_inference"])

    def test_balanced_hardware_uses_four_billion_model(self):
        policy = choose_model(self.profile(ram=16, vram=8), dota_active=False)
        self.assertEqual(policy["model"], "qwen3:4b")
        self.assertEqual(policy["tier"], "balanced")

    def test_quality_hardware_uses_eight_billion_model(self):
        policy = choose_model(self.profile(ram=32, vram=12), dota_active=False)
        self.assertEqual(policy["model"], "qwen3:8b")

    def test_cpu_only_machine_can_use_light_model(self):
        policy = choose_model(self.profile(ram=8, vram=0), dota_active=False)
        self.assertEqual(policy["model"], "qwen3:1.7b")

    @patch("coach_core.runtime.subprocess.run")
    def test_dota_process_detection(self, run):
        run.return_value.stdout = "dota2.exe                 1234 Console"
        run.return_value.returncode = 0
        self.assertTrue(is_dota_running())

    @patch("coach_core.llm.urllib.request.urlopen")
    def test_provider_never_calls_model_while_dota_is_active(self, urlopen):
        provider = LocalModelProvider(
            lambda: {
                "dota_active": True,
                "policy": {"mode": "paused", "model": None, "post_match_model": "qwen3:8b"},
                "ollama": {"available": True, "models": ["qwen3:8b"]},
            }
        )
        result = provider.generate({"match_id": "1"})
        self.assertEqual(result["status"], "deferred")
        self.assertTrue(result["queued"])
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
