# manim-kit

CLI wrapper + Claude skill for Manim Community. Single stdlib-only entry
point `manim_kit.py`; manim lives in the tool-owned `.venv/` (gitignored) that
`manim-kit setup` creates from `requirements-manim.txt`. `requirements.txt`
holds only the host-side `cli-tools-kit` pin for `--install`/`--remove`.

Install, autostart and alias follow the cli-tools-kit contract: [PROTOCOL.md](https://github.com/Probst1nator/cli-tools-kit/blob/main/PROTOCOL.md).

## Layout

- `manim_kit.py` — everything: advertise guard (top, before any non-stdlib
  import), `SKILL_MD_CONTENT`, subcommands `setup doctor new list render music open`,
  installer-protocol flags. `scene_classes()` is an AST scan, no manim import.
- `templates/*.py` — scene templates; `{{SCENE}}` is the class-name placeholder.
- `manim_kit_voice.py` — narration backends, imported by a scene *inside the
  venv*. `parse_spec` and the `voice.json` readers are stdlib-only so the host
  side can import them too; `PhononService` and the Gemini wrapper are built
  lazily inside functions. `python manim_kit_voice.py say|check|setup` is how
  `manim_kit.py` reaches it through `VENV_PYTHON`.
- `voice.json` — voice manifest: the fleet-wide `default` spec, the curated
  voices, and the `phonon` section (model, fallback model and voice catalog
  pinned to Hub revisions, quant, voice names, Kokoro-name map). Text only; the
  models and voice embeddings live in the Hugging Face cache.
- `music.json` — background-music manifest for `render` (id, licence, credit,
  URL, sha256). Text only: MP3s are fetched to `~/.cache/manim-kit/music/`, never
  committed. Only licences that permit redistribution belong here — the real 3Blue1Brown
  music is all rights reserved and must never be added. Mixing is a post-render ffmpeg
  mux (`mux_music`), not `Scene.add_sound`.
- `templates/narrated.py` — the `VoiceoverScene` skeleton: two spoken blocks
  and one bookmark, wired to `default_service()`.
- `templates/sim.py` — plays back simulation snapshots: a toy wave solver inline,
  `SIM_DATA=DIR` for real `.npz` runs. The skill section *Animating your own
  simulation or data* is its manual; keep the two in step.
- `examples/readme_demo.py` — the scene behind the README demo (intro, then the
  derivative as the limit of a secant). Rendered at `-q m` with
  `--voice gemini-flash-tts:Puck`.
- `docs/` — the rendered demo: `readme_demo.mp4` (720p, voice and music) and
  `readme_demo.gif` (silent 8 s excerpt shown in the README). The only binaries
  in the repo.
- `tests/` — `test_manim_kit.py` and `test_voice.py` (stdlib, always run) and
  `test_render.py` (real `-q l` renders, silent and narrated; each skips when
  its dependencies are absent).

## Conventions

- Skill text is the `SKILL_MD_CONTENT` constant. Edit there, never the
  installed `~/.claude/skills/manim-kit/SKILL.md`; `--install-skill` refreshes it.
- Keep `manim_kit.py` importable on the host Python with no third-party
  modules. Anything manim-related runs through `VENV_PYTHON`.
- Render cwd is the scene file's directory, so `media/` sits next to the scene.
- Naming: repo = alias = skill = `manim-kit`. Suffix `-kit` marks a wrapper
  that makes a third-party library easy (sibling conventions: `-client` for a
  service fetcher, bare noun for a generator).

## Narration (added 2026-09-17)

`VoiceoverScene` + manim-voiceover 0.4.0 pace the animation from the voice, not
the other way round. Two backends only, by user decision: `phonon` (local CPU,
English and German, the default) and `gemini-flash-tts` (paid API). Kokoro was
replaced by Phonon on 2026-10-26 (user: of the local engines only Phonon and
Articulino stay fleet-wide). Piper, gTTS and edge-tts stay out on licence
grounds — `NARRATION-DESIGN.md` has the reasoning.

- **Licence split.** Phonon 40M multilingual output is CC BY-NC 4.0:
  non-commercial only, credit "Phonon by Gradium, CC BY-NC 4.0" (`render`
  prints it). When 40M cannot load, English falls back to Phonon 31M English
  (Apache-2.0, same voice names) and German raises, naming the gemini backend.
  Commercial work uses `gemini-flash-tts`. Keep this in the README, the skill
  text and `voice.json` alike.
- **No hang offline.** ptts ignores `HF_HUB_OFFLINE` and hangs on an hf://
  model when the network does not answer. `load_phonon` loads from the local
  snapshot path when the HF cache has one, and tries a download only after a
  3 s TCP probe of the Hub (`HF_HUB_OFFLINE=1` counts as no answer). An
  uncached voice embedding goes through the same probe. Same guard as
  `tools/_shared/voice/phonon_tts.py`.
- **Clip cache key** holds the pinned model string (never a path), catalog,
  quant, language, voice and speed. A fresh clip is keyed by the model that
  really spoke, so a 31M fallback clip is not served later as a 40M one.
- **Old specs.** `kokoro-v1:<id>` maps through `voice.json` `phonon.kokoro`
  (af_heart → Hadley), in both `manim_kit.expand_spec` and
  `manim_kit_voice.migrate_spec`, with one note. `render` exports the mapped
  spec so the scene process does not print the note again.

- **Spec strings** are `backend:voice[:lang]`. Order: `--voice`, then
  `$MANIM_KIT_VOICE`, then `voice.json`'s `default`. A bare language code
  (`de`) expands through `language_defaults` (English: `phonon:Harper`,
  German: `phonon:Annika:de`). `render` exports the spec as
  `MANIM_KIT_VOICE` and puts `SCRIPT_DIR` on the subprocess `PYTHONPATH`, so
  `from manim_kit_voice import default_service` resolves from any scene
  directory.
- **Bookmarks without Whisper.** manim-voiceover only builds a scene's bookmark
  table when the service returned `word_boundaries`, and otherwise tells the
  user to install Whisper — which would pull torch into the venv. Both our
  services therefore attach `linear_word_boundaries()`, the same two-point
  start/end pair the tracker uses as its own fallback, and let it interpolate.
  It is applied to the cached result as well as to a fresh one, or an entry
  written before this existed comes back without them and the next bookmark
  raises.
- **The Gemini wrapper** (`_wrap_gemini`) does two things in one place: it puts
  the optional `style` instruction in front of the text sent to Gemini (which
  reads a leading instruction as a directive and does not speak it) and then
  restores the author's `input_text` in the result, so bookmarks and subcaptions
  are not offset by the instruction.
- **Ducking.** With an audio stream present, `mux_command` switches from
  `-filter:a` to a `-filter_complex` graph: bed at `volume=0.12`, then
  `sidechaincompress` keyed on a split of the voice (threshold 0.03, ratio 8,
  attack 20 ms, release 500 ms — about 10 dB measured), then
  `amix=inputs=2:duration=first:normalize=0`. `--no-ducking` drops the
  compressor. The voice is first padded with `apad=whole_dur=<video duration>`:
  the narration ends with the last spoken line, and without the pad `-shortest`
  cut a closing `self.wait()` off the video (fixed 2026-10-05). A render with no audio stream takes exactly the old command, so
  the "a good silent render never fails because of the music" guarantee stands.
- **The Gemini key** is looked up in the environment, then in the file named by
  `$MANIM_KIT_ENV_FILE`, then in `user_env_file()` (`~/.config/manim-kit/.env`, or
  under `$XDG_CONFIG_HOME`) — the scene process runs in the scene's directory, which
  has no `.env`, and cron or scripted runs miss variables from an interactive rc file.
  Never printed. Tests point `XDG_CONFIG_HOME` at a temp dir so a real file never leaks in.
- **sox**: manim-voiceover imports the `sox` Python package unconditionally and
  warns loudly on stderr because the binary is absent here. Only `global_speed
  != 1` and the microphone recorder actually call it, so `doctor` mentions it
  and nothing more.

## Host facts (2026-08-25)

ManimPango 0.6.1 ships no Linux wheels; it needs `libpango1.0-dev
libcairo2-dev pkg-config` to build. `manim-kit doctor` checks `pkg-config
--exists pangocairo` and prints the apt line.
