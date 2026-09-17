# manim-kit narration — design

> **Implemented 2026-09-17: Kokoro + Gemini; Piper deferred.**

Goal: `manim-kit render lecture.py` produces a finished explainer: the animation, a
synthesized voice reading the narration in sync with what is on screen, and the ambient
music that is already on by default, ducked under the voice. Claude writes the scene and
the narration together, in one file.

## 1. Timing model: the voice paces the animation

The one design decision that matters. Two ways to line voice up with picture:

| | Post-hoc mux | Voice-driven scene (chosen) |
|---|---|---|
| How | Render silent, then lay clips at timestamps | Each narration line is synthesized *before* its animation block runs; the block is told the clip length and stretches to it |
| Voice longer than picture | Overlaps the next segment or gets cut | The scene waits: the block ends when the clip ends |
| Voice shorter than picture | Silence, fine | Animation keeps its own `run_time`; fine |
| Re-voicing with another backend | Timestamps break, re-time by hand | Re-render; every block re-paces itself |
| Authoring | Two files (scene + cue sheet) | One file, the line sits next to the animation it describes |

`manim-voiceover` (Manim Community, 0.4.0 released 2026-06-14, Python ≥ 3.11, MIT)
implements the chosen model: `VoiceoverScene`, a `with self.voiceover(text=...) as tracker:`
block that synthesizes on first render and caches the clip, `tracker.duration` for
`run_time`, an automatic wait at block end, `<bookmark mark='x'/>` tags in the text plus
`self.wait_until_bookmark('x')` to fire an animation on a word, and `subcaption` so manim
writes an `.srt` next to the MP4. It goes into `requirements-manim.txt` (the tool venv is
Python 3.12, manim 0.21, pydub already present). What manim-kit adds is the backends it does
not ship — Kokoro and Piper run offline on CPU — and the music/ducking mux.

```python
from manim import *
from manim_voiceover import VoiceoverScene
from manim_kit_voice import default_service          # ships with manim-kit

class Derivative(VoiceoverScene):
    def construct(self):
        self.set_speech_service(default_service())     # host default; --voice overrides
        ax = Axes(); f = ax.plot(lambda x: x**2)
        with self.voiceover("The derivative measures how fast a function changes at a single point.") as t:
            self.play(Create(ax), Create(f), run_time=t.duration)
        with self.voiceover("Watch the tangent line <bookmark mark='slide'/> as we slide along the curve.") as t:
            tangent = ...; self.play(Create(tangent))
            self.wait_until_bookmark("slide")
            self.play(MoveAlongPath(...), run_time=t.get_remaining_duration())
```

## 2. Voice backends (`manim_kit_voice.py`, importable from the tool venv)

One `SpeechService` subclass per backend, all returning the same cache dict, so a scene is
backend-agnostic. Only licence-clean voices are offered by `voice list`; gTTS is not wired in even
though manim-voiceover ships it. Selection order: `--voice` flag → `$MANIM_KIT_VOICE` → `voice.json`
default (fleet-wide, since the repo is synced) → first backend that `doctor` finds usable.
Spec string: `backend:voice[:lang]`, e.g. `kokoro:af_heart`, `piper:de_DE-thorsten-high`,
`gemini:Kore`.

| Backend | Runs | Languages | Why it is in |
|---|---|---|---|
| `kokoro` (kokoro-onnx, v1.0 model) | local CPU | EN (+ a few others, no DE) | default for English: natural, fast, offline, Apache-2.0 |
| `piper` | local CPU | EN, DE (thorsten) | default for German; fastest of all; MIT code, voices limited to CC0 / CC BY / PD (thorsten, kerstin, alba, cori, libritts_r) |
| `gemini` (manim-voiceover's own `GeminiService`) | API, paid | EN, DE, 24 languages | best prosody, style-promptable ("read like a patient teacher"), for finals |

Measured on the Ideapad (12-thread CPU, no GPU), one backend at a time, 2026-09-17. Full per-voice
numbers, clips and quality notes are on the audition page; the medians:

| Backend | Runs | Clips | Median RTF | 10 min of narration |
|---|---|---|---|---|
| `piper` | local-cpu | 7 | 0.039 | 23 s |
| `supertonic` | local-cpu | 2 | 0.139 | 1 min |
| `kitten-tts` | local-cpu | 3 | 0.225 | 2 min |
| `pocket-tts` | local-cpu | 3 | 0.236 | 2 min |
| `coqui-vits` | local-cpu | 5 | 0.279 | 3 min |
| `kokoro` | local-cpu | 10 | 0.392 | 4 min |
| `kokoro-v1` | local-cpu | 12 | 0.396 | 4 min |
| `gemini-flash-tts` | network-paid | 16 | 0.803 | 8 min |
| `gemini-pro-tts` | network-paid | 2 | 0.905 | 9 min |
| `gemini-25-flash-tts` | network-paid | 1 | 0.938 | 9 min |

RTF = synthesis wall clock divided by audio length. Piper's median covers only its licence-clean voices
(CC0 / CC BY / public domain); the non-commercial, Blizzard and unconfirmed-terms voices are excluded.

**Excluded on licence grounds (user decision 2026-09-17):** `edge-tts` and `gtts` (audio from
unofficial endpoints, no licence for this use), `coqui-xtts` (Coqui Public Model License,
non-commercial), and the Piper voices hfc_female/hfc_male/ryan (CC BY-NC-SA), lessac (Blizzard
research terms), jenny_dioco, amy, eva_k, karlsson (dataset terms unconfirmed). `espeak` is the
robotic baseline, not a candidate. `pocket-tts` has real German at 0.24× (CC BY 4.0) and is worth a
second look once its gated cloning weights are accepted.
Rule for the pick: draft renders (`-q l`) use the local default; a final render may pass
`--voice gemini:Kore` and re-uses every cached clip whose text did not change.

Cache: manim-voiceover keys clips by hash(text, service config) under `media/voiceovers/`
next to the scene — same place as `media/videos/`, so a re-render with unchanged text costs
nothing and a text edit re-synthesizes only that line.

## 3. Music under the voice (change to the existing mux)

Today `mux_music` maps `-map 1:a` and discards the render's own audio track. With narration
the render *has* an audio track (manim's `add_sound` mixes the clips into the MP4). New
behaviour, in `mux_music`:

- no audio stream in the render → today's path, unchanged;
- audio stream present → mix: music through `volume=<gain>` and, by default, a
  sidechain compressor keyed on the voice (`sidechaincompress`) so the bed dips ~8 dB while
  someone speaks and comes back in the pauses; `amix=inputs=2:duration=first:normalize=0`.
  `--no-ducking` keeps the flat 0.12 bed.

Still `-c:v copy`: the video is never re-encoded. Music credit line printed as today.

## 4. CLI surface

| Command | Does |
|---|---|
| `manim-kit new NAME --template narrated` | `VoiceoverScene` skeleton with two voiceover blocks and a bookmark |
| `manim-kit voice list` | backends usable on this host, their voices, which is the default |
| `manim-kit voice say "text" [--voice SPEC] [--out f.mp3]` | preview a voice in two seconds, no render |
| `manim-kit voice setup [kokoro\|piper]` | pip into the tool venv + model download into `~/.cache/manim-kit/voices/` (Kokoro ≈ 310 MB, one Piper voice ≈ 60 MB); prints sizes first |
| `manim-kit render FILE [--voice SPEC] [--no-ducking] [--srt]` | as today, plus narration |
| `manim-kit doctor` | adds a line per voice backend (installed / model cached / key present) |

Lecture mode is a skill workflow, not code: the SKILL.md gets a "narrated explainer" recipe —
outline → one `VoiceoverScene` per section, ≤ 2 sentences per block, bookmarks for
"now look at" moments, draft at `-q l` with the local voice, final at `-q h`.

## 5. What stays out of v1

- Two speakers in dialogue (Gemini multi-speaker exists in `tools/_shared`; add when a
  script asks for it).
- Word-level timing via Whisper (`manim-voiceover[transcribe]`): bookmarks cover the need
  and the extra pulls torch into the tool venv.
- Voice cloning (XTTS): CPU-only hosts pay minutes per clip; see benchmark.
- A separate narration file: the narration lives in the scene, by design (§1).

## 6. Open decisions for the user

1. Default English voice (pick from the comparison page).
2. Default German voice — Piper thorsten is the only offline option; Gemini otherwise.
3. Ducking on by default, or flat bed?
4. Should `voice.json` default be fleet-wide (synced) or per host (`$MANIM_KIT_VOICE` in `~/.bashrc`)?
