import unittest
from datetime import datetime

from src.data import Quote
from src.demo import demo_data
from src.render import fmt_num, fmt_pct, render_html, render_text

NOW = datetime(2026, 9, 28, 8, 0)


class FormatTest(unittest.TestCase):
    def test_fmt_num_spanish_style(self):
        self.assertEqual(fmt_num(19724.4), "19.724,40")
        self.assertEqual(fmt_num(1.1474), "1,1474")
        self.assertEqual(fmt_num(None), "—")

    def test_fmt_pct_has_sign(self):
        self.assertEqual(fmt_pct(1.234), "+1,23 %")
        self.assertEqual(fmt_pct(-0.5), "-0,50 %")


class RenderTest(unittest.TestCase):
    def test_demo_html_contains_sections_and_banner(self):
        html = render_html(demo_data(), NOW, demo=True)
        for expected in ("Mercado general", "Mi seguimiento", "IBEX 35",
                         "Nueva Expresión Textil", "DATOS DE EJEMPLO", "lunes 28 de septiembre de 2026"):
            self.assertIn(expected, html)

    def test_real_html_has_no_demo_banner(self):
        self.assertNotIn("DATOS DE EJEMPLO", render_html(demo_data(), NOW, demo=False))

    def test_error_quote_renders_placeholder(self):
        data = {"general": [Quote("X", "Activo <roto>", error="boom")], "watchlist": []}
        html = render_html(data, NOW)
        self.assertIn("Datos no disponibles", html)
        self.assertIn("Activo &lt;roto&gt;", html)  # escapado
        self.assertNotIn("Mi seguimiento", html)

    def test_text_version(self):
        text = render_text(demo_data(), NOW, demo=True)
        self.assertIn("IBEX 35", text)
        self.assertIn("MI SEGUIMIENTO", text)



class HeadlinesRenderTest(unittest.TestCase):
    def test_headlines_section_escapes_and_links(self):
        from datetime import timezone

        from src.news import Headline
        hs = [Headline("Fuente <X>", "Petróleo <sube> & baja", "https://ejemplo.com/a?x=1&y=2",
                       datetime(2026, 9, 26, tzinfo=timezone.utc))]
        html = render_html(demo_data(), NOW, headlines=hs)
        self.assertIn("Titulares de la semana", html)
        self.assertIn("Petróleo &lt;sube&gt; &amp; baja", html)
        self.assertIn('href="https://ejemplo.com/a?x=1&amp;y=2"', html)
        self.assertIn("TITULARES DE LA SEMANA", render_text(demo_data(), NOW, headlines=hs))

    def test_no_headlines_no_section(self):
        self.assertNotIn("Titulares de la semana", render_html(demo_data(), NOW))


if __name__ == "__main__":
    unittest.main()
