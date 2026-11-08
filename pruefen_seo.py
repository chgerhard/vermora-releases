"""Suchmaschinen-Grundlagen der Seiten (Issue #1234, Freigabe Christian 2026-10-25).

Geprueft wird, was ohne Nachschlagen bei einer Suchmaschine pruefbar ist:

  - keine Seite ausser `404.html` traegt `noindex` (die Seite soll gefunden werden);
  - jede Seite hat `<title>`, Beschreibung, Canonical und Open-Graph-Angaben mit vorhandenem
    Bild (og:url gleich Canonical, Issue #1350); die Startseite zusaetzlich JSON-LD
    (`SoftwareApplication`, gueltiges JSON, ohne Preisangabe);
  - `robots.txt` erlaubt alles und nennt die Sitemap; `sitemap.xml` listet jede Seite
    (ohne 404) unter https://vermora.de/ und nichts, was es nicht gibt.

Die Seiten unter anleitung/ (mkdocs) sind ausgenommen, sie bringen ihre eigene Sitemap mit.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from xml.etree import ElementTree

from pruefen_html import attr as _attr, eigene_dateien, ohne_kommentare

BASIS = "https://vermora.de/"
_META_RE = re.compile(r"<meta\b([^>]*)>", re.IGNORECASE)
_LINK_RE = re.compile(r"<link\b([^>]*)>", re.IGNORECASE)
_LD_RE = re.compile(r'<script\s+type="application/ld\+json">(.*?)</script>', re.DOTALL | re.IGNORECASE)
_NOINDEX_ERLAUBT = ("404.html",)
OG_PLATZHALTER = "<!--og-->"


def og_einsetzen(roh: str, src: Path) -> str:
    """Setzt den gemeinsamen Open-Graph-Block (`assets/og-block.inc`) am Platzhalter ein.

    In `dist/` hat der Bau das schon getan (die Datei fehlt dort dann); in `src/` macht es
    diese Pruefung, damit der Guard den Block so sieht, wie ihn Besucher bekommen.
    """
    quelle = src / "assets" / "og-block.inc"
    if OG_PLATZHALTER not in roh or not quelle.is_file():
        return roh
    return roh.replace(OG_PLATZHALTER, quelle.read_text(encoding="utf-8").strip())


def _meta(roh: str, key: str, name: str) -> str | None:
    for m in _META_RE.finditer(roh):
        if (_attr(m.group(1), key) or "").lower() == name:
            return _attr(m.group(1), "content")
    return None


def _canonical(roh: str) -> str | None:
    for m in _LINK_RE.finditer(roh):
        if (_attr(m.group(1), "rel") or "").lower() == "canonical":
            return _attr(m.group(1), "href")
    return None


def _hat_favicon(roh: str) -> bool:
    for m in _LINK_RE.finditer(roh):
        if (_attr(m.group(1), "rel") or "").lower() == "icon" and (_attr(m.group(1), "href") or "") == "/assets/favicon.svg":
            return True
    return False


def pruefe_seo(src: Path, wurzel: Path) -> list[str]:
    funde: list[str] = []
    seiten = [p for p in eigene_dateien(src, "*.html")]
    urls: set[str] = set()
    for pfad in seiten:
        rel = pfad.relative_to(src).as_posix()
        roh = ohne_kommentare(og_einsetzen(pfad.read_text(encoding="utf-8"), src))
        robots = _meta(roh, "name", "robots") or ""
        if "noindex" in robots.lower() and rel not in _NOINDEX_ERLAUBT:
            funde.append(f"{rel} -- noindex: die Seite soll auffindbar sein (nur 404.html bleibt draussen)")
        if not _hat_favicon(roh):
            funde.append(f"{rel} -- Browsersymbol fehlt: <link rel=\"icon\" href=\"/assets/favicon.svg\" type=\"image/svg+xml\">")
        if rel in _NOINDEX_ERLAUBT:
            continue
        url = BASIS + ("" if rel == "index.html" else rel)
        urls.add(url)
        if not re.search(r"<title>\s*\S.*?</title>", roh, re.DOTALL):
            funde.append(f"{rel} -- <title> fehlt oder ist leer")
        if _canonical(roh) != url:
            funde.append(f"{rel} -- Canonical fehlt oder weicht ab (erwartet {url})")
        funde += _teilen(roh, rel, src, url, 70 if rel == "index.html" else 50)
        if rel == "index.html":
            funde += _startseite(roh)
    funde += _robots_sitemap(src, urls)
    return funde


def _teilen(roh: str, rel: str, src: Path, url: str, min_len: int) -> list[str]:
    """Beschreibung und Open-Graph-Angaben, die jede Seite braucht (Issue #1350)."""
    funde: list[str] = []
    desc = _meta(roh, "name", "description") or ""
    if not min_len <= len(desc) <= 170:
        funde.append(f"{rel} -- meta description {len(desc)} Zeichen, erwartet {min_len} bis 170")
    for prop in ("og:title", "og:description", "og:url", "og:image", "og:type"):
        if not _meta(roh, "property", prop):
            funde.append(f"{rel} -- {prop} fehlt")
    og_url = _meta(roh, "property", "og:url")
    if og_url and og_url != url:
        funde.append(f"{rel} -- og:url weicht vom Canonical ab (erwartet {url})")
    bild = _meta(roh, "property", "og:image") or ""
    if bild.startswith(BASIS) and not (src / bild[len(BASIS):]).is_file():
        funde.append(f"{rel} -- og:image zeigt auf fehlende Datei: {bild}")
    elif bild and not bild.startswith(BASIS):
        funde.append(f"{rel} -- og:image muss eine absolute Adresse unter https://vermora.de/ sein")
    if not _meta(roh, "name", "twitter:card"):
        funde.append(f"{rel} -- twitter:card fehlt")
    return funde


def _startseite(roh: str) -> list[str]:
    funde: list[str] = []
    ld = _LD_RE.search(roh)
    if not ld:
        return funde + ["index.html -- JSON-LD (SoftwareApplication) fehlt"]
    try:
        daten = json.loads(ld.group(1))
    except ValueError:
        return funde + ["index.html -- JSON-LD ist kein gueltiges JSON"]
    if daten.get("@type") != "SoftwareApplication":
        funde.append("index.html -- JSON-LD @type muss SoftwareApplication sein")
    if any(k in daten for k in ("offers", "price", "author", "creator")):
        funde.append("index.html -- JSON-LD ohne Preis- und Personenangaben (Leitplanke 1, Datenschutz)")
    return funde


def _robots_sitemap(src: Path, urls: set[str]) -> list[str]:
    funde: list[str] = []
    robots = src / "robots.txt"
    if not robots.is_file():
        funde.append("robots.txt fehlt")
    else:
        text = robots.read_text(encoding="utf-8")
        if re.search(r"^Disallow:\s*/\s*$", text, re.MULTILINE):
            funde.append("robots.txt sperrt die ganze Seite (Disallow: /)")
        if f"Sitemap: {BASIS}sitemap.xml" not in text:
            funde.append(f"robots.txt nennt {BASIS}sitemap.xml nicht")
    karte = src / "sitemap.xml"
    if not karte.is_file():
        return funde + ["sitemap.xml fehlt"]
    try:
        wurzel = ElementTree.fromstring(karte.read_text(encoding="utf-8"))
    except ElementTree.ParseError:
        return funde + ["sitemap.xml ist kein gueltiges XML"]
    eintraege = {e.text.strip() for e in wurzel.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc") if e.text}
    for url in sorted(urls - eintraege):
        funde.append(f"sitemap.xml -- Seite fehlt: {url}")
    for url in sorted(eintraege - urls):
        funde.append(f"sitemap.xml -- Eintrag ohne Seite: {url}")
    return funde
