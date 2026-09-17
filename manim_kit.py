#!/usr/bin/env python3
"""manim-kit — scaffold, list, render and open Manim Community scenes.

Stdlib-only entry point. Manim itself lives in a tool-owned virtualenv
(``.venv/`` next to this file) created by ``manim-kit setup``; every render
is delegated to that interpreter, so the host Python stays clean and the
``--advertise`` probe answers instantly.

Speaks the cli-tools-kit installer protocol (``--advertise``, ``--install``,
``--remove``, ``--install-skill``, ``--uninstall-skill``).
"""

import json
import os
import sys

# Windows pipes default to the ANSI codepage (cp1252 on a German install), which
# cannot encode the emoji in _ok()/_warn()/_fail(). The installer captures our
# stdout, so without this any run that prints one dies with UnicodeEncodeError.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):  # not a reconfigurable text stream
        pass

__version__ = "0.1.0"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(SCRIPT_DIR, ".venv")
if os.name == "nt":
    VENV_PYTHON = os.path.join(VENV_DIR, "Scripts", "python.exe")
else:
    VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python")
TEMPLATE_DIR = os.path.join(SCRIPT_DIR, "templates")
MANIM_REQUIREMENTS = os.path.join(SCRIPT_DIR, "requirements-manim.txt")

MUSIC_JSON = os.path.join(SCRIPT_DIR, "music.json")
MUSIC_DIR = os.path.join(os.path.expanduser("~"), ".cache", "manim-kit", "music")
MUSIC_GAIN = 0.12   # ~ -18 dB: a bed a later voice-over still sits on top of
MUSIC_FADE = 2.0    # seconds of fade in and out
RUBINETTI_FORM = "https://vincerubinetti.github.io/using-the-music-of-3blue1brown/"

VOICE_JSON = os.path.join(SCRIPT_DIR, "voice.json")
VOICE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "manim-kit", "voices")
VOICE_MODULE = os.path.join(SCRIPT_DIR, "manim_kit_voice.py")
# Sidechain ducking, keyed on the narration: the music drops while someone
# speaks and comes back in the pauses. threshold 0.03 is about -30 dB, so a
# normal speaking level triggers it; ratio 8 is a firm dip without pumping;
# 20 ms attack catches the start of a word, 500 ms release lets the bed return
# between sentences instead of stuttering on every pause.
DUCK_THRESHOLD = 0.03
DUCK_RATIO = 8
DUCK_ATTACK_MS = 20
DUCK_RELEASE_MS = 500

SKILL_NAME = "manim-kit"
SKILL_DIR = os.path.join(os.path.expanduser("~"), ".claude", "skills", SKILL_NAME)
SKILL_FILE = os.path.join(SKILL_DIR, "SKILL.md")

# Single source of truth for ~/.claude/skills/manim-kit/SKILL.md. Edit this,
# then `manim-kit --install-skill` to refresh the on-disk copy.
SKILL_MD_CONTENT = '''---
name: manim-kit
description: Write and render Manim Community (3Blue1Brown-style) math animations with the manim-kit CLI — scaffold a scene, list scenes, render at draft/final quality, open the result.
---

# manim-kit — Manim Community animations from the CLI

Use this skill when the user wants a math/science animation, a 3Blue1Brown-style
explainer clip, an animated plot, or asks to "manim" something. It wraps
[Manim Community](https://docs.manim.community) (`pip install manim`), not ManimGL.

## Commands

| Task | Command |
|---|---|
| One-time setup (creates `.venv` with manim, checks ffmpeg/LaTeX) | `manim-kit setup` |
| Check the install | `manim-kit doctor` |
| New scene file from a template | `manim-kit new NAME [--template basic\\|text\\|graph\\|threed\\|narrated] [--dir DIR]` |
| List the Scene classes in a file | `manim-kit list FILE.py` |
| Render (1080p60, the default) | `manim-kit render FILE.py [SceneName]` |
| Draft render (480p15, seconds) | `manim-kit render FILE.py SceneName -q l` |
| Render every scene in the file | `manim-kit render FILE.py --all` |
| GIF / PNG last frame / transparent | `--format gif` · `--last-frame` · `--transparent` |
| Render silent (music is on by default) | `manim-kit render FILE.py --no-music` |
| Music library | `manim-kit music list\\|fetch\\|add FILE\\|credits` |
| Narrated scene from a template | `manim-kit new NAME --template narrated` |
| Render with narration | `manim-kit render FILE.py [--voice SPEC] [--srt] [--no-ducking]` |
| Voices: list, audition, cache the model | `manim-kit voice list\\|say TEXT\\|setup` |
| Open the newest render of a file | `manim-kit open FILE.py` |

Quality presets: `l` 480p15 · `m` 720p30 · `h` 1080p60 (default) · `p` 1440p60 · `k` 2160p60.
The default is `h`: a 480p clip looks pixelated the moment it is shown at any real size, so only go below `h` for drafts.
Output lands next to the scene file: `media/videos/<file-stem>/<res>/<Scene>.mp4`
(`media/images/<file-stem>/…png` for last-frame renders). `render` prints the
produced paths on success. Anything after `--` is passed straight to `manim render`.

## Workflow

1. `manim-kit doctor` once per host. If it reports missing system libraries,
   show the user the exact `apt` line it prints — you cannot sudo for them.
2. `manim-kit new my_scene --template graph` → edit `my_scene.py`.
3. Iterate with `-q l` while the timing and layout are in flux (seconds per render). Read the traceback if it fails;
   the usual causes are listed under *Gotchas*.
4. Ship with the default quality (`-q h`, 1080p60) - never a `-q l` draft - then `manim-kit open`.

Keep one idea per Scene class and one file per topic; several short scenes
beat one long one — they render and debug independently.

## Music

Renders mix an ambient track under the finished MP4 by default, with ffmpeg: looped or
trimmed to the exact video length, faded in and out, at `volume=0.12` so a later
voice-over sits on top (`--music-gain` to change it, `--no-music` to skip it). The video
is not re-encoded, so it costs a second. First use downloads the track into
`~/.cache/manim-kit/music/`; `manim-kit music fetch` does it ahead of time. `--track ID`
picks another one, `manim-kit music add FILE` takes the user's own audio.

The bundled tracks are Chris Zabriskie, CC BY. **After a render with music the command
prints a credit line — tell the user it has to go into the video description.** The actual
3Blue1Brown music (Vincent Rubinetti) is all rights reserved and licensed per project via
`https://vincerubinetti.github.io/using-the-music-of-3blue1brown/`; do not download or
suggest ripping it, point at that form instead.

Music is skipped automatically for `--last-frame`, `--format png` and `--format gif` — no
audio track.

## Narration

A narrated scene subclasses `VoiceoverScene` and wraps each animation in a
`with self.voiceover(...)` block. The line is synthesized *before* the block runs, so the
animation can be told how long it has and the block waits at the end until the voice has
finished. The narration lives in the scene file, next to the animation it describes —
there is no separate script or cue sheet.

```python
from manim import *
from manim_voiceover import VoiceoverScene
from manim_kit_voice import default_service, subcaptions_wanted

class Derivative(VoiceoverScene):
    def construct(self):
        self.set_speech_service(default_service(), create_subcaption=subcaptions_wanted())

        ax = Axes(); curve = ax.plot(lambda x: x**2, color=BLUE)
        with self.voiceover("The derivative measures how fast a function changes.") as t:
            self.play(Create(ax), Create(curve), run_time=t.duration)

        with self.voiceover("Watch the point <bookmark mark='go'/> slide along the curve.") as t:
            self.play(Write(label))
            self.wait_until_bookmark("go")          # fires at that word
            self.play(MoveAlongPath(dot, curve), run_time=t.get_remaining_duration())
```

- `t.duration` is the clip length: use it as `run_time` to stretch one animation over the
  whole line. `t.get_remaining_duration()` is what is left after a bookmark.
- `<bookmark mark='name'/>` in the text plus `self.wait_until_bookmark("name")` fires an
  animation partway through a line. The mark lands at its position in the text, so it is
  accurate to a fraction of a second, not to the exact word.
- **At most two sentences per block.** Short lines re-synthesize faster when you edit one,
  and they line up with a single animation instead of several.
- Clips are cached under `media/voiceovers/` next to the scene, keyed by the text and the
  voice settings. Re-rendering an unchanged line costs nothing; editing one re-synthesizes
  only that line.

### Voices

A voice spec is `backend:voice[:lang]`. `manim-kit voice list` prints these with the
default marked and says which backend works on this host.

| Spec | Lang | |
|---|---|---|
| `kokoro-v1:af_sarah` | en | **the default** — even, unhurried, good for maths |
| `kokoro-v1:af_heart` | en | warmer, a little more expressive |
| `kokoro-v1:af_sky` | en | lighter, younger |
| `kokoro-v1:am_puck` | en | male, the clearest of the Kokoro male voices |
| `gemini-flash-tts:Puck` | en | male, best prosody — paid API |
| `gemini-flash-tts:Leda` | en | calm female, good for a long explainer — paid API |
| `gemini-flash-tts:Aoede:de` | de | German female — paid API |
| `gemini-flash-tts:Charon:de` | de | German male — paid API |

`kokoro-v1` runs offline on the CPU at roughly 0.4x real time (10 minutes of narration
takes about 4). `gemini-flash-tts` calls the Gemini API and **costs money** — about
$0.006 per two-sentence line, so a 10-minute explainer is a few cents. There is no
offline German voice in this version.

Pick one with `--voice SPEC`; without it the scene uses `$MANIM_KIT_VOICE`, else the
fleet-wide default in `voice.json`. Audition one without rendering:

```bash
manim-kit voice say "The derivative measures how fast a function changes."
manim-kit voice say "Kurz erklärt." --voice gemini-flash-tts:Aoede:de --open
```

`manim-kit voice setup` downloads the Kokoro model (354 MB) into
`~/.cache/manim-kit/voices/` and checks its SHA-256. Run it once per host;
`manim-kit doctor` says whether it is there.

### Music under the voice

With narration the render already has an audio track, so the music is *mixed in* rather
than replacing it: the bed plays at `volume=0.12` and a `sidechaincompress` keyed on the
voice dips it about 8 dB while someone speaks, letting it back up in the pauses
(threshold 0.03, ratio 8, attack 20 ms, release 500 ms). `--no-ducking` keeps the bed
flat. A silent render is mixed exactly as before. The video is never re-encoded.

`--srt` writes subtitles next to the MP4; without it no subtitle file is produced.

### Credits

Only the music needs a credit: the bundled tracks are CC BY, and the credit line printed
after the render goes into the video description. The voices need none — Kokoro's
Apache-2.0 licence covers the model, not the audio it produces, and Google's Gemini API
terms put no attribution requirement on generated speech. If the platform you upload to
asks whether the video contains synthetic media, answer yes for the narration.

### Writing a narrated explainer

1. Outline the sections first, in plain sentences — that outline *is* the narration.
2. One `VoiceoverScene` per section, in its own file or its own class. Several short
   scenes beat one long one: they render, re-voice and debug independently.
3. Each block gets at most two sentences and the animation that illustrates them.
   Bookmarks for the "now look at this" moments.
4. Draft with `-q l` and the local Kokoro voice — seconds per render, no API cost.
5. Ship with `-q h`. Switching to a Gemini voice for the final pass re-synthesizes every
   line, so decide the wording first.
6. Tell the user the music credit line, and if a Gemini voice was used, that it was paid.

## Manim CE cheat sheet (v0.19+)

```python
from manim import *

class Demo(Scene):                   # ThreeDScene for 3D, MovingCameraScene for zoom/pan
    def construct(self):
        # --- mobjects ---
        c = Circle(radius=1, color=BLUE, fill_opacity=0.5)
        s = Square(side_length=2).next_to(c, RIGHT, buff=0.5)
        t = Text("plain text", font_size=36)                # Pango, no LaTeX needed
        f = MathTex(r"\\int_0^1 x^2\\,dx = \\frac{1}{3}")     # needs latex + dvisvgm
        f.to_edge(UP); t.to_corner(DL); s.shift(UP * 0.5); c.move_to(ORIGIN)
        g = VGroup(c, s).arrange(RIGHT, buff=1)              # lay out a group
        # --- animations ---
        self.play(Create(c), Write(t), FadeIn(f, shift=DOWN))
        self.play(c.animate.shift(LEFT).set_color(RED), run_time=2, rate_func=smooth)
        self.play(Transform(c, s))                # c now *looks like* s (c stays the handle)
        self.play(ReplacementTransform(t, f))     # t is replaced by f in the scene
        self.play(Indicate(f), Circumscribe(f), FadeOut(g))
        self.wait(1)
```

- **Directions/positions:** `UP DOWN LEFT RIGHT ORIGIN UL UR DL DR`; frame is 14.2 × 8 units.
  `.next_to(m, DIR, buff)`, `.to_edge(DIR)`, `.to_corner(DIR)`, `.move_to(point_or_mobject)`,
  `.shift(vec)`, `.scale(k)`, `.rotate(angle)`, `.align_to(m, DIR)`, `.set_x/.set_y`.
- **Colors:** `RED GREEN BLUE YELLOW ORANGE PURPLE TEAL WHITE GRAY` (+ `_A…_E` shades), hex strings ok.
- **Animations:** `Create, Uncreate, Write, Unwrite, FadeIn, FadeOut, GrowFromCenter, DrawBorderThenFill,
  Transform, ReplacementTransform, TransformMatchingTex, TransformMatchingShapes, MoveAlongPath,
  Rotate, Indicate, Flash, Circumscribe, Wiggle, ApplyWave, LaggedStart(..., lag_ratio=0.2),
  AnimationGroup, Succession`. Every `.play` takes `run_time=` and `rate_func=` (`linear, smooth,
  there_and_back, rush_into, ease_in_out_sine`). `self.wait(t)` pauses; `self.add(m)` shows instantly.
- **Updaters / continuous change:**
  ```python
  tr = ValueTracker(0)
  dot = always_redraw(lambda: Dot(axes.c2p(tr.get_value(), f(tr.get_value()))))
  label = DecimalNumber(0).add_updater(lambda m: m.set_value(tr.get_value()))
  self.add(dot, label); self.play(tr.animate.set_value(5), run_time=3)
  ```
- **Plots:** `axes = Axes(x_range=[a,b,step], y_range=[...], axis_config={"include_numbers": True})`,
  `axes.plot(lambda x: ..., color=...)`, `axes.get_graph_label(graph, "f(x)")`, `axes.c2p(x, y)`,
  `axes.get_area(graph, x_range=[0,1])`, `axes.get_vertical_line(point)`. `NumberPlane()` for a grid,
  `NumberLine()` for 1-D.
- **Text:** `Text` (unicode, `font=`, `weight=BOLD`, `t2c={"word": RED}`), `MarkupText` (Pango markup),
  `Tex(r"\\LaTeX")` (text mode), `MathTex(r"a^2")` (math mode). `MathTex` substrings are addressable:
  `f[0][2:5]` or via `substrings_to_isolate=["x"]` / `f.get_part_by_tex("x")`. Multi-line: `Tex(r"a", r"b")`.
- **3D:** `ThreeDScene`, `ThreeDAxes()`, `Surface(lambda u,v: ..., u_range, v_range)`, `Sphere(), Cube()`,
  `self.set_camera_orientation(phi=70*DEGREES, theta=-45*DEGREES)`,
  `self.begin_ambient_camera_rotation(rate=0.2)`, `self.move_camera(...)`.
- **Camera:** in `MovingCameraScene`, `self.camera.frame.animate.scale(0.5).move_to(m)`.
- **Code / tables / images:** `Code(code_string=..., language="python")`, `Table([[...]])`,
  `ImageMobject("file.png")`, `SVGMobject("file.svg")`.

## Gotchas

- ManimGL names don't exist here: `ShowCreation`→`Create`, `TextMobject`→`Tex`, `TexMobject`→`MathTex`,
  `ApplyMethod(m.shift, X)`→`m.animate.shift(X)`, `get_graph`→`plot`, `GraphScene` is gone (use `Axes`).
- Always raw strings for TeX (`r"\\frac{a}{b}"`). A LaTeX error prints the offending `.tex` path — open it.
- `Transform(a, b)` leaves `b` unshown and keeps `a` as the handle; use `ReplacementTransform` when
  you'll keep animating the target.
- `.animate` chains apply simultaneously, not sequentially; use `Succession` or separate `play` calls.
- `Text` renders without LaTeX; only `Tex`/`MathTex` need `latex` + `dvisvgm`.
- `-q l` output is 480p; do not judge line weights or font sizes from it. Off-screen? The frame is
  only 8 units tall — `.scale_to_fit_height(6)` or `.to_edge` instead of guessing coordinates.
- Long `self.wait()` at the end is cheap; a missing one cuts the last frame off.
- Renders are deterministic and cached per scene: rerunning only re-renders changed sections.
'''

METADATA = {
    "name": "manim-kit",
    "desktop_file": "manim_kit.desktop",
    "icon": "applications-graphics",
    "desc": "Scaffold, render and open Manim Community (3Blue1Brown-style) math animations",
    "terminal": True,
    "args": [],
    "tags": ["CLI"],
    "alias": "manim-kit",
    "skill_name": SKILL_NAME,
}


def _skill_status() -> str:
    if not os.path.isfile(SKILL_FILE):
        return "absent"
    try:
        with open(SKILL_FILE, encoding="utf-8") as f:
            return "current" if f.read() == SKILL_MD_CONTENT else "stale"
    except OSError:
        return "stale"


# --- respond to --advertise BEFORE anything else (5 s probe budget) -------------
if "--advertise" in sys.argv:
    print(json.dumps([{**METADATA, "skill_status": _skill_status()}]))
    sys.exit(0)

import argparse
import ast
import hashlib
import re
import shutil
import subprocess
import time
import urllib.request
from typing import Dict, Iterable, List, Optional

QUALITY = {
    "l": "480p15",
    "m": "720p30",
    "h": "1080p60",
    "p": "1440p60",
    "k": "2160p60",
}
TEMPLATES = ("basic", "text", "graph", "threed", "narrated")
APT_HINT = "sudo apt install libpango1.0-dev libcairo2-dev pkg-config"
WINDOWS = os.name == "nt"
WINGET_FFMPEG = "winget install Gyan.FFmpeg"
WINGET_LATEX = "winget install MiKTeX.MiKTeX"


# --- helpers -----------------------------------------------------------------------

def _info(msg: str) -> None:
    print(f"  • {msg}")


def _ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def _warn(msg: str) -> None:
    print(f"  ⚠️  {msg}")


def _fail(msg: str, code: int = 1) -> "NoReturn":  # type: ignore[name-defined]
    print(f"  ❌ {msg}", file=sys.stderr)
    sys.exit(code)


def _venv_ready() -> bool:
    return os.path.isfile(VENV_PYTHON)


def _manim_version() -> Optional[str]:
    """Version string of manim inside the tool venv, or None."""
    if not _venv_ready():
        return None
    try:
        out = subprocess.run(
            [VENV_PYTHON, "-c", "import manim; print(manim.__version__)"],
            capture_output=True, text=True, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    # manim-voiceover imports `sox`, which logs a multi-line "SoX could not be
    # found!" banner to stdout when the binary is absent. The version we asked
    # for is the last line printed, not the whole buffer.
    lines = [line.strip() for line in out.stdout.splitlines() if line.strip()]
    return lines[-1] if lines else None


def _require_manim() -> None:
    if _manim_version() is None:
        _fail(f"manim is not installed in {VENV_DIR}. Run: manim-kit setup")


def _class_name_from(name: str) -> str:
    """'my_cool-scene' -> 'MyCoolScene'; already-CamelCase input passes through."""
    stem = os.path.splitext(os.path.basename(name))[0]
    parts = re.split(r"[^0-9A-Za-z]+", stem)
    parts = [p for p in parts if p]
    if not parts:
        raise ValueError(f"cannot derive a class name from {name!r}")
    if len(parts) == 1 and parts[0][:1].isupper():
        cls = parts[0]
    else:
        cls = "".join(p[:1].upper() + p[1:] for p in parts)
    if cls[0].isdigit():
        cls = "Scene" + cls
    return cls


def scene_classes(path: str) -> List[str]:
    """Names of classes in *path* whose base list mentions a *Scene class.

    Pure AST scan — no manim import, so it works on the host interpreter and
    on files that would not even import.
    """
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    found: List[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            base_name = base.id if isinstance(base, ast.Name) else (
                base.attr if isinstance(base, ast.Attribute) else ""
            )
            if base_name.endswith("Scene"):
                found.append(node.name)
                break
    return found


def render_template(template: str, class_name: str) -> str:
    src = os.path.join(TEMPLATE_DIR, f"{template}.py")
    if not os.path.isfile(src):
        raise FileNotFoundError(f"unknown template {template!r}; choose from {', '.join(TEMPLATES)}")
    with open(src, encoding="utf-8") as f:
        return f.read().replace("{{SCENE}}", class_name)


def _media_outputs(scene_dir: str, stem: str, since: float) -> List[str]:
    """Files under media/{videos,images}/<stem>/ modified at or after *since*."""
    out: List[str] = []
    for kind in ("videos", "images"):
        root = os.path.join(scene_dir, "media", kind, stem)
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, names in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "partial_movie_files"]
            for n in names:
                p = os.path.join(dirpath, n)
                try:
                    if os.path.getmtime(p) >= since - 1:
                        out.append(p)
                except OSError:
                    continue
    return sorted(out)


def _newest_output(scene_dir: str, stem: str) -> Optional[str]:
    files = _media_outputs(scene_dir, stem, since=0)
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def _xdg_open(path: str) -> None:
    if WINDOWS:
        os.startfile(path)  # the file's default application
        return
    opener = shutil.which("xdg-open")
    if opener is None:
        _warn(f"xdg-open not found; open manually: {path}")
        return
    subprocess.Popen([opener, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# --- music -------------------------------------------------------------------------

AUDIO_EXTS = (".mp3", ".m4a", ".wav", ".ogg", ".flac")


def music_manifest() -> List[Dict[str, object]]:
    """The committed track list from music.json (empty list if it is missing)."""
    if not os.path.isfile(MUSIC_JSON):
        return []
    with open(MUSIC_JSON, encoding="utf-8") as f:
        return json.load(f).get("tracks", [])


def _manifest_entry(track_id: str) -> Optional[Dict[str, object]]:
    for entry in music_manifest():
        if entry["id"] == track_id:
            return entry
    return None


def _track_path(entry: Dict[str, object]) -> str:
    ext = os.path.splitext(str(entry["url"]).split("?")[0])[1] or ".mp3"
    return os.path.join(MUSIC_DIR, f"{entry['id']}{ext}")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_cached(entry: Dict[str, object]) -> bool:
    path = _track_path(entry)
    return os.path.isfile(path) and _sha256(path) == entry["sha256"]


def fetch_track(entry: Dict[str, object], force: bool = False) -> str:
    """Download *entry* into MUSIC_DIR unless it is already there and intact.

    Downloads to ``<name>.part`` and only renames once the digest matches, so an
    interrupted fetch can never leave a truncated file that later passes as cached.
    """
    path = _track_path(entry)
    if not force and _is_cached(entry):
        return path
    os.makedirs(MUSIC_DIR, exist_ok=True)
    part = path + ".part"
    _info(f"fetching {entry['id']} ({entry['title']})")
    # The URL is percent-encoded as archive.org serves it; re-encoding breaks the
    # redirect to the dnNNNNNN node for names with commas or apostrophes.
    req = urllib.request.Request(str(entry["url"]), headers={"User-Agent": f"manim-kit/{__version__}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, open(part, "wb") as out:
            shutil.copyfileobj(resp, out)
    except Exception as exc:  # network, HTTP, disk — all end the same way
        if os.path.exists(part):
            os.remove(part)
        raise RuntimeError(f"could not download {entry['id']}: {exc}") from exc
    got = _sha256(part)
    if got != entry["sha256"]:
        os.remove(part)
        raise RuntimeError(f"checksum mismatch for {entry['id']}: got {got}, expected {entry['sha256']}")
    os.replace(part, path)
    return path


def _local_tracks() -> Dict[str, str]:
    """Audio files sitting in MUSIC_DIR, keyed by filename stem."""
    if not os.path.isdir(MUSIC_DIR):
        return {}
    found = {}
    for name in sorted(os.listdir(MUSIC_DIR)):
        if name.lower().endswith(AUDIO_EXTS):
            found[os.path.splitext(name)[0]] = os.path.join(MUSIC_DIR, name)
    return found


def resolve_track(track_id: Optional[str]) -> tuple:
    """(path, credit) for *track_id*; fetches it when it is a manifest entry.

    A bare filename stem in MUSIC_DIR wins over nothing; the manifest wins over a
    stale local file of the same id. With no id, the first manifest entry is used.
    """
    if track_id is None:
        track_id = os.environ.get("MANIM_KIT_TRACK") or None
    if track_id is None:
        manifest = music_manifest()
        if not manifest:
            raise RuntimeError(f"no tracks in {MUSIC_JSON} and none requested")
        entry = manifest[0]
    else:
        entry = _manifest_entry(track_id)
        if entry is None:
            local = _local_tracks().get(track_id)
            if local is None:
                known = sorted(set(list(_local_tracks()) + [str(e["id"]) for e in music_manifest()]))
                raise RuntimeError(f"unknown track {track_id!r}; have: {', '.join(known) or '(none)'}")
            return local, ""
    return fetch_track(entry), str(entry["credit"])


def _video_duration(path: str) -> Optional[float]:
    probe = shutil.which("ffprobe")
    if probe is None:
        return None
    out = subprocess.run(
        [probe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def has_audio_stream(path: str) -> bool:
    """True when *path* carries at least one audio stream.

    A narrated render does — manim mixes the voice clips into the MP4 — and a
    silent one does not. The two need different music mixes.
    """
    probe = shutil.which("ffprobe")
    if probe is None:
        return False
    out = subprocess.run(
        [probe, "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=codec_type", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    return "audio" in out.stdout


def mux_command(video: str, track: str, out: str, duration: float,
                gain: float = MUSIC_GAIN, fade: float = MUSIC_FADE,
                voice: bool = False, duck: bool = True) -> List[str]:
    """The ffmpeg call that lays *track* under *video* at *gain*, faded in and out.

    ``-stream_loop -1`` covers a track shorter than the video, ``-shortest`` trims a
    longer one, and ``-c:v copy`` means the video is never re-encoded.

    With *voice* the render already has a narration track, so the music is mixed
    with it rather than replacing it: by default a ``sidechaincompress`` keyed on
    the voice dips the bed while someone speaks (``duck=False`` keeps it flat),
    then ``amix`` combines the two at their own levels.
    """
    music_filters = []
    if fade > 0:
        music_filters.append(f"afade=t=in:st=0:d={fade:g}")
        music_filters.append(f"afade=t=out:st={max(duration - fade, 0):.3f}:d={fade:g}")
    music_filters.append(f"volume={gain:g}")

    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    head = [ffmpeg, "-y", "-loglevel", "error",
            "-i", video, "-stream_loop", "-1", "-i", track]
    tail = ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out]

    if not voice:
        return head + ["-filter:a", ",".join(music_filters),
                       "-map", "0:v", "-map", "1:a"] + tail

    steps = [f"[1:a]{','.join(music_filters)}[bed]"]
    if duck:
        # The voice is split: one copy is the compressor's key, the other is
        # what the listener hears. sidechaincompress takes the bed first and
        # the key second.
        steps.append("[0:a]asplit=2[vkey][vout]")
        steps.append(
            f"[bed][vkey]sidechaincompress=threshold={DUCK_THRESHOLD:g}:ratio={DUCK_RATIO:g}"
            f":attack={DUCK_ATTACK_MS:g}:release={DUCK_RELEASE_MS:g}[ducked]"
        )
        steps.append("[ducked][vout]amix=inputs=2:duration=first:normalize=0[mix]")
    else:
        steps.append("[bed][0:a]amix=inputs=2:duration=first:normalize=0[mix]")
    return head + ["-filter_complex", ";".join(steps),
                   "-map", "0:v", "-map", "[mix]"] + tail


def mux_music(video: str, track: str, gain: float = MUSIC_GAIN, fade: float = MUSIC_FADE,
              duck: bool = True) -> bool:
    """Mix *track* under *video* in place. False (with a warning) on any failure.

    A render that produced a good silent file must never fail because of the music.
    """
    if shutil.which("ffmpeg") is None:
        _warn("ffmpeg not found — leaving the render silent")
        return False
    duration = _video_duration(video)
    if duration is None:
        _warn(f"no duration for {os.path.basename(video)} — leaving it silent")
        return False
    tmp = video + ".music.mp4"
    proc = subprocess.run(
        mux_command(video, track, tmp, duration, gain, fade,
                    voice=has_audio_stream(video), duck=duck),
        capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.isfile(tmp):
        if os.path.exists(tmp):
            os.remove(tmp)
        _warn(f"ffmpeg could not add music ({proc.stderr.strip().splitlines()[-1:] or ['no output']}); "
              "the silent render is intact")
        return False
    os.replace(tmp, video)
    return True


# --- voice -------------------------------------------------------------------------

def voice_manifest() -> Dict[str, object]:
    """The committed voice.json (empty dict when it is missing)."""
    if not os.path.isfile(VOICE_JSON):
        return {}
    with open(VOICE_JSON, encoding="utf-8") as f:
        return json.load(f)


def voice_default() -> str:
    """The fleet-wide default spec: $MANIM_KIT_VOICE wins over voice.json."""
    from_env = os.environ.get("MANIM_KIT_VOICE")
    if from_env:
        return from_env
    return str(voice_manifest().get("default") or "kokoro-v1:af_sarah")


def curated_voices() -> List[Dict[str, str]]:
    return list(voice_manifest().get("voices", []))  # type: ignore[arg-type]


def kokoro_manifest() -> List[Dict[str, object]]:
    """The Kokoro model files: name, url, sha256, bytes."""
    model = voice_manifest().get("kokoro_model", {})
    return list(model.get("files", []))  # type: ignore[union-attr]


def _voice_file_path(entry: Dict[str, object]) -> str:
    return os.path.join(VOICE_DIR, str(entry["name"]))


def _voice_file_cached(entry: Dict[str, object]) -> bool:
    path = _voice_file_path(entry)
    return os.path.isfile(path) and _sha256(path) == entry["sha256"]


def kokoro_cached() -> bool:
    """True when every Kokoro file is present with the right digest."""
    files = kokoro_manifest()
    return bool(files) and all(_voice_file_cached(e) for e in files)


def fetch_voice_file(entry: Dict[str, object], force: bool = False) -> str:
    """Download one Kokoro file into VOICE_DIR, verifying its sha256.

    Same shape as fetch_track: a ``.part`` file that is only renamed once the
    digest matches, so an interrupted download cannot pass as cached later.
    """
    path = _voice_file_path(entry)
    if not force and _voice_file_cached(entry):
        return path
    os.makedirs(VOICE_DIR, exist_ok=True)
    part = path + ".part"
    _info(f"fetching {entry['name']} ({int(entry['bytes']) / 1e6:.0f} MB)")
    req = urllib.request.Request(str(entry["url"]), headers={"User-Agent": f"manim-kit/{__version__}"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(part, "wb") as out:
            shutil.copyfileobj(resp, out)
    except Exception as exc:
        if os.path.exists(part):
            os.remove(part)
        raise RuntimeError(f"could not download {entry['name']}: {exc}") from exc
    got = _sha256(part)
    if got != entry["sha256"]:
        os.remove(part)
        raise RuntimeError(f"checksum mismatch for {entry['name']}: got {got}, expected {entry['sha256']}")
    os.replace(part, path)
    return path


def _voice_check() -> List[Dict[str, str]]:
    """Ask manim_kit_voice.py, inside the venv, which backends are usable.

    Returns one dict per backend. An empty list means the venv could not answer
    (no venv, no manim-voiceover), which the caller reports as such.
    """
    if not _venv_ready() or not os.path.isfile(VOICE_MODULE):
        return []
    try:
        out = subprocess.run([VENV_PYTHON, VOICE_MODULE, "check"],
                             capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if out.returncode != 0:
        return []
    rows = []
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[1] in ("usable", "unusable"):
            rows.append({"backend": parts[0], "usable": parts[1], "note": parts[2]})
        elif len(parts) >= 2 and parts[0] == "note":
            rows.append({"backend": "note", "usable": "", "note": parts[1]})
    return rows


def _valid_spec(spec: str) -> bool:
    """Whether *spec* names a known backend and a voice. Mirrors parse_spec."""
    parts = spec.split(":")
    backends = set(voice_manifest().get("backends", {}))  # type: ignore[arg-type]
    return 2 <= len(parts) <= 3 and parts[0] in backends and bool(parts[1].strip())


# --- commands ----------------------------------------------------------------------

def cmd_setup(args: argparse.Namespace) -> int:
    if args.force and os.path.isdir(VENV_DIR):
        _info(f"Removing {VENV_DIR}")
        shutil.rmtree(VENV_DIR)
    if not _venv_ready():
        _info(f"Creating venv at {VENV_DIR}")
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
    pip = [VENV_PYTHON, "-m", "pip"]
    subprocess.run(pip + ["install", "-q", "--upgrade", "pip"], check=False)
    _info(f"Installing manim from {os.path.basename(MANIM_REQUIREMENTS)} (this takes a few minutes)")
    proc = subprocess.run(pip + ["install", "-r", MANIM_REQUIREMENTS], capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        print(tail, file=sys.stderr)
        if WINDOWS:
            # manimpango ships Windows wheels, so a pip failure here is not a
            # missing system library and apt is not the answer.
            _warn("pip could not install manim. Read the error above; "
                  "manimpango has Windows wheels, so this is not a missing "
                  "Pango/Cairo build dependency.")
        elif "pangocairo" in proc.stderr or "manimpango" in proc.stderr:
            _warn("ManimPango has no Linux wheels and must compile against Pango/Cairo headers.")
            print(f"Run: {APT_HINT} && manim-kit setup")
        return 1
    _ok(f"manim {_manim_version()} installed")
    return cmd_doctor(args)


def cmd_doctor(args: argparse.Namespace) -> int:
    problems = 0
    print("manim-kit doctor")
    ver = _manim_version()
    if ver:
        _ok(f"manim {ver} in {VENV_DIR}")
    else:
        problems += 1
        _warn(f"manim not installed in {VENV_DIR} — run: manim-kit setup")
    if WINDOWS:
        install_hint = {
            "ffmpeg": WINGET_FFMPEG,
            "latex": f"{WINGET_LATEX}  (MiKTeX; TeX Live works too)",
            "dvisvgm": f"{WINGET_LATEX}  (dvisvgm comes with MiKTeX)",
        }
    else:
        install_hint = {}
    probes = [
        ("ffmpeg", "video encoding (required)", True),
        ("latex", "Tex/MathTex (optional — Text() works without)", False),
        ("dvisvgm", "Tex/MathTex SVG conversion (optional)", False),
    ]
    if not WINDOWS:  # Windows opens files through os.startfile, no helper needed
        probes.append(("xdg-open", "`manim-kit open` (optional)", False))
    for exe, why, required in probes:
        path = shutil.which(exe)
        if path:
            _ok(f"{exe}: {path}")
            continue
        hint = install_hint.get(exe)
        note = f"{exe} missing — {why}" + (f". Install: {hint}" if hint else "")
        if required:
            problems += 1
            _warn(note)
        else:
            _info(note)
    # manimpango ships Windows wheels, so the Pango/Cairo header check is a
    # Linux-only concern.
    pkgconfig = None if WINDOWS else shutil.which("pkg-config")
    if pkgconfig and ver is None:
        have = subprocess.run([pkgconfig, "--exists", "pangocairo"], capture_output=True).returncode == 0
        if not have:
            _warn(f"pangocairo headers missing (ManimPango builds from source). Run: {APT_HINT}")
    cached = sum(1 for e in music_manifest() if _is_cached(e))
    total = len(music_manifest())
    if cached:
        _ok(f"music: {cached}/{total} manifest tracks cached in {MUSIC_DIR}")
    else:
        _info(f"music: no tracks cached — run: manim-kit music fetch")
    rows = _voice_check()
    if not rows:
        _info("voice: the venv could not be asked — run: manim-kit setup")
    for row in rows:
        if row["backend"] == "note":
            _info(f"voice: {row['note']}")
        elif row["usable"] == "usable":
            _ok(f"voice {row['backend']}: {row['note']}")
        else:
            _info(f"voice {row['backend']}: {row['note']}")
    if rows:
        _info(f"voice default: {voice_default()}")
    status = _skill_status()
    (_ok if status == "current" else _info)(f"Claude skill '{SKILL_NAME}': {status}")
    print("  all good" if problems == 0 else f"  {problems} problem(s)")
    return 0 if problems == 0 else 1


def cmd_new(args: argparse.Namespace) -> int:
    class_name = args.scene or _class_name_from(args.name)
    stem = os.path.splitext(os.path.basename(args.name))[0]
    target = os.path.join(args.dir, f"{stem}.py")
    if os.path.exists(target) and not args.force:
        _fail(f"{target} exists (use --force to overwrite)")
    os.makedirs(args.dir, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        f.write(render_template(args.template, class_name))
    _ok(f"wrote {target}  (class {class_name}, template {args.template})")
    print(f"Run: manim-kit render {target} {class_name} -q l")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    if not os.path.isfile(args.file):
        _fail(f"no such file: {args.file}")
    names = scene_classes(args.file)
    if not names:
        _warn(f"no Scene subclasses found in {args.file}")
        return 1
    for n in names:
        print(n)
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    _require_manim()
    path = os.path.abspath(args.file)
    if not os.path.isfile(path):
        _fail(f"no such file: {args.file}")
    scene_dir = os.path.dirname(path)
    stem = os.path.splitext(os.path.basename(path))[0]

    scenes: List[str] = list(args.scenes)
    available = scene_classes(path)
    if not scenes and not args.all:
        if len(available) == 1:
            scenes = available
        elif not available:
            _fail(f"no Scene subclasses found in {args.file}")
        else:
            _fail("several scenes in file, name one or pass --all:\n    " + "\n    ".join(available))
    unknown = [s for s in scenes if s not in available]
    if unknown:
        _fail(f"scene(s) not in {args.file}: {', '.join(unknown)}  (have: {', '.join(available)})")

    cmd = [VENV_PYTHON, "-m", "manim", "render", "-q", args.quality]
    if args.all:
        cmd.append("-a")
    if args.preview:
        cmd.append("-p")
    if args.last_frame:
        cmd.append("-s")
    if args.transparent:
        cmd.append("-t")
    if args.format:
        cmd += ["--format", args.format]
    if args.output:
        cmd += ["-o", args.output]
    cmd += args.manim_args
    cmd.append(path)
    cmd += scenes

    # Music only makes sense for a video output; a PNG or GIF carries no audio track.
    want_music = getattr(args, "music", False)
    silent_output = args.last_frame or args.format in ("png", "gif")
    if want_music and silent_output:
        want_music = False
    track = credit = None
    if want_music:
        try:
            track, credit = resolve_track(args.track)
        except RuntimeError as exc:
            _fail(str(exc))

    # The scene imports manim_kit_voice, which lives next to this script rather
    # than next to the scene, so the repo goes on the subprocess PYTHONPATH.
    env = dict(os.environ)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = SCRIPT_DIR + (os.pathsep + existing if existing else "")
    voice_spec = args.voice or env.get("MANIM_KIT_VOICE") or ""
    if args.voice:
        if not _valid_spec(args.voice):
            _fail(f"unknown voice spec {args.voice!r}; see: manim-kit voice list")
        env["MANIM_KIT_VOICE"] = args.voice
    env["MANIM_KIT_SRT"] = "1" if args.srt else "0"

    if args.dry_run:
        print(" ".join(cmd))
        print(f"PYTHONPATH={env['PYTHONPATH']}")
        if voice_spec:
            print(f"MANIM_KIT_VOICE={voice_spec}")
        print(f"MANIM_KIT_SRT={env['MANIM_KIT_SRT']}")
        if want_music:
            # The render does not exist yet, so the dry run shows the silent
            # mix; a narrated render takes the ducking branch of mux_command.
            print(" ".join(mux_command("<video.mp4>", track, "<video.mp4>.music.mp4",
                                       duration=60.0, gain=args.music_gain,
                                       fade=0.0 if args.no_music_fade else MUSIC_FADE,
                                       voice=bool(voice_spec), duck=not args.no_ducking)))
        return 0

    start = time.time()
    _info(f"cwd {scene_dir}")
    _info(" ".join(os.path.basename(c) if c == VENV_PYTHON else c for c in cmd))
    proc = subprocess.run(cmd, cwd=scene_dir, env=env)
    if proc.returncode != 0:
        _fail(f"manim exited with {proc.returncode}", proc.returncode)
    outputs = _media_outputs(scene_dir, stem, since=start)
    narrated = any(p.lower().endswith(".mp4") and has_audio_stream(p) for p in outputs)
    mixed = 0
    if want_music:
        for p in outputs:
            if p.lower().endswith(".mp4") and mux_music(
                p, track, args.music_gain, 0.0 if args.no_music_fade else MUSIC_FADE,
                duck=not args.no_ducking,
            ):
                mixed += 1
    if outputs:
        print("Output:")
        for p in outputs:
            print(f"  {p}")
    else:
        _warn("render finished but no new files found under media/")
    if mixed and credit:
        print("Music credit — put this in the video description:")
        print(f"  {credit}")
    if narrated and voice_spec.startswith("gemini"):
        print(f"Voice: {voice_spec} (Gemini TTS, paid — about $0.006 per narration line; "
              "unchanged lines are served from media/voiceovers/ and cost nothing)")
    return 0


def cmd_music(args: argparse.Namespace) -> int:
    manifest = music_manifest()
    action = args.action or "list"

    if action == "list":
        local = _local_tracks()
        for entry in manifest:
            mark = "cached" if _is_cached(entry) else "not fetched"
            print(f"  {entry['id']:<24} {entry['title']} — {entry['artist']} "
                  f"({entry['licence']}) [{mark}]")
            local.pop(str(entry["id"]), None)
        for stem, path in local.items():
            print(f"  {stem:<24} (your own file: {path})")
        if not manifest and not local:
            _info(f"no tracks; run: manim-kit music fetch")
        return 0

    if action == "fetch":
        wanted = args.ids or [str(e["id"]) for e in manifest]
        failed = 0
        for track_id in wanted:
            entry = _manifest_entry(track_id)
            if entry is None:
                _warn(f"not in the manifest: {track_id}")
                failed += 1
                continue
            try:
                path = fetch_track(entry, force=args.force)
            except RuntimeError as exc:
                _warn(str(exc))
                failed += 1
                continue
            _ok(f"{entry['id']} → {path}")
        return 1 if failed else 0

    if action == "add":
        if not args.ids:
            _fail("music add needs a file path")
        src = args.ids[0]
        if not os.path.isfile(src):
            _fail(f"no such file: {src}")
        track_id = args.id or os.path.splitext(os.path.basename(src))[0]
        dst = os.path.join(MUSIC_DIR, track_id + os.path.splitext(src)[1].lower())
        os.makedirs(MUSIC_DIR, exist_ok=True)
        shutil.copy2(src, dst)
        _ok(f"added {track_id} → {dst}")
        print(f"Use it with: manim-kit render FILE.py --track {track_id}")
        return 0

    if action == "credits":
        wanted = args.ids or [str(e["id"]) for e in manifest]
        for track_id in wanted:
            entry = _manifest_entry(track_id)
            print(entry["credit"] if entry else f"(no credit on record for {track_id})")
        return 0

    _fail(f"unknown music action: {action}")


def cmd_voice(args: argparse.Namespace) -> int:
    action = args.action or "list"

    if action == "list":
        default = voice_default()
        usable = {r["backend"]: r for r in _voice_check() if r["backend"] != "note"}
        for entry in curated_voices():
            spec = str(entry["spec"])
            backend = spec.split(":")[0]
            row = usable.get(backend)
            if row is None:
                mark = "backend unknown to the venv"
            elif row["usable"] == "usable":
                mark = "usable"
            else:
                mark = row["note"]
            star = "*" if spec == default else " "
            print(f" {star} {spec:<30} {entry['lang']:<3} {entry['note']}")
            print(f"{'':<36}[{mark}]")
        print(f"\nDefault: {default}"
              + ("  (from $MANIM_KIT_VOICE)" if os.environ.get("MANIM_KIT_VOICE") else
                 f"  (from {os.path.basename(VOICE_JSON)})"))
        print("Override per render with: manim-kit render FILE.py --voice SPEC")
        return 0

    if action == "setup":
        files = kokoro_manifest()
        if not files:
            _fail(f"no Kokoro files listed in {VOICE_JSON}")
        total = sum(int(e["bytes"]) for e in files)
        _info(f"Kokoro v1.0 model into {VOICE_DIR}: "
              + ", ".join(f"{e['name']} {int(e['bytes']) / 1e6:.0f} MB" for e in files)
              + f" ({total / 1e6:.0f} MB total)")
        failed = 0
        for entry in files:
            if not args.force and _voice_file_cached(entry):
                _ok(f"{entry['name']} already cached")
                continue
            try:
                path = fetch_voice_file(entry, force=args.force)
            except RuntimeError as exc:
                _warn(str(exc))
                failed += 1
                continue
            _ok(f"{entry['name']} → {path}")
        if failed:
            return 1
        print("Run: manim-kit voice say \"A first test of the narration voice.\"")
        return 0

    if action == "say":
        if not args.text:
            _fail("voice say needs some text")
        _require_manim()
        spec = args.voice or voice_default()
        if not _valid_spec(spec):
            _fail(f"unknown voice spec {spec!r}; see: manim-kit voice list")
        backend, voice = spec.split(":")[0], spec.split(":")[1]
        out = args.out or os.path.join(os.getcwd(), f"voice-{backend}-{voice}.mp3")
        cmd = [VENV_PYTHON, VOICE_MODULE, "say", " ".join(args.text),
               "--voice", spec, "--out", os.path.abspath(out)]
        if args.style:
            cmd += ["--style", args.style]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            tail = "\n".join(proc.stderr.strip().splitlines()[-10:])
            print(tail, file=sys.stderr)
            _fail(f"synthesis failed for {spec}")
        _ok(f"{spec} → {os.path.abspath(out)}")
        if args.open:
            _xdg_open(os.path.abspath(out))
        return 0

    _fail(f"unknown voice action: {action}")


def cmd_open(args: argparse.Namespace) -> int:
    path = os.path.abspath(args.file)
    scene_dir = os.path.dirname(path)
    stem = os.path.splitext(os.path.basename(path))[0]
    target = _newest_output(scene_dir, stem)
    if args.scene and target is not None:
        cands = [p for p in _media_outputs(scene_dir, stem, since=0)
                 if os.path.splitext(os.path.basename(p))[0].startswith(args.scene)]
        target = max(cands, key=os.path.getmtime) if cands else None
    if target is None:
        _fail(f"no renders found under {os.path.join(scene_dir, 'media')} for {stem}")
    _info(f"opening {target}")
    _xdg_open(target)
    return 0


# --- installer protocol ------------------------------------------------------------

def _install_skill() -> None:
    os.makedirs(SKILL_DIR, exist_ok=True)
    if _skill_status() == "current":
        _info(f"Skill already up-to-date: {SKILL_FILE}")
        return
    verb = "Updated" if os.path.exists(SKILL_FILE) else "Installed"
    with open(SKILL_FILE, "w", encoding="utf-8") as f:
        f.write(SKILL_MD_CONTENT)
    _ok(f"{verb} Claude skill at {SKILL_FILE}")


def _uninstall_skill() -> None:
    if os.path.exists(SKILL_FILE):
        os.remove(SKILL_FILE)
        _ok(f"Removed {SKILL_FILE}")
    else:
        _info(f"No skill file at {SKILL_FILE}")
    try:
        os.rmdir(SKILL_DIR)
    except OSError:
        pass


def _tool_installer():
    try:
        from cli_tools_kit import ToolInstaller, ToolMetadata  # lazy: only --install/--remove need it
    except ImportError:
        _fail("cli-tools-kit is not importable by this interpreter.\n"
              "Run: pip install -r requirements.txt   (or use the AutomatedAlchemy installer GUI)")
    import dataclasses
    # skill_name is advertise-only; keep whatever fields this cli-tools-kit version knows.
    known = {f.name for f in dataclasses.fields(ToolMetadata)}
    meta = ToolMetadata(**{k: v for k, v in METADATA.items() if k in known})
    return ToolInstaller(script_path=os.path.abspath(__file__), metadata=meta)


def cmd_install(_args: argparse.Namespace) -> int:
    _tool_installer().install()
    _install_skill()
    if _manim_version() is None:
        print("Run: manim-kit setup")
    return 0


def cmd_remove(_args: argparse.Namespace) -> int:
    _tool_installer().remove()
    _uninstall_skill()
    return 0


# --- CLI ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="manim-kit",
        description="Scaffold, list, render and open Manim Community scenes.",
        epilog="Anything after `--` in `render` is passed to `manim render` unchanged.",
    )
    p.add_argument("--version", action="version", version=f"manim-kit {__version__}")
    p.add_argument("--install", action="store_true", help="install the bash alias + Claude skill")
    p.add_argument("--remove", action="store_true", help="remove the bash alias + Claude skill")
    p.add_argument("--install-skill", action="store_true", help=f"write ~/.claude/skills/{SKILL_NAME}/SKILL.md")
    p.add_argument("--uninstall-skill", action="store_true", help="remove the Claude skill")

    sub = p.add_subparsers(dest="cmd")

    s = sub.add_parser("setup", help="create .venv and install manim into it")
    s.add_argument("--force", action="store_true", help="recreate the venv from scratch")
    s.set_defaults(func=cmd_setup)

    s = sub.add_parser("doctor", help="check manim, ffmpeg, LaTeX and the skill")
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("new", help="write a new scene file from a template")
    s.add_argument("name", help="file stem (e.g. pythagoras → pythagoras.py); class name is derived")
    s.add_argument("--template", "-t", choices=TEMPLATES, default="basic")
    s.add_argument("--dir", "-d", default=".", help="directory to write into (default: cwd)")
    s.add_argument("--scene", "-s", help="explicit Scene class name")
    s.add_argument("--force", action="store_true", help="overwrite an existing file")
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("list", help="list Scene classes in a file")
    s.add_argument("file")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("render", help="render one or more scenes")
    s.add_argument("file")
    s.add_argument("scenes", nargs="*", help="Scene class names (default: the only scene in the file)")
    s.add_argument("-q", "--quality", choices=sorted(QUALITY), default="h",
                   help="l=480p15 m=720p30 h=1080p60 p=1440p60 k=2160p60 (default: h)")
    s.add_argument("-a", "--all", action="store_true", help="render every scene in the file")
    s.add_argument("-p", "--preview", action="store_true", help="open the result when done")
    s.add_argument("-s", "--last-frame", action="store_true", help="save only the last frame as PNG")
    s.add_argument("-t", "--transparent", action="store_true", help="transparent background")
    s.add_argument("--format", choices=["mp4", "gif", "png", "webm", "mov"])
    s.add_argument("-o", "--output", help="output file name (passed to manim -o)")
    s.add_argument("--dry-run", action="store_true", help="print the manim command and exit")
    s.add_argument("--no-music", dest="music", action="store_false", default=True,
                   help="render silent, no background track")
    s.add_argument("--track", help="track id (default: first in music.json, or $MANIM_KIT_TRACK)")
    s.add_argument("--music-gain", type=float, default=MUSIC_GAIN,
                   help=f"music volume, 1.0 = unchanged (default: {MUSIC_GAIN})")
    s.add_argument("--no-music-fade", action="store_true", help="no fade in/out on the music")
    s.add_argument("--voice", help="narration voice, backend:voice[:lang] "
                                   "(default: $MANIM_KIT_VOICE, else voice.json)")
    s.add_argument("--srt", action="store_true",
                   help="also write subtitles next to the video (narrated scenes only)")
    s.add_argument("--no-ducking", action="store_true",
                   help="keep a flat music bed instead of dipping it under the voice")
    s.set_defaults(func=cmd_render)

    s = sub.add_parser(
        "music", help="manage the background-music library",
        epilog="The real 3Blue1Brown music is all rights reserved and licensed per "
               f"project at {RUBINETTI_FORM} — it cannot be shipped here. These tracks "
               "are CC BY; the credit line printed after a render with music belongs in "
               "your video description.",
    )
    s.add_argument("action", nargs="?", choices=["list", "fetch", "add", "credits"], default="list")
    s.add_argument("ids", nargs="*", help="track ids (fetch/credits) or a file path (add)")
    s.add_argument("--id", help="id to store an added file under (default: its filename)")
    s.add_argument("--force", action="store_true", help="re-download even when cached")
    s.set_defaults(func=cmd_music)

    s = sub.add_parser(
        "voice", help="narration voices: list them, audition one, cache the model",
        epilog="A spec is backend:voice[:lang]. kokoro-v1 runs offline on the CPU; "
               "gemini-flash-tts calls the paid Gemini API and needs GEMINI_API_KEY.",
    )
    s.add_argument("action", nargs="?", choices=["list", "say", "setup"], default="list")
    s.add_argument("text", nargs="*", help="the text to speak (say)")
    s.add_argument("--voice", help="spec to use (default: $MANIM_KIT_VOICE, else voice.json)")
    s.add_argument("--out", help="output file (default: voice-<backend>-<voice>.mp3 in cwd)")
    s.add_argument("--style", help="Gemini delivery instruction, e.g. 'Read this slowly'")
    s.add_argument("--open", action="store_true", help="open the clip when it is written")
    s.add_argument("--force", action="store_true", help="re-download the model files (setup)")
    s.set_defaults(func=cmd_voice)

    s = sub.add_parser("open", help="open the newest render of a scene file")
    s.add_argument("file")
    s.add_argument("scene", nargs="?", help="restrict to one Scene name")
    s.set_defaults(func=cmd_open)
    return p


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = build_parser()
    raw = list(argv) if argv is not None else sys.argv[1:]
    # Everything after the first bare `--` is handed to `manim render` verbatim.
    manim_args: List[str] = []
    if "--" in raw:
        cut = raw.index("--")
        raw, manim_args = raw[:cut], raw[cut + 1:]
    args = parser.parse_args(raw)
    args.manim_args = manim_args
    if args.install:
        return cmd_install(args)
    if args.remove:
        return cmd_remove(args)
    if args.install_skill:
        _install_skill()
        return 0
    if args.uninstall_skill:
        _uninstall_skill()
        return 0
    if not args.cmd:
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
