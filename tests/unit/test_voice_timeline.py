import unittest
import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[2] / "platform/voice/generate.py"
SPEC = importlib.util.spec_from_file_location("open_city_generate_v2", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VoiceTimelineTests(unittest.TestCase):
    def test_parse_time_range(self):
        self.assertEqual(MODULE.parse_time_range("0:01-1:02"), (1000, 62000))

    def test_parse_en_dash(self):
        self.assertEqual(MODULE.parse_time_range("0:01–0:02"), (1000, 2000))

    def test_reject_end_before_start(self):
        with self.assertRaises(ValueError):
            MODULE.parse_time_range("0:03-0:02")

    def test_api_key_fallback_order(self):
        from unittest.mock import patch

        with patch.dict("os.environ", {"XI_API_KEY": "xi", "ELEVENLABS_API_KEY": "eleven"}):
            self.assertEqual(MODULE.resolve_api_key(), "xi")
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "eleven"}, clear=True):
            self.assertEqual(MODULE.resolve_api_key(), "eleven")
        self.assertEqual(MODULE.resolve_api_key("explicit"), "explicit")


if __name__ == "__main__":
    unittest.main()
