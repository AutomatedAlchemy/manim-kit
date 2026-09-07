"""Integration: really render the basic template at -q l inside the tool venv."""

import os
import shutil
import subprocess
import sys

import pytest

import manim_kit as mk

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "manim_kit.py")

pytestmark = pytest.mark.skipif(
    mk._manim_version() is None, reason="manim not installed in .venv (run: manim-kit setup)"
)


def test_render_basic_template_low_quality(tmp_path):
    subprocess.run([sys.executable, SCRIPT, "new", "smoke", "--dir", str(tmp_path)], check=True)
    out = subprocess.run(
        [sys.executable, SCRIPT, "render", str(tmp_path / "smoke.py"), "-q", "l"],
        capture_output=True, text=True, timeout=600,
    )
    assert out.returncode == 0, out.stderr[-2000:]
    mp4 = tmp_path / "media" / "videos" / "smoke" / "480p15" / "Smoke.mp4"
    assert mp4.is_file(), out.stdout
    assert str(mp4) in out.stdout


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_render_with_music_adds_an_audio_stream(tmp_path):
    """Render at -q l twice, once silent and once with a locally generated tone."""
    subprocess.run([sys.executable, SCRIPT, "new", "tune", "--dir", str(tmp_path)], check=True)
    scene = str(tmp_path / "tune.py")
    mp4 = tmp_path / "media" / "videos" / "tune" / "480p15" / "Tune.mp4"

    subprocess.run([sys.executable, SCRIPT, "render", scene, "-q", "l"], check=True, timeout=600)
    silent_duration = _duration(mp4)
    assert _codec_types(mp4) == ["video"]

    tone = tmp_path / "tone.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=2",
                    str(tone)], check=True)
    env = {**os.environ, "HOME": str(tmp_path)}  # keep the real ~/.cache out of it
    subprocess.run([sys.executable, SCRIPT, "music", "add", str(tone), "--id", "tone"],
                   check=True, env=env)
    out = subprocess.run([sys.executable, SCRIPT, "render", scene, "-q", "l", "--music",
                          "--track", "tone"], capture_output=True, text=True, timeout=600, env=env)

    assert out.returncode == 0, out.stderr[-2000:]
    assert _codec_types(mp4) == ["video", "audio"]
    assert abs(_duration(mp4) - silent_duration) < 0.2  # the 2 s tone was looped, not truncated


def _ffprobe(path, *entries):
    out = subprocess.run(["ffprobe", "-v", "error", *entries, "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True)
    return out.stdout.split()


def _codec_types(path):
    return _ffprobe(path, "-show_entries", "stream=codec_type")


def _duration(path):
    return float(_ffprobe(path, "-show_entries", "format=duration")[0])
