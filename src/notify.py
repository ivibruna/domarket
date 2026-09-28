"""Aviso de fallo del envío semanal: se ejecuta solo si algún paso anterior del workflow
falla (`if: failure()`), para que un fallo silencioso no pase desapercibido.

Uso: python -m src.notify
Variables de entorno esperadas: SMTP_USER, SMTP_PASSWORD, MAIL_TO (las mismas del envío
normal) y, si están disponibles (GitHub Actions las define automáticamente),
GITHUB_SERVER_URL, GITHUB_REPOSITORY, GITHUB_RUN_ID para enlazar al log del fallo.
"""
import os

from .env import load_dotenv
from .send import build_message, mail_settings_from_env, send_email


def run_url() -> str:
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return "(ejecútalo localmente para ver el error: no hay enlace disponible)"


def main() -> None:
    load_dotenv()
    cfg = mail_settings_from_env()
    body = (
        "El envío semanal de DOMarket Weekly Brief ha fallado y no se ha enviado el correo "
        f"de esta semana.\n\nDetalle del fallo (log completo):\n{run_url()}\n\n"
        "Este aviso es automático."
    )
    msg = build_message(
        subject="⚠️ Fallo en el envío de DOMarket Weekly Brief",
        html=f"<p>{body.replace(chr(10), '<br>')}</p>",
        text=body,
        sender=cfg["user"],
        to=cfg["to"],
        sender_name=cfg["sender_name"],
    )
    send_email(msg, cfg["user"], cfg["password"], cfg["host"], cfg["port"])
    print("Aviso de fallo enviado.")


if __name__ == "__main__":
    main()
