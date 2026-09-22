"""Resumen tipo analista redactado por un modelo de lenguaje (por defecto, Gemma 4 con llama.cpp).

El modelo solo recibe datos ya calculados y titulares: no puede consultar nada por su cuenta.
Probar sin enviar correo:   python -m src.summary
"""
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from typing import Callable, List, Optional

from .render import fmt_date_long, fmt_num, fmt_pct

DEFAULT_MODEL = "gemma-4-E4B-it-Q4_K_M"

SYSTEM_PROMPT = """Eres un analista financiero que escribe un resumen semanal para un inversor particular en España.

Reglas obligatorias:
1. Escribe en español, con tono profesional y claro, en unas 220-280 palabras.
2. Usa SOLO los datos y titulares que se te dan. No inventes cifras, fechas, eventos ni causas. Si algo no consta, no lo menciones.
3. Cuando cites un hecho que venga de un titular, atribúyelo a su fuente (por ejemplo, "según CNBC"), y no lo generalices ni lo reinterpretes más allá de lo que dice el titular. En especial, si un titular describe una decisión de una institución (un banco central, un gobierno, un organismo), no se la atribuyas a una sola persona salvo que el propio titular lo haga explícitamente: di "el BCE decidió...", no "su presidente decidió...", a menos que el titular hable solo de esa persona.
4. Las variaciones porcentuales de la tabla de MERCADO son reales: puedes citarlas tal cual.
5. En "Cómo llegamos" repasa TODOS los activos de la tabla MERCADO, aunque sea en una frase breve para los que apenas se han movido; no te centres solo en los que más subieron o bajaron. Agrupa los que se muevan por motivos parecidos.
6. En "Qué vigilar esta semana" da preferencia a titulares que hablen de algo que vaya a pasar (una reunión, una decisión, una fecha, unos datos que se publiquen próximamente), no solo a lo ya ocurrido. Si ningún titular anticipa algo así, dilo explícitamente en vez de rellenar con noticias pasadas.
7. No des recomendaciones de compra o venta ni predicciones de precios.
8. Formato: exactamente tres párrafos separados por una línea en blanco. Cada párrafo empieza por su etiqueta: "Cómo llegamos:", "Qué vigilar esta semana:", "Riesgos:". Texto plano, sin listas, sin markdown y sin emojis."""


def build_prompt(data: dict, headlines: list, now: datetime) -> str:
    """Construye el mensaje de usuario. Solo incluye el mercado general (no tu seguimiento personal)."""
    lines = [
        f"Fecha: {fmt_date_long(now)}",
        "",
        "MERCADO (último precio | variación 1 semana | variación 1 mes):",
    ]
    for q in data.get("general", []):
        if q.metrics is None:
            continue
        m = q.metrics
        lines.append(f"- {q.name}: {fmt_num(m.last)} | 1 sem {fmt_pct(m.change_1w)} | 1 mes {fmt_pct(m.change_1m)}")
    lines += ["", "TITULARES RECIENTES ([fuente, fecha] titular):"]
    if headlines:
        lines += [f"- [{h.source}, {h.published.strftime('%d/%m')}] {h.title}" for h in headlines]
    else:
        lines.append("- (ninguno disponible)")
    lines += ["", "Escribe el resumen siguiendo las reglas."]
    return "\n".join(lines)


def clean_summary(text: str) -> str:
    """Limpia la salida del modelo y comprueba que tiene una forma razonable."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"^[ \t]*#+[ \t]*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    paragraphs = [p for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) < 2 or not (300 <= len(text) <= 3000):
        raise ValueError(f"Salida del modelo con forma inesperada ({len(paragraphs)} párrafos, {len(text)} caracteres)")
    return text


def ollama_generate(system: str, prompt: str, model: str, host: str = "http://127.0.0.1:11434",
                    num_ctx: int = 6144, temperature: float = 0.3, max_tokens: int = 700,
                    timeout: int = 1500) -> str:
    """Llama a la API local de Ollama. Con CPU puede tardar varios minutos."""
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {"num_ctx": num_ctx, "temperature": temperature, "num_predict": max_tokens},
    }).encode("utf-8")
    req = urllib.request.Request(f"{host}/api/chat", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read())
    return payload["message"]["content"]


def llamacpp_generate(system: str, prompt: str, model: str = "", host: Optional[str] = None,
                      temperature: float = 0.3, max_tokens: int = 700, timeout: int = 1500,
                      **_ignored) -> str:
    """Llama al servidor local de llama.cpp (llama-server), que expone una API tipo OpenAI."""
    host = host or os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8080")
    body = json.dumps({
        "model": model or "local",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode("utf-8")
    req = urllib.request.Request(f"{host}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read())
    return payload["choices"][0]["message"]["content"]


BACKENDS = {"ollama": ollama_generate, "llamacpp": llamacpp_generate}


def generate_summary(data: dict, headlines: list, now: datetime, summary_cfg: Optional[dict] = None,
                     generator: Optional[Callable] = None) -> Optional[str]:
    """Devuelve el resumen o None si algo falla (el correo sale igual, sin este bloque)."""
    cfg = summary_cfg or {}
    model = os.environ.get("SUMMARY_MODEL") or cfg.get("model", DEFAULT_MODEL)
    try:
        generator = generator or BACKENDS[cfg.get("backend", "llamacpp")]
        raw = generator(
            SYSTEM_PROMPT, build_prompt(data, headlines, now), model=model,
            num_ctx=cfg.get("num_ctx", 6144), temperature=cfg.get("temperature", 0.3),
            max_tokens=cfg.get("max_tokens", 700),
        )
        return clean_summary(raw)
    except Exception as exc:  # noqa: BLE001
        print(f"Aviso: no se pudo generar el resumen ({type(exc).__name__}: {exc})", file=sys.stderr)
        return None


if __name__ == "__main__":
    from .data import fetch_all, load_config
    from .news import collect_headlines

    cfg = load_config()
    data = fetch_all(cfg)
    headlines = collect_headlines(cfg.get("news", {}), datetime.now(timezone.utc))
    now = datetime.now()
    print("=== PROMPT ===")
    print(build_prompt(data, headlines, now))
    print("\n=== GENERANDO (puede tardar varios minutos en CPU) ===")
    start = time.time()
    result = generate_summary(data, headlines, now, cfg.get("summary"))
    print(f"\n=== RESULTADO ({time.time() - start:.0f} s) ===")
    print(result if result else "(sin resultado: revisa el aviso de arriba)")