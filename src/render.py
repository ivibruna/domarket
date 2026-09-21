"""Plantilla del correo semanal: HTML con estilos en línea + versión de texto plano."""
from datetime import datetime
from html import escape
from typing import List

from .data import Quote

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

GREEN, RED, GREY = "#1a7f37", "#cf222e", "#57606a"

DISCLAIMER = (
    "Información con fines informativos; no constituye asesoramiento financiero ni una "
    "recomendación de compra o venta. Datos de Yahoo Finance (pueden tener retraso o errores). "
    "Correo generado automáticamente."
)


# ---------- formato ----------
def fmt_num(x, decimals=None) -> str:
    """Número con formato español (1.234,56). 4 decimales si el valor es < 2."""
    if x is None:
        return "—"
    if decimals is None:
        decimals = 4 if abs(x) < 2 else 2
    s = f"{x:,.{decimals}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def fmt_pct(x) -> str:
    if x is None:
        return "—"
    return f"{x:+.2f} %".replace(".", ",")


def fmt_date_long(d: datetime) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]} de {d.year}"


def _pct_html(x) -> str:
    """Porcentaje con color y flecha (la flecha evita depender solo del color)."""
    if x is None:
        return f'<span style="color:{GREY}">—</span>'
    r = round(x, 2)
    color = GREEN if r > 0 else RED if r < 0 else GREY
    arrow = "▲" if r > 0 else "▼" if r < 0 else "•"
    return f'<span style="color:{color}">{arrow} {fmt_pct(x)}</span>'


# ---------- bloques HTML ----------
_TD = "padding:8px 6px;border-bottom:1px solid #eaeef2;font-size:13px;"


def _table(headers: List[str], rows: List[str]) -> str:
    head = "".join(
        f'<th style="padding:6px;font-size:11px;color:{GREY};text-align:{"left" if i == 0 else "right"};'
        f'border-bottom:2px solid #d0d7de;text-transform:uppercase;">{escape(h)}</th>'
        for i, h in enumerate(headers)
    )
    return (
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        f'style="border-collapse:collapse;"><tr>{head}</tr>{"".join(rows)}</table>'
    )


def _error_row(q: Quote, ncols: int) -> str:
    return (
        f'<tr><td style="{_TD}"><strong>{escape(q.name)}</strong></td>'
        f'<td colspan="{ncols - 1}" style="{_TD}text-align:right;white-space:nowrap;color:{GREY};">Datos no disponibles</td></tr>'
    )


def _general_rows(quotes: List[Quote]) -> List[str]:
    rows = []
    for q in quotes:
        if q.metrics is None:
            rows.append(_error_row(q, 4))
            continue
        m = q.metrics
        rows.append(
            f'<tr><td style="{_TD}"><strong>{escape(q.name)}</strong></td>'
            f'<td style="{_TD}text-align:right;white-space:nowrap;">{fmt_num(m.last)}</td>'
            f'<td style="{_TD}text-align:right;white-space:nowrap;">{_pct_html(m.change_1w)}</td>'
            f'<td style="{_TD}text-align:right;white-space:nowrap;">{_pct_html(m.change_1m)}</td></tr>'
        )
    return rows


def _watch_rows(quotes: List[Quote]) -> List[str]:
    rows = []
    for q in quotes:
        if q.metrics is None:
            rows.append(_error_row(q, 7))
            continue
        m = q.metrics
        rows.append(
            f'<tr><td style="{_TD}"><strong>{escape(q.name)}</strong><br>'
            f'<span style="font-size:11px;color:{GREY};">{escape(q.symbol)} · dato a {m.last_date.strftime("%d/%m/%Y")}</span></td>'
            f'<td style="{_TD}text-align:right;white-space:nowrap;">{fmt_num(m.last)}</td>'
            f'<td style="{_TD}text-align:right;white-space:nowrap;">{_pct_html(m.change_1w)}</td>'
            f'<td style="{_TD}text-align:right;white-space:nowrap;">{_pct_html(m.change_1m)}</td>'
            f'<td style="{_TD}text-align:right;white-space:nowrap;">{_pct_html(m.from_high_pct)}</td>'
            f'<td style="{_TD}text-align:right;white-space:nowrap;">{fmt_num(m.high_52w)}</td>'
            f'<td style="{_TD}text-align:right;white-space:nowrap;">{fmt_num(m.low_52w)}</td></tr>'
        )
    return rows


def _section(title: str, body: str) -> str:
    return (
        f'<h2 style="font-size:16px;margin:28px 0 8px;color:#1f2328;">{escape(title)}</h2>{body}'
    )


def _headlines_html(headlines) -> str:
    items = []
    for h in headlines:
        link = escape(h.link, quote=True) if h.link.startswith(("http://", "https://")) else "#"
        items.append(
            f'<li style="margin:0 0 8px;font-size:13px;line-height:1.4;">'
            f'<a href="{link}" style="color:#0969da;text-decoration:none;">{escape(h.title)}</a><br>'
            f'<span style="font-size:11px;color:{GREY};">{escape(h.source)} · {h.published.strftime("%d/%m")}</span></li>'
        )
    return f'<ul style="margin:0;padding-left:18px;">{"".join(items)}</ul>'


AI_NOTE = ("Texto generado automáticamente por un modelo de IA a partir de los datos y titulares de este "
           "correo; puede contener errores.")


def _analysis_html(text: str) -> str:
    paragraphs = []
    for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
        label, sep, rest = para.partition(":")
        if sep and len(label) <= 40:
            para_html = f"<strong>{escape(label)}:</strong>{escape(rest)}"
        else:
            para_html = escape(para)
        paragraphs.append(f'<p style="margin:0 0 10px;font-size:14px;line-height:1.5;">{para_html}</p>')
    note = f'<p style="margin:0;font-size:11px;color:{GREY};font-style:italic;">{escape(AI_NOTE)}</p>'
    return "".join(paragraphs) + note


def render_html(data: dict, now: datetime, demo: bool = False, headlines=None, analysis=None) -> str:
    banner = ""
    if demo:
        banner = (
            '<div style="background:#fff8c5;border:1px solid #d4a72c;padding:10px 12px;margin-bottom:16px;'
            'font-size:13px;color:#1f2328;"><strong>DATOS DE EJEMPLO</strong> — cifras inventadas '
            "solo para ver el diseño. No son reales.</div>"
        )
    general = _section(
        "Mercado general",
        _table(["Activo", "Último", "1 sem.", "1 mes"], _general_rows(data.get("general", []))),
    )
    analysis_html = _section("Análisis de la semana", _analysis_html(analysis)) if analysis else ""
    news = _section("Titulares de la semana", _headlines_html(headlines)) if headlines else ""
    watch = ""
    if data.get("watchlist"):
        watch = _section(
            "Mi seguimiento",
            _table(
                ["Valor", "Último", "1 sem.", "1 mes", "vs. máx. 52s", "Máx. 52s", "Mín. 52s"],
                _watch_rows(data["watchlist"]),
            ),
        )
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Resumen semanal de mercado</title></head>
<body style="margin:0;padding:24px 8px;background:#f6f8fa;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#1f2328;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center">
<table role="presentation" width="640" cellspacing="0" cellpadding="0" style="max-width:640px;width:100%;background:#ffffff;border:1px solid #d0d7de;">
<tr><td style="padding:24px;">
{banner}
<h1 style="font-size:20px;margin:0;">Resumen semanal de mercado</h1>
<p style="margin:4px 0 0;font-size:13px;color:{GREY};">{escape(fmt_date_long(now))}</p>
{analysis_html}
{general}
{news}
{watch}
<p style="margin:28px 0 0;padding-top:12px;border-top:1px solid #eaeef2;font-size:11px;color:{GREY};">{escape(DISCLAIMER)}</p>
</td></tr></table>
</td></tr></table>
</body></html>
"""


# ---------- versión de texto ----------
def render_text(data: dict, now: datetime, demo: bool = False, headlines=None, analysis=None) -> str:
    lines = []
    if demo:
        lines.append("*** DATOS DE EJEMPLO: cifras inventadas, no reales ***\n")
    lines += ["RESUMEN SEMANAL DE MERCADO", fmt_date_long(now)]
    if analysis:
        lines += ["", "ANÁLISIS DE LA SEMANA", analysis, f"({AI_NOTE})"]
    lines += ["", "MERCADO GENERAL"]
    for section, title in (("general", None), ("watchlist", "MI SEGUIMIENTO")):
        if title:
            lines += ["", title]
        for q in data.get(section, []):
            if q.metrics is None:
                lines.append(f"- {q.name}: datos no disponibles")
            else:
                m = q.metrics
                lines.append(
                    f"- {q.name}: {fmt_num(m.last)} (1 sem. {fmt_pct(m.change_1w)}, 1 mes {fmt_pct(m.change_1m)})"
                )
    if headlines:
        lines += ["", "TITULARES DE LA SEMANA"]
        lines += [f"- {h.title} ({h.source}, {h.published.strftime('%d/%m')}) {h.link}" for h in headlines]
    lines += ["", DISCLAIMER]
    return "\n".join(lines)
