"""Genera el resumen semanal. Por defecto solo guarda una vista previa; con --send lo envía.

Uso:
    python -m src.main --demo            # vista previa con datos ficticios
    python -m src.main                   # vista previa con datos reales
    python -m src.main --demo --send     # envía un correo de PRUEBA con datos ficticios
    python -m src.main --send            # envía el correo real
    Añade --ai para incluir el análisis redactado por el modelo de IA (necesita Ollama en marcha).
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path

from .data import fetch_all, load_config
from .demo import demo_data, demo_headlines, demo_summary
from .env import load_dotenv
from .news import collect_headlines
from .render import render_html, render_text
from .summary import generate_summary
from .send import build_message, mail_settings_from_env, send_email


def _all_failed(data: dict) -> bool:
    quotes = [q for section in data.values() for q in section]
    return bool(quotes) and all(q.metrics is None for q in quotes)


def main() -> None:
    ap = argparse.ArgumentParser(description="Resumen semanal de mercado")
    ap.add_argument("--demo", action="store_true", help="usar datos ficticios")
    ap.add_argument("--send", action="store_true", help="enviar por correo (por defecto, solo vista previa)")
    ap.add_argument("--ai", action="store_true", help="añadir el análisis redactado por el modelo de IA")
    ap.add_argument("--config", default="config.yml")
    ap.add_argument("--out", default="preview.html")
    args = ap.parse_args()

    load_dotenv()
    cfg = {}
    if args.demo:
        data, headlines = demo_data(), demo_headlines()
    else:
        cfg = load_config(args.config)
        data = fetch_all(cfg)
        headlines = collect_headlines(cfg.get("news", {}), datetime.now(timezone.utc))
    if not args.demo and _all_failed(data):
        raise SystemExit("No se pudo obtener ningún dato: no se genera ni se envía el correo.")

    now = datetime.now()
    analysis = None
    if args.ai:
        analysis = demo_summary() if args.demo else generate_summary(data, headlines, now, cfg.get("summary"))
    html = render_html(data, now, demo=args.demo, headlines=headlines, analysis=analysis)
    text = render_text(data, now, demo=args.demo, headlines=headlines, analysis=analysis)
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"Vista previa guardada en {args.out}")

    if args.send:
        cfg = mail_settings_from_env()
        prefix = "[EJEMPLO] " if args.demo else ""
        subject = f"{prefix}Resumen semanal de mercado · {now.strftime('%d/%m/%Y')}"
        msg = build_message(subject, html, text, cfg["user"], cfg["to"])
        send_email(msg, cfg["user"], cfg["password"], cfg["host"], cfg["port"])
        print(f"Correo enviado a {len(cfg['to'])} destinatario(s).")


if __name__ == "__main__":
    main()
