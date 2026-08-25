from manim import *


class {{SCENE}}(Scene):
    """Title, LaTeX formula, and a highlighted term.

    MathTex / Tex need a LaTeX install (latex + dvisvgm). Use Text() for
    plain strings — it renders via Pango and needs no LaTeX.
    """

    def construct(self):
        title = Text("A short derivation", font_size=48)
        formula = MathTex(r"e^{i\pi} + 1 = 0", font_size=72)
        formula.next_to(title, DOWN, buff=1)

        self.play(Write(title))
        self.play(FadeIn(formula, shift=UP))
        self.wait(0.5)

        # Index into the TeX string to colour one part.
        self.play(formula[0][0:4].animate.set_color(YELLOW))
        self.wait()
