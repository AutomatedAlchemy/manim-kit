"""Tests for manim_kit_voice — spec parsing, voice.json, the key lookup.

These run on the host Python, where manim-voiceover is not installed: the
module is written so everything above the service classes imports without it.
The few tests that need something out of manim_voiceover inject a stub through
sys.modules, so they pass on either interpreter.
"""

import json
import os
import sys

import pytest

import manim_kit_voice as v


# --- spec strings ------------------------------------------------------------------

@pytest.mark.parametrize("spec,expected", [
    ("kokoro-v1:af_sarah", ("kokoro-v1", "af_sarah", None)),
    ("kokoro-v1:am_puck", ("kokoro-v1", "am_puck", None)),
    ("gemini-flash-tts:Leda", ("gemini-flash-tts", "Leda", None)),
    ("gemini-flash-tts:Aoede:de", ("gemini-flash-tts", "Aoede", "de")),
    ("  kokoro-v1:af_sky  ", ("kokoro-v1", "af_sky", None)),
])
def test_parse_spec_accepts_the_curated_forms(spec, expected):
    assert v.parse_spec(spec) == expected


@pytest.mark.parametrize("spec", [
    "", "   ", "kokoro-v1", "piper:thorsten", "gtts:en",
    "kokoro-v1:af_sarah:en:extra", "kokoro-v1:", ":af_sarah",
])
def test_parse_spec_rejects_junk(spec):
    with pytest.raises(ValueError):
        v.parse_spec(spec)


def test_resolve_spec_order(monkeypatch):
    monkeypatch.delenv("MANIM_KIT_VOICE", raising=False)
    assert v.resolve_spec() == v.manifest_default()
    monkeypatch.setenv("MANIM_KIT_VOICE", "kokoro-v1:af_sky")
    assert v.resolve_spec() == "kokoro-v1:af_sky"          # env beats voice.json
    assert v.resolve_spec("gemini-flash-tts:Leda") == "gemini-flash-tts:Leda"  # argument wins


def test_kokoro_lang_mapping():
    assert v._kokoro_lang(None) == "en-us"
    assert v._kokoro_lang("en") == "en-us"
    assert v._kokoro_lang("gb") == "en-gb"
    assert v._kokoro_lang("xx") == "xx"   # unknown codes pass through untouched


# --- voice.json --------------------------------------------------------------------

def test_voice_manifest_is_complete_and_consistent():
    manifest = v.voice_manifest()
    assert manifest, "voice.json is missing"
    voices = v.curated_voices()
    assert voices, "voice.json lists no voices"

    specs = [x["spec"] for x in voices]
    assert len(specs) == len(set(specs))
    for entry in voices:
        for key in ("spec", "lang", "note"):
            assert entry.get(key), f"{entry.get('spec')} is missing {key}"
        backend, _voice, lang = v.parse_spec(entry["spec"])   # every spec parses
        assert backend in manifest["backends"]
        if lang:
            assert lang == entry["lang"]


def test_default_is_one_of_the_curated_voices():
    assert v.manifest_default() in [x["spec"] for x in v.curated_voices()]


def test_kokoro_file_manifest():
    files = v.kokoro_files()
    assert len(files) == 2
    names = {f["name"] for f in files}
    assert names == {v.KOKORO_MODEL_FILE, v.KOKORO_VOICES_FILE}
    for entry in files:
        assert len(entry["sha256"]) == 64
        assert entry["url"].startswith("https://")
        assert entry["bytes"] > 1_000_000


def test_subcaptions_are_off_unless_asked(monkeypatch):
    monkeypatch.delenv("MANIM_KIT_SRT", raising=False)
    assert v.subcaptions_wanted() is False
    monkeypatch.setenv("MANIM_KIT_SRT", "0")
    assert v.subcaptions_wanted() is False
    monkeypatch.setenv("MANIM_KIT_SRT", "1")
    assert v.subcaptions_wanted() is True


# --- Gemini key lookup -------------------------------------------------------------

def test_gemini_key_prefers_the_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert v.gemini_key() == "from-env"


def test_gemini_key_falls_back_to_an_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    env_file = tmp_path / "tools.env"
    env_file.write_text(
        "# a comment\n"
        "BROWSER_PATH=/usr/bin/firefox\n"
        'GEMINI_API_KEY="from-file"\n'
    )
    monkeypatch.setenv(v.ENV_FILE_VAR, str(env_file))
    monkeypatch.setattr(v, "FLEET_ENV_FILE", str(tmp_path / "nothing-here"))
    assert v.gemini_key() == "from-file"      # quotes stripped, comments skipped


def test_gemini_key_absent_is_none_not_an_error(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv(v.ENV_FILE_VAR, str(tmp_path / "missing.env"))
    monkeypatch.setattr(v, "FLEET_ENV_FILE", str(tmp_path / "also-missing"))
    assert v.gemini_key() is None


# --- word boundaries ---------------------------------------------------------------

def _stub_manim_voiceover(monkeypatch):
    """Inject the two manim_voiceover names linear_word_boundaries needs."""
    import re
    import types

    helper = types.ModuleType("manim_voiceover.helper")
    helper.remove_bookmarks = lambda text: re.sub(r"<bookmark\s*mark\s*=[\'\"].*?[\"\']\s*/>", "", text)
    tracker = types.ModuleType("manim_voiceover.tracker")
    tracker.AUDIO_OFFSET_RESOLUTION = 10_000_000
    root = types.ModuleType("manim_voiceover")

    monkeypatch.setitem(sys.modules, "manim_voiceover", root)
    monkeypatch.setitem(sys.modules, "manim_voiceover.helper", helper)
    monkeypatch.setitem(sys.modules, "manim_voiceover.tracker", tracker)


def test_linear_word_boundaries_span_the_clip(monkeypatch):
    _stub_manim_voiceover(monkeypatch)
    text = "Watch the point <bookmark mark='slide'/> as it slides."
    bounds = v.linear_word_boundaries(text, duration=4.0)

    assert len(bounds) == 2
    assert bounds[0]["audio_offset"] == 0
    assert bounds[1]["audio_offset"] == 40_000_000          # 4 s at the tracker's resolution
    # The offsets are measured on the text with the bookmark tag removed, which
    # is what the tracker interpolates against.
    plain_len = len("Watch the point  as it slides.")
    assert bounds[0]["word_length"] == plain_len
    assert bounds[1]["text_offset"] == plain_len


def test_with_word_boundaries_leaves_an_existing_set_alone(monkeypatch):
    _stub_manim_voiceover(monkeypatch)
    data = {"original_audio": "x.wav", "word_boundaries": [{"audio_offset": 0}]}
    assert v.with_word_boundaries(data, "text", "/nowhere") is data


def test_with_word_boundaries_fills_a_cached_entry(monkeypatch, tmp_path):
    _stub_manim_voiceover(monkeypatch)
    monkeypatch.setattr(v, "_audio_duration", lambda path: 2.5)
    data = {"input_text": "A line.", "original_audio": "clip.wav"}
    filled = v.with_word_boundaries(data, "A line.", str(tmp_path))

    assert "word_boundaries" not in data                     # the original is not mutated
    assert filled["word_boundaries"][1]["audio_offset"] == 25_000_000


# --- backend probes ----------------------------------------------------------------

def test_backend_status_covers_both_backends():
    rows = v.backend_status()
    assert [r["backend"] for r in rows] == [v.KOKORO_BACKEND, v.GEMINI_BACKEND]
    for row in rows:
        assert isinstance(row["usable"], bool)
        assert row["note"]          # usable or not, it always says why


def test_check_command_prints_a_parseable_table(capsys):
    assert v.main(["check"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    backends = {line.split("\t")[0] for line in lines}
    assert {v.KOKORO_BACKEND, v.GEMINI_BACKEND, "default"} <= backends
    for line in lines:
        if line.split("\t")[0] in (v.KOKORO_BACKEND, v.GEMINI_BACKEND):
            assert line.split("\t")[1] in ("usable", "unusable")


def test_unknown_command_is_an_error(capsys):
    assert v.main(["nonsense"]) == 2
