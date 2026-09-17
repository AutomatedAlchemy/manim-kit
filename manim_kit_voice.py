#!/usr/bin/env python3
"""Narration voices for manim-kit scenes.

A scene imports :func:`default_service` from here and hands the result to
``VoiceoverScene.set_speech_service``. Two backends: ``kokoro-v1`` runs the
Kokoro v1.0 ONNX model on the CPU with no network, ``gemini-flash-tts`` calls
the Gemini API through manim-voiceover's own ``GeminiService``.

This module runs inside the tool venv, next to manim-voiceover. The top half
(:func:`parse_spec`, the ``voice.json`` readers) is stdlib-only on purpose so
the host Python can import it for spec checks and the CLI listing; everything
that needs manim-voiceover is built inside a function.

Run it directly through the venv interpreter for a quick audition:

    .venv/bin/python manim_kit_voice.py say "Some text" --voice kokoro-v1:af_sarah
    .venv/bin/python manim_kit_voice.py check
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_JSON = os.path.join(SCRIPT_DIR, "voice.json")
VOICE_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "manim-kit", "voices")

KOKORO_BACKEND = "kokoro-v1"
GEMINI_BACKEND = "gemini-flash-tts"
BACKENDS = (KOKORO_BACKEND, GEMINI_BACKEND)

KOKORO_MODEL_FILE = "kokoro-v1.0.onnx"
KOKORO_VOICES_FILE = "voices-v1.0.bin"
KOKORO_SAMPLE_RATE = 24000
GEMINI_MODEL = "gemini-3.1-flash-tts-preview"

# Where the Gemini key is looked up, in order. The last entry is a convenience
# for this fleet: the tools repo keeps the key in its own .env and a scene
# rendered from any directory should still find it.
ENV_FILE_VAR = "MANIM_KIT_ENV_FILE"
FLEET_ENV_FILE = os.path.join(os.path.expanduser("~"), "Synced", "repos", "tools", ".env")
GEMINI_KEY_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY")

FALLBACK_DEFAULT_SPEC = f"{KOKORO_BACKEND}:af_sarah"


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


def kokoro_files() -> List[Dict[str, Any]]:
    """The Kokoro model file manifest (name, url, sha256, bytes)."""
    return list(voice_manifest().get("kokoro_model", {}).get("files", []))


def kokoro_paths() -> Tuple[str, str]:
    """(model path, voices path) in the cache directory. Neither need exist."""
    return (os.path.join(VOICE_CACHE_DIR, KOKORO_MODEL_FILE),
            os.path.join(VOICE_CACHE_DIR, KOKORO_VOICES_FILE))


def kokoro_cached() -> bool:
    """True when both Kokoro files are present. Size is not re-verified here."""
    return all(os.path.isfile(p) for p in kokoro_paths())


# --- spec strings ------------------------------------------------------------------

def parse_spec(spec: str) -> Tuple[str, str, Optional[str]]:
    """Split ``"backend:voice[:lang]"`` into its three parts.

    >>> parse_spec("kokoro-v1:af_sarah")
    ('kokoro-v1', 'af_sarah', None)
    >>> parse_spec("gemini-flash-tts:Aoede:de")
    ('gemini-flash-tts', 'Aoede', 'de')

    Raises ValueError on an unknown backend or a missing voice name, so a typo
    in ``--voice`` fails before manim starts rather than mid-render.
    """
    if not isinstance(spec, str) or not spec.strip():
        raise ValueError("empty voice spec; expected backend:voice[:lang]")
    parts = spec.strip().split(":")
    if len(parts) < 2 or len(parts) > 3:
        raise ValueError(f"bad voice spec {spec!r}; expected backend:voice[:lang]")
    backend, voice = parts[0].strip(), parts[1].strip()
    lang = parts[2].strip() if len(parts) == 3 and parts[2].strip() else None
    if backend not in BACKENDS:
        raise ValueError(f"unknown voice backend {backend!r}; have: {', '.join(BACKENDS)}")
    if not voice:
        raise ValueError(f"bad voice spec {spec!r}: no voice name")
    return backend, voice, lang


def resolve_spec(spec: Optional[str] = None) -> str:
    """The spec to use: the argument, else $MANIM_KIT_VOICE, else voice.json."""
    return spec or os.environ.get("MANIM_KIT_VOICE") or manifest_default()


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

    Looked up in the environment first, then in $MANIM_KIT_ENV_FILE, then in
    ~/Synced/repos/tools/.env if that exists (a fleet convenience: the scene
    process runs from the scene's directory, which usually has no .env).
    """
    for name in GEMINI_KEY_NAMES:
        value = os.environ.get(name)
        if value:
            return value
    candidates = [os.environ.get(ENV_FILE_VAR), FLEET_ENV_FILE]
    for path in candidates:
        if not path or not os.path.isfile(path):
            continue
        values = _read_env_file(path)
        for name in GEMINI_KEY_NAMES:
            if values.get(name):
                return values[name]
    return None


def _export_gemini_key() -> bool:
    """Put the key into os.environ so GeminiService's own lookup finds it."""
    key = gemini_key()
    if not key:
        return False
    os.environ.setdefault("GEMINI_API_KEY", key)
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


# --- Kokoro speech service ---------------------------------------------------------

def _kokoro_service_class() -> type:
    """Build KokoroService lazily; defining it needs manim-voiceover imported."""
    import soundfile as sf
    from manim_voiceover.helper import remove_bookmarks
    from manim_voiceover.services.base import SpeechService, initialize_speech_service, path_to_string

    class KokoroService(SpeechService):
        """Kokoro v1.0 ONNX, running locally on the CPU.

        The ONNX session is loaded on the first synthesis, not in ``__init__``,
        so building the service (which a scene does at import time) stays cheap
        and a cached render never touches the 325 MB model.
        """

        def __init__(self, voice: str = "af_sarah", lang: str = "en-us",
                     speed: float = 1.0, model_path: Optional[str] = None,
                     voices_path: Optional[str] = None, **kwargs: Any) -> None:
            self.voice = voice
            self.lang = lang
            self.speed = float(speed)
            default_model, default_voices = kokoro_paths()
            self.model_path = model_path or default_model
            self.voices_path = voices_path or default_voices
            self._kokoro = None
            initialize_speech_service(self, kwargs)

        def _model(self) -> Any:
            if self._kokoro is None:
                missing = [p for p in (self.model_path, self.voices_path) if not os.path.isfile(p)]
                if missing:
                    raise RuntimeError(
                        "Kokoro model files are not cached: " + ", ".join(missing)
                        + ". Run: manim-kit voice setup"
                    )
                from kokoro_onnx import Kokoro
                self._kokoro = Kokoro(self.model_path, self.voices_path)
            return self._kokoro

        def _input_data(self, input_text: str) -> Dict[str, Any]:
            # This dict is the cache key manim-voiceover hashes, so every
            # setting that changes the audio has to appear in it.
            return {
                "input_text": input_text,
                "service": "kokoro-v1",
                "config": {"voice": self.voice, "lang": self.lang, "speed": self.speed},
            }

        def generate_from_text(self, text: str, cache_dir: Any = None,
                               path: Any = None, **kwargs: Any) -> Dict[str, Any]:
            if cache_dir is None:
                cache_dir = self.cache_dir

            input_text = remove_bookmarks(text)
            input_data = self._input_data(input_text)

            cached = self.get_cached_result(input_data, cache_dir)
            if cached is not None:
                return with_word_boundaries(cached, text, cache_dir)

            if path is None:
                audio_path = self.get_audio_basename(input_data) + ".wav"
            else:
                audio_path = path_to_string(path)

            samples, sample_rate = self._model().create(
                input_text, voice=self.voice, speed=self.speed, lang=self.lang
            )
            full_path = os.path.join(str(cache_dir), audio_path)
            sf.write(full_path, samples, sample_rate)

            return with_word_boundaries(
                {"input_text": text, "input_data": input_data, "original_audio": audio_path},
                text, cache_dir,
            )

    return KokoroService


def _gemini_service(voice: str, style: Optional[str] = None,
                    model: str = GEMINI_MODEL, **kwargs: Any) -> Any:
    """manim-voiceover's GeminiService, with our model default and a style prefix.

    Gemini reads a leading instruction as a directive and does not speak it, so
    ``style="Read this like a patient teacher."`` changes the delivery without
    ending up in the audio. The prefix is part of the text, so it is also part
    of the cache key: changing the style re-synthesizes.
    """
    from manim_voiceover.services.gemini import GeminiService

    if not _export_gemini_key():
        raise RuntimeError(
            "No Gemini API key. Set GEMINI_API_KEY, or point $MANIM_KIT_ENV_FILE at a "
            f".env that has it, or keep one in {FLEET_ENV_FILE}."
        )

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
    """A SpeechService for *spec*, e.g. ``"kokoro-v1:af_sarah"``.

    ``style`` is a Gemini-only delivery instruction and is ignored by Kokoro.
    Extra keyword arguments go to the underlying service (``cache_dir``,
    ``global_speed``, …).
    """
    backend, voice, lang = parse_spec(spec)
    if backend == KOKORO_BACKEND:
        cls = _kokoro_service_class()
        kokoro_lang = _kokoro_lang(lang)
        return cls(voice=voice, lang=kokoro_lang, speed=speed, **kwargs)
    return _gemini_service(voice, style=style, **kwargs)


def _kokoro_lang(lang: Optional[str]) -> str:
    """Map a two-letter spec language onto a kokoro-onnx language code."""
    if not lang:
        return "en-us"
    table = {"en": "en-us", "gb": "en-gb", "fr": "fr-fr", "it": "it",
             "es": "es", "pt": "pt-br", "hi": "hi", "ja": "ja", "zh": "cmn"}
    return table.get(lang, lang)


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
        import kokoro_onnx  # noqa: F401
        have_kokoro = True
    except ImportError:
        have_kokoro = False

    kokoro_notes = []
    if not have_mv:
        kokoro_notes.append(mv_note)
    if not have_kokoro:
        kokoro_notes.append("kokoro-onnx not installed — run: manim-kit setup")
    if not kokoro_cached():
        kokoro_notes.append("model files not cached — run: manim-kit voice setup")
    rows.append({
        "backend": KOKORO_BACKEND,
        "usable": have_mv and have_kokoro and kokoro_cached(),
        "note": "; ".join(kokoro_notes) or f"model cached in {VOICE_CACHE_DIR}",
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
    p.add_argument("--style", help="Gemini delivery instruction, ignored by Kokoro")
    p.add_argument("--speed", type=float, default=1.0, help="Kokoro speaking rate (default: 1.0)")
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
    print(f"unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
