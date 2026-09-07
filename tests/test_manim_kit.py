"""Stdlib-level tests — no manim needed. The render integration test lives in
test_render.py and skips itself when the tool venv has no manim."""

import json
import os
import subprocess
import sys

import pytest

import manim_kit as mk

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "manim_kit.py")


def run(*args, **kw):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, **kw)


def test_advertise_is_fast_valid_json():
    out = run("--advertise", timeout=5)
    assert out.returncode == 0
    data = json.loads(out.stdout)
    assert data[0]["alias"] == "manim-kit"
    assert data[0]["skill_name"] == "manim-kit"
    assert data[0]["skill_status"] in {"absent", "current", "stale"}
    assert "CLI" in data[0]["tags"]


@pytest.mark.parametrize("raw,expected", [
    ("pythagoras", "Pythagoras"),
    ("my_cool-scene", "MyCoolScene"),
    ("dir/some_file.py", "SomeFile"),
    ("AlreadyCamel", "AlreadyCamel"),
    ("3d_plot", "Scene3dPlot"),
])
def test_class_name_derivation(raw, expected):
    assert mk._class_name_from(raw) == expected


@pytest.mark.parametrize("template", mk.TEMPLATES)
def test_templates_render_and_parse(template):
    src = mk.render_template(template, "Probe")
    assert "{{SCENE}}" not in src
    compile(src, f"{template}.py", "exec")  # syntactically valid


def test_scene_classes_ast(tmp_path):
    f = tmp_path / "s.py"
    f.write_text(
        "from manim import *\n"
        "class A(Scene):\n    pass\n"
        "class B(ThreeDScene):\n    pass\n"
        "class Helper:\n    pass\n"
        "class C(manim.MovingCameraScene):\n    pass\n"
    )
    assert mk.scene_classes(str(f)) == ["A", "B", "C"]


def test_new_writes_file_and_refuses_overwrite(tmp_path):
    out = run("new", "wave_demo", "--template", "graph", "--dir", str(tmp_path))
    assert out.returncode == 0, out.stderr
    target = tmp_path / "wave_demo.py"
    assert target.is_file()
    assert "class WaveDemo(Scene)" in target.read_text()
    assert "Run: manim-kit render" in out.stdout
    again = run("new", "wave_demo", "--dir", str(tmp_path))
    assert again.returncode != 0
    assert run("new", "wave_demo", "--dir", str(tmp_path), "--force").returncode == 0


def test_list_command(tmp_path):
    run("new", "two", "--dir", str(tmp_path))
    out = run("list", str(tmp_path / "two.py"))
    assert out.stdout.split() == ["Two"]


def test_render_refuses_ambiguous_scene(tmp_path, monkeypatch):
    f = tmp_path / "multi.py"
    f.write_text("from manim import *\nclass A(Scene): pass\nclass B(Scene): pass\n")
    monkeypatch.setattr(mk, "_manim_version", lambda: "0.0-test")
    with pytest.raises(SystemExit):
        mk.main(["render", str(f)])
    with pytest.raises(SystemExit):
        mk.main(["render", str(f), "Nope"])


def test_render_dry_run_builds_manim_command(tmp_path, monkeypatch, capsys):
    f = tmp_path / "one.py"
    f.write_text("from manim import *\nclass Only(Scene): pass\n")
    monkeypatch.setattr(mk, "_manim_version", lambda: "0.0-test")
    rc = mk.main(["render", str(f), "-q", "h", "--format", "gif", "-s", "--dry-run",
                  "--", "--disable_caching"])
    assert rc == 0
    cmd = capsys.readouterr().out.strip().split()
    assert cmd[1:4] == ["-m", "manim", "render"]
    assert cmd[cmd.index("-q") + 1] == "h"
    assert "--format" in cmd and "gif" in cmd and "-s" in cmd
    assert "--disable_caching" in cmd
    assert cmd[-2:] == [str(f), "Only"]  # single scene auto-selected


def test_skill_install_uninstall_roundtrip(tmp_path, monkeypatch):
    skill_dir = tmp_path / "skills" / "manim-kit"
    monkeypatch.setattr(mk, "SKILL_DIR", str(skill_dir))
    monkeypatch.setattr(mk, "SKILL_FILE", str(skill_dir / "SKILL.md"))
    assert mk._skill_status() == "absent"
    mk._install_skill()
    assert mk._skill_status() == "current"
    (skill_dir / "SKILL.md").write_text("old")
    assert mk._skill_status() == "stale"
    mk._install_skill()
    assert (skill_dir / "SKILL.md").read_text() == mk.SKILL_MD_CONTENT
    mk._uninstall_skill()
    assert mk._skill_status() == "absent"
    assert not skill_dir.exists()


def test_skill_frontmatter():
    head = mk.SKILL_MD_CONTENT.splitlines()[:3]
    assert head[0] == "---"
    assert head[1] == "name: manim-kit"
    assert head[2].startswith("description: ")


# --- music -------------------------------------------------------------------------

def test_music_manifest_entries_are_complete():
    tracks = mk.music_manifest()
    assert tracks, "music.json has no tracks"
    ids = [t["id"] for t in tracks]
    assert len(ids) == len(set(ids))
    for t in tracks:
        for key in ("id", "title", "artist", "licence", "credit", "url", "sha256"):
            assert t.get(key), f"{t.get('id')} missing {key}"
        assert len(t["sha256"]) == 64
        assert t["url"].startswith("https://")
        assert t["licence"] in t["credit"]


def test_fetch_track_verifies_and_is_idempotent(tmp_path, monkeypatch):
    import hashlib
    src = tmp_path / "tone.mp3"
    src.write_bytes(b"not really an mp3")
    cache = tmp_path / "cache"
    monkeypatch.setattr(mk, "MUSIC_DIR", str(cache))
    entry = {"id": "probe", "title": "Probe", "url": src.as_uri(),
             "sha256": hashlib.sha256(src.read_bytes()).hexdigest()}

    path = mk.fetch_track(entry)
    assert os.path.isfile(path)
    mtime = os.path.getmtime(path)
    assert mk.fetch_track(entry) == path and os.path.getmtime(path) == mtime  # no re-download

    bad = {**entry, "id": "bad", "sha256": "0" * 64}
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        mk.fetch_track(bad)
    assert not list(cache.glob("bad*"))  # nothing half-written left behind


def test_resolve_track_rejects_unknown_id(tmp_path, monkeypatch):
    monkeypatch.setattr(mk, "MUSIC_DIR", str(tmp_path / "empty"))
    with pytest.raises(RuntimeError, match="unknown track"):
        mk.resolve_track("no-such-track")


def test_mux_command_fades_and_lowers_volume():
    cmd = mk.mux_command("in.mp4", "t.mp3", "out.mp4", duration=30.0, gain=0.12, fade=2.0)
    filters = cmd[cmd.index("-filter:a") + 1]
    assert "afade=t=in:st=0:d=2" in filters
    assert "afade=t=out:st=28.000:d=2" in filters
    assert "volume=0.12" in filters
    assert cmd[cmd.index("-c:v") + 1] == "copy"      # video is never re-encoded
    assert "-shortest" in cmd and "-stream_loop" in cmd


def test_render_dry_run_prints_ffmpeg_line(tmp_path, monkeypatch, capsys):
    f = tmp_path / "one.py"
    f.write_text("from manim import *\nclass Only(Scene): pass\n")
    monkeypatch.setattr(mk, "_manim_version", lambda: "0.0-test")
    monkeypatch.setattr(mk, "resolve_track", lambda tid: ("/tmp/t.mp3", "Credit line"))
    assert mk.main(["render", str(f), "--dry-run", "--music"]) == 0
    out = capsys.readouterr().out
    assert "ffmpeg" in out and "afade" in out and "volume=0.12" in out


def test_music_is_ignored_for_last_frame(tmp_path, monkeypatch, capsys):
    f = tmp_path / "one.py"
    f.write_text("from manim import *\nclass Only(Scene): pass\n")
    monkeypatch.setattr(mk, "_manim_version", lambda: "0.0-test")
    assert mk.main(["render", str(f), "--dry-run", "--music", "-s"]) == 0
    out = capsys.readouterr().out
    assert "--music ignored" in out and "ffmpeg" not in out


def test_music_list_and_add(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(mk, "MUSIC_DIR", str(tmp_path / "cache"))
    assert mk.main(["music", "list"]) == 0
    listing = capsys.readouterr().out
    assert "not fetched" in listing and "cached" not in listing.replace("not fetched", "")

    own = tmp_path / "mine.mp3"
    own.write_bytes(b"x")
    assert mk.main(["music", "add", str(own)]) == 0
    assert mk.main(["music", "list"]) == 0
    assert "your own file" in capsys.readouterr().out
