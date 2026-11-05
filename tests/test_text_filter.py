"""Tests for the transcript filtering helpers in stt.daemon."""

from stt import daemon


class TestMeaningful:
    def test_plain_text(self):
        assert daemon._text_is_meaningful("check the proxy token accounting")

    def test_empty_and_punctuation(self):
        assert not daemon._text_is_meaningful("")
        assert not daemon._text_is_meaningful(". . .")
        assert not daemon._text_is_meaningful(".,. ")

    def test_garbage_tokens(self):
        assert not daemon._text_is_meaningful("thank you. thank you.")
        assert not daemon._text_is_meaningful("subscribe")

    def test_whisper_outro_boilerplate(self):
        assert not daemon._text_is_meaningful("thanks for watching")
        assert not daemon._text_is_meaningful("thank you so much for watching")
        assert not daemon._text_is_meaningful("that's all for now thanks for watching")
        assert daemon._text_is_meaningful("thanks, i appreciate the review notes")

    def test_repeated_word_noise(self):
        assert not daemon._text_is_meaningful("uh uh uh uh")
        assert not daemon._text_is_meaningful("you you you")

    def test_single_noise_word(self):
        assert not daemon._text_is_meaningful("um")
        assert not daemon._text_is_meaningful("yeah")


class TestStrip:
    def test_leading_stutter_repetition(self):
        assert daemon._strip_leading_garbage("uh uh uh let me check") == "let me check"

    def test_leading_repetition_with_content_kept(self):
        out = daemon._strip_leading_garbage("sorry sorry i'm sorry open the file")
        assert out.endswith("open the file")

    def test_stutter_collapse(self):
        assert daemon._strip_repeated_stutter("i i i think so") == "i think so"
        assert daemon._strip_repeated_stutter("sorry sorry open it") == "sorry open it"

    def test_non_stutter_repeat_kept(self):
        # Legit non-stutter words are not collapsed.
        assert daemon._strip_repeated_stutter("dark dark theme") == "dark dark theme"

    def test_all_stutter_after_collapse_is_dropped(self):
        assert daemon._strip_repeated_stutter("um um um") == ""


class TestHotkeyParsing:
    def test_combo(self):
        assert daemon._parse_hotkey("<ctrl>+<shift>+space") == {"<ctrl>", "<shift>", "space"}

    def test_collapses_whitespace(self):
        assert daemon._parse_hotkey(" <f9> + <alt> ") == {"<f9>", "<alt>"}


class TestNormalize:
    def test_peaks_are_normalized(self):
        import numpy as np

        clip = np.array([0.5, -0.5, 1.0, -1.0], dtype="float32")
        out, ratio = daemon._normalize_clip(clip)
        assert abs(abs(out).max() - 0.70) < 1e-6
        assert ratio > 0

    def test_quiet_clip_untouched(self):
        import numpy as np

        clip = np.array([0.05, -0.04, 0.03], dtype="float32")
        out, _ = daemon._normalize_clip(clip)
        assert (out == clip).all()
