#!/usr/bin/env python3
"""manim-kit — scaffold, list, render and open Manim Community scenes.

Stdlib-only entry point. Manim itself lives in a tool-owned virtualenv
(``.venv/`` next to this file) created by ``manim-kit setup``; every render
is delegated to that interpreter, so the host Python stays clean and the
``--advertise`` probe answers instantly.

Speaks the cli-tool-kit installer protocol (``--advertise``, ``--install``,
``--remove``, ``--install-skill``, ``--uninstall-skill``).
"""

import json
import os
import sys

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
| New scene file from a template | `manim-kit new NAME [--template basic\\|text\\|graph\\|threed] [--dir DIR]` |
| List the Scene classes in a file | `manim-kit list FILE.py` |
| Render (1080p60, the default) | `manim-kit render FILE.py [SceneName]` |
| Draft render (480p15, seconds) | `manim-kit render FILE.py SceneName -q l` |
| Render every scene in the file | `manim-kit render FILE.py --all` |
| GIF / PNG last frame / transparent | `--format gif` · `--last-frame` · `--transparent` |
| Render silent (music is on by default) | `manim-kit render FILE.py --no-music` |
| Music library | `manim-kit music list\\|fetch\\|add FILE\\|credits` |
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
TEMPLATES = ("basic", "text", "graph", "threed")
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
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


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


def mux_command(video: str, track: str, out: str, duration: float,
                gain: float = MUSIC_GAIN, fade: float = MUSIC_FADE) -> List[str]:
    """The ffmpeg call that lays *track* under *video* at *gain*, faded in and out.

    ``-stream_loop -1`` covers a track shorter than the video, ``-shortest`` trims a
    longer one, and ``-c:v copy`` means the video is never re-encoded.
    """
    filters = []
    if fade > 0:
        filters.append(f"afade=t=in:st=0:d={fade:g}")
        filters.append(f"afade=t=out:st={max(duration - fade, 0):.3f}:d={fade:g}")
    filters.append(f"volume={gain:g}")
    return [
        shutil.which("ffmpeg") or "ffmpeg", "-y", "-loglevel", "error",
        "-i", video, "-stream_loop", "-1", "-i", track,
        "-filter:a", ",".join(filters),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out,
    ]


def mux_music(video: str, track: str, gain: float = MUSIC_GAIN, fade: float = MUSIC_FADE) -> bool:
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
    proc = subprocess.run(mux_command(video, track, tmp, duration, gain, fade),
                          capture_output=True, text=True)
    if proc.returncode != 0 or not os.path.isfile(tmp):
        if os.path.exists(tmp):
            os.remove(tmp)
        _warn(f"ffmpeg could not add music ({proc.stderr.strip().splitlines()[-1:] or ['no output']}); "
              "the silent render is intact")
        return False
    os.replace(tmp, video)
    return True


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

    if args.dry_run:
        print(" ".join(cmd))
        if want_music:
            print(" ".join(mux_command("<video.mp4>", track, "<video.mp4>.music.mp4",
                                       duration=60.0, gain=args.music_gain,
                                       fade=0.0 if args.no_music_fade else MUSIC_FADE)))
        return 0

    start = time.time()
    _info(f"cwd {scene_dir}")
    _info(" ".join(os.path.basename(c) if c == VENV_PYTHON else c for c in cmd))
    proc = subprocess.run(cmd, cwd=scene_dir)
    if proc.returncode != 0:
        _fail(f"manim exited with {proc.returncode}", proc.returncode)
    outputs = _media_outputs(scene_dir, stem, since=start)
    mixed = 0
    if want_music:
        for p in outputs:
            if p.lower().endswith(".mp4") and mux_music(
                p, track, args.music_gain, 0.0 if args.no_music_fade else MUSIC_FADE
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
        from cli_tool_kit import ToolInstaller, ToolMetadata  # lazy: only --install/--remove need it
    except ImportError:
        _fail("cli-tool-kit is not importable by this interpreter.\n"
              "Run: pip install -r requirements.txt   (or use the AutomatedAlchemy installer GUI)")
    import dataclasses
    # skill_name is advertise-only; keep whatever fields this cli-tool-kit version knows.
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
