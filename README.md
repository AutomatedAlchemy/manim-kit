# manim-kit

A small CLI that makes [Manim Community](https://www.manim.community/) — the
3Blue1Brown-style math animation engine — a one-command affair: scaffold a
scene from a template, list the scenes in a file, render at a quality preset,
open the result. Ships a Claude Code skill with a Manim cheat sheet so an AI
session can write and render animations for you.

Built on the [cli-tools-kit](https://github.com/Probst1nator/cli-tools-kit)
installer protocol (`--advertise`, `--install`, `--install-skill`).

## Install

```bash
git clone <this repo> ~/manim-kit && cd ~/manim-kit
pip install -r requirements.txt      # cli-tools-kit, for --install only
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

manim-kit render pythagoras.py --no-music     # skip the ambient bed (on by default)
manim-kit music list                          # library, with what is cached
manim-kit music fetch                         # pre-download every bundled track
manim-kit music add ~/my_track.mp3            # use your own audio

manim-kit new lecture --template narrated     # a scene that speaks
manim-kit render lecture.py --voice kokoro-v1:af_heart
manim-kit render lecture.py --srt             # also write subtitles
manim-kit render lecture.py --no-ducking      # flat music bed
manim-kit voice list                          # the voices, and which work here
manim-kit voice say "A quick audition."       # preview without rendering
manim-kit voice setup                         # cache the local Kokoro model
```

Templates: `basic` (shapes + transform), `text` (Text + MathTex highlight),
`graph` (Axes, plot, ValueTracker dot), `threed` (surface + camera orbit),
`narrated` (VoiceoverScene with two spoken blocks and a bookmark).

Quality presets: `l` 480p15 · `m` 720p30 · `h` 1080p60 · `p` 1440p60 · `k` 2160p60.
Output goes to `media/videos/<file-stem>/<res>/<Scene>.mp4` next to the scene
file; `render` prints the paths it produced.

## Music

Renders get a background track under the finished MP4 by default, mixed with ffmpeg:
looped or trimmed to the exact video length, faded in and out, at `volume=0.12` (about
-18 dB) so a later voice-over still sits on top. Pass `--no-music` for a silent render;
`--music-gain` changes the level, `--no-music-fade` drops the fades. The video stream is
copied, not re-encoded, so it costs a second regardless of quality preset; if ffmpeg
fails the silent render is left intact. Music is skipped automatically for `--last-frame`,
`--format png` and `--format gif` — no audio track.

Tracks are fetched on first use into `~/.cache/manim-kit/music/` and checked against the
SHA-256 in `music.json` — no audio is committed to this repo. The bundled set is six
[Chris Zabriskie](https://chriszabriskie.com) tracks (*Cylinders*, *The Black Hole*,
*Reappear*) under **CC BY 4.0 / CC BY 3.0**, mirrored on archive.org. Each render with
music prints the attribution line, which has to go into your video description;
`manim-kit music credits` reprints them.

The actual 3Blue1Brown soundtrack by Vincent Rubinetti is **all rights reserved** — free
to listen to, licensed per project through
[his form](https://vincerubinetti.github.io/using-the-music-of-3blue1brown/), sometimes
for a fee. It cannot be shipped or auto-fetched by a tool, so it is not in the manifest.

## Narration

`manim-kit render` can speak the scene. A narrated scene subclasses
[manim-voiceover](https://github.com/ManimCommunity/manim-voiceover)'s `VoiceoverScene`
and wraps each animation in a `with self.voiceover(...)` block: the line is synthesized
before the block runs, the animation is told how long the clip is, and the block waits at
the end until the voice has finished. The narration sits in the scene file next to the
animation it describes, so there is no separate cue sheet to keep in sync.

```python
from manim import *
from manim_voiceover import VoiceoverScene
from manim_kit_voice import default_service, subcaptions_wanted

class Derivative(VoiceoverScene):
    def construct(self):
        self.set_speech_service(default_service(), create_subcaption=subcaptions_wanted())
        ax = Axes(); curve = ax.plot(lambda x: x**2)
        with self.voiceover("The derivative measures how fast a function changes.") as t:
            self.play(Create(ax), Create(curve), run_time=t.duration)
        with self.voiceover("Watch the point <bookmark mark='go'/> slide along it.") as t:
            self.wait_until_bookmark("go")
            self.play(MoveAlongPath(dot, curve), run_time=t.get_remaining_duration())
```

Clips are cached under `media/voiceovers/` next to the scene and keyed by the text plus
the voice settings, so re-rendering an unchanged line costs nothing and editing one
re-synthesizes only that line. Bookmarks are placed by text position rather than by
transcription: accurate to a fraction of a second, and no Whisper in the venv.

### Voices

A voice spec is `backend:voice[:lang]`. Two backends ship in this version:

| Spec | Lang | Notes |
|---|---|---|
| `kokoro-v1:af_sarah` | en | **default** — even, unhurried |
| `kokoro-v1:af_heart` | en | warmer, more expressive |
| `kokoro-v1:af_sky` | en | lighter, younger |
| `kokoro-v1:am_puck` | en | male |
| `gemini-flash-tts:Puck` | en | best prosody, paid |
| `gemini-flash-tts:Leda` | en | calm, paid |
| `gemini-flash-tts:Aoede:de` | de | German female, paid |
| `gemini-flash-tts:Charon:de` | de | German male, paid |

`kokoro-v1` is the [Kokoro v1.0 ONNX](https://github.com/thewh1teagle/kokoro-onnx) model
running locally on the CPU at about 0.4x real time — offline, free, Apache-2.0.
`gemini-flash-tts` calls Gemini's `gemini-3.1-flash-tts-preview`: better prosody and the
only German option here, at roughly $0.006 per two-sentence line ($1/1M input text tokens
plus $20/1M audio output tokens). Piper, gTTS and edge-tts are deliberately out — see
[NARRATION-DESIGN.md](NARRATION-DESIGN.md) for the licence reasoning.

Selection order: `--voice SPEC`, then `$MANIM_KIT_VOICE`, then the `default` in
`voice.json`. That file is committed and the repo is synced, so the default is fleet-wide;
it also carries the curated voice list and the Kokoro model manifest (URL, SHA-256, size).

`manim-kit voice setup` downloads the two Kokoro files (354 MB) into
`~/.cache/manim-kit/voices/` and verifies their SHA-256, the same way music tracks are
fetched. Nothing but text is committed.

The Gemini backend needs an API key. It is looked up in `$GEMINI_API_KEY` or
`$GOOGLE_API_KEY` first, then in the file named by `$MANIM_KIT_ENV_FILE`, and finally in
`~/Synced/repos/tools/.env` if that exists — a convenience for this fleet, since the scene
process runs from the scene's directory, which usually has no `.env` of its own.

### Music under a voice

A narrated render already has an audio track, so the music is mixed into it instead of
replacing it: the bed plays at `volume=0.12` and a `sidechaincompress` keyed on the voice
dips it about 8 dB while someone speaks and lets it back up in the pauses — threshold
0.03, ratio 8, attack 20 ms, release 500 ms. `--no-ducking` keeps the bed flat. A silent
render is mixed exactly as before, and the video stream is still copied, never re-encoded.

`--srt` writes a subtitle file next to the MP4.

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
