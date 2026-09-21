"""Titulares desde feeds RSS/Atom (solo biblioteca estándar).

Comprobar los feeds de config.yml:   python -m src.news
"""
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, List, Optional

ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"
USER_AGENT = "resumen-mercado/1.0 (uso personal)"


@dataclass
class Headline:
    source: str
    title: str
    link: str
    published: datetime  # siempre con zona horaria (UTC)
    score: int = 0


def _parse_date(text: Optional[str]) -> Optional[datetime]:
    if not text or not text.strip():
        return None
    text = text.strip()
    try:
        dt = parsedate_to_datetime(text)  # formato RSS (RFC 822)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))  # formato Atom (ISO 8601)
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_feed(xml_bytes: bytes, source: str) -> List[Headline]:
    """Extrae titulares de un feed RSS 2.0 o Atom. Ignora entradas sin título, enlace o fecha."""
    root = ET.fromstring(xml_bytes)
    out: List[Headline] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        date = _parse_date(item.findtext("pubDate") or item.findtext(DC + "date"))
        if title and link and date:
            out.append(Headline(source, title, link, date))
    for entry in root.iter(ATOM + "entry"):
        title = (entry.findtext(ATOM + "title") or "").strip()
        link_el = entry.find(ATOM + "link")
        link = (link_el.get("href", "") if link_el is not None else "").strip()
        date = _parse_date(entry.findtext(ATOM + "updated") or entry.findtext(ATOM + "published"))
        if title and link and date:
            out.append(Headline(source, title, link, date))
    return out


def fetch_url(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def _keyword_regex(keywords: List[str]):
    if not keywords:
        return None
    return re.compile(r"\b(" + "|".join(re.escape(k) for k in keywords) + r")\b", re.IGNORECASE)


def collect_headlines(news_cfg: dict, now: datetime,
                      fetcher: Callable[[str], bytes] = fetch_url) -> List[Headline]:
    """Reúne titulares recientes de todos los feeds, los puntúa y devuelve los mejores.

    `now` debe llevar zona horaria. Un feed que falle se ignora sin romper el resto.
    """
    cutoff = now - timedelta(days=news_cfg.get("days", 7))
    rx = _keyword_regex(news_cfg.get("keywords", []))
    per_feed = news_cfg.get("max_per_feed", 6)
    seen, pool = set(), []
    for feed in news_cfg.get("feeds", []):
        try:
            items = parse_feed(fetcher(feed["url"]), feed["name"])
        except Exception:  # noqa: BLE001 - un feed caído no debe tumbar el correo
            continue
        kept = []
        for h in items:
            if h.published < cutoff or h.published > now + timedelta(hours=12):
                continue
            hits = len({m.lower() for m in rx.findall(h.title)}) if rx else 0
            if feed.get("only_keywords") and hits == 0:
                continue
            key = re.sub(r"\W+", " ", h.title.lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            h.score = hits + (2 if feed.get("priority") else 0)
            kept.append(h)
        kept.sort(key=lambda h: (h.score, h.published), reverse=True)
        pool.extend(kept[:per_feed])
    pool.sort(key=lambda h: (h.score, h.published), reverse=True)
    return pool[: news_cfg.get("max_total", 12)]


def check_feeds(news_cfg: dict, now: datetime) -> None:
    """Imprime el estado de cada feed para validar las URLs."""
    cutoff = now - timedelta(days=news_cfg.get("days", 7))
    for feed in news_cfg.get("feeds", []):
        try:
            items = parse_feed(fetch_url(feed["url"]), feed["name"])
            recent = sum(1 for h in items if h.published >= cutoff)
            print(f"OK    {feed['name']}: {len(items)} titulares, {recent} de los últimos {news_cfg.get('days', 7)} días")
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR {feed['name']}: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    from .data import load_config

    check_feeds(load_config().get("news", {}), datetime.now(timezone.utc))
