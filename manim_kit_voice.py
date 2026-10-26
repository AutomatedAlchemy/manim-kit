#!/usr/bin/env python3
"""Narration voices for manim-kit scenes.

A scene imports :func:`default_service` from here and hands the result to
``VoiceoverScene.set_speech_service``. Two backends: ``phonon`` runs gradium's
Phonon 40M multilingual model (``ptts``) on the CPU with no network, English and
German; ``gemini-flash-tts`` calls the Gemini API through manim-voiceover's own
``GeminiService``.

Licences: Phonon 40M output is CC BY-NC 4.0, non-commercial only, and needs the
credit "Phonon by Gradium, CC BY-NC 4.0". When 40M cannot load, English falls
back to Phonon 31M English (Apache-2.0, same voice names) and German fails.
Commercial work uses the gemini backend. Old ``kokoro-v1:<id>`` specs map to a
Phonon voice through ``voice.json``'s ``phonon.kokoro`` table.

This module runs inside the tool venv, next to manim-voiceover. The top half
(:func:`parse_spec`, the ``voice.json`` readers) is stdlib-only on purpose so
the host Python can import it for spec checks and the CLI listing; everything
that needs manim-voiceover is built inside a function.

Run it directly through the venv interpreter for a quick audition:

    .venv/bin/python manim_kit_voice.py say "Some text" --voice phonon:Harper
    .venv/bin/python manim_kit_voice.py check
    .venv/bin/python manim_kit_voice.py setup     # download the models and default voices
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_JSON = os.path.join(SCRIPT_DIR, "voice.json")

PHONON_BACKEND = "phonon"
GEMINI_BACKEND = "gemini-flash-tts"
BACKENDS = (PHONON_BACKEND, GEMINI_BACKEND)
# Specs of the removed Kokoro backend (2026-10-26) are rewritten to Phonon voices.
LEGACY_KOKORO_BACKEND = "kokoro-v1"
PHONON_LANGS = ("en", "de")
PHONON_DEFAULT_VOICES = {"en": "Harper", "de": "Annika"}
PHONON_CREDIT = "Phonon by Gradium, CC BY-NC 4.0"
HUB_TIMEOUT_S = 3.0
GEMINI_MODEL = "gemini-3.1-flash-tts-preview"

# Where the Gemini key is looked up, in order. The last entry is a convenience
# for this fleet: the tools repo keeps the key in its own .env and a scene
# rendered from any directory should still find it.
ENV_FILE_VAR = "MANIM_KIT_ENV_FILE"
FLEET_ENV_FILE = os.path.join(os.path.expanduser("~"), "Synced", "repos", "tools", ".env")
# The paid key comes first: the free tier allows 10 TTS requests per day, fewer
# than one narrated scene needs (user, 2026-10-17).
GEMINI_KEY_NAMES = ("GEMINI_API_KEY_PAID", "GEMINI_API_KEY", "GOOGLE_API_KEY")

FALLBACK_DEFAULT_SPEC = f"{PHONON_BACKEND}:Harper"


# --- voice.json --------------------------------------------------------------------

def voice_manifest() -> Dict[str, Any]:
    """The committed voice.json, or an empty dict when it is missing."""
    if not os.path.isfile(VOICE_JSON):
        return {}
    with open(VOICE_JSON, encoding="utf-8") as f:
        return json.load(f)


def curated_voices() -> List[Dict[str, str]]:
    """The starred voices, in the order voice.json lists them."""
    return list(voice_manifest().get("voices", []))


def manifest_default() -> str:
    """The fleet-wide default spec from voice.json."""
    return str(voice_manifest().get("default") or FALLBACK_DEFAULT_SPEC)


def language_default(lang: str) -> Optional[str]:
    """The spec voice.json names for a bare language code such as ``de``."""
    return voice_manifest().get("language_defaults", {}).get(lang.strip().lower())


def phonon_pins() -> Dict[str, Any]:
    """voice.json's phonon section: model pins, catalog, quant, voices, Kokoro map."""
    return dict(voice_manifest().get("phonon", {}))


def phonon_voices(lang: str) -> List[str]:
    """The Phonon voice names voice.json lists for *lang* (``en`` or ``de``)."""
    key = "voices_de" if lang == "de" else "voices"
    return list(phonon_pins().get(key, {}))


# --- spec strings ------------------------------------------------------------------

_legacy_noted: set = set()


def migrate_spec(spec: str) -> str:
    """Rewrite an old ``kokoro-v1:<id>`` spec to its Phonon voice; others pass unchanged.

    The Kokoro backend was removed on 2026-10-26. voice.json's ``phonon.kokoro``
    table maps each Kokoro voice to the Phonon voice of the same accent and
    gender (af_heart -> Hadley). A note goes to stderr once per spec and process.
    A Kokoro name without an entry is an error, not a silent default.
    """
    if not isinstance(spec, str):
        return spec
    parts = spec.strip().split(":")
    if len(parts) < 2 or parts[0].strip() != LEGACY_KOKORO_BACKEND:
        return spec
    kokoro = parts[1].strip()
    voice = phonon_pins().get("kokoro", {}).get(kokoro)
    if not voice:
        raise ValueError(f"{spec!r}: the kokoro-v1 backend was removed and {kokoro!r} has no "
                         "Phonon equivalent; pick a voice from: manim-kit voice list")
    new = f"{PHONON_BACKEND}:{voice}"
    if spec not in _legacy_noted:
        _legacy_noted.add(spec)
        print(f"note: kokoro-v1 was removed; {spec.strip()} now speaks as {new}", file=sys.stderr)
    return new


def parse_spec(spec: str) -> Tuple[str, str, Optional[str]]:
    """Split ``"backend:voice[:lang]"`` into its three parts.

    >>> parse_spec("phonon:Harper")
    ('phonon', 'Harper', None)
    >>> parse_spec("gemini-flash-tts:Aoede:de")
    ('gemini-flash-tts', 'Aoede', 'de')

    An old ``kokoro-v1:<id>`` spec is rewritten first (see :func:`migrate_spec`).
    Raises ValueError on an unknown backend, a missing voice name, or a Phonon
    voice or language voice.json does not list, so a typo in ``--voice`` fails
    before manim starts rather than mid-render.
    """
    if not isinstance(spec, str) or not spec.strip():
        raise ValueError("empty voice spec; expected backend:voice[:lang]")
    spec = migrate_spec(spec)
    parts = spec.strip().split(":")
    if len(parts) < 2 or len(parts) > 3:
        raise ValueError(f"bad voice spec {spec!r}; expected backend:voice[:lang]")
    backend, voice = parts[0].strip(), parts[1].strip()
    lang = parts[2].strip() if len(parts) == 3 and parts[2].strip() else None
    if backend not in BACKENDS:
        raise ValueError(f"unknown voice backend {backend!r}; have: {', '.join(BACKENDS)}")
    if not voice:
        raise ValueError(f"bad voice spec {spec!r}: no voice name")
    if backend == PHONON_BACKEND:
        if lang is not None and lang not in PHONON_LANGS:
            raise ValueError(f"phonon speaks {', '.join(PHONON_LANGS)}, not {lang!r}; "
                             f"for other languages use {GEMINI_BACKEND}")
        known = phonon_voices("en") + phonon_voices("de")
        if known and voice not in known:
            raise ValueError(f"unknown Phonon voice {voice!r}; have: {', '.join(known)}")
    return backend, voice, lang


def phonon_lang(voice: str, lang: Optional[str] = None) -> str:
    """The language a Phonon spec speaks: its ``:lang`` part, else the voice's own."""
    if lang:
        return lang
    return "de" if voice in phonon_voices("de") else "en"


def resolve_spec(spec: Optional[str] = None) -> str:
    """The spec to use: the argument, else $MANIM_KIT_VOICE, else voice.json.

    A bare language code (``de``) stands for that language's default voice.
    """
    chosen = spec or os.environ.get("MANIM_KIT_VOICE") or manifest_default()
    return migrate_spec(language_default(chosen) or chosen)


# --- Gemini key lookup -------------------------------------------------------------

def _read_env_file(path: str) -> Dict[str, str]:
    """KEY=value pairs from a .env file. Quotes stripped, comments skipped."""
    values: Dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                value = value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                values[key.strip()] = value
    except OSError:
        return {}
    return values


def gemini_key() -> Optional[str]:
    """The Gemini API key, or None. Never printed anywhere.

    Names in GEMINI_KEY_NAMES order, so a paid key anywhere beats a free one.
    Each name is looked up in the environment first, then in $MANIM_KIT_ENV_FILE,
    then in ~/Synced/repos/tools/.env if that exists (a fleet convenience: the
    scene process runs from the scene's directory, which usually has no .env).
    """
    files = [_read_env_file(p) for p in (os.environ.get(ENV_FILE_VAR), FLEET_ENV_FILE)
             if p and os.path.isfile(p)]
    for name in GEMINI_KEY_NAMES:
        for values in [os.environ, *files]:
            if values.get(name):
                return values[name]
    return None


def _export_gemini_key() -> bool:
    """Put the key into os.environ so GeminiService's own lookup finds it."""
    key = gemini_key()
    if not key:
        return False
    # Overwrite, not setdefault: a free key already in the environment must not
    # shadow the paid one gemini_key() chose.
    os.environ["GEMINI_API_KEY"] = key
    return True


# --- bookmarks without Whisper -----------------------------------------------------

def linear_word_boundaries(text: str, duration: float) -> List[Dict[str, Any]]:
    """Two boundary points that map the text linearly onto the clip.

    manim-voiceover only builds a scene's bookmark table when the service
    returned ``word_boundaries``; without them ``wait_until_bookmark`` raises
    and tells the user to install Whisper. Whisper is deliberately out of this
    version (it pulls torch into the tool venv), and a bookmark only needs to
    know roughly where in the line a word sits, so we hand back the same
    start/end pair the tracker uses as its own fallback and let it interpolate.

    The cost is that a bookmark fires at its position in the *text*, not at the
    word: a pause or a long number shifts it by a fraction of a second.
    """
    from manim_voiceover.helper import remove_bookmarks
    from manim_voiceover.tracker import AUDIO_OFFSET_RESOLUTION

    plain = remove_bookmarks(text)
    return [
        {"audio_offset": 0, "text_offset": 0, "word_length": len(plain),
         "text": plain, "boundary_type": "Word"},
        {"audio_offset": int(duration * AUDIO_OFFSET_RESOLUTION),
         "text_offset": len(plain), "word_length": 1, "text": ".",
         "boundary_type": "Word"},
    ]


def _audio_duration(path: str) -> float:
    from manim_voiceover.modify_audio import get_duration
    return float(get_duration(path))


def with_word_boundaries(data: Dict[str, Any], text: str, cache_dir: Any) -> Dict[str, Any]:
    """Return *data* with ``word_boundaries`` filled in when it has none.

    Applied to the cached result as well as to a fresh one: a cache entry
    written before this existed, or by another tool, otherwise comes back
    without boundaries and the next bookmark in the scene raises.
    """
    if data.get("word_boundaries"):
        return data
    filled = dict(data)
    audio = os.path.join(str(cache_dir), str(data["original_audio"]))
    filled["word_boundaries"] = linear_word_boundaries(text, _audio_duration(audio))
    return filled


# --- Phonon models -----------------------------------------------------------------
#
# ptts ignores HF_HUB_OFFLINE, and handed an hf:// model on a network that does not
# answer it hangs for minutes. So a model is loaded from its local snapshot when the
# Hugging Face cache has one, and a download is only tried after a 3 s TCP probe of
# the Hub succeeds. The same guard covers voice embeddings that are not cached yet.
# (Copied from tools/_shared/voice/phonon_tts.py.)

_phonon_loaded: Dict[str, Tuple[Any, str]] = {}   # lang -> (ptts.TTS, pinned model it loaded)
_hub_answer: Optional[bool] = None


def _hf_snapshot(repo: str) -> str:
    """Local snapshot folder of a pinned ``hf://owner/name@rev`` in the HF cache."""
    name, _, revision = repo[len("hf://"):].partition("@")
    hub = os.environ.get("HF_HUB_CACHE") or os.path.join(
        os.environ.get("HF_HOME", os.path.join(os.path.expanduser("~"), ".cache", "huggingface")),
        "hub")
    return os.path.join(hub, "models--" + name.replace("/", "--"), "snapshots", revision)


def _snapshot_if_complete(repo: str) -> Optional[str]:
    """The model's local snapshot when the files ptts loads are all there, else None."""
    path = _hf_snapshot(repo)
    quant = phonon_pins().get("quant", "q8")
    files = ("config.json", f"model.{quant}.gguf", "tokenizer.json")
    return path if all(os.path.exists(os.path.join(path, f)) for f in files) else None


def _hub_reachable(timeout: float = HUB_TIMEOUT_S) -> bool:
    """True if a TCP connection to the Hub (or the HTTPS proxy) opens. Asked once.

    HF_HUB_OFFLINE=1 counts as no answer, since ptts itself does not honour it.
    """
    global _hub_answer
    if os.environ.get("HF_HUB_OFFLINE", "") not in ("", "0"):
        return False
    if _hub_answer is None:
        import socket
        import urllib.parse
        proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        if proxy:
            url = urllib.parse.urlsplit(proxy if "://" in proxy else "http://" + proxy)
            host, port = url.hostname, url.port or 80
        else:
            host, port = "huggingface.co", 443
        try:
            socket.create_connection((host, port), timeout=timeout).close()
            _hub_answer = True
        except OSError:
            _hub_answer = False
    return _hub_answer


def phonon_models(lang: str) -> List[str]:
    """Pinned models for *lang*, best first: 40M multilingual, then 31M English for English."""
    pins = phonon_pins()
    return [pins["model"], pins["model_en"]] if lang == "en" else [pins["model"]]


def expected_phonon_model(lang: str) -> str:
    """The pin a synthesis would load, judged from the local cache only.

    Part of the clip cache key. It is a pin string, never a path, so the key does
    not change with $HOME or the network.
    """
    models = phonon_models(lang)
    return next((m for m in models if _snapshot_if_complete(m)), models[0])


def _cached_voice_files() -> Dict[str, str]:
    """Voice name -> embedding file, for the catalog voices already downloaded."""
    folder = _hf_snapshot(phonon_pins()["catalog"])
    try:
        with open(os.path.join(folder, "voices.jsonl"), encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
    except (OSError, ValueError):
        return {}
    found = {}
    for row in rows:
        path = os.path.join(folder, row.get("filename", ""))
        if row.get("name") and os.path.isfile(path):
            found[row["name"]] = path
    return found


def _model_licence(model: str) -> str:
    return PHONON_CREDIT + ", non-commercial only" if model == phonon_pins().get("model") \
        else "Phonon 31M English, Apache-2.0"


def load_phonon(lang: str) -> Tuple[Any, str]:
    """(ptts.TTS, pinned model) for *lang*, loaded once per process.

    ``lang`` picks ptts's text normalizer at load time, so each language has its
    own instance. English takes 40M, else 31M English; German needs 40M and
    otherwise raises with a pointer to the gemini backend. One stderr line says
    which model loaded, since the licence of the output depends on it.
    """
    if lang in _phonon_loaded:
        return _phonon_loaded[lang]
    import ptts

    pins = phonon_pins()
    errors: List[str] = []
    for model in phonon_models(lang):
        local = _snapshot_if_complete(model)
        if local is None and not _hub_reachable():
            errors.append(f"{model}: not cached and the Hub does not answer")
            continue
        try:
            tts = ptts.TTS(local or model, lang=lang, quant=pins["quant"],
                           voice_catalog=pins["catalog"])
        except Exception as exc:  # gated without a token, download failed
            errors.append(f"{model}: {exc}")
            continue
        # Registered voices are not looked up in the online catalog.
        for name, path in _cached_voice_files().items():
            tts.add_voice(name, path)
        if errors:
            print(f"phonon: {errors[0]}", file=sys.stderr)
        print(f"phonon: {lang} speaks with {model.split('@')[0][len('hf://'):]} "
              f"({_model_licence(model)})", file=sys.stderr)
        _phonon_loaded[lang] = (tts, model)
        return _phonon_loaded[lang]
    hint = ("German narration needs Phonon 40M multilingual: accept its terms on "
            "huggingface.co/gradium/phonon-40m-multilingual and log in with `hf auth login`, "
            f"or use the gemini backend (--voice {GEMINI_BACKEND}:Kore:de). "
            if lang == "de" else "Run: manim-kit voice setup. ")
    raise RuntimeError(f"Phonon could not load for {lang}. {hint}Details: " + "; ".join(errors))


def phonon_synth(tts: Any, text: str, voice: str) -> Any:
    """One line from a loaded Phonon model as float32 samples at ``tts.sample_rate``.

    A voice whose embedding is not cached downloads from the pinned catalog, but
    only when the Hub answers; otherwise this raises instead of letting ptts hang.
    The sampling seed is fixed, so the same text and voice give the same clip.
    """
    import numpy as np

    if voice not in tts.voices and not _hub_reachable():
        raise RuntimeError(f"Phonon voice {voice!r} is not cached and the Hub does not answer; "
                           "run `manim-kit voice setup` on a connected host, or pick a cached voice")
    audio = np.asarray(tts.synth(text, voice=voice), dtype=np.float32)
    if audio.size == 0:
        raise RuntimeError(f"Phonon returned no audio for {text[:60]!r} ({voice})")
    return audio


def time_stretch(audio: Any, sample_rate: int, speed: float) -> Any:
    """*audio* played *speed* times as fast, same pitch, with ffmpeg's atempo filter.

    Phonon has no speed control of its own. 0.5 to 2.0; ffmpeg must be installed
    (manim needs it anyway). A failure raises rather than ignoring the speed.
    """
    import shutil
    import subprocess

    import numpy as np

    if abs(speed - 1.0) < 1e-3:
        return audio
    if not 0.5 <= speed <= 2.0:
        raise ValueError(f"speed {speed} is outside 0.5..2.0")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("a speed other than 1.0 needs ffmpeg")
    cmd = [ffmpeg, "-v", "error", "-f", "f32le", "-ar", str(sample_rate), "-ac", "1",
           "-i", "pipe:0", "-filter:a", f"atempo={speed:.3f}", "-f", "f32le", "pipe:1"]
    out = subprocess.run(cmd, input=np.asarray(audio, dtype="<f4").tobytes(),
                         capture_output=True, check=True, timeout=120).stdout
    return np.frombuffer(out, dtype="<f4").astype(np.float32)


# --- Phonon speech service ---------------------------------------------------------

def _phonon_service_class() -> type:
    """Build PhononService lazily; defining it needs manim-voiceover imported."""
    import soundfile as sf
    from manim_voiceover.helper import remove_bookmarks
    from manim_voiceover.services.base import SpeechService, initialize_speech_service, path_to_string

    class PhononService(SpeechService):
        """Phonon (ptts), running locally on the CPU.

        The model is loaded on the first synthesis, not in ``__init__``, so
        building the service (which a scene does at import time) stays cheap and
        a cached render never touches the model.
        """

        def __init__(self, voice: str = "Harper", lang: str = "en",
                     speed: float = 1.0, **kwargs: Any) -> None:
            self.voice = voice
            self.lang = lang
            self.speed = float(speed)
            initialize_speech_service(self, kwargs)

        def _input_data(self, input_text: str, model: Optional[str] = None) -> Dict[str, Any]:
            # This dict is the cache key manim-voiceover hashes, so every
            # setting that changes the audio has to appear in it.
            pins = phonon_pins()
            return {
                "input_text": input_text,
                "service": PHONON_BACKEND,
                "config": {"model": model or expected_phonon_model(self.lang),
                           "catalog": pins["catalog"], "quant": pins["quant"],
                           "lang": self.lang, "voice": self.voice, "speed": self.speed},
            }

        def generate_from_text(self, text: str, cache_dir: Any = None,
                               path: Any = None, **kwargs: Any) -> Dict[str, Any]:
            if cache_dir is None:
                cache_dir = self.cache_dir

            input_text = remove_bookmarks(text)
            cached = self.get_cached_result(self._input_data(input_text), cache_dir)
            if cached is not None:
                return with_word_boundaries(cached, text, cache_dir)

            tts, model = load_phonon(self.lang)
            samples = time_stretch(phonon_synth(tts, input_text, self.voice),
                                   tts.sample_rate, self.speed)
            # Keyed by the model that really spoke, so a 31M fallback clip is not
            # served later as if 40M had made it.
            input_data = self._input_data(input_text, model)
            if path is None:
                audio_path = self.get_audio_basename(input_data) + ".wav"
            else:
                audio_path = path_to_string(path)
            sf.write(os.path.join(str(cache_dir), audio_path), samples, tts.sample_rate)

            return with_word_boundaries(
                {"input_text": text, "input_data": input_data, "original_audio": audio_path},
                text, cache_dir,
            )

    return PhononService


def _gemini_service(voice: str, style: Optional[str] = None,
                    model: str = GEMINI_MODEL, **kwargs: Any) -> Any:
    """manim-voiceover's GeminiService, with our model default and a style prefix.

    Gemini reads a leading instruction as a directive and does not speak it, so
    ``style="Read this like a patient teacher."`` changes the delivery without
    ending up in the audio. The prefix is part of the text, so it is also part
    of the cache key: changing the style re-synthesizes.
    """
    # Export before the import: manim_voiceover.services.gemini runs
    # load_dotenv(find_dotenv(usecwd=True)) at import time, which walks up from
    # the scene directory and would otherwise put a stale key from ~/.env into
    # the environment first (load_dotenv does not override a variable that is set).
    if not _export_gemini_key():
        raise RuntimeError(
            "No Gemini API key. Set GEMINI_API_KEY_PAID or GEMINI_API_KEY, or point "
            "$MANIM_KIT_ENV_FILE at a "
            f".env that has it, or keep one in {FLEET_ENV_FILE}."
        )

    from manim_voiceover.services.gemini import GeminiService

    service = GeminiService(voice=voice, model=model, **kwargs)
    return _wrap_gemini(service, style)


def _wrap_gemini(service: Any, style: Optional[str] = None) -> Any:
    """Add the style prefix and the linear word boundaries to *service*.

    Two fixes on top of GeminiService, both in one wrapper because both live in
    ``generate_from_text``:

    * ``style`` is sent to Gemini in front of the line and removed again from
      the returned ``input_text``, so the scene's bookmarks and subcaptions see
      the narration the author wrote, not the instruction.
    * ``word_boundaries`` are added so ``wait_until_bookmark`` works without
      Whisper (see :func:`linear_word_boundaries`).
    """
    original = service.generate_from_text
    prefix = (style.rstrip() + " ") if style else ""

    def generate_from_text(text: str, cache_dir: Any = None, path: Any = None, **kwargs: Any) -> Any:
        data = dict(original(prefix + text, cache_dir=cache_dir, path=path, **kwargs))
        data["input_text"] = text
        return with_word_boundaries(data, text, cache_dir or service.cache_dir)

    service.generate_from_text = generate_from_text
    return service


# --- factories ---------------------------------------------------------------------

def service_for(spec: str, style: Optional[str] = None, speed: float = 1.0,
                **kwargs: Any) -> Any:
    """A SpeechService for *spec*, e.g. ``"phonon:Harper"`` or ``"phonon:Annika:de"``.

    ``style`` is a Gemini-only delivery instruction and is ignored by Phonon;
    ``speed`` is a Phonon tempo factor (ffmpeg atempo) that Gemini does not take.
    Extra keyword arguments go to the underlying service (``cache_dir``,
    ``global_speed``, …).
    """
    backend, voice, lang = parse_spec(spec)
    if backend == PHONON_BACKEND:
        cls = _phonon_service_class()
        return cls(voice=voice, lang=phonon_lang(voice, lang), speed=speed, **kwargs)
    if abs(speed - 1.0) > 1e-3:
        raise ValueError(f"speed applies to the {PHONON_BACKEND} backend only")
    return _gemini_service(voice, style=style, **kwargs)


def default_service(spec: Optional[str] = None, **kwargs: Any) -> Any:
    """The service a narrated scene should use.

    Spec order: the argument, then ``$MANIM_KIT_VOICE`` (which
    ``manim-kit render --voice`` sets), then the ``voice.json`` default.
    """
    return service_for(resolve_spec(spec), **kwargs)


def subcaptions_wanted() -> bool:
    """Whether the scene should write an .srt. Off unless MANIM_KIT_SRT=1."""
    return os.environ.get("MANIM_KIT_SRT", "") == "1"


def set_service(scene: Any, spec: Optional[str] = None, **kwargs: Any) -> Any:
    """Attach the default service to *scene* and return it.

    Convenience for templates: it also honours ``MANIM_KIT_SRT``, which plain
    ``set_speech_service`` would not know about.
    """
    service = default_service(spec, **kwargs)
    scene.set_speech_service(service, create_subcaption=subcaptions_wanted())
    return service


# --- backend probes ----------------------------------------------------------------

def backend_status() -> List[Dict[str, Any]]:
    """One row per backend: is it usable on this host, and why not."""
    rows: List[Dict[str, Any]] = []
    try:
        import manim_voiceover  # noqa: F401
        have_mv = True
        mv_note = ""
    except ImportError as exc:
        have_mv = False
        mv_note = f"manim-voiceover not importable ({exc})"

    try:
        import ptts  # noqa: F401
        have_ptts = True
    except ImportError:
        have_ptts = False

    pins = phonon_pins()
    has_40m = bool(pins) and _snapshot_if_complete(pins["model"]) is not None
    has_31m = bool(pins) and _snapshot_if_complete(pins["model_en"]) is not None
    phonon_notes = []
    if not have_mv:
        phonon_notes.append(mv_note)
    if not have_ptts:
        phonon_notes.append("ptts not installed — run: manim-kit setup")
    if has_40m:
        model_note = (f"40M multilingual cached: English and German, output {PHONON_CREDIT}, "
                      "non-commercial only")
    elif has_31m:
        model_note = (f"only 31M English cached: English works (Apache-2.0), German needs "
                      f"40M or {GEMINI_BACKEND}")
    else:
        model_note = "no model cached — run: manim-kit voice setup"
    voices = sorted(_cached_voice_files()) if pins else []
    rows.append({
        "backend": PHONON_BACKEND,
        "usable": have_mv and have_ptts and (has_40m or has_31m),
        "note": "; ".join(phonon_notes + [model_note]
                          + ([f"voices cached: {', '.join(voices)}"] if voices else [])),
    })

    try:
        import google.genai  # noqa: F401
        have_genai = True
    except ImportError:
        have_genai = False
    have_key = gemini_key() is not None
    gemini_notes = []
    if not have_mv:
        gemini_notes.append(mv_note)
    if not have_genai:
        gemini_notes.append("google-genai not installed — run: manim-kit setup")
    if not have_key:
        gemini_notes.append(f"no GEMINI_API_KEY (env, $MANIM_KIT_ENV_FILE or {FLEET_ENV_FILE})")
    rows.append({
        "backend": GEMINI_BACKEND,
        "usable": have_mv and have_genai and have_key,
        "note": "; ".join(gemini_notes) or f"key found, model {GEMINI_MODEL}",
    })
    return rows


def sox_binary_missing() -> bool:
    """True when the `sox` binary is absent and something might want it.

    manim-voiceover imports the `sox` Python package unconditionally, but only
    calls it for `global_speed != 1` and for its microphone recorder. Normal
    narration never touches it, so this is a note, not a problem.
    """
    import shutil
    return shutil.which("sox") is None


# --- CLI ---------------------------------------------------------------------------

def _cmd_say(argv: List[str]) -> int:
    import argparse

    p = argparse.ArgumentParser(prog="manim_kit_voice.py say")
    p.add_argument("text")
    p.add_argument("--voice", help="backend:voice[:lang] (default: $MANIM_KIT_VOICE or voice.json)")
    p.add_argument("--out", help="output file (default: voice-<backend>-<voice>.mp3 in cwd)")
    p.add_argument("--style", help="Gemini delivery instruction, ignored by Phonon")
    p.add_argument("--speed", type=float, default=1.0,
                   help="Phonon tempo factor 0.5..2.0, applied with ffmpeg (default: 1.0)")
    args = p.parse_args(argv)

    spec = resolve_spec(args.voice)
    backend, voice, _ = parse_spec(spec)
    out = args.out or f"voice-{backend}-{voice}.mp3"

    import shutil
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        service = service_for(spec, style=args.style, speed=args.speed, cache_dir=tmp)
        data = service._wrap_generate_from_text(args.text)
        produced = os.path.join(tmp, data["final_audio"])
        if out.lower().endswith(".wav"):
            shutil.copyfile(produced, out)
        else:
            ffmpeg = shutil.which("ffmpeg")
            if ffmpeg is None:
                raise RuntimeError("ffmpeg is needed to write anything but .wav")
            subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", produced,
                            "-ac", "1", "-b:a", "96k", out], check=True)
    print(os.path.abspath(out))
    return 0


def _cmd_check(_argv: List[str]) -> int:
    for row in backend_status():
        mark = "usable" if row["usable"] else "unusable"
        print(f"{row['backend']}\t{mark}\t{row['note']}")
    print(f"default\t{manifest_default()}")
    if sox_binary_missing():
        print("note\tthe `sox` binary is not installed; only speed changes and the "
              "microphone recorder need it, narration does not")
    return 0


def _cmd_setup(_argv: List[str]) -> int:
    """Download the Phonon models and the starred voices into the HF cache.

    Loads English and German once and speaks one word per starred Phonon voice,
    which fetches its embedding, so later renders work offline. German failing
    (no access to the gated 40M model) is reported with the gemini alternative.
    """
    voices: Dict[str, List[str]] = {lang: [PHONON_DEFAULT_VOICES[lang]] for lang in PHONON_LANGS}
    for entry in curated_voices():
        backend, voice, lang = parse_spec(entry["spec"])
        if backend == PHONON_BACKEND and voice not in voices[phonon_lang(voice, lang)]:
            voices[phonon_lang(voice, lang)].append(voice)
    failed = 0
    for lang in PHONON_LANGS:
        try:
            tts, model = load_phonon(lang)
        except Exception as exc:
            print(f"{lang}	failed	{exc}")
            failed += 1
            continue
        for voice in voices[lang]:
            try:
                phonon_synth(tts, "Bereit." if lang == "de" else "Ready.", voice)
                print(f"{lang}	ok	{voice} ({model})")
            except Exception as exc:
                print(f"{lang}	failed	{voice}: {exc}")
                failed += 1
    return 1 if failed else 0


def main(argv: Optional[List[str]] = None) -> int:
    raw = list(argv) if argv is not None else sys.argv[1:]
    if not raw or raw[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = raw[0], raw[1:]
    if cmd == "say":
        return _cmd_say(rest)
    if cmd == "check":
        return _cmd_check(rest)
    if cmd == "setup":
        return _cmd_setup(rest)
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
