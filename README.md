# manim-kit

A small CLI that makes [Manim Community](https://www.manim.community/) — the
3Blue1Brown-style math animation engine — a one-command affair: scaffold a
scene from a template, list the scenes in a file, render at a quality preset,
open the result. Ships a Claude Code skill with a Manim cheat sheet so an AI
session can write and render animations for you.

Built on the [cli-tool-kit](https://github.com/Probst1nator/cli-tool-kit)
installer protocol (`--advertise`, `--install`, `--install-skill`).

## Install

```bash
git clone <this repo> ~/manim-kit && cd ~/manim-kit
pip install -r requirements.txt      # cli-tool-kit, for --install only
python3 manim_kit.py --install       # bash alias `manim-kit` + Claude skill
source ~/.bashrc
manim-kit setup                      # creates .venv with manim, runs doctor
```

`manim_kit.py` itself is stdlib-only. Manim lives in a tool-owned `.venv/`
next to the script; the host Python never sees it.

### System requirements

- Python ≥ 3.11 (manim ≥ 0.20 needs it), `ffmpeg`.
- **ManimPango has no Linux wheels** and compiles against Pango/Cairo headers.
  On Debian/Ubuntu: `sudo apt install libpango1.0-dev libcairo2-dev pkg-config`.
  `manim-kit doctor` tells you when this is missing.
- Optional: a LaTeX install with `latex` + `dvisvgm` for `Tex`/`MathTex`.
  `Text()` works without it.

## Usage

```bash
manim-kit new pythagoras --template graph     # → pythagoras.py, class Pythagoras
manim-kit list pythagoras.py                  # scene classes in the file
manim-kit render pythagoras.py                # 1080p60 by default
manim-kit render pythagoras.py -q l           # draft, 480p15, seconds
manim-kit render pythagoras.py Pythagoras -q h --preview   # final 1080p60, auto-open
manim-kit render pythagoras.py --all --format gif
manim-kit render pythagoras.py -s             # last frame as PNG
manim-kit open pythagoras.py                  # newest render of that file
manim-kit render f.py -- --disable_caching    # anything after -- goes to `manim render`

manim-kit render pythagoras.py --music        # ambient bed under the finished mp4
manim-kit music list                          # library, with what is cached
manim-kit music fetch                         # pre-download every bundled track
manim-kit music add ~/my_track.mp3            # use your own audio
```

Templates: `basic` (shapes + transform), `text` (Text + MathTex highlight),
`graph` (Axes, plot, ValueTracker dot), `threed` (surface + camera orbit).

Quality presets: `l` 480p15 · `m` 720p30 · `h` 1080p60 · `p` 1440p60 · `k` 2160p60.
Output goes to `media/videos/<file-stem>/<res>/<Scene>.mp4` next to the scene
file; `render` prints the paths it produced.

## Music

`--music` mixes a background track under the finished MP4 with ffmpeg: looped or trimmed
to the exact video length, faded in and out, at `volume=0.12` (about -18 dB) so a later
voice-over still sits on top. `--music-gain` changes that, `--no-music-fade` drops the
fades. The video stream is copied, not re-encoded, so it costs a second regardless of
quality preset; if ffmpeg fails the silent render is left intact.

Tracks are fetched on first use into `~/.cache/manim-kit/music/` and checked against the
SHA-256 in `music.json` — no audio is committed to this repo. The bundled set is six
[Chris Zabriskie](https://chriszabriskie.com) tracks (*Cylinders*, *The Black Hole*,
*Reappear*) under **CC BY 4.0 / CC BY 3.0**, mirrored on archive.org. Each `--music`
render prints the attribution line, which has to go into your video description;
`manim-kit music credits` reprints them.

The actual 3Blue1Brown soundtrack by Vincent Rubinetti is **all rights reserved** — free
to listen to, licensed per project through
[his form](https://vincerubinetti.github.io/using-the-music-of-3blue1brown/), sometimes
for a fee. It cannot be shipped or auto-fetched by a tool, so it is not in the manifest.

## Claude Code skill

`--install` (or `--install-skill` alone) writes `~/.claude/skills/manim-kit/SKILL.md`
from the `SKILL_MD_CONTENT` constant in `manim_kit.py`. The skill carries the
commands above, a workflow (draft with `-q l`, ship at the default `-q h`), a Manim CE
cheat sheet (mobjects, animations, positioning, updaters, plots, text, 3D) and
the usual gotchas (ManimGL names that don't exist in Manim CE, `Transform` vs
`ReplacementTransform`, raw strings for TeX). The `--advertise` probe reports
`skill_status` so the AutomatedAlchemy installer GUI can offer a refresh when
the bundled skill changes.

## Tests

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pytest tests
```

On Windows the venv interpreter is `.venv\Scripts\python.exe`:

```powershell
.venv\Scripts\python.exe -m pip install pytest
.venv\Scripts\python.exe -m pytest tests
```

`tests/test_render.py` really renders the basic template at `-q l` and skips
itself when manim is not installed in `.venv`.

## License

MIT — see [LICENSE](LICENSE).
