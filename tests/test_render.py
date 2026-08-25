"""Integration: really render the basic template at -q l inside the tool venv."""

import os
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
