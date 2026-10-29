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
    ("phonon:Harper", ("phonon", "Harper", None)),
    ("phonon:Annika:de", ("phonon", "Annika", "de")),
    ("gemini-flash-tts:Leda", ("gemini-flash-tts", "Leda", None)),
    ("gemini-flash-tts:Aoede:de", ("gemini-flash-tts", "Aoede", "de")),
    ("  phonon:Trevor  ", ("phonon", "Trevor", None)),
    ("kokoro-v1:af_heart", ("phonon", "Hadley", None)),     # old spec, mapped
])
def test_parse_spec_accepts_the_curated_forms(spec, expected):
    assert v.parse_spec(spec) == expected


@pytest.mark.parametrize("spec", [
    "", "   ", "phonon", "piper:thorsten", "gtts:en",
    "phonon:Harper:en:extra", "phonon:", ":Harper",
    "phonon:Nobody", "phonon:Harper:fr", "kokoro-v1:no_such_voice",
])
def test_parse_spec_rejects_junk(spec):
    with pytest.raises(ValueError):
        v.parse_spec(spec)


def test_resolve_spec_order(monkeypatch):
    monkeypatch.delenv("MANIM_KIT_VOICE", raising=False)
    assert v.resolve_spec() == v.manifest_default()
    monkeypatch.setenv("MANIM_KIT_VOICE", "phonon:Trevor")
    assert v.resolve_spec() == "phonon:Trevor"             # env beats voice.json
    assert v.resolve_spec("gemini-flash-tts:Leda") == "gemini-flash-tts:Leda"  # argument wins


def test_bare_language_code_picks_the_language_default(monkeypatch):
    monkeypatch.delenv("MANIM_KIT_VOICE", raising=False)
    assert v.resolve_spec("de") == "phonon:Annika:de"
    assert v.resolve_spec("en") == "phonon:Harper"
    monkeypatch.setenv("MANIM_KIT_VOICE", "de")
    assert v.resolve_spec() == "phonon:Annika:de"


def test_language_defaults_are_curated():
    langs = {x["spec"]: x["lang"] for x in v.curated_voices()}
    for lang, spec in v.voice_manifest()["language_defaults"].items():
        assert langs.get(spec) == lang


def test_phonon_lang_comes_from_the_spec_or_the_voice():
    assert v.phonon_lang("Harper") == "en"
    assert v.phonon_lang("Annika") == "de"          # a German voice speaks German
    assert v.phonon_lang("Annika", "de") == "de"
    assert v.phonon_lang("Harper", "de") == "de"    # an explicit language wins


def test_kokoro_specs_map_to_phonon_with_one_note(monkeypatch, capsys):
    monkeypatch.setattr(v, "_legacy_noted", set())
    assert v.migrate_spec("kokoro-v1:af_heart") == "phonon:Hadley"
    assert v.migrate_spec("kokoro-v1:af_heart") == "phonon:Hadley"
    assert v.migrate_spec("kokoro-v1:af_sarah") == "phonon:Harper"
    err = capsys.readouterr().err
    assert err.count("kokoro-v1:af_heart") == 1     # one note per spec, not per call
    assert v.migrate_spec("gemini-flash-tts:Kore:de") == "gemini-flash-tts:Kore:de"
    monkeypatch.setenv("MANIM_KIT_VOICE", "kokoro-v1:am_puck")
    assert v.resolve_spec() == "phonon:Micah"       # an old value in the environment too


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


def test_phonon_pins_are_fixed_revisions():
    pins = v.phonon_pins()
    for key in ("model", "model_en", "catalog"):
        repo, _, rev = pins[key].partition("@")
        assert repo.startswith("hf://gradium/") and len(rev) == 40, key
    assert pins["quant"] == "q8"
    assert v.PHONON_DEFAULT_VOICES["en"] in pins["voices"]
    assert v.PHONON_DEFAULT_VOICES["de"] in pins["voices_de"]
    for kokoro, phonon in pins["kokoro"].items():
        assert phonon in pins["voices"], kokoro     # every old name lands on a real voice


def test_subcaptions_are_off_unless_asked(monkeypatch):
    monkeypatch.delenv("MANIM_KIT_SRT", raising=False)
    assert v.subcaptions_wanted() is False
    monkeypatch.setenv("MANIM_KIT_SRT", "0")
    assert v.subcaptions_wanted() is False
    monkeypatch.setenv("MANIM_KIT_SRT", "1")
    assert v.subcaptions_wanted() is True


# --- Gemini key lookup -------------------------------------------------------------

def test_gemini_key_prefers_the_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY_PAID", raising=False)
    monkeypatch.setenv(v.ENV_FILE_VAR, str(tmp_path / "missing.env"))
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert v.gemini_key() == "from-env"


def test_gemini_key_falls_back_to_an_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_PAID", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    env_file = tmp_path / "tools.env"
    env_file.write_text(
        "# a comment\n"
        "BROWSER_PATH=/usr/bin/firefox\n"
        'GEMINI_API_KEY="from-file"\n'
    )
    monkeypatch.setenv(v.ENV_FILE_VAR, str(env_file))
    assert v.gemini_key() == "from-file"      # quotes stripped, comments skipped


def test_gemini_key_prefers_a_paid_key_in_a_file_over_a_free_one_in_the_environment(
        tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "free-from-env")
    monkeypatch.delenv("GEMINI_API_KEY_PAID", raising=False)
    env_file = tmp_path / "tools.env"
    env_file.write_text("GEMINI_API_KEY=free-from-file\nGEMINI_API_KEY_PAID=paid-from-file\n")
    monkeypatch.setenv(v.ENV_FILE_VAR, str(env_file))
    assert v.gemini_key() == "paid-from-file"
    assert v._export_gemini_key()
    assert os.environ["GEMINI_API_KEY"] == "paid-from-file"   # overwrites the free key


def test_gemini_key_absent_is_none_not_an_error(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY_PAID", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.setenv(v.ENV_FILE_VAR, str(tmp_path / "missing.env"))
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
    assert [r["backend"] for r in rows] == [v.PHONON_BACKEND, v.GEMINI_BACKEND]
    for row in rows:
        assert isinstance(row["usable"], bool)
        assert row["note"]          # usable or not, it always says why


def test_check_command_prints_a_parseable_table(capsys):
    assert v.main(["check"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    backends = {line.split("\t")[0] for line in lines}
    assert {v.PHONON_BACKEND, v.GEMINI_BACKEND, "default"} <= backends
    for line in lines:
        if line.split("\t")[0] in (v.PHONON_BACKEND, v.GEMINI_BACKEND):
            assert line.split("\t")[1] in ("usable", "unusable")


def test_unknown_command_is_an_error(capsys):
    assert v.main(["nonsense"]) == 2


# --- Phonon loading, with ptts stubbed ---------------------------------------------

class _FakeTTS:
    """Stands in for ptts.TTS: records how it was built, refuses models on request."""

    refuse: set = set()
    built: list = []

    def __init__(self, model, *, lang, quant, voice_catalog):
        if any(model.startswith(r.split("@")[0]) for r in self.refuse):
            raise RuntimeError("401 gated")
        self.model, self.lang = model, lang
        self.sample_rate = 24000
        self.voices = []
        _FakeTTS.built.append(model)

    def add_voice(self, name, path):
        self.voices.append(name)

    def synth(self, text, *, voice=None):
        import numpy as np
        return np.zeros(2400, dtype=np.float32)


@pytest.fixture
def fake_ptts(monkeypatch, tmp_path):
    """ptts replaced by _FakeTTS, an empty HF cache, no network, nothing loaded yet."""
    import types
    module = types.ModuleType("ptts")
    module.TTS = _FakeTTS
    monkeypatch.setitem(sys.modules, "ptts", module)
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "hub"))
    monkeypatch.setattr(v, "_phonon_loaded", {})
    monkeypatch.setattr(v, "_hub_answer", None)
    monkeypatch.setattr(_FakeTTS, "refuse", set())
    monkeypatch.setattr(_FakeTTS, "built", [])
    return tmp_path / "hub"


def _snapshot(repo, quant="q8"):
    path = v._hf_snapshot(repo)
    os.makedirs(path, exist_ok=True)
    for name in ("config.json", f"model.{quant}.gguf", "tokenizer.json"):
        open(os.path.join(path, name), "w").close()
    return path


def test_load_phonon_prefers_the_local_snapshot(fake_ptts, monkeypatch):
    monkeypatch.setattr(v, "_hub_reachable", lambda *a: pytest.fail("no Hub probe when cached"))
    local = _snapshot(v.phonon_pins()["model"])
    tts, model = v.load_phonon("de")
    assert tts.model == local                      # a path, so ptts downloads nothing
    assert model == v.phonon_pins()["model"]       # the pin is what goes into the cache key
    assert v.load_phonon("de")[0] is tts           # loaded once per process


def test_load_phonon_english_falls_back_to_31m(fake_ptts, monkeypatch, capsys):
    pins = v.phonon_pins()
    monkeypatch.setattr(v, "_hub_reachable", lambda *a: True)
    _FakeTTS.refuse = {pins["model"]}              # 40M gated for this account
    tts, model = v.load_phonon("en")
    assert model == pins["model_en"]
    assert "Apache-2.0" in capsys.readouterr().err  # the licence that applies is said


def test_load_phonon_german_without_40m_names_gemini(fake_ptts, monkeypatch):
    monkeypatch.setattr(v, "_hub_reachable", lambda *a: True)
    _FakeTTS.refuse = {v.phonon_pins()["model"]}
    with pytest.raises(RuntimeError, match="gemini-flash-tts:Kore:de"):
        v.load_phonon("de")


def test_load_phonon_offline_and_uncached_does_not_call_ptts(fake_ptts, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    with pytest.raises(RuntimeError, match="Hub does not answer"):
        v.load_phonon("en")
    assert _FakeTTS.built == []                    # ptts would hang on an hf:// model here


def test_uncached_voice_offline_raises_instead_of_hanging(fake_ptts, monkeypatch):
    pytest.importorskip("numpy")                   # phonon_synth needs it; the host Python may not
    monkeypatch.setattr(v, "_hub_reachable", lambda *a: False)
    tts = _FakeTTS("local", lang="en", quant="q8", voice_catalog="x")
    tts.voices = ["Harper"]
    assert v.phonon_synth(tts, "Hi.", "Harper").size == 2400
    with pytest.raises(RuntimeError, match="not cached"):
        v.phonon_synth(tts, "Hi.", "Hadley")


def test_expected_model_is_a_pin_not_a_path(fake_ptts):
    pins = v.phonon_pins()
    assert v.expected_phonon_model("en") == pins["model"]     # nothing cached: the first pin
    _snapshot(pins["model_en"])
    assert v.expected_phonon_model("en") == pins["model_en"]  # only 31M here
    assert v.expected_phonon_model("de") == pins["model"]
