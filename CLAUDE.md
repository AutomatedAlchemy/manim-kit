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
- `music.json` — background-music manifest for `render` (id, licence, credit,
  URL, sha256). Text only: MP3s are fetched to `~/.cache/manim-kit/music/`, never
  committed. Only licences that permit redistribution belong here — the real 3Blue1Brown
  music is all rights reserved and must never be added. Mixing is a post-render ffmpeg
  mux (`mux_music`), not `Scene.add_sound`.
- `tests/` — `test_manim_kit.py` (stdlib, always runs) and `test_render.py`
  (real `-q l` render, skips without manim).

## Conventions

- Skill text is the `SKILL_MD_CONTENT` constant. Edit there, never the
  installed `~/.claude/skills/manim-kit/SKILL.md`; `--install-skill` refreshes it.
- Keep `manim_kit.py` importable on the host Python with no third-party
  modules. Anything manim-related runs through `VENV_PYTHON`.
- Render cwd is the scene file's directory, so `media/` sits next to the scene.
- Naming: repo = alias = skill = `manim-kit`. Suffix `-kit` marks a wrapper
  that makes a third-party library easy (sibling conventions: `-client` for a
  service fetcher, bare noun for a generator).

## Host facts (2026-08-25)

ManimPango 0.6.1 ships no Linux wheels; it needs `libpango1.0-dev
libcairo2-dev pkg-config` to build. `manim-kit doctor` checks `pkg-config
--exists pangocairo` and prints the apt line.
