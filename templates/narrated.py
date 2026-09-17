from manim import *
from manim_voiceover import VoiceoverScene

from manim_kit_voice import default_service, subcaptions_wanted


class {{SCENE}}(VoiceoverScene):
    """A narrated scene: each block's animation is paced by its spoken line.

    `with self.voiceover(text) as t:` synthesizes the line, caches the clip
    under `media/voiceovers/`, and waits at the end of the block until the
    clip has finished. Use `run_time=t.duration` to stretch an animation over
    the whole line, and `<bookmark mark='name'/>` plus
    `self.wait_until_bookmark("name")` to fire one on a particular word.

    Keep a block to at most two sentences: shorter lines re-synthesize faster
    when you edit them, and they line up better with a single animation.
    """

    def construct(self):
        # The voice comes from --voice, else $MANIM_KIT_VOICE, else voice.json.
        self.set_speech_service(default_service(), create_subcaption=subcaptions_wanted())

        axes = Axes(x_range=[-3, 3, 1], y_range=[0, 9, 2], x_length=8, y_length=4.5)
        curve = axes.plot(lambda x: x**2, color=BLUE)
        label = MathTex(r"f(x) = x^2").next_to(axes, UP)

        with self.voiceover(
            "The derivative measures how fast a function changes at a single point."
        ) as t:
            self.play(Create(axes), Create(curve), run_time=t.duration)

        with self.voiceover(
            "Watch the point <bookmark mark='slide'/> as it slides along the curve."
        ) as t:
            self.play(Write(label))
            self.wait_until_bookmark("slide")
            dot = Dot(axes.c2p(-2, 4), color=YELLOW)
            self.add(dot)
            self.play(MoveAlongPath(dot, curve), run_time=t.get_remaining_duration())
