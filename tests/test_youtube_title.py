"""Examples of how youtube_remux.strip_title cleans a filename stem."""

import importlib.util
import unittest
from pathlib import Path


def _load_script():
    script = Path(__file__).resolve().parents[1] / "bin" / "youtube_remux.py"
    spec = importlib.util.spec_from_file_location("youtube_remux", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TitleStrippingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_script()

    def test_all_caps_category_before_pipe(self):
        self.assertEqual(
            self.mod.strip_title("DOCUMENTARY | How The Berlin Wall Fell"),
            "How The Berlin Wall Fell",
        )

    def test_category_word_without_separator_stays(self):
        self.assertEqual(
            self.mod.strip_title("Documentary Filmmaking"),
            "Documentary Filmmaking",
        )

    def test_bracketed_category_and_accents(self):
        self.assertEqual(
            self.mod.strip_title("[Interview] Café del Mar"),
            "Cafe del Mar",
        )

    def test_emoji_and_decorative_marks_are_removed(self):
        self.assertEqual(
            self.mod.strip_title("★ How 🎬 The Berlin Wall Fell ★"),
            "How The Berlin Wall Fell",
        )

    def test_bracketed_codec_tags(self):
        self.assertEqual(
            self.mod.strip_title("How The Berlin Wall Fell [1080p][HEVC][AAC]"),
            "How The Berlin Wall Fell",
        )

    def test_dotted_release_name(self):
        self.assertEqual(
            self.mod.strip_title("How.The.Berlin.Wall.Fell.1080p.WEB-DL.x264"),
            "How The Berlin Wall Fell",
        )

    def test_spaced_dash_inside_the_title_stays(self):
        self.assertEqual(
            self.mod.strip_title("How The Berlin Wall Fell - Full Story"),
            "How The Berlin Wall Fell - Full Story",
        )

    def test_short_all_caps_label(self):
        self.assertEqual(
            self.mod.strip_title("USA | Election Night"),
            "Election Night",
        )


if __name__ == "__main__":
    unittest.main()
