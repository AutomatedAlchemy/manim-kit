# manim-kit

CLI wrapper + Claude skill for Manim Community. Single stdlib-only entry
point `manim_kit.py`; manim lives in the tool-owned `.venv/` (gitignored) that
`manim-kit setup` creates from `requirements-manim.txt`. `requirements.txt`
holds only the host-side `cli-tools-kit` pin for `--install`/`--remove`.

## Layout

- `manim_kit.py` — everything: advertise guard (top, before any non-stdlib
  import), `SKILL_MD_CONTENT`, subcommands `setup doctor new list render music open`,
  installer-protocol flags. `scene_classes()` is an AST scan, no manim import.
- `templates/*.py` — scene templates; `{{SCENE}}` is the class-name placeholder.
- `manim_kit_voice.py` — narration backends, imported by a scene *inside the
  venv*. `parse_spec` and the `voice.json` readers are stdlib-only so the host
  side can import them too; `KokoroService` and the Gemini wrapper are built
  lazily inside functions. `python manim_kit_voice.py say|check` is how
  `manim_kit.py` reaches it through `VENV_PYTHON`.
- `voice.json` — voice manifest: the fleet-wide `default` spec, the eight
  curated voices, and the Kokoro model files (url, sha256, bytes). Text only;
  the 354 MB model is fetched to `~/.cache/manim-kit/voices/`, like music.
- `music.json` — background-music manifest for `render` (id, licence, credit,
  URL, sha256). Text only: MP3s are fetched to `~/.cache/manim-kit/music/`, never
  committed. Only licences that permit redistribution belong here — the real 3Blue1Brown
  music is all rights reserved and must never be added. Mixing is a post-render ffmpeg
  mux (`mux_music`), not `Scene.add_sound`.
- `templates/narrated.py` — the `VoiceoverScene` skeleton: two spoken blocks
  and one bookmark, wired to `default_service()`.
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
the other way round. Two backends only, by user decision: `kokoro-v1` (local
CPU, the default) and `gemini-flash-tts` (paid API, the only German). Piper,
gTTS and edge-tts stay out on licence grounds — `NARRATION-DESIGN.md` has the
reasoning.

- **Spec strings** are `backend:voice[:lang]`. Order: `--voice`, then
  `$MANIM_KIT_VOICE`, then `voice.json`'s `default`. `render` exports the spec
  as `MANIM_KIT_VOICE` and puts `SCRIPT_DIR` on the subprocess `PYTHONPATH`, so
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
  compressor. A render with no audio stream takes exactly the old command, so
  the "a good silent render never fails because of the music" guarantee stands.
- **The Gemini key** is looked up in the environment, then `$MANIM_KIT_ENV_FILE`,
  then `~/Synced/repos/tools/.env` — the scene process runs in the scene's
  directory, which has no `.env`. Never printed.
- **sox**: manim-voiceover imports the `sox` Python package unconditionally and
  warns loudly on stderr because the binary is absent here. Only `global_speed
  != 1` and the microphone recorder actually call it, so `doctor` mentions it
  and nothing more.

## Host facts (2026-08-25)

ManimPango 0.6.1 ships no Linux wheels; it needs `libpango1.0-dev
libcairo2-dev pkg-config` to build. `manim-kit doctor` checks `pkg-config
--exists pangocairo` and prints the apt line.
