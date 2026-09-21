import json
import unittest
from datetime import datetime, timezone
from unittest import mock

from src.demo import demo_data, demo_headlines
from src.summary import SYSTEM_PROMPT, build_prompt, clean_summary, generate_summary, ollama_generate

NOW = datetime(2026, 9, 28, 8, 0)
GOOD = ("Cómo llegamos: " + "el petróleo cayó esta semana según CNBC. " * 6 + "\n\n"
        "Qué vigilar esta semana: " + "las fuentes no anticipan eventos concretos. " * 4 + "\n\n"
        "Riesgos: " + "la tensión geopolítica sigue presente. " * 4)


class PromptTest(unittest.TestCase):
    def test_prompt_has_market_and_headlines_but_not_watchlist(self):
        prompt = build_prompt(demo_data(), demo_headlines(), NOW)
        self.assertIn("IBEX 35", prompt)
        self.assertIn("Titular de ejemplo sobre el petróleo", prompt)
        self.assertNotIn("Nueva Expresión", prompt)  # el seguimiento personal no se envía al modelo

    def test_prompt_without_headlines(self):
        self.assertIn("ninguno disponible", build_prompt(demo_data(), [], NOW))

    def test_system_prompt_forbids_advice_and_inventing(self):
        self.assertIn("No des recomendaciones de compra o venta", SYSTEM_PROMPT)
        self.assertIn("No inventes", SYSTEM_PROMPT)


class CleanTest(unittest.TestCase):
    def test_strips_markdown_and_think(self):
        raw = "<think>razonando...</think>\n\n**" + GOOD.split("\n\n")[0] + "**\n\n### " + GOOD.split("\n\n")[1]
        cleaned = clean_summary(raw)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("think", cleaned)
        self.assertNotIn("###", cleaned)

    def test_too_short_or_single_paragraph_rejected(self):
        with self.assertRaises(ValueError):
            clean_summary("Muy corto.")
        with self.assertRaises(ValueError):
            clean_summary("Un solo párrafo largo. " * 30)


class GenerateTest(unittest.TestCase):
    def test_uses_injected_generator_and_cleans(self):
        calls = {}

        def fake(system, prompt, **kw):
            calls.update(kw, system=system, prompt=prompt)
            return GOOD

        text = generate_summary(demo_data(), demo_headlines(), NOW, {"model": "m1", "num_ctx": 4096}, generator=fake)
        self.assertIn("Cómo llegamos:", text)
        self.assertEqual(calls["model"], "m1")
        self.assertEqual(calls["num_ctx"], 4096)

    def test_env_overrides_model(self):
        seen = {}
        with mock.patch.dict("os.environ", {"SUMMARY_MODEL": "otro"}):
            generate_summary(demo_data(), [], NOW, {"model": "m1"}, generator=lambda s, p, **kw: seen.update(kw) or GOOD)
        self.assertEqual(seen["model"], "otro")

    def test_failure_returns_none(self):
        def boom(*a, **kw):
            raise ConnectionError("Ollama no responde")
        with mock.patch("sys.stderr"):
            self.assertIsNone(generate_summary(demo_data(), [], NOW, generator=boom))


class OllamaTest(unittest.TestCase):
    def test_request_shape_and_response_parsing(self):
        resp = mock.MagicMock()
        resp.read.return_value = json.dumps({"message": {"content": "hola"}}).encode()
        with mock.patch("src.summary.urllib.request.urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value = resp
            out = ollama_generate("sys", "user", model="m", num_ctx=1024, temperature=0.1, max_tokens=50)
        self.assertEqual(out, "hola")
        req = urlopen.call_args[0][0]
        body = json.loads(req.data)
        self.assertEqual(body["model"], "m")
        self.assertFalse(body["stream"])
        self.assertEqual(body["options"]["num_ctx"], 1024)
        self.assertEqual(body["messages"][0]["role"], "system")


if __name__ == "__main__":
    unittest.main()
