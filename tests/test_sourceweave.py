import tempfile
import unittest
from pathlib import Path

from sourceweave import (
    SourceweaveError,
    add_detail,
    add_relation,
    add_source,
    first_appearance,
    load,
    new_project,
    observe,
    render_markdown,
    render_mermaid,
    save,
)


class SourceweaveTests(unittest.TestCase):
    def test_first_appearance_uses_earliest_present_source(self):
        data = new_project("Lineage")
        s1 = add_source(data, "Original report", "primary", "1900-12-20")
        s2 = add_source(data, "Later book", "later-retelling", "1987")
        d1 = add_detail(data, "An overturned chair is mentioned.")
        observe(data, s1, d1, "absent")
        observe(data, s2, d1, "present")
        first = first_appearance(data, d1)
        self.assertEqual(first["id"], s2)

    def test_lineage_and_rendering(self):
        data = new_project("Lineage")
        s1 = add_source(data, "Primary record", "primary", "1900")
        s2 = add_source(data, "Newspaper retelling", "later-retelling", "1901")
        d1 = add_detail(data, "A meal was left untouched.")
        add_relation(data, s2, s1, "derived-from")
        observe(data, s1, d1, "unclear")
        observe(data, s2, d1, "present")
        md = render_markdown(data)
        mm = render_mermaid(data)
        self.assertIn("First recorded appearance", md)
        self.assertIn("S002 → S001", md)
        self.assertIn("S002 -->|derived from| S001", mm)

    def test_round_trip_and_duplicate_observation_update(self):
        data = new_project("Round trip")
        s1 = add_source(data, "Archive note", "primary", "1920-03")
        d1 = add_detail(data, "The door was locked.")
        observe(data, s1, d1, "unclear")
        observe(data, s1, d1, "present", "Later inspection clarified the wording.")
        self.assertEqual(len(data["observations"]), 1)
        self.assertEqual(data["observations"][0]["state"], "present")
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "project.json"
            save(path, data)
            loaded = load(path)
        self.assertEqual(loaded["observations"][0]["state"], "present")

    def test_rejects_self_relation(self):
        data = new_project("Bad relation")
        s1 = add_source(data, "One", "other")
        with self.assertRaises(SourceweaveError):
            add_relation(data, s1, s1, "cites")


if __name__ == "__main__":
    unittest.main()
