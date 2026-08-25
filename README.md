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
```

Templates: `basic` (shapes + transform), `text` (Text + MathTex highlight),
`graph` (Axes, plot, ValueTracker dot), `threed` (surface + camera orbit).

Quality presets: `l` 480p15 · `m` 720p30 · `h` 1080p60 · `p` 1440p60 · `k` 2160p60.
Output goes to `media/videos/<file-stem>/<res>/<Scene>.mp4` next to the scene
file; `render` prints the paths it produced.

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

`tests/test_render.py` really renders the basic template at `-q l` and skips
itself when manim is not installed in `.venv`.

## License

MIT — see [LICENSE](LICENSE).
