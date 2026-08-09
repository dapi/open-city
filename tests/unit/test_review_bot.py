import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("review_bot", ROOT / "platform/publishing/review_bot.py")
REVIEW_BOT = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(REVIEW_BOT)


class ReviewBotTests(unittest.TestCase):
    def make_issue(self, directory: Path) -> None:
        (directory / "art").mkdir(parents=True)
        (directory / "art/master.png").write_bytes(b"master-v1")
        (directory / "issue.json").write_text(
            json.dumps({"id": "issue-999", "status": "ready_for_review", "canonical_files": {"art_master": "art/master.png"}}),
            encoding="utf-8",
        )
        (directory / "manifest.json").write_text(
            json.dumps({"issue": "issue-999", "status": "ready_for_review"}),
            encoding="utf-8",
        )

    def test_callback_round_trip(self):
        value = REVIEW_BOT.callback_data("approve", "issue-004", "a" * 64)
        self.assertEqual(REVIEW_BOT.parse_callback(value), ("approve", "issue-004", "a" * 12))

    def test_approval_is_bound_to_current_master_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "issue-999"
            self.make_issue(directory)
            record = REVIEW_BOT.apply_decision(
                "issue-999",
                "approved",
                base_directory=directory,
                decided_at="2026-08-09T12:00:00+00:00",
            )
            issue = json.loads((directory / "issue.json").read_text(encoding="utf-8"))
            manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(record["decision"], "approved")
            self.assertEqual(record["master_sha256"], REVIEW_BOT.sha256(directory / "art/master.png"))
            self.assertEqual(issue["status"], "approved")
            self.assertEqual(manifest["status"], "approved")

    def test_changes_request_records_comment_and_reopens_issue(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "issue-999"
            self.make_issue(directory)
            record = REVIEW_BOT.apply_decision(
                "issue-999",
                "changes_requested",
                "Увеличить финальную реплику",
                base_directory=directory,
                decided_at="2026-08-09T12:00:00+00:00",
            )
            self.assertEqual(record["comment"], "Увеличить финальную реплику")
            self.assertEqual(
                json.loads((directory / "issue.json").read_text(encoding="utf-8"))["status"],
                "ready_for_review",
            )


if __name__ == "__main__":
    unittest.main()
