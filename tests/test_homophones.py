"""Tests for the deterministic homophone/correction pass in stt.transcribe."""

from stt import transcribe


def test_guarded_verb_follow():
    # "wheel" followed by a verb phrase becomes "will it".
    assert transcribe.fix_homophones("wheel work it") == "will it work it"
    # A determiner keeps the noun.
    assert transcribe.fix_homophones("the wheel works") == "the wheel works"


def test_case_preserved():
    assert transcribe.fix_homophones("Alot of it") == "A lot of it"
    assert transcribe.fix_homophones("alot of it") == "a lot of it"
    assert transcribe.fix_homophones("Gonna run it") == "Going to run it"


def test_unconditional_contractions():
    assert transcribe.fix_homophones("gonna wanna gotta") == "going to want to got to"
    assert transcribe.fix_homophones("dunno where it went") == "don't know where it went"


def test_phrase_fixes():
    assert transcribe.fix_homophones("I could of done it") == "I could have done it"
    assert transcribe.fix_homophones("we should of known") == "we should have known"
    assert transcribe.fix_homophones("You're suppose to run it") == "You're supposed to run it"


def test_normal_words_untouched():
    assert transcribe.fix_homophones("the aisle was clear") == "the aisle was clear"
    assert transcribe.fix_homophones("hello world") == "hello world"


def test_empty_input():
    assert transcribe.fix_homophones("") == ""


def test_cap_sentences():
    text = "One. Two. Three. Four. Five."
    assert transcribe._cap_sentences(text, 3) == "One. Two. Three."
    assert transcribe._cap_sentences(text, 10) == "One. Two. Three. Four. Five."
    assert transcribe._cap_sentences(text, 0) == text
