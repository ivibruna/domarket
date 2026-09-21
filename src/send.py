"""Envío del correo por SMTP (por defecto Gmail, SSL en el puerto 465)."""
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid


def mail_settings_from_env() -> dict:
    """Lee la configuración del entorno. Los secretos nunca van en el código."""
    missing = [k for k in ("SMTP_USER", "SMTP_PASSWORD", "MAIL_TO") if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Faltan variables de entorno: {', '.join(missing)}")
    return {
        "user": os.environ["SMTP_USER"].strip(),
        # Google muestra la contraseña de aplicación con espacios: se ignoran
        "password": os.environ["SMTP_PASSWORD"].replace(" ", ""),
        "to": [a.strip() for a in os.environ["MAIL_TO"].split(",") if a.strip()],
        "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.environ.get("SMTP_PORT", "465")),
    }


def build_message(subject: str, html: str, text: str, sender: str, to: list) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid()
    msg.set_content(text)                      # versión de texto plano
    msg.add_alternative(html, subtype="html")  # versión HTML
    return msg


def send_email(msg: EmailMessage, user: str, password: str,
               host: str = "smtp.gmail.com", port: int = 465) -> None:
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
