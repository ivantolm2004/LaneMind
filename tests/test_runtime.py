import unittest
from unittest.mock import patch

from coach_core.llm import LocalModelProvider
from coach_core.runtime import GpuInfo, HardwareProfile, choose_model, is_dota_running, runtime_status


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

    @patch("coach_core.runtime.ollama_models")
    @patch("coach_core.runtime.is_dota_running", return_value=False)
    @patch("coach_core.runtime.detect_hardware")
    def test_explicit_model_selection_overrides_automatic_choice(self, hardware, _dota, ollama):
        hardware.return_value = self.profile(ram=32, vram=12)
        ollama.return_value = {"available": True, "models": ["gemma3:4b"]}
        status = runtime_status("gemma3:4b")
        self.assertEqual(status["automatic_model"], "qwen3:8b")
        self.assertEqual(status["policy"]["model"], "gemma3:4b")
        self.assertTrue(status["policy"]["model_installed"])

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
